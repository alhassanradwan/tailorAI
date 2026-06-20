import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import useAuth from '../hooks/useAuth';

export default function Login() {
  const { t } = useTranslation();
  const [tab, setTab] = useState('login'); // 'login' | 'signup'
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [signupName, setSignupName] = useState('');
  const [signupEmail, setSignupEmail] = useState('');
  const [signupPassword, setSignupPassword] = useState('');
  const [signupConfirm, setSignupConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const navigate = useNavigate();
  const { login, signup } = useAuth();

  const handleLogin = async (e) => {
    e.preventDefault();
    if (!loginEmail || !loginPassword) return setError(t('login.errors.missingLogin'));
    setError('');
    setLoading(true);
    try {
      await login(loginEmail, loginPassword);
      navigate('/chat');
    } catch (err) {
      setError(err.response?.data?.error || err.message || t('login.errors.loginFailed'));
    } finally {
      setLoading(false);
    }
  };

  const handleSignup = async (e) => {
    e.preventDefault();
    if (!signupName || !signupEmail || !signupPassword || !signupConfirm) return setError(t('login.errors.missingSignup'));
    if (signupPassword !== signupConfirm) return setError(t('login.errors.passwordMismatch'));
    if (signupPassword.length < 6) return setError(t('login.errors.passwordShort'));
    setError('');
    setLoading(true);
    try {
      await signup(signupName, signupEmail, signupPassword);
      navigate('/chat');
    } catch (err) {
      setError(err.response?.data?.error || err.message || t('login.errors.signupFailed'));
    } finally {
      setLoading(false);
    }
  };

  return (
    <section className="view active" id="signin">
      <div className="hero-section">
        <div className="hero-badge">
          <svg width="16" height="16" viewBox="0 0 16 16" fill="currentColor">
            <path d="M8 15A7 7 0 1 1 8 1a7 7 0 0 1 0 14zm0 1A8 8 0 1 0 8 0a8 8 0 0 0 0 16z" />
            <path d="M8.93 6.588l-2.29.287-.082.38.45.083c.294.07.352.176.288.469l-.738 3.468c-.194.897.105 1.319.808 1.319.545 0 1.178-.252 1.465-.598l.088-.416c-.2.176-.492.246-.686.246-.275 0-.375-.193-.304-.533L8.93 6.588zM9 4.5a1 1 0 1 1-2 0 1 1 0 0 1 2 0z" />
          </svg>
          <span> {t('login.badge')}</span>
        </div>

        <h1 className="hero-title">
          {t('login.titleLine1')}<br />
          <span className="gradient-text">{t('login.titleLine2')}</span>
        </h1>

        <p className="hero-subtitle">
          {t('login.subtitle')}
        </p>

        <div className="auth-card glass-effect">
          <div className="auth-tabs">
            <button
              className={`auth-tab ${tab === 'login' ? 'active' : ''}`}
              onClick={() => { setTab('login'); setError(''); }}
              type="button"
            >
              {t('login.tabLogin')}
            </button>
            <button
              className={`auth-tab ${tab === 'signup' ? 'active' : ''}`}
              onClick={() => { setTab('signup'); setError(''); }}
              type="button"
            >
              {t('login.tabSignup')}
            </button>
          </div>

          {error && (
            <div
              className="auth-error"
              style={{ color: 'var(--error)', textAlign: 'center', marginBottom: 12, fontSize: 14 }}
            >
              ❌ {error}
            </div>
          )}

          {tab === 'login' ? (
            <form onSubmit={handleLogin}>
              <div className="form-group">
                <label>{t('login.email')}</label>
                <input
                  type="email"
                  value={loginEmail}
                  onChange={(e) => setLoginEmail(e.target.value)}
                  placeholder={t('login.placeholders.email')}
                  required
                />
              </div>

              <div className="form-group">
                <label>{t('login.password')}</label>
                <input
                  type="password"
                  value={loginPassword}
                  onChange={(e) => setLoginPassword(e.target.value)}
                  placeholder={t('login.placeholders.password')}
                  required
                />
              </div>

              <button type="submit" className="btn-primary btn-full" disabled={loading}>
                {loading ? (
                  <>
                    <span className="btn-spinner"></span> {t('login.loggingIn')}
                  </>
                ) : (
                  t('login.loginButton')
                )}
              </button>
            </form>
          ) : (
            <form onSubmit={handleSignup}>
              <div className="form-group">
                <label>{t('login.fullName')}</label>
                <input
                  type="text"
                  value={signupName}
                  onChange={(e) => setSignupName(e.target.value)}
                  placeholder={t('login.placeholders.name')}
                  required
                />
              </div>

              <div className="form-group">
                <label>{t('login.email')}</label>
                <input
                  type="email"
                  value={signupEmail}
                  onChange={(e) => setSignupEmail(e.target.value)}
                  placeholder={t('login.placeholders.email')}
                  required
                />
              </div>

              {/* UPDATED: Password + Confirm side-by-side */}
              <div className="form-row">
                <div className="form-group">
                  <label>{t('login.password')}</label>
                  <input
                    type="password"
                    value={signupPassword}
                    onChange={(e) => setSignupPassword(e.target.value)}
                    placeholder={t('login.placeholders.passwordMin')}
                    required
                  />
                </div>

                <div className="form-group">
                  <label>{t('login.confirmPassword')}</label>
                  <input
                    type="password"
                    value={signupConfirm}
                    onChange={(e) => setSignupConfirm(e.target.value)}
                    placeholder={t('login.placeholders.confirmPassword')}
                    required
                  />
                </div>
              </div>

              <button type="submit" className="btn-primary btn-full" disabled={loading}>
                {loading ? (
                  <>
                    <span className="btn-spinner"></span> {t('login.creatingAccount')}
                  </>
                ) : (
                  t('login.signupButton')
                )}
              </button>
            </form>
          )}
        </div>
      </div>
    </section>
  );
}
