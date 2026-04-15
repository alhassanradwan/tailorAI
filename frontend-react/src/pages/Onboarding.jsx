import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import useAuth from '../hooks/useAuth';

const TONE_OPTIONS = ['Friendly', 'Professional', 'Socratic', 'Concise'];
const SKILL_LABELS = ['Beginner', 'Intermediate', 'Advanced'];

export default function Onboarding() {
  const { t } = useTranslation();
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
        alert(t('onboarding.alerts.missingStep1'));
        return;
      }
    }
    if (step === 2 && target > 2) {
      if (!tone) {
        alert(t('onboarding.alerts.missingTone'));
        return;
      }
    }
    setStep(target);
    setGlobalStep(target);
  };

  const handleStartLearning = () => {
    if (!consent) {
      alert(t('onboarding.alerts.missingConsent'));
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
          ← {t('onboarding.backToSignIn')}
        </button>

        <div className="progress-bar-container">
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
          <span className="progress-text">{t('onboarding.progressComplete', { value: Math.round(progress) })}</span>
        </div>

        {/* Step 1: Basic Info */}
        {step === 1 && (
          <div className="onboarding-step active">
            <h2 className="step-title">{t('onboarding.step1.title')}</h2>
            <p className="step-subtitle">{t('onboarding.step1.subtitle')}</p>

            <div className="form-group">
              <label>{t('onboarding.step1.fullName')}</label>
              <input type="text" value={name} onChange={(e) => setName(e.target.value)} placeholder={t('onboarding.step1.placeholders.name')} required />
            </div>

            <div className="form-group">
              <label>{t('onboarding.step1.major')}</label>
              <input type="text" value={major} onChange={(e) => setMajor(e.target.value)} placeholder={t('onboarding.step1.placeholders.major')} required />
            </div>

            <div className="form-group">
              <label>{t('onboarding.step1.academicLevel')}</label>
              <select value={level} onChange={(e) => setLevel(e.target.value)} required>
                <option value="">{t('onboarding.step1.selectLevel')}</option>
                <option value="Freshman">{t('onboarding.levels.freshman')}</option>
                <option value="Sophomore">{t('onboarding.levels.sophomore')}</option>
                <option value="Junior">{t('onboarding.levels.junior')}</option>
                <option value="Senior">{t('onboarding.levels.senior')}</option>
                <option value="Graduate">{t('onboarding.levels.graduate')}</option>
                <option value="Professional">{t('onboarding.levels.professional')}</option>
              </select>
            </div>

            <button className="btn-primary btn-full" onClick={() => goToStep(2)}>
              {t('common.continue')} →
            </button>
          </div>
        )}

        {/* Step 2: Preferences */}
        {step === 2 && (
          <div className="onboarding-step active">
            <h2 className="step-title">{t('onboarding.step2.title')}</h2>
            <p className="step-subtitle">{t('onboarding.step2.subtitle')}</p>

            <div className="form-group">
              <label>{t('onboarding.step2.learningStyle')}</label>
              <div className="selection-cards">
                {TONE_OPTIONS.map((toneOption) => (
                  <div key={toneOption} className={`selection-card ${tone === toneOption ? 'selected' : ''}`} onClick={() => setTone(toneOption)}>
                    <span>{t(`onboarding.tones.${toneOption.toLowerCase()}`)}</span>
                  </div>
                ))}
              </div>
            </div>

            <div className="form-group">
              <label>{t('onboarding.step2.pythonSkill')}: <strong>{t(`onboarding.skillLabels.${SKILL_LABELS[pyLevel].toLowerCase()}`)}</strong></label>
              <input type="range" min="0" max="2" value={pyLevel} onChange={(e) => setPyLevel(Number(e.target.value))} />
            </div>

            <div className="form-group">
              <label>{t('onboarding.step2.mathSkill')}: <strong>{t(`onboarding.skillLabels.${SKILL_LABELS[mathLevel].toLowerCase()}`)}</strong></label>
              <input type="range" min="0" max="2" value={mathLevel} onChange={(e) => setMathLevel(Number(e.target.value))} />
            </div>

            <div className="form-group consent-group">
              <label>
                <input type="checkbox" checked={consent} onChange={(e) => setConsent(e.target.checked)} />
                <span> {t('onboarding.step2.consent')}</span>
              </label>
            </div>

            <div className="step-buttons">
              <button className="btn-secondary" onClick={() => goToStep(1)}>
                ← {t('common.back')}
              </button>
              <button className="btn-primary" onClick={handleStartLearning}>
                {t('common.startLearning')}
              </button>
            </div>
          </div>
        )}
      </div>
    </section>
  );
}
