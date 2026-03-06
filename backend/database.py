"""
AdaptiveAI — MongoDB Database Manager
Supports local MongoDB and MongoDB Atlas M0 free tier.
"""

import logging
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import ConnectionFailure, OperationFailure
from config import Config

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database connection manager (Atlas-ready)"""

    client = None
    db = None

    @staticmethod
    def initialize():
        """Initialize MongoDB connection with Atlas-safe settings"""
        try:
            Database.client = MongoClient(
                Config.MONGODB_URI,
                maxPoolSize=10,              # M0 free tier allows 100 connections
                serverSelectionTimeoutMS=2000,  # Fast fail if DB unavailable
                connectTimeoutMS=2000,
                retryWrites=True,
            )
            # Verify connection is alive
            Database.client.admin.command('ping')
            Database.db = Database.client[Config.MONGODB_DB_NAME]
            logger.info("✅ Connected to MongoDB: %s", Config.MONGODB_DB_NAME)
            Database._ensure_indexes()
            return True
        except ConnectionFailure as e:
            logger.warning("⚠️  MongoDB unavailable (will retry on first request): %s", e)
            # Set db to None but don't crash - app can start without DB
            Database.db = None
            return False
        except Exception as e:
            logger.warning("⚠️  MongoDB init error: %s", e)
            Database.db = None
            return False

    @staticmethod
    def _ensure_indexes():
        """Create indexes for production performance (idempotent)"""
        try:
            db = Database.db

            # users — unique email lookup
            db['users'].create_index('email', unique=True, background=True)

            # interactions — per-user history lookup + topic queries
            db['interactions'].create_index(
                [('user_id', ASCENDING), ('timestamp', DESCENDING)],
                background=True,
            )
            db['interactions'].create_index(
                [('user_id', ASCENDING), ('analysis.topics', ASCENDING)],
                background=True,
            )

            # knowledge_states — one doc per user
            db['knowledge_states'].create_index('user_id', unique=True, background=True)

            # sessions — active session lookup
            db['sessions'].create_index(
                [('user_id', ASCENDING), ('active', ASCENDING)],
                background=True,
            )

            # analytics snapshots (if used later)
            db['analytics_snapshots'].create_index(
                [('user_id', ASCENDING), ('date', DESCENDING)],
                background=True,
            )

            logger.info("Database indexes verified")
        except OperationFailure as e:
            logger.warning("Index creation issue (non-fatal): %s", e)

    @staticmethod
    def get_collection(collection_name):
        """Get a specific collection from the database"""
        if Database.db is None:
            Database.initialize()
        return Database.db[collection_name]

    @staticmethod
    def is_healthy():
        """Health check — returns True if MongoDB is reachable"""
        try:
            if Database.client is None:
                return False
            Database.client.admin.command('ping')
            return True
        except Exception:
            return False
