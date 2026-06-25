"""
AdaptiveAI - Analytics Routes
Handles quiz analytics, learning patterns, progress tracking,
and server-side knowledge-state analytics.
"""

import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from database import Database
from services.knowledge_state import KnowledgeStateService
from services.recommendation_service import RecommendationService
from datetime import datetime

logger = logging.getLogger(__name__)
analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/save', methods=['POST'])
def save_analytics():
    """Legacy endpoint disabled. Use JWT-protected analytics endpoints."""
    return jsonify({
        "success": False,
        "error": "Legacy endpoint disabled. Use JWT-protected analytics endpoints."
    }), 410


@analytics_bp.route('/user/<email>', methods=['GET'])
def get_user_analytics(email):
    """Legacy endpoint disabled. Use JWT-protected analytics endpoints."""
    return jsonify({
        "success": False,
        "error": "Legacy endpoint disabled. Use JWT-protected analytics endpoints."
    }), 410


@analytics_bp.route('/progress/<email>', methods=['GET'])
def get_progress_report(email):
    """Legacy endpoint disabled. Use JWT-protected analytics endpoints."""
    return jsonify({
        "success": False,
        "error": "Legacy endpoint disabled. Use JWT-protected analytics endpoints."
    }), 410


@analytics_bp.route('/webhook/n8n', methods=['POST'])
def n8n_webhook():
    """Legacy endpoint disabled. Use JWT-protected analytics endpoints."""
    return jsonify({
        "success": False,
        "error": "Legacy endpoint disabled. Use JWT-protected analytics endpoints."
    }), 410


# ════════════════════════════════════════════════════════════
# NEW: Server-side analytics (reads from knowledge_states)
# All JWT-protected, keyed by user_id
# ════════════════════════════════════════════════════════════

@analytics_bp.route('/summary', methods=['GET'])
@jwt_required()
def analytics_summary():
    """
    One-shot summary consumed by the React Analytics dashboard.
    Returns everything the frontend needs in a single call.
    """
    user_id = get_jwt_identity()
    try:
        ks = KnowledgeStateService.get(user_id)
        ba = ks.get('behavioral', {})
        topics = ks.get('topics', {})
        eng = ba.get('engagement_metrics', {})

        # Top topics by interaction count
        sorted_topics = sorted(
            [(t, td) for t, td in topics.items() if isinstance(td, dict)],
            key=lambda x: x[1].get('count', 0),
            reverse=True,
        )

        # Compute overall mastery average
        mastery_vals = [
            td.get('mastery_level', 0)
            for _, td in sorted_topics
            if td.get('count', 0) >= 2
        ]
        avg_mastery = round(sum(mastery_vals) / max(len(mastery_vals), 1), 2)

        return jsonify({
            "success": True,
            "summary": {
                "skill_level": ks.get('skill_level', 'Intermediate'),
                "total_messages": eng.get('total_messages', 0),
                "avg_message_length": eng.get('avg_message_length', 0),
                "code_requests": eng.get('code_requests', 0),
                "question_types": ba.get('question_types', {}),
                "complexity_distribution": ba.get('complexity_distribution', {}),
                "strong_topics": ks.get('strong_topics', []),
                "weak_topics": ks.get('weak_topics', []),
                "avg_mastery": avg_mastery,
                "topics_count": len(sorted_topics),
                "skill_progression": ba.get('skill_progression', []),
                "conversation_preferences": ks.get('conversation_preferences', {}),
                "updated_at": ks.get('updated_at'),
            },
        }), 200
    except Exception as e:
        logger.error("analytics/summary error: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route('/mastery-map', methods=['GET'])
@jwt_required()
def mastery_map():
    """Per-topic mastery data for charts / heatmaps."""
    user_id = get_jwt_identity()
    try:
        ks = KnowledgeStateService.get(user_id)
        topics = ks.get('topics', {})

        mastery = []
        for t, td in topics.items():
            if isinstance(td, dict) and td.get('count', 0) >= 1:
                mastery.append({
                    "topic": t,
                    "mastery_level": td.get('mastery_level', 0),
                    "interactions": td.get('count', 0),
                    "complexity_levels": td.get('complexity_levels', {}),
                    "first_seen": td.get('first_seen'),
                    "last_seen": td.get('last_seen'),
                })

        mastery.sort(key=lambda x: x['mastery_level'], reverse=True)

        return jsonify({"success": True, "mastery": mastery}), 200
    except Exception as e:
        logger.error("analytics/mastery-map error: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route('/misconceptions', methods=['GET'])
@jwt_required()
def misconceptions():
    """Active + corrected misconceptions."""
    user_id = get_jwt_identity()
    try:
        ks = KnowledgeStateService.get(user_id)
        raw = ks.get('misconceptions', {})

        items = []
        for topic, md in raw.items():
            if isinstance(md, dict):
                items.append({
                    "topic": topic,
                    "detail": md.get('detail', ''),
                    "count": md.get('count', 0),
                    "corrected": md.get('corrected', False),
                    "first_seen": md.get('first_seen'),
                    "last_seen": md.get('last_seen'),
                })

        return jsonify({"success": True, "misconceptions": items}), 200
    except Exception as e:
        logger.error("analytics/misconceptions error: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route('/engagement', methods=['GET'])
@jwt_required()
def engagement():
    """Engagement metrics + recent interaction timeline."""
    user_id = get_jwt_identity()
    try:
        ks = KnowledgeStateService.get(user_id)
        ba = ks.get('behavioral', {})
        eng = ba.get('engagement_metrics', {})

        # Pull last 20 interactions for a mini-timeline
        interactions_coll = Database.get_collection('interactions')
        recent = list(
            interactions_coll.find(
                {"user_id": user_id},
                {"_id": 0, "timestamp": 1, "analysis.topics": 1,
                 "analysis.complexity": 1, "tokens_used": 1},
            )
            .sort("timestamp", -1)
            .limit(20)
        )

        return jsonify({
            "success": True,
            "engagement": eng,
            "recent_interactions": recent,
        }), 200
    except Exception as e:
        logger.error("analytics/engagement error: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@analytics_bp.route('/recommendations', methods=['GET'])
@jwt_required()
def recommendations():
    """Personalized topic recommendations based on mastery, misconceptions, and knowledge graph."""
    user_id = get_jwt_identity()
    try:
        recs = RecommendationService.generate(user_id)
        return jsonify({"success": True, "recommendations": recs}), 200
    except Exception as e:
        logger.error("analytics/recommendations error: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500

