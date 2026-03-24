"""
AdaptiveAI - AI Agents Service
This module contains the 4 AI agents:
1. Adaptive Agent (Orchestrator) - Personalizes everything
2. Data Science Agent (Supervisor)
3. Machine Learning Agent
4. Deep Learning Agent
"""

import openai
from config import Config

# Initialize OpenAI client
#client = openai.OpenAI(api_key=Config.OPENAI_API_KEY)
client = ""
class AdaptiveAgent:
    """
    The Adaptive Agent is the orchestrator that:
    1. Analyzes the learner's profile
    2. Determines the appropriate teaching style
    3. Adjusts complexity based on skill level
    4. Routes queries to specialized agents
    5. Post-processes responses for personalization
    """
    
    @staticmethod
    def build_learner_context(profile):
        """Build a context string from learner profile for personalization"""
        
        if not profile:
            return "New learner with no profile data yet."
        
        # Extract profile information
        name = profile.get('name', 'Student')
        level = profile.get('level', 'undergraduate')
        major = profile.get('major', 'Computer Science')
        tone = profile.get('tone', 'friendly')
        python_skill = profile.get('python', 'Beginner')
        math_skill = profile.get('math', 'Beginner')
        
        # Domain analysis from quiz
        domain_analysis = profile.get('domain_analysis', {})
        detected_level = domain_analysis.get('detected_level', 'Beginner')
        strongest_domain = domain_analysis.get('strongest_domain', 'Machine Learning')
        overall_accuracy = domain_analysis.get('overall_accuracy', 0)
        
        # Learning preferences
        preferences = profile.get('preferences', {})
        learning_style = preferences.get('learning_style', 'friendly')
        
        context = f"""
=== LEARNER PROFILE ===
Name: {name}
Academic Level: {level}
Major: {major}
Detected Skill Level: {detected_level} (Quiz Accuracy: {overall_accuracy:.1f}%)
Strongest Domain: {strongest_domain}

=== SKILL LEVELS ===
Python Programming: {python_skill}
Mathematics: {math_skill}

=== LEARNING PREFERENCES ===
Preferred Teaching Style: {tone}
- If 'friendly': Use conversational tone, analogies, real-world examples, encouragement
- If 'concise': Be direct, technical, documentation-style, minimal fluff
- If 'socratic': Ask guiding questions, let them discover answers, challenge thinking

=== ADAPTATION RULES ===
1. For {detected_level} level: {"Use simple analogies, step-by-step explanations, avoid jargon" if detected_level == "Beginner" else "Balance theory with practice, introduce mathematical concepts gradually" if detected_level == "Intermediate" else "Dive deep into mathematics, show code implementations, discuss edge cases"}
2. Their strongest area is {strongest_domain}, so they may understand concepts from that perspective better
3. Python level is {python_skill}: {"Keep code examples simple and well-commented" if python_skill == "Beginner" else "Can handle intermediate Python patterns" if python_skill == "Intermediate" else "Can handle advanced Python, decorators, generators, etc."}
4. Math level is {math_skill}: {"Minimize equations, use intuitive explanations" if math_skill == "Beginner" else "Can handle basic calculus and linear algebra" if math_skill == "Intermediate" else "Comfortable with advanced mathematics, proofs, derivations"}
"""
        return context
    
    @staticmethod
    def get_teaching_style_prompt(tone):
        """Get specific instructions based on teaching style"""
        
        styles = {
            'friendly': """
TEACHING STYLE: Friendly & Encouraging
- Use a warm, conversational tone
- Include real-world analogies and examples
- Break complex concepts into digestible pieces
- Use phrases like "Great question!", "Let's explore this together"
- Add emojis sparingly for engagement 
- Celebrate their progress and encourage questions
""",
            'concise': """
TEACHING STYLE: Concise & Technical
- Be direct and to the point
- Use technical terminology appropriately
- Structure responses with clear headings
- Include code snippets when relevant
- No unnecessary pleasantries
- Focus on accuracy and completeness
""",
            'socratic': """
TEACHING STYLE: Socratic Method
- Answer questions with guiding questions
- Help them discover the answer themselves
- Challenge their assumptions constructively
- Use phrases like "What do you think would happen if...?"
- Build on their existing knowledge
- Only provide direct answers after they've attempted reasoning
"""
        }
        return styles.get(tone, styles['friendly'])
    
    @staticmethod
    def determine_agent(query, profile):
        """Determine which specialized agent should handle the query"""
        
        query_lower = query.lower()
        
        # Keywords for each domain
        ds_keywords = ['data', 'pandas', 'numpy', 'visualization', 'eda', 'exploratory', 
                       'statistics', 'correlation', 'distribution', 'cleaning', 'preprocessing',
                       'matplotlib', 'seaborn', 'plotly', 'csv', 'dataframe', 'analysis']
        
        ml_keywords = ['machine learning', 'supervised', 'unsupervised', 'regression', 
                       'classification', 'clustering', 'random forest', 'decision tree',
                       'svm', 'knn', 'k-means', 'pca', 'feature', 'training', 'testing',
                       'cross-validation', 'overfitting', 'underfitting', 'scikit', 'sklearn']
        
        dl_keywords = ['deep learning', 'neural network', 'cnn', 'rnn', 'lstm', 'transformer',
                       'backpropagation', 'gradient descent', 'activation', 'relu', 'sigmoid',
                       'tensorflow', 'pytorch', 'keras', 'epoch', 'batch', 'dropout', 'layer',
                       'convolution', 'attention', 'bert', 'gpt', 'embedding']
        
        # Count keyword matches
        ds_score = sum(1 for kw in ds_keywords if kw in query_lower)
        ml_score = sum(1 for kw in ml_keywords if kw in query_lower)
        dl_score = sum(1 for kw in dl_keywords if kw in query_lower)
        
        # Determine agent based on scores
        if dl_score > ml_score and dl_score > ds_score:
            return 'deep_learning'
        elif ml_score > ds_score:
            return 'machine_learning'
        elif ds_score > 0:
            return 'data_science'
        else:
            # Default to user's strongest domain or ML
            strongest = profile.get('domain_analysis', {}).get('strongest_domain', 'Machine Learning')
            return strongest.lower().replace(' ', '_')
    
    @staticmethod
    def adapt_response(response, profile):
        """Post-process the response for additional personalization"""
        # This could add personalized tips, track concepts covered, etc.
        # For now, we return as-is but this is where n8n could hook in
        return response


class DataScienceAgent:
    """Specialized agent for Data Science topics"""
    
    SYSTEM_PROMPT = """You are an expert Data Science tutor specializing in:
- Exploratory Data Analysis (EDA)
- Data Cleaning and Preprocessing
- Statistical Analysis
- Data Visualization (Matplotlib, Seaborn, Plotly)
- Pandas and NumPy operations
- Descriptive and Inferential Statistics
- Feature Engineering basics

You are the SUPERVISOR agent that oversees the learning path.
When a topic ventures into ML or DL territory, acknowledge it and explain the connection.

Always provide practical Python code examples when relevant.
Focus on building strong data intuition and analytical thinking."""


class MachineLearningAgent:
    """Specialized agent for Machine Learning topics"""
    
    SYSTEM_PROMPT = """You are an expert Machine Learning tutor specializing in:
- Supervised Learning (Classification, Regression)
- Unsupervised Learning (Clustering, Dimensionality Reduction)
- Model Selection and Evaluation
- Feature Engineering and Selection
- Cross-Validation and Hyperparameter Tuning
- Scikit-learn implementation
- Classical ML algorithms (Random Forest, SVM, KNN, etc.)
- Ensemble Methods

You work under the Data Science supervisor agent.
Connect ML concepts to data science foundations when helpful.
Always explain the intuition before diving into mathematics."""


class DeepLearningAgent:
    """Specialized agent for Deep Learning topics"""
    
    SYSTEM_PROMPT = """You are an expert Deep Learning tutor specializing in:
- Neural Network fundamentals
- Backpropagation and Gradient Descent
- CNNs for Computer Vision
- RNNs and LSTMs for Sequential Data
- Transformers and Attention Mechanisms
- TensorFlow and PyTorch implementation
- Transfer Learning
- Modern architectures (ResNet, BERT, GPT, etc.)

You work under the Data Science supervisor agent.
Build on ML foundations when explaining DL concepts.
Balance mathematical rigor with practical intuition based on learner level."""


class AIService:
    """Main service for handling AI interactions"""
    
    @staticmethod
    def generate_response(query, profile, chat_history=None):
        """
        Generate a personalized response using the appropriate agent
        
        Args:
            query: User's question
            profile: User's learner profile
            chat_history: Previous messages for context
        
        Returns:
            dict with response, agent used, and metadata
        """
        
        # Step 1: Build learner context
        learner_context = AdaptiveAgent.build_learner_context(profile)
        
        # Step 2: Get teaching style instructions
        tone = profile.get('tone', 'friendly') if profile else 'friendly'
        style_prompt = AdaptiveAgent.get_teaching_style_prompt(tone)
        
        # Step 3: Determine which agent should handle this
        agent_type = AdaptiveAgent.determine_agent(query, profile or {})
        
        # Step 4: Get agent-specific system prompt
        agent_prompts = {
            'data_science': DataScienceAgent.SYSTEM_PROMPT,
            'machine_learning': MachineLearningAgent.SYSTEM_PROMPT,
            'deep_learning': DeepLearningAgent.SYSTEM_PROMPT
        }
        agent_prompt = agent_prompts.get(agent_type, MachineLearningAgent.SYSTEM_PROMPT)
        
        # Step 5: Build the complete system prompt
        system_prompt = f"""
{agent_prompt}

{learner_context}

{style_prompt}

IMPORTANT RULES:
1. Always adapt your explanation to the learner's detected level
2. Use their preferred teaching style consistently
3. Reference their skill levels when deciding complexity
4. Build on their strongest domain when making connections
5. If they seem to be improving, slightly increase complexity
6. Encourage questions and provide actionable next steps
"""
        
        # Step 6: Build messages array
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add chat history for context (last 10 messages)
        if chat_history:
            for msg in chat_history[-10:]:
                role = "assistant" if msg.get('type') == 'agent' else "user"
                messages.append({"role": role, "content": msg.get('text', '')})
        
        # Add current query
        messages.append({"role": "user", "content": query})
        
        # Step 7: Call OpenAI API
        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",  # Cost-effective, great for education
                messages=messages,
                temperature=0.7,
                max_tokens=1500
            )
            
            ai_response = response.choices[0].message.content
            
            # Step 8: Post-process with Adaptive Agent
            final_response = AdaptiveAgent.adapt_response(ai_response, profile)
            
            return {
                "success": True,
                "response": final_response,
                "agent": agent_type,
                "model": "gpt-4o-mini",
                "tokens_used": response.usage.total_tokens
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "agent": agent_type
            }
    
    @staticmethod
    def analyze_level_progression(quiz_analytics, chat_history):
        """
        Analyze if the student's level should be updated
        This can be called by n8n or scheduled task
        
        Returns recommendation for level adjustment
        """
        
        if not quiz_analytics:
            return {"should_update": False, "reason": "No quiz data"}
        
        accuracy = quiz_analytics.get('performance', {}).get('accuracy_percentage', 0)
        
        # Simple level progression logic (can be enhanced with ML)
        current_level = quiz_analytics.get('profile', {}).get('domain_analysis', {}).get('detected_level', 'Beginner')
        
        recommendation = {
            "current_level": current_level,
            "should_update": False,
            "new_level": current_level,
            "reason": ""
        }
        
        if current_level == "Beginner" and accuracy >= 80:
            recommendation["should_update"] = True
            recommendation["new_level"] = "Intermediate"
            recommendation["reason"] = f"High accuracy ({accuracy:.1f}%) indicates readiness for intermediate content"
        
        elif current_level == "Intermediate" and accuracy >= 85:
            recommendation["should_update"] = True
            recommendation["new_level"] = "Advanced"
            recommendation["reason"] = f"Excellent performance ({accuracy:.1f}%) indicates readiness for advanced content"
        
        elif current_level == "Advanced" and accuracy < 50:
            recommendation["should_update"] = True
            recommendation["new_level"] = "Intermediate"
            recommendation["reason"] = f"Performance drop ({accuracy:.1f}%) suggests need for reinforcement"
        
        return recommendation
