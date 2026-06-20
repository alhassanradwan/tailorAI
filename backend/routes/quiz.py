from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
import logging
from services.quiz import (
    QuizService,
    QuizGenerationAgent,
    build_wrong_answer_explanation_context,
    get_quiz_generation_summary,
)
from database import Database

quiz_bp = Blueprint('quiz', __name__)
logger = logging.getLogger(__name__)


@quiz_bp.route('/generate', methods=['POST'])
@jwt_required()
def generate_quiz():
    """
    Generate a quiz for the authenticated user.

    Expected payload
    ----------------
    {
        "message":        "give me a quiz on Neural Networks with 5 questions",
        "topic":          "Neural Networks",   # optional — extracted from message if absent
        "trigger_reason": "direct_request"     # optional
    }

    The FULL raw user message must be sent as "message" so that
    extract_topic_from_prompt() and extract_requested_count() can parse it.
    "topic" is only used when the caller has already resolved the topic
    server-side (e.g. from the chat router).
    """
    try:
        data           = request.get_json()
        # "message" is the raw user utterance — this is what drives topic + count extraction
        user_message   = (data.get('message') or data.get('user_prompt') or '').strip()
        # "topic" may be pre-resolved by the chat router; if absent it's extracted from message
        topic          = data.get('topic') or None
        trigger_reason = data.get('trigger_reason', 'direct_request')
        profile        = data.get('profile', {})
        user_id        = get_jwt_identity()

        if not user_message and not topic:
            return jsonify({
                "success": False,
                "error": "Provide either 'message' (raw user text) or 'topic'."
            }), 400

        quiz = QuizService.generate_quiz(
            user_id        = user_id,
            topic          = topic,          # None → extracted from message
            trigger_reason = trigger_reason,
            profile        = profile,
            user_prompt    = user_message,   # raw text for topic + count extraction
        )

        # Build a lightweight summary the chat agent can inject into its next turn
        chat_context = get_quiz_generation_summary(quiz)

        return jsonify({
            "success":      True,
            "quiz":         quiz,
            # The frontend/chat agent should store this and inject it into
            # the next system prompt so the agent knows a quiz was just created.
            "chat_context": chat_context,
        }), 200

    except Exception as e:
        logger.error("Error generating quiz: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500


@quiz_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit_quiz():
    """
    Submit answers for a completed quiz.

    Expected payload
    ----------------
    {
        "quiz_id": "uuid-...",
        "answers": {"q1": "B", "q2": "A", ...}
    }

    Returns the graded quiz plus a `chat_context` string the chat agent
    should inject into its next system prompt so it can explain wrong answers.
    """
    try:
        data    = request.get_json()
        quiz_id = data.get('quiz_id')
        answers = data.get('answers')

        if not quiz_id or not answers:
            return jsonify({
                "success": False,
                "error": "Missing quiz_id or answers"
            }), 400

        # submit_answers lives on QuizGenerationAgent (static method)
        graded = QuizGenerationAgent.submit_answers(
            quiz_id = quiz_id,
            answers = answers,
        )

        # Build the post-quiz explanation context for the chat agent
        chat_context = build_wrong_answer_explanation_context(graded)

        # Persist the explanation context in MongoDB against the user so the
        # chat route can pick it up on the next message without the frontend
        # having to pass it back.
        user_id = graded.get("user_id")
        if user_id and chat_context:
            try:
                Database.get_collection("quiz_chat_context").replace_one(
                    {"user_id": user_id},
                    {
                        "user_id":      user_id,
                        "quiz_id":      quiz_id,
                        "context":      chat_context,
                        "created_at":   graded.get("completed_at"),
                    },
                    upsert=True,
                )
            except Exception as db_err:
                logger.warning("Failed to persist quiz_chat_context: %s", db_err)

        return jsonify({
            "success":      True,
            "quiz":         graded,
            "chat_context": chat_context,
        }), 200

    except Exception as e:
        logger.error("Error submitting quiz: %s", e, exc_info=True)
        return jsonify({"success": False, "error": str(e)}), 500