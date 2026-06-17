import logging
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from services.deepresearch.graph import build_research_graph

logger = logging.getLogger(__name__)
research_bp = Blueprint('research', __name__)

class DeepResearchOrchestrator:
    """
    Service class to handle the Deep Research workflow steps via LangGraph
    """
    def __init__(self):
        self.graph = build_research_graph()

    def run(self, params: dict):
        topic = params.get("topic")
        user_id = params.get("user_id")

        initial_state = {
            "user_id": user_id,
            "topic": topic,
            "plan": [],
            "documents": [],
            "facts": [],
            "report": "",
            "sources": [],
            "critique": None,
            "revision_count": 0
        }

        final_state = self.graph.invoke(initial_state)

        return {
            "query": topic,
            "report": final_state.get("report", ""),
            "sources": final_state.get("sources", []),
            "quality": final_state.get("critique", {})
        }

# Singleton instance
deep_research_service = DeepResearchOrchestrator()


@research_bp.route('/deep-research', methods=['POST'])
@jwt_required()
def deep_research():
    try:
        data = request.get_json()
        user_id = get_jwt_identity()

        message = data.get("message")
        topic = data.get("topic") or message

        if not topic:
            return jsonify({"error": "topic required"}), 400

        result = deep_research_service.run({
            "user_id": user_id,
            "topic": topic,
            "depth": data.get("depth", "medium"),
            "max_sources": data.get("max_sources", 10)
        })

        return jsonify({
            "success": True,
            "report": result.get("report"),
            "sources": result.get("sources", [])
        }), 200

    except Exception as e:
        logger.error('Error in deep-research route: %s', e)
        return jsonify({"success": False, "error": str(e)}), 500