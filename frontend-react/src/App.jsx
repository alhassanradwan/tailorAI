import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import useAuth from './hooks/useAuth';
import ProtectedRoute from './components/ProtectedRoute';
import Navbar from './components/Navbar';
import SpaceBackground from './components/SpaceBackground';
import Login from './pages/Login';
import Onboarding from './pages/Onboarding';
import Chat from './pages/Chat';
import Analytics from './pages/Analytics';
import Features from './pages/Features';
import About from './pages/About';
import './index.css';

function AppRoutes() {
  const { user, profile, loading } = useAuth();

  if (loading) {
    return (
      <div className="loading-overlay loading-show">
        <div className="loading-spinner"></div>
        <div className="loading-text">Loading AdaptiveAI...</div>
      </div>
    );
  }

  // Determine where to redirect logged-in users
  const getAuthRedirect = () => {
    if (!user) return '/login';
    // Check if user has completed onboarding
    // A user has completed onboarding if they have any of these:
    // - consent is true
    // - domain_analysis exists
    // - major/level exists (from onboarding)
    // - behavioral_analytics exists with data
    if (profile) {
      const hasCompletedOnboarding = 
        profile.consent === true || 
        profile.domain_analysis || 
        profile.major || 
        profile.level ||
        (profile.behavioral_analytics && Object.keys(profile.behavioral_analytics).length > 0);
      
      return hasCompletedOnboarding ? '/chat' : '/onboarding';
    }
    return '/onboarding';
  };

  return (
    <>
      <Navbar />
      <Routes>
        {/* Public routes — wrapped in .container for proper spacing */}
        <Route path="/login" element={user ? <Navigate to={getAuthRedirect()} replace /> : <div className="container"><Login /></div>} />
        <Route path="/features" element={<div className="container"><Features /></div>} />
        <Route path="/about" element={<div className="container"><About /></div>} />

        {/* Full-viewport routes (no .container padding) */}
        <Route path="/onboarding" element={
          <ProtectedRoute><div className="container"><Onboarding /></div></ProtectedRoute>
        } />
        <Route path="/chat" element={
          <ProtectedRoute><Chat /></ProtectedRoute>
        } />
        <Route path="/analytics" element={
          <ProtectedRoute><div className="container"><Analytics /></div></ProtectedRoute>
        } />

        {/* Default redirect */}
        <Route path="*" element={<Navigate to={user ? getAuthRedirect() : '/login'} replace />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <Router>
      <AuthProvider>
        <SpaceBackground />
        <AppRoutes />
      </AuthProvider>
    </Router>
  );
}
