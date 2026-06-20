"""
AdaptiveAI — LangGraph Orchestration Service
Flow: orchestrator → [specialist agents in parallel] → aggregator → END
"""

import operator
import os
from typing import Annotated, List, TypedDict

from groq import Groq
from langgraph.graph import StateGraph, END

from services.agent_router import DeepAgentRouter
from services.agents import AGENTS
from services.rag.rag_router import RAGRouter
from config import Config


# 1. State Definition
class AgentState(TypedDict):
    message:         str
    profile:         dict
    knowledge_state: dict
    chat_history:    list
    analysis:        dict
    next_steps:      List[str]
    # operator.add lets multiple parallel agents append without overwriting
    agent_outputs:   Annotated[List[dict], operator.add]
    final_response:  dict


# 2. Orchestrator node
def orchestrator_node(state: AgentState) -> dict:
    """
    Analyses the message and decides routing.
    Uses user_intent + question_type from the enhanced analyzer
    so 'exam as context' never triggers quiz mode.
    """
    client = Groq(api_key=os.getenv('GROQ_API_KEY'))
    analysis = DeepAgentRouter.analyze(None, state['message'], state['knowledge_state'])

    topics      = analysis.get('topics', [])
    qtype       = analysis.get('question_type', 'general')
    user_intent = analysis.get('user_intent', 'learning')

    
    msg_lower = state['message'].lower()
    _QUIZ_COMMANDS = [
        r'\b(give me a quiz|quiz me|test me|start a quiz|can i have a quiz)\b',
        r'\b(quiz time|exam time|practice questions|give me questions)\b',
        r'\b(assess me|examine me|let\'?s do a quiz)\b',
    ]
    import re
    llm_failed = not analysis.get('langchain', {}).get('used') and qtype != 'quiz'
    if llm_failed and any(re.search(p, msg_lower) for p in _QUIZ_COMMANDS):
        user_intent = 'testing'
        qtype       = 'quiz'

    # Quiz mode ONLY when LLM explicitly says the user wants to be tested.
    # Keyword "quiz" alone is NOT enough — the LLM must confirm user_intent='testing'.
    is_quiz = (user_intent == 'testing') or (qtype == 'quiz')

    next_steps: List[str] = []

    if is_quiz:
        # Strict isolation — no specialist agents leak in
        next_steps = ['quiz_generator']
    else:
        # Route to relevant specialist agents (can be multiple → parallel)
        if any(t in topics for t in ['machine_learning', 'regression', 'classification',
                                      'clustering', 'ensemble', 'model_evaluation',
                                      'feature_engineering', 'scikit_learn']):
            next_steps.append('ml_agent')

        if any(t in topics for t in ['deep_learning', 'neural_networks', 'cnn', 'rnn',
                                      'transformers', 'backpropagation', 'activation_functions',
                                      'transfer_learning', 'gan', 'pytorch', 'tensorflow']):
            next_steps.append('dl_agent')

        if any(t in topics for t in ['data_science', 'statistics', 'data_visualization',
                                      'pandas', 'numpy', 'sql', 'eda']):
            next_steps.append('ds_agent')

        # Default fallback
        if not next_steps:
            next_steps = ['ml_agent']

    return {
        'analysis':   analysis,
        'next_steps': next_steps,
    }


# 3. Specialist Agent node

# Map node names → AGENTS keys
_AGENT_KEY_MAP = {
    'ml_agent':       'machine_learning',
    'dl_agent':       'deep_learning',
    'ds_agent':       'data_science',
    'quiz_generator': 'machine_learning',   # quiz uses ML agent persona as base
}


def call_specialist_agent(state: AgentState, node_name: str) -> dict:
    """
    Calls Groq using the correct agent persona.
    node_name is the LangGraph node name (e.g. 'ml_agent').
    """
    agent_key = _AGENT_KEY_MAP.get(node_name, 'machine_learning')
    client    = Groq(api_key=os.getenv('GROQ_API_KEY'))

    analysis  = state.get('analysis', {})
    recs      = analysis.get('recommendations', {})

    # Quiz node gets a different system instruction
    if node_name == 'quiz_generator':
        system_prompt = (
            f"{AGENTS[agent_key]['system']}\n\n"
            "The student has requested a quiz. Generate 5 multiple-choice questions "
            "based on the topic they mentioned. Format each question clearly with "
            "options A, B, C, D and mark the correct answer at the end."
        )
    else:
        # Retrieve RAG context if enabled
        rag_context = None
        if Config.USE_RAG:
            try:
                rag_result = RAGRouter.retrieve(
                    user_message=state['message'],
                    agent_key=agent_key
                )
                if rag_result:
                    rag_context = rag_result.get('formatted_context', '') or None
            except Exception as e:
                import logging
                logging.getLogger(__name__).warning(f"RAG retrieval failed in LangGraph: {e}")
                
        system_prompt = DeepAgentRouter.build_system_prompt(
            agent_key=agent_key,
            profile=state.get('profile', {}),
            knowledge_state=state.get('knowledge_state', {}),
            analysis=analysis,
            forced_mode=recs.get('tutoring_mode', 'direct'),
            forced_reason=recs.get('mode_reason', ''),
            rag_context=rag_context,
        )

    messages = [{'role': 'system', 'content': system_prompt}]

    # Include last 6 chat history messages for context
    for m in (state.get('chat_history') or [])[-6:]:
        messages.append({
            'role':    m.get('role', 'user'),
            'content': m.get('content', ''),
        })

    messages.append({'role': 'user', 'content': state['message']})

    try:
        completion = client.chat.completions.create(
            model='llama-3.3-70b-versatile',
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            top_p=0.9,
        )
        content     = completion.choices[0].message.content
        tokens_used = completion.usage.total_tokens if completion.usage else 0
        return {
            'agent_outputs': [{
                'agent':       agent_key,
                'node':        node_name,
                'content':     content,
                'tokens_used': tokens_used,
                'success':     True,
            }]
        }
    except Exception as e:
        return {
            'agent_outputs': [{
                'agent':   agent_key,
                'node':    node_name,
                'content': f'Agent error: {e}',
                'success': False,
            }]
        }


# 4. Aggregator node
def aggregator_node(state: AgentState) -> dict:
    """
    Merges outputs from one or more specialist agents into
    a single cohesive response.
    """
    outputs = state.get('agent_outputs', [])

    if not outputs:
        return {
            'final_response': {
                'success':         False,
                'response':        'No agent produced a response.',
                'agents_involved': [],
                'analysis':        state.get('analysis', {}),
            }
        }

    if len(outputs) == 1:
        # Single agent — return directly, no synthesis needed
        final_text = outputs[0]['content']
    else:
        # Multiple agents — synthesise into one fluent response
        combined_raw = '\n\n'.join(
            f"[{o['node'].upper()} response]:\n{o['content']}"
            for o in outputs
        )

        client = Groq(api_key=os.getenv('GROQ_API_KEY'))
        synthesis_prompt = (
            'You are an expert orchestrator. Below are responses from different specialist AI agents '
            'answering parts of a student\'s question. Merge them into a single, cohesive, and fluid '
            'response. Remove redundancies, ensure smooth transitions, and maintain one consistent voice.\n\n'
            f'Student question: {state["message"]}\n\n'
            f'Agent responses:\n{combined_raw}'
        )

        try:
            completion = client.chat.completions.create(
                model='llama-3.3-70b-versatile',
                messages=[{'role': 'system', 'content': synthesis_prompt}],
                temperature=0.3,
                max_tokens=1500,
            )
            final_text = completion.choices[0].message.content
        except Exception as e:
            # Fallback: just concatenate if synthesis fails
            final_text = '\n\n'.join(o['content'] for o in outputs)

    return {
        'final_response': {
            'success':         True,
            'response':        final_text,
            'agents_involved': [o['agent'] for o in outputs],
            'nodes_involved':  [o['node'] for o in outputs],
            'analysis':        state.get('analysis', {}),
            'user_intent':     state.get('analysis', {}).get('user_intent', 'learning'),
            'tutoring_mode':   state.get('analysis', {}).get('recommendations', {}).get('tutoring_mode', 'direct'),
        }
    }


# 5. Router Function
def route_to_agents(state: AgentState) -> List[str]:
    """Tells LangGraph which nodes to run next (can be multiple → parallel)."""
    return state.get('next_steps', ['ml_agent'])


# 6. Build the Graph
workflow = StateGraph(AgentState)

# Nodes
workflow.add_node('orchestrator',  orchestrator_node)
workflow.add_node('ml_agent',      lambda s: call_specialist_agent(s, 'ml_agent'))
workflow.add_node('dl_agent',      lambda s: call_specialist_agent(s, 'dl_agent'))
workflow.add_node('ds_agent',      lambda s: call_specialist_agent(s, 'ds_agent'))
workflow.add_node('quiz_generator', lambda s: call_specialist_agent(s, 'quiz_generator'))
workflow.add_node('aggregator',    aggregator_node)

# Entry point
workflow.set_entry_point('orchestrator')

# Conditional edges: orchestrator → one or more specialist agents
workflow.add_conditional_edges(
    'orchestrator',
    route_to_agents,
    {
        'ml_agent':       'ml_agent',
        'dl_agent':       'dl_agent',
        'ds_agent':       'ds_agent',
        'quiz_generator': 'quiz_generator',
    }
)

# All specialist agents → aggregator
workflow.add_edge('ml_agent',       'aggregator')
workflow.add_edge('dl_agent',       'aggregator')
workflow.add_edge('ds_agent',       'aggregator')
workflow.add_edge('quiz_generator', 'aggregator')

# Final edge
workflow.add_edge('aggregator', END)
app = workflow.compile()
