import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from services.knowledge_state import KnowledgeStateService
from database import Database

logger = logging.getLogger(__name__)
profile_bp = Blueprint('profile', __name__)


# ── JWT-protected "me" endpoints ────────────────────────────
@profile_bp.route('/me', methods=['GET'])
@profile_bp.route('/get', methods=['GET'])          # alias for AuthContext.jsx
@jwt_required()
def get_me():
    """Return current user + their knowledge state in one payload."""
    user_id = get_jwt_identity()
    result, status = User.get_user_by_id(user_id)
    if status != 200:
        return jsonify(result), status

    user = result['user']
    ks = KnowledgeStateService.get(user_id)

    return jsonify({
        "success": True,
        "user": user,
        "knowledge_state": ks,
    }), 200


@profile_bp.route('/me', methods=['PUT'])
@jwt_required()
def update_me():
    """Update current user's profile (onboarding / settings)."""
    user_id = get_jwt_identity()
    data = request.get_json()
    profile_data = data.get('profile')

    if not profile_data:
        return jsonify({"error": "No profile data provided"}), 400

    result, status = User.update_profile(user_id, profile_data)
    return jsonify(result), status


# ── Legacy path-param endpoints (keep for backward compat) ──
@profile_bp.route('/<user_id>', methods=['GET'])
def get_profile(user_id):
    """Get user profile by ID"""
    result, status = User.get_user_by_id(user_id)
    return jsonify(result), status

@profile_bp.route('/<user_id>', methods=['PUT'])
def update_profile(user_id):
    """Update user profile"""
    data = request.get_json()
    profile_data = data.get('profile')
    
    if not profile_data:
        return jsonify({"error": "No profile data provided"}), 400
    
    result, status = User.update_profile(user_id, profile_data)
    return jsonify(result), status
