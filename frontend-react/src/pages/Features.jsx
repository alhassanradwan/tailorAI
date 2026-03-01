import { Link } from 'react-router-dom';

export default function Features() {
  return (
    <section className="view active" id="features">
      <div className="features-container">
        <h1 className="section-title gradient-text">Platform Features</h1>
        <p className="section-subtitle">Everything you need for adaptive AI-powered learning</p>

        <div className="features-grid">
          <div className="feature-card glass-effect">
            <h3>Adaptive AI Tutor</h3>
            <p>Personalizes explanations to match your skill level, learning style, and pace. The AI learns and adapts as you interact.</p>
          </div>

          <div className="feature-card glass-effect">
            <h3>Learning Analytics</h3>
            <p>Track your progress with detailed analytics — topics explored, skill progression, complexity distribution, and more.</p>
          </div>

          <div className="feature-card glass-effect">
            <h3>Behavioral Analysis</h3>
            <p>4-phase conversation analysis detects your question patterns, knowledge gaps, misconceptions, and learning preferences.</p>
          </div>

          <div className="feature-card glass-effect">
            <h3>Personalized Approach</h3>
            <p>Choose your learning style — Friendly, Professional, Socratic, or Concise — and the AI adapts its tone and method.</p>
          </div>

          <div className="feature-card glass-effect">
            <h3>Skill Tracking</h3>
            <p>Automatic skill level assessment that evolves with your conversations. Watch yourself grow from beginner to advanced.</p>
          </div>

          <div className="feature-card glass-effect">
            <h3>Chat History</h3>
            <p>All your conversations are saved and organized. Pick up where you left off or revisit past explanations.</p>
          </div>
        </div>

        <div style={{ textAlign: 'center', marginTop: 40 }}>
          <Link to="/login" className="btn-primary">Get Started</Link>
        </div>
      </div>
    </section>
  );
}
