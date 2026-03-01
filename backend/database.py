from pymongo import MongoClient
from config import Config

class Database:
    """MongoDB database connection manager"""
    
    client = None
    db = None
    
    @staticmethod
    def initialize():
        """Initialize MongoDB connection"""
        try:
            Database.client = MongoClient(Config.MONGODB_URI)
            Database.db = Database.client[Config.MONGODB_DB_NAME]
            print(f"[OK] Connected to MongoDB: {Config.MONGODB_DB_NAME}")
            return True
        except Exception as e:
            print(f"[ERROR] MongoDB connection failed: {e}")
            return False
    
    @staticmethod
    def get_collection(collection_name):
        """Get a specific collection from the database"""
        if Database.db is None:
            Database.initialize()
        return Database.db[collection_name]
