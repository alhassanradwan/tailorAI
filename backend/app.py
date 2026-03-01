from flask import Flask
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import Config
from database import Database
from routes.auth import auth_bp
from routes.profile import profile_bp
from routes.chat import chat_bp
from routes.analytics import analytics_bp
from routes.context import context_bp
from routes.adaptive import adaptive_bp


# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize JWT
jwt = JWTManager(app)

# Enable CORS for frontend
CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)

# Initialize database
Database.initialize()

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(profile_bp, url_prefix='/api/profile')
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
app.register_blueprint(context_bp, url_prefix='/api/context')
app.register_blueprint(adaptive_bp, url_prefix='/api/adaptive')

@app.route('/')
def home():
    return {
        "message": "AdaptiveAI Backend API",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth (login, signup, refresh, logout)",
            "profile": "/api/profile (user profiles)",
            "chat": "/api/chat (AI agent interactions)",
            "analytics": "/api/analytics (quiz data, progress)",
            "context": "/api/context (user state management)",
            "adaptive": "/api/adaptive (hybrid analysis, knowledge state, enriched prompts)"
        }
    }

if __name__ == '__main__':
    app.run(debug=True, port=5000, use_reloader=False)
## Note: use_reloader=False is important to prevent the app from running twice in development mode.