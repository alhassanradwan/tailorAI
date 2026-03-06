
import { createContext, useState, useEffect, useCallback, useRef } from 'react';
import api from '../api/axios';
import { migrateChatHistory, migrateProfilePicture } from '../utils/helpers';

const AuthContext = createContext(null);

// Lightweight profile defaults (analytics now live server-side in knowledge_states collection)
function ensureProfileFields(profile) {
  if (!profile) return profile;
  return {
    ...profile,
    strong_topics: profile.strong_topics || [],
    weak_topics: profile.weak_topics || [],
  };
}

// Storage helpers
const STORAGE_PREFIX = 'adaptiveai';
const gk = (name) => `${STORAGE_PREFIX}:global:${name}`;
const uk = (userKey, name) => `${STORAGE_PREFIX}:${userKey}:${name}`;

// ✅ One-time migration guard key
const migratedKey = (userKey) => `${STORAGE_PREFIX}:${userKey}:migrated_v1`;

// ✅ Run migrations only once per userKey
function runMigrationsOnce(userKey, email) {
  if (!userKey) return;

  const already = localStorage.getItem(migratedKey(userKey));
  if (already === 'true') return;

  migrateChatHistory(userKey, email);
  migrateProfilePicture(userKey);

  localStorage.setItem(migratedKey(userKey), 'true');
  console.log(`✅ Migrations completed and guarded for userKey=${userKey}`);
}

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);         // { email, name, id, isAdmin }
  const [profile, setProfile] = useState(null);   // full learner profile
  const [loading, setLoading] = useState(true);   // initial session check
  const [chatMessages, setChatMessages] = useState([]);
  const [currentStep, setCurrentStep] = useState(1);
  const [selectedTone, setSelectedTone] = useState(null);

  // ─── Token helpers ───
  const setTokens = (access, refresh) => {
    localStorage.setItem(gk('access_token'), access);
    localStorage.setItem(gk('refresh_token'), refresh);

    // legacy compatibility (if anything still reads these)
    localStorage.setItem('access_token', access);
    localStorage.setItem('refresh_token', refresh);
  };

  const getAccessToken = () => localStorage.getItem(gk('access_token')) || localStorage.getItem('access_token');
//   const getRefreshToken = () => localStorage.getItem(gk('refresh_token')) || localStorage.getItem('refresh_token');

  const clearSession = useCallback(() => {
    localStorage.removeItem(gk('access_token'));
    localStorage.removeItem(gk('refresh_token'));
    localStorage.removeItem(gk('current_user_key'));

    // legacy keys
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    localStorage.removeItem('last_logged_in_user');
    localStorage.removeItem('admin_auth');

    setUser(null);
    setProfile(null);
    setChatMessages([]);
    setCurrentStep(1);
    setSelectedTone(null);
  }, []);

  const cacheUser = useCallback((u) => {
    if (!u) return;
    const userKey = u.id || u.email;
    if (!userKey) return;

    localStorage.setItem(gk('current_user_key'), userKey);
    localStorage.setItem(uk(userKey, 'auth_user'), JSON.stringify(u));

    if (u.email) localStorage.setItem('last_logged_in_user', u.email);
    if (u.isAdmin) localStorage.setItem('admin_auth', 'true');
    else localStorage.removeItem('admin_auth');
  }, []);

  const restoreCachedUser = useCallback(() => {
    const currentUserKey = localStorage.getItem(gk('current_user_key'));
    if (!currentUserKey) return null;

    const cached = localStorage.getItem(uk(currentUserKey, 'auth_user'));
    if (!cached) return null;

    try {
      return JSON.parse(cached);
    } catch {
      return null;
    }
  }, []);

  // ─── Save context to backend ───
  const saveContext = useCallback(async () => {
    const token = getAccessToken();
    if (!token) return;

    try {
      await api.post('/context/save', {
        profile,
        quiz_progress: { quizIndex: 0, score: 0, analytics: [], domainScores: {} },
        active_chat_id: null,
        chat_messages: chatMessages,
        onboarding_step: currentStep,
        selected_agent: selectedTone,
      });
    } catch (err) {
      console.error('Failed to save context:', err);
    }
  }, [profile, chatMessages, currentStep, selectedTone]);

  // ✅ Keep saveContext ref updated for intervals
  const saveContextRef = useRef(saveContext);
  useEffect(() => {
    saveContextRef.current = saveContext;
  }, [saveContext]);

  // ─── Load context from backend ───
  const loadContext = useCallback(async () => {
    const token = getAccessToken();
    if (!token) return;

    try {
      const { data } = await api.get('/context/load');
      if (data.profile) setProfile(ensureProfileFields(data.profile));
      if (data.chat_messages?.length) setChatMessages(data.chat_messages);
      if (data.onboarding_step) setCurrentStep(data.onboarding_step);
      if (data.selected_agent) setSelectedTone(data.selected_agent);
    } catch (err) {
      console.error('Failed to load context:', err);
    }
  }, []);

  // ─── Login ───
  const login = async (email, password) => {
    const { data } = await api.post('/auth/login', { email, password });

    if (data.user) {
      setTokens(data.access_token, data.refresh_token);

      const u = {
        email,
        name: data.user.profile?.full_name || data.user.username || email.split('@')[0],
        id: data.user._id || data.user.id,
        isAdmin: data.user.is_admin || false,
      };

      setUser(u);
      cacheUser(u);

      // ✅ run migrations only once
      runMigrationsOnce(u.id || u.email, u.email);

      if (data.user.profile) setProfile(ensureProfileFields(data.user.profile));

      await loadContext();
      setLoading(false);
      return u;
    }

    throw new Error(data.error || 'Login failed');
  };

  // ─── Signup ───
  const signup = async (name, email, password) => {
    const { data } = await api.post('/auth/signup', {
      username: email.split('@')[0],
      email,
      password,
      full_name: name,
    });

    if (data.user) {
      setTokens(data.access_token, data.refresh_token);

      const u = {
        email,
        name,
        id: data.user._id || data.user.id,
        isAdmin: data.user.is_admin || false,
      };

      setUser(u);
      cacheUser(u);

      // ✅ run migrations only once
      runMigrationsOnce(u.id || u.email, u.email);

      setLoading(false);
      return u;
    }

    throw new Error(data.error || 'Signup failed');
  };

  // ─── Logout ───
  const logout = async () => {
    try {
      const token = getAccessToken();
      if (token) await api.post('/auth/logout');
    } catch {
      // ignore
    }
    clearSession();
  };

  // ─── Update profile wrapper ───
  const updateProfile = useCallback((updater) => {
    setProfile((prev) => {
      const updated = typeof updater === 'function' ? updater(prev) : updater;
      return ensureProfileFields(updated);
    });
  }, []);

  // ─── Reset in-memory chat messages when user changes ───
  useEffect(() => {
    setChatMessages([]);
  }, [user?.id, user?.email]);

  // ─── Check session on mount ───
  useEffect(() => {
    const checkSession = async () => {
      // restore cached user early (prevents "User" flicker)
      const cached = restoreCachedUser();
      if (cached) setUser(cached);

      const token = getAccessToken();
      if (!token) {
        setLoading(false);
        return;
      }

      try {
        const { data } = await api.get('/profile/get');

        if (data.success && data.user) {
          const userDoc = data.user;
          const u = {
            email: userDoc.email || cached?.email || localStorage.getItem('last_logged_in_user') || '',
            name: userDoc.profile?.full_name || userDoc.username || cached?.name || '',
            id: userDoc._id || cached?.id || '',
            isAdmin: userDoc.is_admin || cached?.isAdmin || false,
          };

          setUser(u);
          cacheUser(u);

          // ✅ run migrations only once
          runMigrationsOnce(u.id || u.email, u.email);

          if (userDoc.profile) setProfile(ensureProfileFields(userDoc.profile));

          // Only load context if session is valid
          await loadContext();
        } else {
          // Server said success=false or no user — treat as logged out
          clearSession();
        }
        setLoading(false);
      } catch (err) {
        // 401/403 = invalid token → clear everything, don't retry
        console.warn('Session check failed:', err?.response?.status || err.message);
        clearSession();
        setLoading(false);
      }
    };

    checkSession();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // ─── Auto-save every 30s ───
  useEffect(() => {
    const interval = setInterval(() => {
      if (getAccessToken()) {
        saveContextRef.current();
      }
    }, 30000);
    return () => clearInterval(interval);
  }, []); // Stable interval, uses ref for latest saveContext

  // ─── Save on beforeunload ───
  useEffect(() => {
    const handler = () => {
      saveContextRef.current();
    };
    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, []); // Stable listener, uses ref for latest saveContext

  const value = {
    user,
    profile,
    loading,
    chatMessages,
    currentStep,
    selectedTone,
    login,
    signup,
    logout,
    setProfile: updateProfile,
    setChatMessages,
    setCurrentStep,
    setSelectedTone,
    saveContext,
    loadContext,
    setUser,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export default AuthContext;
