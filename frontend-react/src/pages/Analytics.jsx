import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import api from '../api/axios';

export default function Analytics() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [summary, setSummary] = useState(null);
  const [mastery, setMastery] = useState([]);
  const [miscItems, setMiscItems] = useState([]);
  const [loading, setLoading] = useState(true);

  // Fetch all analytics data from backend on mount
  useEffect(() => {
    if (!user) return;
    let cancelled = false;

    (async () => {
      try {
        const [sumRes, mastRes, miscRes] = await Promise.all([
          api.get('/analytics/summary'),
          api.get('/analytics/mastery-map'),
          api.get('/analytics/misconceptions'),
        ]);
        if (cancelled) return;
        if (sumRes.data.success) setSummary(sumRes.data.summary);
        if (mastRes.data.success) setMastery(mastRes.data.mastery || []);
        if (miscRes.data.success) setMiscItems(miscRes.data.misconceptions || []);
      } catch (err) {
        console.error('Failed to load analytics:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => { cancelled = true; };
  }, [user]);

  if (loading) {
    return (
      <section className="view active" id="analytics">
        <div className="analytics-container" style={{ textAlign: 'center', padding: '60px 20px' }}>
          <h2>Loading Analytics…</h2>
        </div>
      </section>
    );
  }

  if (!summary || summary.total_messages === 0) {
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

  const cd = summary.complexity_distribution || { beginner: 0, intermediate: 0, advanced: 0 };
  const total = cd.beginner + cd.intermediate + cd.advanced;
  const bPct = total > 0 ? ((cd.beginner / total) * 100).toFixed(0) : 0;
  const iPct = total > 0 ? ((cd.intermediate / total) * 100).toFixed(0) : 0;
  const aPct = total > 0 ? ((cd.advanced / total) * 100).toFixed(0) : 0;

  // Adaptation badge
  const prefs = summary.conversation_preferences || {};
  let badgeText = 'Normal Mode';
  let description = 'AI is providing balanced explanations tailored to your level';
  if (prefs.preferred_length === 'short') {
    badgeText = 'Concise Mode';
    description = 'AI is giving brief, focused answers as you requested';
  } else if (prefs.preferred_length === 'detailed') {
    badgeText = 'Deep Dive Mode';
    description = 'AI is providing thorough, in-depth explanations';
  }

  const activeMisc = miscItems.filter((m) => !m.corrected);

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
            <div className="analytics-card-value">{summary.skill_level || 'Beginner'}</div>
          </div>
          <div className="analytics-card glass-effect">
            <div className="analytics-card-label">Questions Asked</div>
            <div className="analytics-card-value">{summary.total_messages}</div>
          </div>
          <div className="analytics-card glass-effect">
            <div className="analytics-card-label">Topics Explored</div>
            <div className="analytics-card-value">{summary.topics_count}</div>
          </div>
          <div className="analytics-card glass-effect">
            <div className="analytics-card-label">Avg Mastery</div>
            <div className="analytics-card-value">{(summary.avg_mastery * 100).toFixed(0)}%</div>
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

        {/* Topic Mastery Map */}
        {mastery.length > 0 && (
          <div className="analytics-section glass-effect">
            <h3>Topic Mastery</h3>
            <div className="complexity-bars">
              {mastery.slice(0, 10).map((t) => (
                <div className="complexity-row" key={t.topic}>
                  <span className="complexity-label">{t.topic.replace(/_/g, ' ')}</span>
                  <div className="complexity-bar">
                    <div
                      className={`complexity-fill ${t.mastery_level >= 0.7 ? 'advanced' : t.mastery_level >= 0.4 ? 'intermediate' : 'beginner'}`}
                      style={{ width: `${(t.mastery_level * 100).toFixed(0)}%` }}
                    ></div>
                  </div>
                  <span className="complexity-value">{(t.mastery_level * 100).toFixed(0)}% ({t.interactions})</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Strong & Weak Topics */}
        <div className="analytics-topics-row">
          <div className="analytics-section glass-effect">
            <h3> Strong Topics</h3>
            <div className="topic-tags">
              {(summary.strong_topics || []).length > 0
                ? summary.strong_topics.slice(0, 8).map((t) => <span key={t} className="topic-tag strong">✅ {t.replace(/_/g, ' ')}</span>)
                : <span className="analytics-empty">No mastered topics yet. Keep learning!</span>}
            </div>
          </div>
          <div className="analytics-section glass-effect">
            <h3> Topics in Progress</h3>
            <div className="topic-tags">
              {(summary.weak_topics || []).length > 0
                ? summary.weak_topics.slice(0, 8).map((t) => <span key={t} className="topic-tag weak">📚 {t.replace(/_/g, ' ')}</span>)
                : <span className="analytics-empty">No topics in progress yet</span>}
            </div>
          </div>
        </div>

        {/* Misconceptions */}
        <div className="analytics-section glass-effect">
          <h3> Misconceptions</h3>
          <div className="topic-tags">
            {activeMisc.length > 0
              ? activeMisc.slice(0, 6).map((m) => (
                  <span key={m.topic} className="topic-tag misconception" title={m.detail}>
                    🚨 {m.topic.replace(/_/g, ' ')} ({m.count})
                  </span>
                ))
              : <span className="analytics-empty"> No misconceptions detected</span>}
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
