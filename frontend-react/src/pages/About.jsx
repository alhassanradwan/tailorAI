import { Link } from 'react-router-dom';

export default function About() {
  return (
    <section className="view active" id="about">
      <div className="about-container" style={{ maxWidth: 900, margin: '0 auto', padding: '4rem 2rem', textAlign: 'center' }}>
        <h1 className="section-title gradient-text">About TailorAI</h1>
        <p className="section-subtitle" style={{ color: 'var(--text-secondary)', fontSize: '1.25rem', lineHeight: 1.8, marginTop: 16, marginBottom: 40 }}>
          TailorAI is a graduation project built to demonstrate how artificial intelligence can personalize education. Unlike traditional platforms that treat every student the same, TailorAI analyzes your learning patterns, question types, knowledge gaps, and preferences to create a truly individualized learning experience.
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem', marginBottom: 40 }}>
          <div className="glass-effect" style={{ padding: '2rem', borderRadius: 'var(--radius-xl)', textAlign: 'left' }}>
            <h3 style={{ marginBottom: 12 }}>4-Phase Analysis</h3>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              Behavioral analytics, skill progression tracking, knowledge state mastery scoring, and misconception detection work together to build a complete picture of each learner.
            </p>
          </div>
          <div className="glass-effect" style={{ padding: '2rem', borderRadius: 'var(--radius-xl)', textAlign: 'left' }}>
            <h3 style={{ marginBottom: 12 }}>Groq-Powered AI</h3>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              Leveraging Groq's ultra-fast LLM inference for real-time, context-aware responses. The AI receives your full profile with every message to tailor its teaching approach.
            </p>
          </div>
          <div className="glass-effect" style={{ padding: '2rem', borderRadius: 'var(--radius-xl)', textAlign: 'left' }}>
            <h3 style={{ marginBottom: 12 }}>Real-Time Personalization</h3>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              Automatically detects frustration, curiosity, and understanding. Switches between normal mode, Socratic questioning, and support mode based on your emotional state.
            </p>
          </div>
        </div>

        <div style={{ marginBottom: 40 }}>
          <h2 style={{ marginBottom: 12 }}>Built by Hassan Radwan</h2>
          <p style={{ color: 'var(--text-secondary)' }}>A graduation project demonstrating personalized AI in education.</p>
        </div>

        <Link to="/login" className="btn-primary btn-large">Try It Now</Link>
      </div>
    </section>
  );
}
