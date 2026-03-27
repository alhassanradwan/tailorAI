import { Link, useLocation } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import { useTranslation } from 'react-i18next';
import LanguageSwitcher from './LanguageSwitcher';

export default function Navbar() {
  const location = useLocation();
  const { user } = useAuth();
  const { t } = useTranslation();

  const homePath = user ? '/chat' : '/login';

  // Hide navbar in chat view
  if (location.pathname === '/chat') return null;

  return (
    <nav className="navbar glass-effect">
      <div className="nav-container">
        <Link to={homePath} className="logo">
          <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
            <path
              d="M16 2L28 9V23L16 30L4 23V9L16 2Z"
              stroke="url(#navbarGradient)"
              strokeWidth="2"
              fill="none"
            />
            <defs>
              <linearGradient id="navbarGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style={{ stopColor: '#667EEA' }} />
                <stop offset="50%" style={{ stopColor: '#764BA2' }} />
                <stop offset="100%" style={{ stopColor: '#F093FB' }} />
              </linearGradient>
            </defs>
          </svg>
          <span>
            Tailor<strong>AI</strong>
          </span>
        </Link>

        <div className="nav-links">
          <Link to="/features">{t('navbar.features')}</Link>
          <Link to="/about">{t('navbar.about')}</Link>
          {user?.isAdmin && <Link to="/admin">{t('navbar.admin')}</Link>}
          <LanguageSwitcher />
        </div>
      </div>
    </nav>
  );
}

