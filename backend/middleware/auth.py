"""
Authentication Middleware
JWT verification and protection for routes
"""

from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity, get_jwt
from database import Database

def token_required(fn):
    """Decorator to require valid JWT token"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": "Invalid or expired token", "details": str(e)}), 401
    return wrapper

def admin_required(fn):
    """Decorator to require admin privileges"""
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            verify_jwt_in_request()
            claims = get_jwt()
            
            if not claims.get('is_admin', False):
                return jsonify({"error": "Admin privileges required"}), 403
            
            return fn(*args, **kwargs)
        except Exception as e:
            return jsonify({"error": "Authentication failed", "details": str(e)}), 401
    return wrapper

def get_current_user():
    """Get current user ID from JWT token"""
    try:
        verify_jwt_in_request()
        return get_jwt_identity()
    except:
        return None

def is_admin_user(email):
    """Check admin flag from database for a given email."""
    users = Database.get_collection('users')
    user = users.find_one({'email': email}, {'_id': 0, 'is_admin': 1})
    return bool((user or {}).get('is_admin', False))
