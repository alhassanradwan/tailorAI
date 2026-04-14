"""
AdaptiveAI - Chat Routes
Handles all chat-related API endpoints
"""

import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from models.user import User
from services.ai_agents import AIService
from services.agent_router import DeepAgentRouter
from services.knowledge_state import KnowledgeStateService
from services.adaptive_mode_service import AdaptiveModeService
from database import Database
from datetime import datetime
import os
from groq import Groq

logger = logging.getLogger(__name__)
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/message', methods=['POST'])
def send_message():
    """Legacy endpoint intentionally disabled. Use /api/chat/groq."""
    return jsonify({
        "success": False,
        "error": "Legacy endpoint disabled. Use /api/chat/groq."
    }), 410


@chat_bp.route('/history/<user_id>', methods=['GET'])
def get_chat_history(user_id):
    """Get chat history for a specific user"""
    
    try:
        interactions = Database.get_collection('interactions')
        history = list(interactions.find(
            {"user_id": user_id},
            {"_id": 0}
        ).sort("timestamp", -1).limit(50))
        
        return jsonify({
            "success": True,
            "history": history
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@chat_bp.route('/analyze-progression', methods=['POST'])
def analyze_progression():
    """
    Analyze if student should level up/down
    Can be called by n8n webhook or frontend
    """
    data = request.get_json()
    
    quiz_analytics = data.get('quiz_analytics')
    chat_history = data.get('chat_history', [])
    
    result = AIService.analyze_level_progression(quiz_analytics, chat_history)
    
    return jsonify(result), 200


@chat_bp.route('/groq', methods=['POST'])
@jwt_required()
def chat_groq():
    """
    Chat via Groq API using DeepAgentRouter + KnowledgeStateService.

    Expected payload:
    {
        "message": "Explain gradient descent",
        "profile": { "skill_level": "intermediate", ... },
        "chat_history": [ {"role": "user", "content": "..."}, ... ]
    }

    JWT identity supplies user_id automatically.
    """
    try:
        data = request.get_json()
        message = data.get('message')
        profile = data.get('profile', {})
        chat_history = data.get('chat_history', [])

        if not message:
            return jsonify({"error": "Message is required"}), 400

        user_id = get_jwt_identity()

        # 1. Load server-side knowledge state
        ks = KnowledgeStateService.get(user_id)

        # 2. Run full pipeline: analyse → route → prompt → Groq
        result = DeepAgentRouter.generate(
            message=message,
            profile=profile,
            knowledge_state=ks,
            chat_history=chat_history,
            user_id=user_id,
        )

        if not result.get('success'):
            return jsonify({"success": False, "error": result.get('error', 'Unknown error')}), 500

        analysis = result.get('analysis', {})
        recs = analysis.get('recommendations', {})

        mode = result.get('tutoring_mode')
        reason = result.get('mode_reason')
        if not mode:
            mode, reason = AdaptiveModeService.decide_mode(
                learner_level=ks.get('skill_level', 'intermediate'),
                uncertainty_markers=analysis.get('message_analysis', {}).get('uncertainty_markers', 0),
                misconception_detected=recs.get('misconception_detected', False),
                emotional_state=recs.get('emotional_state', 'neutral'),
                low_mastery_detected=False,
                user_preference=ks.get('conversation_preferences', {}).get('adaptive_preference'),
            )
        recs['tutoring_mode'] = mode
        recs['mode_reason'] = reason

        # 3. Update knowledge state from analysis (server-side analytics)
        try:
            KnowledgeStateService.update_from_analysis(user_id, analysis, message)
        except Exception as e:
            logger.warning("Failed to update knowledge state: %s", e)

        # 4. Save interaction to DB (replaces old 'conversations' save)
        try:
            interactions = Database.get_collection('interactions')
            interactions.insert_one({
                "user_id": user_id,
                "user_message": message,
                "ai_response": result['response'],
                "agent": result['agent'],
                "agent_name": result.get('agent_name', ''),
                "tokens_used": result.get('tokens_used', 0),
                "response_time_ms": result.get('response_time_ms', 0),
                "analysis": {
                    "topics": analysis.get('topics', []),
                    "complexity": analysis.get('complexity', 'intermediate'),
                    "question_type": analysis.get('question_type', 'general'),
                    "method": analysis.get('analysis_method', 'keywords'),
                    "mode": mode,
                    "mode_reason": reason,
                    "generation": result.get('generation', {}),
                },
                "tutoring_mode": mode,
                "mode_reason": reason,
                "timestamp": datetime.utcnow().isoformat(),
            })
        except Exception as e:
            logger.warning("Failed to save interaction: %s", e)

        # 5. Bump user stats counter
        try:
            users = Database.get_collection('users')
            users.update_one(
                {"user_id": user_id},
                {"$inc": {"stats.total_conversations": 1, "stats.total_tokens": result.get('tokens_used', 0)}},
            )
        except Exception as e:
            logger.warning("Failed to update user stats: %s", e)

        # 6. Return response + lightweight metadata
        logger.debug(
            "chat_groq return mode=%s reason=%s analysis_mode=%s",
            mode,
            reason,
            analysis.get('recommendations', {}).get('tutoring_mode'),
        )

        return jsonify({
            "success": True,
            "response": result['response'],
            "model": "llama-3.3-70b-versatile",
            "agent": result['agent'],
            "agent_name": result.get('agent_name', ''),
            "tokens_used": result.get('tokens_used', 0),
            "mode": mode,
            "reason": reason,
            "analysis": {
                "topics": analysis.get('topics', []),
                "complexity": analysis.get('complexity'),
                "question_type": analysis.get('question_type'),
                "mode": mode,
                "mode_reason": reason,
            },
            "generation": result.get('generation', {}),
        }), 200

    except Exception as e:
        logger.error("Groq chat error: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500
