
//##################3##############################################################################3


import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import useAuth from '../hooks/useAuth';
import api from '../api/axios';
import Sidebar from '../components/Sidebar';
import { formatTimestamp, ChatHistory } from '../utils/helpers';

const SUGGESTIONS = {
  'Data Science': ['What is data cleaning?', 'Explain correlation vs causation', 'How do I handle missing values?'],
  'Machine Learning': ['What is gradient descent?', 'Explain overfitting', 'What are ensemble methods?'],
  'Deep Learning': ['What is backpropagation?', 'Explain CNN architecture', 'How do transformers work?'],
};

const STORAGE_PREFIX = 'adaptiveai';
const profilePicKey = (userKey) => `${STORAGE_PREFIX}:${userKey}:profilePic`;

export default function Chat() {
  const { t } = useTranslation();
  const { user, profile, setProfile, chatMessages, setChatMessages, saveContext, selectedTone } = useAuth();

  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [currentSession, setCurrentSession] = useState(null);
  const [activeMode, setActiveMode] = useState('direct');
  const [modeReason, setModeReason] = useState('stable understanding detected');

  // ✅ One state controls sidebar + overlay + chat layout
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const userKey = useMemo(() => (user?.id || user?.email || 'guest'), [user?.id, user?.email]);

  const strongest = profile?.domain_analysis?.strongest_domain || 'Machine Learning';
  const suggestions = SUGGESTIONS[strongest] || SUGGESTIONS['Machine Learning'];

  // Auto scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chatMessages, isTyping]);

  // When user changes, reset in-memory session to avoid leaking between users
  useEffect(() => {
    setCurrentSession(null);
    setChatMessages([]);
  }, [userKey, setChatMessages]);

  // Initialize session
  useEffect(() => {
    if (!currentSession && userKey) {
      const sessions = ChatHistory.getSessions(userKey);
      if (sessions.length > 0) setCurrentSession(sessions[0]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [userKey]);

  const startNewChat = useCallback(() => {
    const session = ChatHistory.createSession(selectedTone || 'Adaptive Agent');
    ChatHistory.saveSession(userKey, session);
    setCurrentSession(session);
    setChatMessages([]);
    inputRef.current?.focus();
  }, [userKey, selectedTone, setChatMessages]);

  const loadSession = useCallback((sessionId) => {
    const session = ChatHistory.getSession(userKey, sessionId);
    if (!session) return;

    setCurrentSession(session);

    const msgs = session.messages.map((m) => ({
      role: m.sender,
      content: m.text,
      timestamp: m.timestamp ? new Date(m.timestamp).getTime() : Date.now(),
    }));

    setChatMessages(msgs);

    // Optional: on mobile, close sidebar after selecting chat
    if (window.innerWidth <= 1024) setSidebarOpen(false);
  }, [userKey, setChatMessages]);

  const deleteSession = useCallback((sessionId) => {
    ChatHistory.deleteSession(userKey, sessionId);
    if (currentSession?.id === sessionId) {
      setCurrentSession(null);
      setChatMessages([]);
    }
  }, [userKey, currentSession, setChatMessages]);

  // ── analyzeAndUpdateProfile REMOVED ──
  // All analytics are now computed server-side in KnowledgeStateService.update_from_analysis()
  // which is called automatically by the /chat/groq endpoint.

  // Send message
  const sendMessage = async (text) => {
    if (!text.trim()) return;
    const userMsg = text.trim();
    setInput('');

    // ✅ Local intercept: answer "what is my name" AND still show/save the user message
    const normalized = userMsg.toLowerCase().trim();
    const isAskingName =
      normalized === 'what is my name' ||
      normalized === "what's my name" ||
      normalized === 'tell me my name' ||
      normalized.includes('my name');

    if (isAskingName) {
      const myName =
        user?.name ||
        profile?.full_name ||
        profile?.name ||
        (user?.email ? user.email.split('@')[0] : '');

      if (myName) {
        // ensure session exists
        let session = currentSession;
        if (!session) {
          session = ChatHistory.createSession(selectedTone || 'Adaptive Agent');
          ChatHistory.saveSession(userKey, session);
          setCurrentSession(session);
        }

        // 1) add user message to UI + history
        const userBubble = { role: 'user', content: userMsg, timestamp: Date.now() };
        setChatMessages((prev) => [...prev, userBubble]);

        ChatHistory.addMessage(userKey, session.id, {
          text: userMsg,
          sender: 'user',
          timestamp: new Date().toISOString(),
        });

        // 2) add AI response to UI + history
        const aiText = `Your name is **${myName}**.`;
        const aiBubble = { role: 'agent', content: aiText, timestamp: Date.now() };
        setChatMessages((prev) => [...prev, aiBubble]);
        setActiveMode('direct');
        setModeReason('identity lookup request');

        ChatHistory.addMessage(userKey, session.id, {
          text: aiText,
          sender: 'agent',
          timestamp: new Date().toISOString(),
        });

        return; // ✅ do not call the API
      }
    }

    // Normal flow
    const newMsgs = [...chatMessages, { role: 'user', content: userMsg, timestamp: Date.now() }];
    setChatMessages(newMsgs);

    let session = currentSession;
    if (!session) {
      session = ChatHistory.createSession(selectedTone || 'Adaptive Agent');
      ChatHistory.saveSession(userKey, session);
      setCurrentSession(session);
    }

    ChatHistory.addMessage(userKey, session.id, { text: userMsg, sender: 'user', timestamp: new Date().toISOString() });
    setIsTyping(true);

    try {
      const chatHistory = newMsgs
        .slice(-10)
        .map((m) => ({ role: m.role === 'user' ? 'user' : 'assistant', content: m.content }));

      setProfile((prev) => prev ? { ...prev, conversation_count: (prev.conversation_count || 0) + 1 } : prev);

      const profilePayload = {
        ...profile,

        // ✅ send identity so backend can inject into system prompt (still isolated)
        user_name: user?.name || profile?.full_name || profile?.name || '',
        user_email: user?.email || '',
        user_id: user?.id || '',

        skill_level: profile?.python || profile?.estimated_skill_level || 'intermediate',
        learning_tone: profile?.tone || 'Friendly',
        strongest_domain: profile?.strongestDomain || profile?.major || 'general',
      };

      const { data } = await api.post('/chat/groq', {
        user_id: user?.id,
        message: userMsg,
        profile: profilePayload,
        chat_history: chatHistory,
      });

      setIsTyping(false);

      if (data.success && data.response) {
        const aiMsg = { role: 'agent', content: data.response, timestamp: Date.now() };
        setChatMessages((prev) => [...prev, aiMsg]);

        if (data.mode) setActiveMode(data.mode);
        if (data.reason) setModeReason(data.reason);

        ChatHistory.addMessage(userKey, session.id, { text: data.response, sender: 'agent', timestamp: new Date().toISOString() });

        // Analytics are now handled server-side automatically
        saveContext();
      } else {
        throw new Error(data.error || 'API error');
      }
    } catch (err) {
      setIsTyping(false);
      const errMsg = { role: 'agent', content: 'Sorry, I encountered an error. Please try again.', timestamp: Date.now() };
      setChatMessages((prev) => [...prev, errMsg]);
      console.error('Chat error:', err);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage(input);
    }
  };

  const profileScore = profile?.domain_analysis
    ? `${(profile.domain_analysis.overall_accuracy || 0).toFixed(0)}%`
    : (profile?.estimated_skill_level || 'Beginner');

  const profileStrongest = profile?.domain_analysis
    ? profile.domain_analysis.strongest_domain?.split(' ')[0]
    : 'General';

  const profileTone = profile?.tone || profile?.preferences?.learning_style || 'Friendly';

  const prettyMode = activeMode
    .split('_')
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(' ');

  useEffect(() => {
    console.debug('[Chat badge mode]', { activeMode, modeReason });
  }, [activeMode, modeReason]);

  return (
    <div className={`chat-view-with-sidebar ${sidebarOpen ? '' : 'sidebar-collapsed'}`}>
      <Sidebar
        onNewChat={startNewChat}
        onLoadSession={loadSession}
        onDeleteSession={deleteSession}
        currentSessionId={currentSession?.id}
        sidebarOpen={sidebarOpen}
        setSidebarOpen={setSidebarOpen}
      />

      <div className="chat-main">
        <div className="chat-header">
          {!sidebarOpen && (
            <button
              className="sidebar-open-btn"
              onClick={() => setSidebarOpen(true)}
              aria-label={t('chat.openSidebar')}
              type="button"
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="3" y1="12" x2="21" y2="12" />
                <line x1="3" y1="6" x2="21" y2="6" />
                <line x1="3" y1="18" x2="21" y2="18" />
              </svg>
            </button>
          )}

          <div className="chat-header-info">
            <h3 id="studentNameDisplay">{user?.name || profile?.name || t('common.student')}</h3>
            <div className="chat-header-stats">
              <span className="stat-chip">{profileScore}</span>
              <span className="stat-chip">{profileStrongest}</span>
              <span className="stat-chip">{profileTone}</span>
              <span className="stat-chip" title={modeReason}>{t('chat.modeLabel')}: {prettyMode}</span>
            </div>
          </div>
        </div>

        <div className="chat-messages" id="chatMessages">
          {chatMessages.length === 0 && (
            <div className="welcome-message">
              <div className="welcome-icon">
                <svg viewBox="0 0 32 32" fill="none">
                  <path d="M16 3L27 9.5V22.5L16 29L5 22.5V9.5L16 3Z" stroke="url(#hexWelcome)" strokeWidth="2" fill="none" />
                  <defs>
                    <linearGradient id="hexWelcome" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" style={{ stopColor: '#667eea' }} />
                      <stop offset="50%" style={{ stopColor: '#764ba2' }} />
                      <stop offset="100%" style={{ stopColor: '#f093fb' }} />
                    </linearGradient>
                  </defs>
                </svg>
              </div>
              <h3>{t('chat.welcomeTitle', { name: user?.name || t('common.student') })}</h3>
              <p>{t('chat.welcomeSubtitle')}</p>
            </div>
          )}

          {chatMessages.map((msg, i) => (
            <MessageBubble key={i} message={msg} userKey={userKey} />
          ))}

          {isTyping && (
            <div className="message-enhanced agent-message">
              <div className="message-enhanced-avatar">
                <HexagonAvatar />
              </div>
              <div className="message-enhanced-wrapper">
                <div className="message-enhanced-content loading-message">
                  <img src="/favicon.svg" className="loading-icon" alt={t('chat.typingAlt')} />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {chatMessages.length === 0 && (
          <div className="chat-suggestions">
            {suggestions.map((text, i) => (
              <button key={i} className="suggestion-chip" onClick={() => sendMessage(text)} type="button">
                {text}
              </button>
            ))}
          </div>
        )}

        <form className="chat-input-container" onSubmit={(e) => { e.preventDefault(); sendMessage(input); }}>
          <textarea
            ref={inputRef}
            className="chat-input"
            id="chatInput"
            value={input}
            onChange={(e) => {
              setInput(e.target.value);
              e.target.style.height = 'auto';
              e.target.style.height = Math.min(e.target.scrollHeight, 120) + 'px';
            }}
            onKeyDown={handleKeyDown}
            placeholder={t('chat.inputPlaceholder')}
            rows={1}
          />
          <button type="submit" className="chat-send-btn" disabled={!input.trim() || isTyping}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="22" y1="2" x2="11" y2="13" />
              <polygon points="22 2 15 22 11 13 2 9 22 2" />
            </svg>
          </button>
        </form>
      </div>
    </div>
  );
}

function HexagonAvatar() {
  return (
    <svg viewBox="0 0 32 32" fill="none">
      <path d="M16 3L27 9.5V22.5L16 29L5 22.5V9.5L16 3Z" stroke="url(#hexStroke)" strokeWidth="2" fill="none" />
      <defs>
        <linearGradient id="hexStroke" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" style={{ stopColor: '#667eea' }} />
          <stop offset="50%" style={{ stopColor: '#764ba2' }} />
          <stop offset="100%" style={{ stopColor: '#f093fb' }} />
        </linearGradient>
      </defs>
    </svg>
  );
}

function MessageBubble({ message, userKey }) {
  const isUser = message.role === 'user';
  const profilePic = localStorage.getItem(profilePicKey(userKey));

  return (
    <div className={`message-enhanced ${isUser ? 'user-message' : 'agent-message'}`}>
      {!isUser && (
        <div className="message-enhanced-avatar">
          <HexagonAvatar />
        </div>
      )}

      <div className="message-enhanced-wrapper">
        <div className="message-enhanced-content">{message.content}</div>
        <div className="message-enhanced-timestamp">{formatTimestamp(message.timestamp || new Date().toISOString())}</div>
      </div>

      {isUser && (
        <div
          className="message-enhanced-avatar"
          style={profilePic ? { backgroundImage: `url(${profilePic})`, backgroundSize: 'cover', backgroundPosition: 'center' } : {}}
        >
          {!profilePic && (
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z" />
            </svg>
          )}
        </div>
      )}
    </div>
  );
}
