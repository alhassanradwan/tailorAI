
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

const TONE_DROPDOWN_OPTIONS = [
  { value: 'auto', label: 'Auto' },
  { value: 'friendly', label: 'Friendly' },
  { value: 'professional', label: 'Professional' },
  { value: 'socratic', label: 'Socratic' },
  { value: 'concise', label: 'Concise' },
];

const MODE_DROPDOWN_OPTIONS = [
  { value: 'auto', label: 'Auto' },
  { value: 'direct', label: 'Direct' },
  { value: 'supportive', label: 'Supportive' },
  { value: 'socratic', label: 'Socratic' },
  { value: 'supportive_socratic', label: 'Supportive Socratic' },
];

const MAX_FILE_EXTRACT_CHARS = 7000;
const TEXT_FILE_EXTENSIONS = new Set([
  'txt', 'md', 'markdown', 'json', 'csv', 'tsv', 'xml', 'html', 'css', 'js', 'jsx', 'ts', 'tsx',
  'py', 'java', 'c', 'cpp', 'h', 'hpp', 'go', 'rs', 'php', 'rb', 'sql', 'yaml', 'yml', 'ini', 'log',
]);

function normalizeToneChoice(value) {
  const v = (value || '').toString().trim().toLowerCase();
  const allowed = new Set(['auto', 'friendly', 'professional', 'socratic', 'concise']);
  return allowed.has(v) ? v : 'auto';
}

function normalizeModeChoice(value) {
  const v = (value || '').toString().trim().toLowerCase();
  const allowed = new Set(['auto', 'direct', 'supportive', 'socratic', 'supportive_socratic']);
  return allowed.has(v) ? v : 'auto';
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isLikelyTextFile(file) {
  const fileName = (file?.name || '').toLowerCase();
  const extension = fileName.includes('.') ? fileName.split('.').pop() : '';
  const type = (file?.type || '').toLowerCase();

  if (type.startsWith('text/')) return true;
  if (type.includes('json') || type.includes('xml') || type.includes('javascript')) return true;
  if (extension && TEXT_FILE_EXTENSIONS.has(extension)) return true;

  return false;
}

export default function Chat() {
  const { t, i18n } = useTranslation();
  const { user, profile, setProfile, chatMessages, setChatMessages, saveContext, selectedTone } = useAuth();

  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [currentSession, setCurrentSession] = useState(null);
  const [activeMode, setActiveMode] = useState('direct');
  const [modeReason, setModeReason] = useState('stable understanding detected');
  const [toneChoice, setToneChoice] = useState('auto');
  const [modeChoice, setModeChoice] = useState('auto');
  const [isListening, setIsListening] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);

  // ✅ One state controls sidebar + overlay + chat layout
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const speechRecognitionRef = useRef(null);

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
        force_tone: toneChoice === 'auto' ? '' : toneChoice,
        force_tutoring_mode: modeChoice === 'auto' ? '' : modeChoice,
        adaptive_preference: modeChoice === 'auto' ? '' : modeChoice,
        conversation_preferences: {
          ...(profile?.conversation_preferences || {}),
          preferred_tone: toneChoice === 'auto' ? '' : (toneChoice === 'professional' ? 'formal' : toneChoice),
          preferred_length: toneChoice === 'concise' ? 'short' : ((profile?.conversation_preferences || {}).preferred_length || ''),
          adaptive_preference: modeChoice === 'auto' ? '' : modeChoice,
        },
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
      const status = err?.response?.status;
      const backendError = err?.response?.data?.error;
      const backendMsg = err?.response?.data?.msg;
      let friendlyError = 'Sorry, I encountered an error. Please try again.';

      if (status === 401) {
        friendlyError = 'Your session expired. Please log in again, then resend your message.';
      } else if (typeof backendError === 'string' && backendError.trim()) {
        friendlyError = backendError;
      } else if (typeof backendMsg === 'string' && backendMsg.trim()) {
        friendlyError = backendMsg;
      }

      const errMsg = { role: 'agent', content: friendlyError, timestamp: Date.now() };
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

  useEffect(() => {
    const prefToneRaw =
      profile?.conversation_preferences?.preferred_tone
      || profile?.tone
      || profile?.preferences?.learning_style
      || 'auto';
    const prefTone = prefToneRaw.toString().trim().toLowerCase();
    const mappedTone = prefTone === 'formal' ? 'professional' : prefTone;
    setToneChoice(normalizeToneChoice(mappedTone));

    const prefModeRaw =
      profile?.conversation_preferences?.adaptive_preference
      || profile?.adaptive_preference
      || 'auto';
    setModeChoice(normalizeModeChoice(prefModeRaw));
  }, [
    profile?.conversation_preferences?.preferred_tone,
    profile?.conversation_preferences?.adaptive_preference,
    profile?.adaptive_preference,
    profile?.tone,
    profile?.preferences?.learning_style,
  ]);

  const handleToneChange = (event) => {
    const next = normalizeToneChoice(event.target.value);
    setToneChoice(next);
    setProfile((prev) => {
      if (!prev) return prev;
      const mappedTone = next === 'professional' ? 'formal' : (next === 'auto' ? '' : next);
      return {
        ...prev,
        conversation_preferences: {
          ...(prev.conversation_preferences || {}),
          preferred_tone: mappedTone,
          preferred_length: next === 'concise' ? 'short' : ((prev.conversation_preferences || {}).preferred_length || ''),
        },
      };
    });
  };

  const handleModeChange = (event) => {
    const next = normalizeModeChoice(event.target.value);
    setModeChoice(next);
    setProfile((prev) => {
      if (!prev) return prev;
      return {
        ...prev,
        adaptive_preference: next === 'auto' ? '' : next,
        conversation_preferences: {
          ...(prev.conversation_preferences || {}),
          adaptive_preference: next === 'auto' ? '' : next,
        },
      };
    });

    if (next !== 'auto') {
      setActiveMode(next);
      setModeReason('user selected tutoring mode');
    }
  };

  useEffect(() => {
    console.debug('[Chat badge mode]', { activeMode, modeReason });
  }, [activeMode, modeReason]);

  useEffect(() => {
    return () => {
      if (speechRecognitionRef.current) {
        speechRecognitionRef.current.stop();
      }
    };
  }, []);

  const pushLocalAgentMessage = useCallback((content) => {
    setChatMessages((prev) => [...prev, { role: 'agent', content, timestamp: Date.now() }]);
  }, [setChatMessages]);

  const handlePickFile = () => {
    fileInputRef.current?.click();
  };

  const handleFileSelected = async (event) => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    if (!isLikelyTextFile(file)) {
      setAttachedFile({
        name: file.name,
        size: file.size,
        status: 'ui-only',
        extractedChars: 0,
        truncated: false,
      });
      pushLocalAgentMessage(t('chat.fileUnsupported', { fileName: file.name }));
      return;
    }

    try {
      const rawText = await file.text();
      const cleanText = rawText.trim();
      const extracted = cleanText.slice(0, MAX_FILE_EXTRACT_CHARS);
      const truncated = cleanText.length > MAX_FILE_EXTRACT_CHARS;

      setAttachedFile({
        name: file.name,
        size: file.size,
        status: 'ready',
        extractedChars: extracted.length,
        truncated,
      });

      const prompt = t('chat.filePrompt', {
        fileName: file.name,
        fileContent: extracted || t('chat.fileEmptyFallback'),
      });

      setInput(prompt);
      inputRef.current?.focus();
      pushLocalAgentMessage(t('chat.fileReady', { fileName: file.name }));
    } catch {
      setAttachedFile({
        name: file.name,
        size: file.size,
        status: 'error',
        extractedChars: 0,
        truncated: false,
      });
      pushLocalAgentMessage(t('chat.fileReadError', { fileName: file.name }));
    }
  };

  const handleVoiceInput = () => {
    const SpeechRecognitionClass = window.SpeechRecognition || window.webkitSpeechRecognition;

    if (!SpeechRecognitionClass) {
      pushLocalAgentMessage(t('chat.voiceNotSupported'));
      return;
    }

    if (!speechRecognitionRef.current) {
      const recognition = new SpeechRecognitionClass();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognition.onerror = () => {
        setIsListening(false);
        pushLocalAgentMessage(t('chat.voiceError'));
      };

      recognition.onresult = (evt) => {
        const transcript = evt?.results?.[0]?.[0]?.transcript?.trim();
        if (!transcript) return;
        sendMessage(transcript);
      };

      speechRecognitionRef.current = recognition;
    }

    if (isListening) {
      speechRecognitionRef.current.stop();
      return;
    }

    speechRecognitionRef.current.lang = i18n.language?.startsWith('ar') ? 'ar-SA' : 'en-US';
    speechRecognitionRef.current.start();
  };

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
              <label className="header-inline-control" title="Choose tone">
                <span className="header-inline-label">Tone:</span>
                <select value={toneChoice} onChange={handleToneChange} aria-label="Tone selector">
                  {TONE_DROPDOWN_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </label>
              <label className="header-inline-control" title={modeReason}>
                <span className="header-inline-label">Mode:</span>
                <select value={modeChoice} onChange={handleModeChange} aria-label="Mode selector">
                  {MODE_DROPDOWN_OPTIONS.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </label>
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
          <input
            ref={fileInputRef}
            type="file"
            className="chat-hidden-file-input"
            onChange={handleFileSelected}
            accept=".txt,.md,.markdown,.json,.csv,.tsv,.xml,.html,.css,.js,.jsx,.ts,.tsx,.py,.java,.c,.cpp,.go,.rs,.php,.rb,.sql,.yaml,.yml,.ini,.log,.pdf,.doc,.docx"
          />

          <div className="chat-composer-row chat-composer-pill">
            <button type="button" className="chat-icon-btn chat-plus-btn" onClick={handlePickFile} aria-label={t('chat.attachFile')}>
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="12" y1="5" x2="12" y2="19" />
                <line x1="5" y1="12" x2="19" y2="12" />
              </svg>
            </button>

            <textarea
              ref={inputRef}
              className="chat-input"
              id="chatInput"
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                e.target.style.height = 'auto';
                e.target.style.height = Math.min(e.target.scrollHeight, 100) + 'px';
              }}
              onKeyDown={handleKeyDown}
              placeholder={t('chat.askAnything')}
              rows={1}
            />

            <button
              type="button"
              className={`chat-icon-btn chat-mic-btn ${isListening ? 'is-listening' : ''}`}
              onClick={handleVoiceInput}
              aria-label={isListening ? t('chat.listening') : t('chat.recordVoice')}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M12 1a3 3 0 00-3 3v8a3 3 0 006 0V4a3 3 0 00-3-3z" />
                <path d="M19 10v2a7 7 0 01-14 0v-2" />
                <line x1="12" y1="19" x2="12" y2="23" />
                <line x1="8" y1="23" x2="16" y2="23" />
              </svg>
            </button>

            <button
              type="submit"
              className="chat-send-btn chat-send-action-btn"
              aria-label={t('chat.send')}
              disabled={isTyping}
            >
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <line x1="22" y1="2" x2="11" y2="13" />
                <polygon points="22 2 15 22 11 13 2 9 22 2" />
              </svg>
              <span>{t('chat.send')}</span>
            </button>
          </div>

          {attachedFile && (
            <div className="chat-file-pill" title={attachedFile.name}>
              <strong>{attachedFile.name}</strong>
              <span>{formatFileSize(attachedFile.size)}</span>
              {attachedFile.status === 'ready' && (
                <span>
                  {attachedFile.extractedChars} {t('chat.charsExtracted')}
                  {attachedFile.truncated ? ` (${t('chat.truncated')})` : ''}
                </span>
              )}
              {attachedFile.status === 'ui-only' && <span>{t('chat.uiOnly')}</span>}
              {attachedFile.status === 'error' && <span>{t('chat.readFailed')}</span>}
            </div>
          )}
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
