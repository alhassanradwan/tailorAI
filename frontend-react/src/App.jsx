import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import useAuth from './hooks/useAuth';
import ProtectedRoute from './components/ProtectedRoute';
import AdminRoute from './components/AdminRoute';
import Navbar from './components/Navbar';
import SpaceBackground from './components/SpaceBackground';
import Login from './pages/Login';
import Chat from './pages/Chat';
import Analytics from './pages/Analytics';
import Admin from './pages/Admin';
import Features from './pages/Features';
import About from './pages/About';
import './index.css';

function AppRoutes() {
  const { user, profile, loading, currentStep } = useAuth();

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
    return '/chat';
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
        <Route path="/chat" element={
          <ProtectedRoute><Chat /></ProtectedRoute>
        } />
        <Route path="/analytics" element={
          <ProtectedRoute><div className="container"><Analytics /></div></ProtectedRoute>
        } />
        <Route path="/admin" element={
          <AdminRoute><div className="container"><Admin /></div></AdminRoute>
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
