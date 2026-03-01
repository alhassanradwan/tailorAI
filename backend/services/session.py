"""
Session Management Service
Handles user sessions, tokens, and activity tracking
"""

from database import Database
from datetime import datetime, timedelta
import uuid

class SessionService:
    """Manage user sessions"""
    
    @staticmethod
    def create_session(user_id, token, device_info=None):
        """Create a new session"""
        sessions = Database.get_collection('sessions')
        
        session_data = {
            "_id": str(uuid.uuid4()),
            "user_id": user_id,
            "token_id": token,  # JWT access token string
            "created_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "expires_at": (datetime.utcnow() + timedelta(hours=8)).isoformat(),
            "device_info": device_info or {},
            "active": True
        }
        
        sessions.insert_one(session_data)
        return session_data
    
    @staticmethod
    def update_activity(user_id):
        """Update last activity timestamp"""
        sessions = Database.get_collection('sessions')
        
        sessions.update_many(
            {"user_id": user_id, "active": True},
            {"$set": {"last_activity": datetime.utcnow().isoformat()}}
        )
    
    @staticmethod
    def invalidate_session(user_id):
        """Invalidate all sessions for a user (logout)"""
        sessions = Database.get_collection('sessions')
        
        sessions.update_many(
            {"user_id": user_id},
            {"$set": {"active": False}}
        )
    
    @staticmethod
    def cleanup_expired_sessions():
        """Remove expired sessions"""
        sessions = Database.get_collection('sessions')
        
        now = datetime.utcnow().isoformat()
        result = sessions.delete_many({"expires_at": {"$lt": now}})
        
        return result.deleted_count
    
    @staticmethod
    def get_active_sessions(user_id):
        """Get all active sessions for a user"""
        sessions = Database.get_collection('sessions')
        
        return list(sessions.find({
            "user_id": user_id,
            "active": True
        }))
