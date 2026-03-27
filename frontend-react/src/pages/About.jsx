import { Link } from 'react-router-dom';
import { useTranslation } from 'react-i18next';

export default function About() {
  const { t } = useTranslation();
  return (
    <section className="view active" id="about">
      <div className="about-container" style={{ maxWidth: 900, margin: '0 auto', padding: '4rem 2rem', textAlign: 'center' }}>
        <h1 className="section-title gradient-text">{t('about.title')}</h1>
        <p className="section-subtitle" style={{ color: 'var(--text-secondary)', fontSize: '1.25rem', lineHeight: 1.8, marginTop: 16, marginBottom: 40 }}>
          {t('about.subtitle')}
        </p>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '2rem', marginBottom: 40 }}>
          <div className="glass-effect" style={{ padding: '2rem', borderRadius: 'var(--radius-xl)', textAlign: 'left' }}>
            <h3 style={{ marginBottom: 12 }}>{t('about.cards.phaseAnalysis.title')}</h3>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              {t('about.cards.phaseAnalysis.description')}
            </p>
          </div>
          <div className="glass-effect" style={{ padding: '2rem', borderRadius: 'var(--radius-xl)', textAlign: 'left' }}>
            <h3 style={{ marginBottom: 12 }}>{t('about.cards.groqPowered.title')}</h3>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              {t('about.cards.groqPowered.description')}
            </p>
          </div>
          <div className="glass-effect" style={{ padding: '2rem', borderRadius: 'var(--radius-xl)', textAlign: 'left' }}>
            <h3 style={{ marginBottom: 12 }}>{t('about.cards.realtime.title')}</h3>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7 }}>
              {t('about.cards.realtime.description')}
            </p>
          </div>
        </div>

        <div style={{ marginBottom: 40 }}>
          <h2 style={{ marginBottom: 12 }}>{t('about.builtBy')}</h2>
          <p style={{ color: 'var(--text-secondary)' }}>{t('about.projectNote')}</p>
        </div>

        <Link to="/login" className="btn-primary btn-large">{t('about.cta')}</Link>
      </div>
    </section>
  );
}
