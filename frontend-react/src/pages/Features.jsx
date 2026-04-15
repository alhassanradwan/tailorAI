import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import useAuth from '../hooks/useAuth';

export default function Features() {
  const { t } = useTranslation();
  const { user } = useAuth();
  const ctaPath = user ? '/chat' : '/login';
  return (
    <section className="view active" id="features">
      <div className="features-container">
        <h1 className="section-title gradient-text">{t('features.title')}</h1>
        <p className="section-subtitle">{t('features.subtitle')}</p>

        <div className="features-grid">
          <div className="feature-card glass-effect">
            <h3>{t('features.items.adaptiveTutor.title')}</h3>
            <p>{t('features.items.adaptiveTutor.description')}</p>
          </div>

          <div className="feature-card glass-effect">
            <h3>{t('features.items.learningAnalytics.title')}</h3>
            <p>{t('features.items.learningAnalytics.description')}</p>
          </div>

          <div className="feature-card glass-effect">
            <h3>{t('features.items.behavioralAnalysis.title')}</h3>
            <p>{t('features.items.behavioralAnalysis.description')}</p>
          </div>

          <div className="feature-card glass-effect">
            <h3>{t('features.items.personalizedApproach.title')}</h3>
            <p>{t('features.items.personalizedApproach.description')}</p>
          </div>

          <div className="feature-card glass-effect">
            <h3>{t('features.items.skillTracking.title')}</h3>
            <p>{t('features.items.skillTracking.description')}</p>
          </div>

          <div className="feature-card glass-effect">
            <h3>{t('features.items.chatHistory.title')}</h3>
            <p>{t('features.items.chatHistory.description')}</p>
          </div>
        </div>

        <div style={{ textAlign: 'center', marginTop: 40 }}>
          <Link to={ctaPath} className="btn-primary">{t('features.getStarted')}</Link>
        </div>
      </div>
    </section>
  );
}
