import os
from datetime import timedelta
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    """Application configuration settings"""
    
    # Flask settings
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'default-secret-key')
    DEBUG = os.getenv('FLASK_ENV') == 'development'
    
    # JWT settings
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-secret-key-change-this')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_TOKEN_LOCATION = ['headers']
    JWT_HEADER_NAME = 'Authorization'
    JWT_HEADER_TYPE = 'Bearer'
    
    # MongoDB settings
    MONGODB_URI = os.getenv('MONGODB_URI', 'mongodb://localhost:27017/')
    MONGODB_DB_NAME = os.getenv('MONGODB_DB_NAME', 'adaptiveai')
    # Keep Atlas SRV DNS + initial handshake timeout practical on home networks
    MONGODB_SERVER_SELECTION_TIMEOUT_MS = int(os.getenv('MONGODB_SERVER_SELECTION_TIMEOUT_MS', '10000'))
    MONGODB_CONNECT_TIMEOUT_MS = int(os.getenv('MONGODB_CONNECT_TIMEOUT_MS', '10000'))
    MONGODB_SOCKET_TIMEOUT_MS = int(os.getenv('MONGODB_SOCKET_TIMEOUT_MS', '10000'))
    
    # Admin credentials
    ADMIN_EMAIL = 'hassangrdwan@gmail.com'
    ADMIN_PASSWORD_HASH = None  # Will be set on first admin login
    
    # API Keys (for future use with AI agents)
    OPENAI_API_KEY = os.getenv('OPENAI_API_KEY', '')
    HUGGINGFACE_API_KEY = os.getenv('HUGGINGFACE_API_KEY', '')

    # LangChain integration feature flag (default: enabled)
    USE_LANGCHAIN = os.getenv('USE_LANGCHAIN', 'true').strip().lower() in ('1', 'true', 'yes', 'on')

    # RAG integration feature flag (default: disabled for safe rollout)
    USE_RAG = os.getenv('USE_RAG', 'false').strip().lower() in ('1', 'true', 'yes', 'on')

    # Dynamic chat schema rollout flags (default: disabled for safe rollout)
    DYNAMIC_CHAT_SCHEMA_ENABLED = os.getenv('DYNAMIC_CHAT_SCHEMA_ENABLED', 'true').strip().lower() in ('1', 'true', 'yes', 'on')
    DYNAMIC_INTENT_ROUTER_ENABLED = os.getenv('DYNAMIC_INTENT_ROUTER_ENABLED', 'true').strip().lower() in ('1', 'true', 'yes', 'on')
    
    # CORS settings (allow frontend to connect)
    # In production, set CORS_ORIGINS env var as comma-separated URLs
    CORS_ORIGINS = [
        o.strip() for o in
        os.getenv('CORS_ORIGINS', 'http://127.0.0.1:5500,http://localhost:5500,http://localhost:3000,http://127.0.0.1:3000,http://localhost:5173,http://127.0.0.1:5173').split(',')
    ]
