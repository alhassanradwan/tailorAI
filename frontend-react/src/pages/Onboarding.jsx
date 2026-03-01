import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';

const TONE_OPTIONS = ['Friendly', 'Professional', 'Socratic', 'Concise'];
const SKILL_LABELS = ['Beginner', 'Intermediate', 'Advanced'];

export default function Onboarding() {
  const { user, setProfile, saveContext, setCurrentStep: setGlobalStep, setSelectedTone: setGlobalTone, logout } = useAuth();
  const navigate = useNavigate();

  const [step, setStep] = useState(1);
  const [name, setName] = useState(user?.name || '');
  const [major, setMajor] = useState('');
  const [level, setLevel] = useState('');
  const [tone, setTone] = useState(null);
  const [pyLevel, setPyLevel] = useState(0);
  const [mathLevel, setMathLevel] = useState(0);
  const [consent, setConsent] = useState(false);

  const progress = (step / 2) * 100;

  const handleBackToLogin = async () => {
    await logout();
    navigate('/login');
  };

  const goToStep = (target) => {
    if (step === 1 && target > 1) {
      if (!name.trim() || !major.trim() || !level) {
        alert(' Please fill in all required fields (Name, Major, and Academic Level)');
        return;
      }
    }
    if (step === 2 && target > 2) {
      if (!tone) {
        alert(' Please select your learning style');
        return;
      }
    }
    setStep(target);
    setGlobalStep(target);
  };

  const handleStartLearning = () => {
    if (!consent) {
      alert(' Please consent to learning analytics to proceed');
      return;
    }

    const profileData = {
      email: user?.email,
      name: name.trim() || user?.name,
      major: major.trim(),
      level,
      tone: tone || 'Friendly',
      python: SKILL_LABELS[pyLevel],
      math: SKILL_LABELS[mathLevel],
      consent: true,
      created_at: new Date().toISOString(),
      preferences: {
        learning_style: tone || 'Friendly',
        skill_levels: {
          python: SKILL_LABELS[pyLevel],
          mathematics: SKILL_LABELS[mathLevel],
        },
      },
      estimated_skill_level: SKILL_LABELS[pyLevel],
      strong_topics: [],
      weak_topics: [],
      conversation_count: 0,
      behavioral_analytics: {
        question_types: { definition: 0, how_to: 0, why: 0, comparison: 0, debugging: 0, code_request: 0, general: 0 },
        topics_discussed: {},
        complexity_distribution: { beginner: 0, intermediate: 0, advanced: 0 },
        skill_progression: [],
        engagement_metrics: { total_messages: 0, avg_message_length: 0, follow_up_rate: 0, code_requests: 0, uncertainty_count: 0 },
        last_analyzed: null,
      },
      knowledge_state: {},
      misconceptions: {},
      conversation_preferences: {
        explanation_style: '',
        prefers_examples: false,
        prefers_code: false,
        prefers_analogies: false,
        preferred_tone: '',
        preferred_length: '',
      },
      current_adaptations: {
        socratic_mode: false,
        emotional_state: 'neutral',
        suggested_approach: 'explain_simply',
        comprehension_check: null,
      },
    };

    setProfile(profileData);
    setGlobalTone(tone);
    saveContext();
    navigate('/chat');
  };

  return (
    <section className="view active" id="onboarding">
      <div className="onboarding-container">
        {/* Back button */}
        <button className="btn-back" onClick={handleBackToLogin} style={{ marginBottom: 16 }}>
          ← Back to Sign In
        </button>

        <div className="progress-bar-container">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
          <span className="progress-text">{Math.round(progress)}% Complete</span>
        </div>

        {/* Step 1: Basic Info */}
        {step === 1 && (
          <div className="onboarding-step active">
            <h2 className="step-title">Tell us about yourself</h2>
            <p className="step-subtitle">Help us personalize your learning experience</p>

            <div className="form-group">
              <label>Full Name *</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder="Your full name" required />
            </div>

            <div className="form-group">
              <label>Major / Field of Study *</label>
              <input type="text" value={major} onChange={(e) => setMajor(e.target.value)} placeholder="e.g. Computer Science" required />
            </div>

            <div className="form-group">
              <label>Academic Level *</label>
              <select value={level} onChange={(e) => setLevel(e.target.value)} required>
                <option value="">Select your level</option>
                <option value="Freshman">Freshman</option>
                <option value="Sophomore">Sophomore</option>
                <option value="Junior">Junior</option>
                <option value="Senior">Senior</option>
                <option value="Graduate">Graduate</option>
                <option value="Professional">Professional</option>
              </select>
            </div>

            <button className="btn-primary btn-full" onClick={() => goToStep(2)}>
              Continue →
            </button>
          </div>
        )}

        {/* Step 2: Preferences */}
        {step === 2 && (
          <div className="onboarding-step active">
            <h2 className="step-title">Customize your experience</h2>
            <p className="step-subtitle">Choose your learning style and skill levels</p>

            <div className="form-group">
              <label>Learning Style *</label>
              <div className="selection-cards">
                {TONE_OPTIONS.map((t) => (
                  <div key={t} className={`selection-card ${tone === t ? 'selected' : ''}`} onClick={() => setTone(t)}>
                    <span>{t}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="form-group">
              <label>Python Skill Level: <strong>{SKILL_LABELS[pyLevel]}</strong></label>
              <input type="range" min="0" max="2" value={pyLevel} onChange={(e) => setPyLevel(Number(e.target.value))} />
            </div>

            <div className="form-group">
              <label>Mathematics Skill Level: <strong>{SKILL_LABELS[mathLevel]}</strong></label>
              <input type="range" min="0" max="2" value={mathLevel} onChange={(e) => setMathLevel(Number(e.target.value))} />
            </div>

            <div className="form-group consent-group">
              <label>
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
                <span> I consent to learning analytics to improve my experience</span>
              </label>
            </div>

            <div className="step-buttons">
              <button className="btn-secondary" onClick={() => goToStep(1)}>
                ← Back
              </button>
              <button className="btn-primary" onClick={handleStartLearning}>
                 Start Learning
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
