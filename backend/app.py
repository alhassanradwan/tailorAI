import logging
import os
from flask import Flask, jsonify
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

# ── Logging ─────────────────────────────────────────────────
log_level = logging.DEBUG if Config.DEBUG else logging.INFO
logging.basicConfig(
    level=log_level,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config.from_object(Config)

# Initialize JWT
jwt = JWTManager(app)

# Enable CORS for frontend
CORS(app, origins=Config.CORS_ORIGINS, supports_credentials=True)

# Initialize database
Database.initialize()

# ── Rate limiting (optional — gracefully skip if flask-limiter missing) ──
try:
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address
    limiter = Limiter(
        get_remote_address,
        app=app,
        default_limits=["200 per minute"],
        storage_uri="memory://",
    )
    logger.info("Rate limiter enabled")
except ImportError:
    limiter = None
    logger.info("flask-limiter not installed — rate limiting disabled")

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(profile_bp, url_prefix='/api/profile')
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(analytics_bp, url_prefix='/api/analytics')
app.register_blueprint(context_bp, url_prefix='/api/context')
app.register_blueprint(adaptive_bp, url_prefix='/api/adaptive')


# ── Health & root ───────────────────────────────────────────
@app.route('/')
def home():
    return {
        "message": "AdaptiveAI Backend API",
        "status": "running",
        "version": "2.0.0",
        "endpoints": {
            "auth": "/api/auth (login, signup, refresh, logout)",
            "profile": "/api/profile (user profiles)",
            "chat": "/api/chat (AI agent interactions)",
            "analytics": "/api/analytics (learning analytics)",
            "context": "/api/context (user state management)",
            "adaptive": "/api/adaptive (hybrid analysis, knowledge state)",
        }
    }


@app.route('/api/health')
def health():
    """Liveness probe for Docker / Render."""
    db_ok = Database.is_healthy()
    status = 200 if db_ok else 503
    return jsonify({
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "unreachable",
    }), status


# ── Error handlers ──────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return jsonify({"error": "Not found"}), 404


@app.errorhandler(422)
def unprocessable(e):
    return jsonify({"error": "Unprocessable request", "detail": str(e)}), 422


@app.errorhandler(500)
def internal_error(e):
    logger.error("Internal server error: %s", e, exc_info=True)
    return jsonify({"error": "Internal server error"}), 500


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(debug=Config.DEBUG, host='0.0.0.0', port=port, use_reloader=False)