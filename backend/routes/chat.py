"""
AdaptiveAI - Chat Routes
Handles all chat-related API endpoints
"""

from flask import Blueprint, request, jsonify
from models.user import User
from services.ai_agents import AIService
from database import Database
from datetime import datetime
import os
from groq import Groq

chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/message', methods=['POST'])
def send_message():
    """
    Handle incoming chat messages and return AI response
    
    Expected payload:
    {
        "user_id": "user-uuid",
        "message": "What is gradient descent?",
        "profile": { ... learner profile ... },
        "chat_history": [ ... previous messages ... ]
    }
    """
    data = request.get_json()
    
    user_id = data.get('user_id')
    message = data.get('message')
    profile = data.get('profile')
    chat_history = data.get('chat_history', [])
    
    if not message:
        return jsonify({"error": "Message is required"}), 400
    
    # Generate AI response using the agent system
    result = AIService.generate_response(
        query=message,
        profile=profile,
        chat_history=chat_history
    )
    
    if result.get('success'):
        # Store interaction in database if user is logged in
        if user_id:
            try:
                interactions = Database.get_collection('interactions')
                interactions.insert_one({
                    "user_id": user_id,
                    "message": message,
                    "response": result['response'],
                    "agent": result['agent'],
                    "tokens_used": result.get('tokens_used', 0),
                    "timestamp": datetime.utcnow().isoformat()
                })
            except Exception as e:
                print(f"Failed to log interaction: {e}")
        
        return jsonify({
            "success": True,
            "response": result['response'],
            "agent": result['agent'],
            "agent_name": result['agent'].replace('_', ' ').title()
        }), 200
    else:
        return jsonify({
            "success": False,
            "error": result.get('error', 'Unknown error occurred')
        }), 500


@chat_bp.route('/history/<user_id>', methods=['GET'])
def get_chat_history(user_id):
    """Get chat history for a specific user"""
    
    try:
        interactions = Database.get_collection('interactions')
        history = list(interactions.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(50))
        
        return jsonify({
            "success": True,
            "history": history
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@chat_bp.route('/analyze-progression', methods=['POST'])
def analyze_progression():
    """
    Analyze if student should level up/down
    Can be called by n8n webhook or frontend
    """
    data = request.get_json()
    
    quiz_analytics = data.get('quiz_analytics')
    chat_history = data.get('chat_history', [])
    
    result = AIService.analyze_level_progression(quiz_analytics, chat_history)
    
    return jsonify(result), 200


@chat_bp.route('/groq', methods=['POST'])
def chat_groq():
    """
    Handle chat messages using Groq API with Llama3-70b model
    
    Expected payload:
    {
        "message": "Explain gradient descent",
        "profile": {
            "skill_level": "intermediate",
            "learning_tone": "encouraging",
            "strongest_domain": "mathematics"
        },
        "chat_history": [
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ]
    }
    """
    try:
        data = request.get_json()
        message = data.get('message')
        profile = data.get('profile', {})
        chat_history = data.get('chat_history', [])
        
        if not message:
            return jsonify({"error": "Message is required"}), 400
        
        # Initialize Groq client
        api_key = os.getenv('GROQ_API_KEY')
        if not api_key:
            return jsonify({"error": "Groq API key not configured"}), 500
        
        client = Groq(api_key=api_key)
        
        # Build personalized system prompt based on user profile
        skill_level = profile.get('skill_level', profile.get('python', 'intermediate'))
        learning_tone = profile.get('learning_tone', profile.get('tone', 'Friendly')).lower()
        strongest_domain = profile.get('strongest_domain', 'general')
        conversation_count = profile.get('conversation_count', 0)
        
        # === PHASE 1+2+3+4: Enriched adaptive prompt ===
        # Pull in behavioral analytics, knowledge state, misconceptions
        strong_topics = profile.get('strong_topics', [])
        weak_topics = profile.get('weak_topics', [])
        ba = profile.get('behavioral_analytics', {})
        knowledge_state = profile.get('knowledge_state', {})
        misconceptions = profile.get('misconceptions', {})
        conversation_prefs = profile.get('conversation_preferences', {})
        adaptations = profile.get('current_adaptations', {})
        
        # Build mastery context
        topics_discussed = ba.get('topics_discussed', {})
        mastery_lines = []
        for topic, tdata in topics_discussed.items():
            if isinstance(tdata, dict) and tdata.get('count', 0) >= 2:
                cl = tdata.get('complexity_levels', {})
                total = sum(cl.values()) if cl else tdata.get('count', 1)
                adv = cl.get('advanced', 0)
                score = round((adv * 0.9 + cl.get('intermediate', 0) * 0.5 + cl.get('beginner', 0) * 0.2) / max(total, 1), 2)
                mastery_lines.append(f"  - {topic}: {score:.0%} mastery ({tdata.get('count', 0)} interactions)")
        
        # Active misconceptions
        misconception_lines = []
        for topic, mdata in misconceptions.items():
            if isinstance(mdata, dict) and not mdata.get('corrected', False):
                misconception_lines.append(f"  - {topic}: {mdata.get('detail', 'unclear understanding')}")
        
        # Effective level from rolling complexity average
        complexity_dist = ba.get('complexity_distribution', {})
        total_q = sum(complexity_dist.values()) if complexity_dist else 0
        if total_q >= 5:
            adv_ratio = complexity_dist.get('advanced', 0) / total_q
            beg_ratio = complexity_dist.get('beginner', 0) / total_q
            effective_level = 'Advanced' if adv_ratio > 0.5 else ('Beginner' if beg_ratio > 0.5 else 'Intermediate')
        else:
            effective_level = skill_level
        
        # Style preferences
        style_notes = []
        if conversation_prefs.get('prefers_examples'):
            style_notes.append('real-world examples')
        if conversation_prefs.get('prefers_code'):
            style_notes.append('code snippets')
        if conversation_prefs.get('prefers_analogies'):
            style_notes.append('analogies')
        style_pref_str = f"Include {', '.join(style_notes)} when possible." if style_notes else ''
        
        # Tone & length preferences — detect from BOTH saved profile AND chat history
        # This ensures preferences are caught even if frontend JS is cached
        preferred_tone = conversation_prefs.get('preferred_tone', '')
        preferred_length = conversation_prefs.get('preferred_length', '')
        
        # Scan chat history for preference-setting messages (backend-side detection)
        tone_keywords = {
            'friendly': ['friendly', 'casual', 'informal', 'chill', 'relaxed'],
            'formal': ['formal', 'professional', 'academic', 'serious']
        }
        length_keywords = {
            'short': ['short', 'brief', 'concise', 'to the point', 'keep it short', 'shorter', 'quick', 'don\'t be too long', 'not too long'],
            'detailed': ['detailed', 'in depth', 'elaborate', 'go deeper', 'explain more', 'thorough']
        }
        
        for msg in chat_history:
            if msg.get('role') == 'user':
                content_lower = msg.get('content', '').lower()
                # Only scan messages that look like preference-setting requests
                if any(trigger in content_lower for trigger in ['keep', 'want', 'prefer', 'make it', 'be more', 'can you', 'please', 'always', 'tone', 'style']):
                    for tone_val, keywords in tone_keywords.items():
                        if any(kw in content_lower for kw in keywords):
                            preferred_tone = tone_val
                    for len_val, keywords in length_keywords.items():
                        if any(kw in content_lower for kw in keywords):
                            preferred_length = len_val
        
        # Also check the current message
        msg_lower = message.lower()
        if any(trigger in msg_lower for trigger in ['keep', 'want', 'prefer', 'make it', 'be more', 'can you', 'please', 'always', 'tone', 'style']):
            for tone_val, keywords in tone_keywords.items():
                if any(kw in msg_lower for kw in keywords):
                    preferred_tone = tone_val
            for len_val, keywords in length_keywords.items():
                if any(kw in msg_lower for kw in keywords):
                    preferred_length = len_val
        
        # Build instructions from detected preferences
        tone_instruction = ''
        if preferred_tone == 'friendly':
            tone_instruction = 'CRITICAL RULE: The student EXPLICITLY asked for a FRIENDLY, casual tone. Be warm, use contractions, talk like a helpful friend. This overrides all other tone settings.'
        elif preferred_tone == 'formal':
            tone_instruction = 'CRITICAL RULE: The student EXPLICITLY asked for a FORMAL, professional tone. Be precise and academic. This overrides all other tone settings.'
        
        length_instruction = ''
        if preferred_length == 'short':
            length_instruction = 'CRITICAL RULE: The student EXPLICITLY asked for SHORT responses. Keep EVERY response to 2-4 sentences MAX. No bullet points, no long lists. Be brief and direct. This is the #1 priority.'
        elif preferred_length == 'detailed':
            length_instruction = 'CRITICAL RULE: The student EXPLICITLY asked for DETAILED responses. Go deep, cover edge cases, and be thorough.'
        
        # Build adaptation directives
        adapt_directives = []
        if adaptations.get('socratic_mode'):
            adapt_directives.append(
                "🔄 SOCRATIC MODE ACTIVE: Student shows confusion. Ask probing questions BEFORE explaining. "
                "Example: 'What do you think happens when...?' Then correct gently."
            )
        emotional = adaptations.get('emotional_state', 'neutral')
        if emotional == 'frustrated':
            adapt_directives.append("❤️ Student seems frustrated. Be extra warm and break concepts into tiny steps.")
        elif emotional == 'curious':
            adapt_directives.append("🚀 Student is curious! Go deeper, share interesting insights.")
        
        check_topic = adaptations.get('comprehension_check')
        if check_topic:
            adapt_directives.append(
                f"💡 After answering, ask a quick check about '{check_topic}': "
                f"'Quick check: Can you explain {check_topic} in your own words?'"
            )
        
        # Enhanced adaptive system prompt
        # Put critical user preferences at the TOP so LLM prioritizes them
        pref_header = ''
        if tone_instruction or length_instruction:
            pref_header = f"""⚡ STUDENT'S EXPLICIT PREFERENCES (MUST FOLLOW):
{tone_instruction}
{length_instruction}
---
"""
        
        system_prompt = f"""{pref_header}You are AdaptiveAI, an intelligent tutoring assistant that truly knows this student.

=== LEARNER INTELLIGENCE PROFILE ===
Name: {profile.get('name', 'Student')}
Effective Skill Level: {effective_level} (from {total_q} analyzed interactions)
Learning Tone: {learning_tone}
Background: {strongest_domain}
Conversations: {conversation_count}
{'✅ MASTERED TOPICS: ' + ', '.join(strong_topics) if strong_topics else ''}
{'⚠️ STILL LEARNING (simplify these): ' + ', '.join(weak_topics) if weak_topics else ''}

{'📊 TOPIC MASTERY MAP:' + chr(10) + chr(10).join(mastery_lines) if mastery_lines else ''}

{'🚨 ACTIVE MISCONCEPTIONS (correct gently when relevant):' + chr(10) + chr(10).join(misconception_lines) if misconception_lines else ''}

=== ADAPTATION RULES ===
1. Level {effective_level}: {'Use simple analogies, step-by-step, avoid jargon' if effective_level == 'Beginner' else 'Balance theory + practice, some math' if effective_level == 'Intermediate' else 'Deep technical depth, math foundations, research-level'}
2. Strongest area: {strongest_domain} — connect new concepts through this lens
3. {style_pref_str}
{''.join(chr(10) + d for d in adapt_directives)}

{tone_instruction}
{length_instruction}

=== TEACHING STRATEGY ===
- Adapt depth based on the TOPIC, not just one message
- If topic is in MASTERED list → Skip basics, go to nuances
- If topic is in STILL LEARNING list → Start from fundamentals
- If misconception exists for this topic → Address it proactively
- Track confusion signals ("I don't understand", "wait, so...") → Switch to Socratic questioning
- Celebrate progress and encourage exploration

{'REMEMBER: Keep responses to 2-4 sentences MAXIMUM. The student asked for SHORT answers. Do NOT write long paragraphs or lists.' if preferred_length == 'short' else 'Keep responses concise but thorough (150-300 words unless more detail requested).'}"""

        # Build message history for context
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add recent chat history (last 10 messages for context)
        for msg in chat_history[-10:]:
            messages.append({
                "role": msg.get('role', 'user'),
                "content": msg.get('content', '')
            })
        
        # Add current message
        messages.append({"role": "user", "content": message})
        
        # Call Groq API
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
            top_p=0.9
        )
        
        response_text = completion.choices[0].message.content
        
        # Save conversation to database for tracking
        try:
            if data.get('user_id'):
                conversations = Database.get_collection('conversations')
                conversations.insert_one({
                    "user_id": data.get('user_id'),
                    "user_message": message,
                    "ai_response": response_text,
                    "skill_level": skill_level,
                    "conversation_number": conversation_count + 1,
                    "tokens_used": completion.usage.total_tokens if completion.usage else 0,
                    "timestamp": datetime.utcnow().isoformat()
                })
        except Exception as e:
            print(f"Failed to save conversation: {e}")
        
        return jsonify({
            "success": True,
            "response": response_text,
            "model": "llama-3.3-70b-versatile",
            "tokens_used": completion.usage.total_tokens if completion.usage else 0
        }), 200
        
    except Exception as e:
        print(f"Groq API error: {e}")
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500
