"""
User Context Management
Saves and restores user state (quiz, chat, onboarding)
"""

from database import Database
from datetime import datetime

class ContextService:
    """Manage user context and state"""
    
    @staticmethod
    def save_context(user_id, context_data):
        """
        Save user context to database
        
        context_data = {
            'quiz_progress': {...},
            'chat_messages': [...],
            'onboarding_step': 1,
            'selected_agent': 'Machine Learning'
        }
        """
        contexts = Database.get_collection('contexts')
        
        context = {
            "user_id": user_id,
            "profile": context_data.get('profile', None),
            "quiz_progress": context_data.get('quiz_progress', None),
            "chat_messages": context_data.get('chat_messages', []),
            "active_chat_id": context_data.get('active_chat_id', None),
            "onboarding_step": context_data.get('onboarding_step', 1),
            "selected_agent": context_data.get('selected_agent', None),
            "updated_at": datetime.utcnow().isoformat()
        }
        
        # Upsert: update if exists, insert if not
        contexts.update_one(
            {"user_id": user_id},
            {"$set": context},
            upsert=True
        )
        
        return {"success": True, "message": "Context saved"}
    
    @staticmethod
    def load_context(user_id):
        """Load user context from database"""
        contexts = Database.get_collection('contexts')
        
        context = contexts.find_one({"user_id": user_id})
        
        if not context:
            return {
                "profile": None,
                "quiz_progress": None,
                "chat_messages": [],
                "active_chat_id": None,
                "onboarding_step": 1,
                "selected_agent": None
            }
        
        # Remove MongoDB _id for cleaner response
        context.pop('_id', None)
        context.pop('user_id', None)
        
        return context
    
    @staticmethod
    def clear_context(user_id):
        """Clear user context (e.g., on logout)"""
        contexts = Database.get_collection('contexts')
        
        contexts.delete_one({"user_id": user_id})
        
        return {"success": True, "message": "Context cleared"}
    
    @staticmethod
    def update_quiz_progress(user_id, quiz_data):
        """Update only quiz progress"""
        contexts = Database.get_collection('contexts')
        
        contexts.update_one(
            {"user_id": user_id},
            {
                "$set": {
                    "quiz_progress": quiz_data,
                    "updated_at": datetime.utcnow().isoformat()
                }
            },
            upsert=True
        )
    
    @staticmethod
    def add_chat_message(user_id, message):
        """Add a chat message to context"""
        contexts = Database.get_collection('contexts')
        
        contexts.update_one(
            {"user_id": user_id},
            {
                "$push": {"chat_messages": message},
                "$set": {"updated_at": datetime.utcnow().isoformat()}
            },
            upsert=True
        )
