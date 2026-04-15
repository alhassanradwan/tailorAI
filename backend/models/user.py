from database import Database
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import uuid

class User:
    """User model for handling user data and authentication"""
    
    collection = None
    
    @staticmethod
    def initialize():
        """Get the users collection from database"""
        User.collection = Database.get_collection('users')
    
    @staticmethod
    def create_user(username, email, password, full_name=""):
        """Create a new user account"""
        if User.collection is None:
            User.initialize()
        
        # Check if user already exists
        if User.collection.find_one({"email": email}):
            return {"error": "Email already registered"}, 400
        
        if User.collection.find_one({"username": username}):
            return {"error": "Username already taken"}, 400
        
        # Create user document
        user_data = {
            "_id": str(uuid.uuid4()),
            "username": username,
            "email": email,
            "password_hash": generate_password_hash(password),
            "is_admin": False,
            "created_at": datetime.utcnow().isoformat(),
            "profile": {
                "full_name": full_name,
                "learning_style": "balanced",
                "difficulty_level": "beginner"
            },
            "quiz_history": [],
            "chat_history": [],
            "agent3_data": {}
        }
        
        User.collection.insert_one(user_data)
        
        # Return user without password
        user_data.pop("password_hash")
        return {"message": "User created successfully", "user": user_data}, 201
    
    @staticmethod
    def authenticate(email, password):
        """Login user with email and password"""
        if User.collection is None:
            User.initialize()
        
        user = User.collection.find_one({"email": email})
        
        if not user:
            return {"error": "Invalid email or password"}, 401
        
        if not check_password_hash(user["password_hash"], password):
            return {"error": "Invalid email or password"}, 401
        
        # Return user without password
        user.pop("password_hash")
        return {"message": "Login successful", "user": user}, 200
    
    @staticmethod
    def get_user_by_id(user_id):
        """Get user profile by ID"""
        if User.collection is None:
            User.initialize()
        
        user = User.collection.find_one({"_id": user_id})
        
        if not user:
            return {"error": "User not found"}, 404
        
        user.pop("password_hash", None)
        return {"user": user}, 200
    
    @staticmethod
    def update_profile(user_id, profile_data):
        """Update user profile information"""
        if User.collection is None:
            User.initialize()
        
        result = User.collection.update_one(
            {"_id": user_id},
            {"$set": {"profile": profile_data}}
        )
        
        if result.matched_count == 0:
            return {"error": "User not found"}, 404
        
        return {"message": "Profile updated successfully"}, 200
