"""Admin aggregation service for dashboard endpoints."""

from collections import defaultdict
from database import Database


class AdminService:
    @staticmethod
    def get_users_overview(limit=100):
        users_coll = Database.get_collection('users')
        ks_coll = Database.get_collection('knowledge_states')

        users = list(
            users_coll.find(
                {},
                {
                    '_id': 1,
                    'email': 1,
                    'created_at': 1,
                    'is_admin': 1,
                },
            )
            .sort('created_at', -1)
            .limit(int(limit))
        )

        user_ids = [u.get('_id') for u in users if u.get('_id')]
        ks_docs = list(
            ks_coll.find(
                {'user_id': {'$in': user_ids}},
                {
                    '_id': 0,
                    'user_id': 1,
                    'behavioral.engagement_metrics.total_messages': 1,
                    'current_adaptations.tutoring_mode': 1,
                },
            )
        )

        ks_by_user = {d.get('user_id'): d for d in ks_docs}

        result = []
        for u in users:
            uid = u.get('_id')
            ks = ks_by_user.get(uid, {})
            total_messages = (
                ks.get('behavioral', {})
                .get('engagement_metrics', {})
                .get('total_messages', 0)
            )
            current_mode = (
                ks.get('current_adaptations', {})
                .get('tutoring_mode')
            )

            result.append({
                'id': uid,
                'email': u.get('email', ''),
                'created_at': u.get('created_at', ''),
                'is_admin': bool(u.get('is_admin', False)),
                'total_messages': int(total_messages or 0),
                'current_tutoring_mode': current_mode,
            })

        return result

    @staticmethod
    def get_analytics_summary(top_topics_limit=8):
        users_coll = Database.get_collection('users')
        interactions_coll = Database.get_collection('interactions')
        ks_coll = Database.get_collection('knowledge_states')

        total_users = users_coll.count_documents({})
        total_messages = interactions_coll.count_documents({})

        mastery_values = []
        topic_counts = defaultdict(int)

        for ks in ks_coll.find({}, {'_id': 0, 'topics': 1}):
            topics = ks.get('topics', {})
            if not isinstance(topics, dict):
                continue

            for topic, td in topics.items():
                if not isinstance(td, dict):
                    continue
                count = int(td.get('count', 0) or 0)
                mastery = td.get('mastery_level')

                if isinstance(mastery, (int, float)):
                    mastery_values.append(float(mastery))
                if count > 0:
                    topic_counts[topic] += count

        avg_mastery = round(sum(mastery_values) / len(mastery_values), 2) if mastery_values else 0.0

        top_topics = [
            {'topic': t, 'count': c}
            for t, c in sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)[: int(top_topics_limit)]
        ]

        return {
            'total_users': total_users,
            'total_messages': total_messages,
            'average_mastery': avg_mastery,
            'top_topics': top_topics,
        }

    @staticmethod
    def get_recent_interactions(limit=20):
        interactions_coll = Database.get_collection('interactions')

        docs = list(
            interactions_coll.find(
                {},
                {
                    '_id': 0,
                    'user_id': 1,
                    'user_message': 1,
                    'message': 1,
                    'tutoring_mode': 1,
                    'analysis.mode': 1,
                    'timestamp': 1,
                },
            )
            .sort('timestamp', -1)
            .limit(int(limit))
        )

        out = []
        for d in docs:
            out.append({
                'user_id': d.get('user_id', ''),
                'user_message': d.get('user_message') or d.get('message', ''),
                'tutoring_mode': d.get('tutoring_mode') or d.get('analysis', {}).get('mode'),
                'timestamp': d.get('timestamp', ''),
            })

        return out

    @staticmethod
    def get_user_detail(user_id, interactions_limit=10):
        users_coll = Database.get_collection('users')
        ks_coll = Database.get_collection('knowledge_states')
        interactions_coll = Database.get_collection('interactions')

        user_doc = users_coll.find_one({'_id': user_id}, {'_id': 1, 'email': 1})
        ks_doc = ks_coll.find_one({'user_id': user_id}, {'_id': 0}) or {}

        topics = ks_doc.get('topics', {}) if isinstance(ks_doc.get('topics', {}), dict) else {}
        mastery = []
        for topic, td in topics.items():
            if not isinstance(td, dict):
                continue
            mastery.append({
                'topic': topic,
                'mastery_level': td.get('mastery_level', 0),
                'interactions': td.get('count', 0),
            })

        mastery.sort(key=lambda x: x.get('mastery_level', 0), reverse=True)

        misconceptions_map = ks_doc.get('misconceptions', {}) if isinstance(ks_doc.get('misconceptions', {}), dict) else {}
        misconceptions = []
        for topic, md in misconceptions_map.items():
            if not isinstance(md, dict):
                continue
            misconceptions.append({
                'topic': topic,
                'detail': md.get('detail', ''),
                'count': md.get('count', 0),
                'corrected': md.get('corrected', False),
                'last_seen': md.get('last_seen'),
            })

        recent = list(
            interactions_coll.find(
                {'user_id': user_id},
                {
                    '_id': 0,
                    'user_message': 1,
                    'message': 1,
                    'tutoring_mode': 1,
                    'analysis.mode': 1,
                    'timestamp': 1,
                },
            )
            .sort('timestamp', -1)
            .limit(int(interactions_limit))
        )

        recent_interactions = []
        for r in recent:
            recent_interactions.append({
                'user_message': r.get('user_message') or r.get('message', ''),
                'tutoring_mode': r.get('tutoring_mode') or r.get('analysis', {}).get('mode'),
                'timestamp': r.get('timestamp', ''),
            })

        return {
            'user_id': user_id,
            'email': (user_doc or {}).get('email', ''),
            'knowledge_state': ks_doc,
            'mastery': mastery,
            'misconceptions': misconceptions,
            'mode_history': ks_doc.get('mode_history', []),
            'recent_interactions': recent_interactions,
        }
