from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt_identity
from models.user import User
from services.session import SessionService

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/signup', methods=['POST'])
def signup():
    """Handle user registration"""
    data = request.get_json()
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    full_name = data.get('full_name', '')
    
    if not username or not email or not password:
        return jsonify({"error": "Missing required fields"}), 400
    
    result, status = User.create_user(username, email, password, full_name)
    
    if status == 201:
        # Generate tokens for new user
        user_id = result['user']['_id']
        is_admin = bool(result['user'].get('is_admin', False))
        
        access_token = create_access_token(
            identity=user_id,
            additional_claims={'is_admin': is_admin}
        )
        refresh_token = create_refresh_token(identity=user_id)
        
        # Create session
        device_info = request.headers.get('User-Agent', 'Unknown')
        SessionService.create_session(user_id, access_token, device_info)
        
        result['access_token'] = access_token
        result['refresh_token'] = refresh_token
        result['user']['is_admin'] = is_admin
    
    return jsonify(result), status

@auth_bp.route('/login', methods=['POST'])
def login():
    """Handle user login"""
    data = request.get_json()
    
    email = data.get('email')
    password = data.get('password')
    
    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400
    
    result, status = User.authenticate(email, password)
    
    if status == 200:
        # Generate tokens
        user_id = result['user']['_id']
        is_admin = bool(result['user'].get('is_admin', False))
        
        access_token = create_access_token(
            identity=user_id,
            additional_claims={'is_admin': is_admin}
        )
        refresh_token = create_refresh_token(identity=user_id)
        
        # Create session
        device_info = request.headers.get('User-Agent', 'Unknown')
        SessionService.create_session(user_id, access_token, device_info)
        
        result['access_token'] = access_token
        result['refresh_token'] = refresh_token
        result['user']['is_admin'] = is_admin
    
    return jsonify(result), status

@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """Refresh access token"""
    user_id = get_jwt_identity()
    
    # Generate new access token
    result, status = User.get_user_by_id(user_id)
    if status != 200 or not result.get('user'):
        return jsonify({"error": "User not found"}), 404

    is_admin = bool(result['user'].get('is_admin', False))
    
    access_token = create_access_token(
        identity=user_id,
        additional_claims={'is_admin': is_admin}
    )
    
    # Update session
    device_info = request.headers.get('User-Agent', 'Unknown')
    SessionService.create_session(user_id, access_token, device_info)
    
    return jsonify({
        "access_token": access_token
    }), 200

@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """Handle user logout"""
    user_id = get_jwt_identity()
    
    # Get token from header
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    # Invalidate session
    SessionService.invalidate_session(token)
    
    return jsonify({"message": "Logged out successfully"}), 200
