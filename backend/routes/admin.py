import logging
from flask import Blueprint, jsonify, request
from middleware.auth import admin_required
from services.admin_service import AdminService

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__)


@admin_bp.route('/users', methods=['GET'])
@admin_required
def admin_users():
    try:
        limit = request.args.get('limit', default=100, type=int)
        limit = max(1, min(limit, 200))
        users = AdminService.get_users_overview(limit=limit)
        return jsonify({
            'success': True,
            'count': len(users),
            'users': users,
        }), 200
    except Exception as e:
        logger.error('admin/users error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/analytics/summary', methods=['GET'])
@admin_required
def admin_analytics_summary():
    try:
        summary = AdminService.get_analytics_summary(top_topics_limit=8)
        return jsonify({'success': True, 'summary': summary}), 200
    except Exception as e:
        logger.error('admin/analytics/summary error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/interactions/recent', methods=['GET'])
@admin_required
def admin_recent_interactions():
    try:
        limit = request.args.get('limit', default=20, type=int)
        limit = max(1, min(limit, 50))
        interactions = AdminService.get_recent_interactions(limit=limit)
        return jsonify({
            'success': True,
            'count': len(interactions),
            'interactions': interactions,
        }), 200
    except Exception as e:
        logger.error('admin/interactions/recent error: %s', e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500


@admin_bp.route('/user/<user_id>', methods=['GET'])
@admin_required
def admin_user_detail(user_id):
    try:
        detail = AdminService.get_user_detail(user_id=user_id, interactions_limit=10)
        return jsonify({'success': True, 'user': detail}), 200
    except Exception as e:
        logger.error('admin/user/%s error: %s', user_id, e, exc_info=True)
        return jsonify({'success': False, 'error': str(e)}), 500
