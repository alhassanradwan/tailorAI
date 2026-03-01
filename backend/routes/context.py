"""
Context Routes
Manage user context (quiz progress, chat, onboarding, etc.)
"""

from flask import Blueprint, request, jsonify
from services.context import ContextService
from middleware.auth import token_required, get_current_user

context_bp = Blueprint('context', __name__)

@context_bp.route('/save', methods=['POST'])
@token_required
def save_context():
    """Save user context"""
    data = request.get_json()
    user_id = get_current_user()
    
    context_data = {
        'profile': data.get('profile'),
        'quiz_progress': data.get('quiz_progress'),
        'chat_messages': data.get('chat_messages', []),
        'active_chat_id': data.get('active_chat_id'),
        'onboarding_step': data.get('onboarding_step', 1),
        'selected_agent': data.get('selected_agent')
    }
    
    result = ContextService.save_context(user_id, context_data)
    return jsonify(result), 200

@context_bp.route('/load', methods=['GET'])
@token_required
def load_context():
    """Load user context"""
    user_id = get_current_user()
    
    context = ContextService.load_context(user_id)
    return jsonify(context), 200

@context_bp.route('/clear', methods=['DELETE'])
@token_required
def clear_context():
    """Clear user context"""
    user_id = get_current_user()
    
    result = ContextService.clear_context(user_id)
    return jsonify(result), 200

@context_bp.route('/quiz', methods=['POST'])
@token_required
def update_quiz():
    """Update quiz progress only"""
    data = request.get_json()
    user_id = get_current_user()
    
    quiz_data = data.get('quiz_progress')
    if not quiz_data:
        return jsonify({"error": "quiz_progress is required"}), 400
    
    ContextService.update_quiz_progress(user_id, quiz_data)
    return jsonify({"success": True}), 200

@context_bp.route('/chat', methods=['POST'])
@token_required
def add_chat_message():
    """Add a chat message"""
    data = request.get_json()
    user_id = get_current_user()
    
    message = data.get('message')
    if not message:
        return jsonify({"error": "message is required"}), 400
    
    ContextService.add_chat_message(user_id, message)
    return jsonify({"success": True}), 200
