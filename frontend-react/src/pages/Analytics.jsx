import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';

export default function Analytics() {
  const { profile } = useAuth();
  const navigate = useNavigate();
  const ba = profile?.behavioral_analytics;

  if (!profile || !ba) {
    return (
      <section className="view active" id="analytics">
        <div className="analytics-container" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <h2>Learning Analytics</h2>
          <p style={{ color: 'var(--text-muted)', marginTop: 16 }}>No data yet. Start chatting to build your analytics!</p>
          <button className="btn-primary" onClick={() => navigate('/chat')} style={{ marginTop: 24 }}>Go to Chat</button>
        </div>
      </section>
    );
  }

  const cd = ba.complexity_distribution || { beginner: 0, intermediate: 0, advanced: 0 };
  const total = cd.beginner + cd.intermediate + cd.advanced;
  const bPct = total > 0 ? ((cd.beginner / total) * 100).toFixed(0) : 0;
  const iPct = total > 0 ? ((cd.intermediate / total) * 100).toFixed(0) : 0;
  const aPct = total > 0 ? ((cd.advanced / total) * 100).toFixed(0) : 0;

  const adapts = profile.current_adaptations || {};
  let badgeText = 'Normal Mode';
  let description = 'AI is providing balanced explanations tailored to your level';
  if (adapts.socratic_mode) { badgeText = 'Socratic Mode'; description = 'AI is using guided questioning to help you discover answers'; }
  else if (adapts.emotional_state === 'frustrated') { badgeText = 'Support Mode'; description = 'AI is providing extra encouragement and simplified explanations'; }
  else if (adapts.emotional_state === 'curious') { badgeText = 'Exploration Mode'; description = 'AI is offering deeper insights and advanced topics'; }

  return (
    <section className="view active" id="analytics">
      <div className="analytics-container">
        <div className="analytics-header">
          <button className="btn-back" onClick={() => navigate('/chat')}>← Back to Chat</button>
          <h2>Learning Analytics</h2>
          <p>Track your learning progress and Personalized AI insights</p>
        </div>

        {/* Overview cards */}
        <div className="analytics-grid">
          <div className="analytics-card glass-effect">
            <div className="analytics-card-label">Skill Level</div>
            <div className="analytics-card-value">{profile.skill_level || profile.python || 'Beginner'}</div>
          </div>
          <div className="analytics-card glass-effect">
            <div className="analytics-card-label">Questions Asked</div>
            <div className="analytics-card-value">{ba.engagement_metrics?.total_messages || 0}</div>
          </div>
          <div className="analytics-card glass-effect">
            <div className="analytics-card-label">Topics Explored</div>
            <div className="analytics-card-value">{Object.keys(ba.topics_discussed || {}).length}</div>
          </div>
          <div className="analytics-card glass-effect">
            <div className="analytics-card-label">Sessions</div>
            <div className="analytics-card-value">{profile.conversation_count || 0}</div>
          </div>
        </div>

        {/* Complexity Distribution */}
        <div className="analytics-section glass-effect">
          <h3>Complexity Distribution</h3>
          <div className="complexity-bars">
            <div className="complexity-row">
              <span className="complexity-label">Beginner</span>
              <div className="complexity-bar"><div className="complexity-fill beginner" style={{ width: `${bPct}%` }}></div></div>
              <span className="complexity-value">{cd.beginner} ({bPct}%)</span>
            </div>
            <div className="complexity-row">
              <span className="complexity-label">Intermediate</span>
              <div className="complexity-bar"><div className="complexity-fill intermediate" style={{ width: `${iPct}%` }}></div></div>
              <span className="complexity-value">{cd.intermediate} ({iPct}%)</span>
            </div>
            <div className="complexity-row">
              <span className="complexity-label">Advanced</span>
              <div className="complexity-bar"><div className="complexity-fill advanced" style={{ width: `${aPct}%` }}></div></div>
              <span className="complexity-value">{cd.advanced} ({aPct}%)</span>
            </div>
          </div>
        </div>

        {/* Strong & Weak Topics */}
        <div className="analytics-topics-row">
          <div className="analytics-section glass-effect">
            <h3> Strong Topics</h3>
            <div className="topic-tags">
              {(profile.strong_topics || []).length > 0
                ? profile.strong_topics.slice(0, 8).map((t) => <span key={t} className="topic-tag strong">✅ {t.replace(/_/g, ' ')}</span>)
                : <span className="analytics-empty">No mastered topics yet. Keep learning!</span>}
            </div>
          </div>
          <div className="analytics-section glass-effect">
            <h3> Topics in Progress</h3>
            <div className="topic-tags">
              {(profile.weak_topics || []).length > 0
                ? profile.weak_topics.slice(0, 8).map((t) => <span key={t} className="topic-tag weak">📚 {t.replace(/_/g, ' ')}</span>)
                : <span className="analytics-empty">No topics in progress yet</span>}
            </div>
          </div>
        </div>

        {/* Misconceptions */}
        <div className="analytics-section glass-effect">
          <h3> Misconceptions</h3>
          <div className="topic-tags">
            {(() => {
              const misc = profile.misconceptions || {};
              const active = Object.entries(misc).filter(([, v]) => v && !v.corrected);
              return active.length > 0
                ? active.slice(0, 6).map(([t]) => <span key={t} className="topic-tag misconception">🚨 {t.replace(/_/g, ' ')}</span>)
                : <span className="analytics-empty"> No misconceptions detected</span>;
            })()}
          </div>
        </div>

        {/* Adaptation Status */}
        <div className="analytics-section glass-effect">
          <h3> AI Personalization</h3>
          <div className="adaptation-badge">
            <span>{badgeText}</span>
          </div>
          <p className="adaptation-description">{description}</p>
        </div>
      </div>
    </section>
  );
}
