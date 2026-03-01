"""
AdaptiveAI - Analytics Routes
Handles quiz analytics, learning patterns, and progress tracking
"""

from flask import Blueprint, request, jsonify
from database import Database
from datetime import datetime

analytics_bp = Blueprint('analytics', __name__)

@analytics_bp.route('/save', methods=['POST'])
def save_analytics():
    """
    Save complete quiz analytics after quiz completion
    This is called automatically by the frontend after the quiz
    
    Expected payload matches the auto-exported JSON structure
    """
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "No analytics data provided"}), 400
    
    try:
        analytics = Database.get_collection('analytics')
        
        # Add metadata
        data['saved_at'] = datetime.utcnow().isoformat()
        data['_id'] = f"{data.get('profile', {}).get('email', 'unknown')}_{datetime.utcnow().timestamp()}"
        
        analytics.insert_one(data)
        
        # Also update user profile if user exists
        user_email = data.get('profile', {}).get('email')
        if user_email:
            users = Database.get_collection('users')
            users.update_one(
                {"email": user_email},
                {
                    "$set": {
                        "profile": data.get('profile'),
                        "latest_quiz": data.get('quiz_metadata'),
                        "domain_analysis": data.get('domain_analysis'),
                        "learning_patterns": data.get('learning_patterns')
                    },
                    "$push": {
                        "quiz_history": {
                            "date": data.get('quiz_metadata', {}).get('ended_at'),
                            "score": data.get('performance', {}).get('final_score'),
                            "accuracy": data.get('performance', {}).get('accuracy_percentage')
                        }
                    }
                }
            )
        
        return jsonify({
            "success": True,
            "message": "Analytics saved successfully",
            "id": data['_id']
        }), 201
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route('/user/<email>', methods=['GET'])
def get_user_analytics(email):
    """Get all analytics for a specific user"""
    
    try:
        analytics = Database.get_collection('analytics')
        user_analytics = list(analytics.find(
            {"profile.email": email},
            {"_id": 0}
        ).sort("saved_at", -1))
        
        return jsonify({
            "success": True,
            "count": len(user_analytics),
            "analytics": user_analytics
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route('/progress/<email>', methods=['GET'])
def get_progress_report(email):
    """
    Generate a progress report for a user
    Shows improvement over time, strengths, weaknesses
    """
    
    try:
        analytics = Database.get_collection('analytics')
        user_analytics = list(analytics.find(
            {"profile.email": email}
        ).sort("saved_at", 1))
        
        if not user_analytics:
            return jsonify({
                "success": False,
                "error": "No analytics found for this user"
            }), 404
        
        # Calculate progress metrics
        progress = {
            "total_quizzes": len(user_analytics),
            "first_quiz_date": user_analytics[0].get('quiz_metadata', {}).get('started_at'),
            "latest_quiz_date": user_analytics[-1].get('quiz_metadata', {}).get('started_at'),
            "accuracy_trend": [],
            "level_progression": [],
            "domain_improvements": {
                "Data Science": [],
                "Machine Learning": [],
                "Deep Learning": []
            }
        }
        
        for session in user_analytics:
            perf = session.get('performance', {})
            patterns = session.get('learning_patterns', {})
            domain_acc = patterns.get('accuracy_by_domain', {})
            
            progress['accuracy_trend'].append({
                "date": session.get('quiz_metadata', {}).get('ended_at'),
                "accuracy": perf.get('accuracy_percentage', 0)
            })
            
            progress['level_progression'].append({
                "date": session.get('quiz_metadata', {}).get('ended_at'),
                "level": patterns.get('detected_level', 'Beginner')
            })
            
            for domain in progress['domain_improvements']:
                if domain in domain_acc:
                    progress['domain_improvements'][domain].append({
                        "date": session.get('quiz_metadata', {}).get('ended_at'),
                        "accuracy": domain_acc[domain]
                    })
        
        # Calculate overall improvement
        if len(progress['accuracy_trend']) >= 2:
            first_acc = progress['accuracy_trend'][0]['accuracy']
            last_acc = progress['accuracy_trend'][-1]['accuracy']
            progress['overall_improvement'] = last_acc - first_acc
        else:
            progress['overall_improvement'] = 0
        
        return jsonify({
            "success": True,
            "progress": progress
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


@analytics_bp.route('/webhook/n8n', methods=['POST'])
def n8n_webhook():
    """
    Webhook endpoint for n8n automation
    Can be used to trigger level updates, send notifications, etc.
    """
    data = request.get_json()
    
    action = data.get('action')
    
    if action == 'check_level_update':
        # Check if any users need level updates
        email = data.get('email')
        if email:
            users = Database.get_collection('users')
            user = users.find_one({"email": email})
            
            if user:
                current_level = user.get('domain_analysis', {}).get('detected_level', 'Beginner')
                latest_accuracy = user.get('latest_quiz', {}).get('accuracy', 0)
                
                # Level progression logic
                should_update = False
                new_level = current_level
                
                if current_level == 'Beginner' and latest_accuracy >= 80:
                    should_update = True
                    new_level = 'Intermediate'
                elif current_level == 'Intermediate' and latest_accuracy >= 85:
                    should_update = True
                    new_level = 'Advanced'
                
                if should_update:
                    users.update_one(
                        {"email": email},
                        {"$set": {"domain_analysis.detected_level": new_level}}
                    )
                
                return jsonify({
                    "updated": should_update,
                    "previous_level": current_level,
                    "new_level": new_level,
                    "accuracy": latest_accuracy
                }), 200
    
    return jsonify({"received": True, "action": action}), 200
