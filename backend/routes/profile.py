from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User

profile_bp = Blueprint('profile', __name__)

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

@profile_bp.route('/save-message', methods=['POST'])
@jwt_required()
def save_message():
    """Save a chat message to user's chat history in MongoDB"""
    user_id = get_jwt_identity()
    data = request.get_json()
    
    user_message = data.get('user_message')
    ai_response = data.get('ai_response')
    timestamp = data.get('timestamp')
    profile_snapshot = data.get('profile_snapshot', {})
    
    if not user_message or not ai_response:
        return jsonify({"error": "Missing message data"}), 400
    
    result, status = User.save_chat_message(
        user_id, 
        user_message, 
        ai_response, 
        timestamp, 
        profile_snapshot
    )
    
    return jsonify(result), status
