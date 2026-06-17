
//##################3##############################################################################3


import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useTranslation } from 'react-i18next';
import useAuth from '../hooks/useAuth';
import api from '../api/axios';
import Sidebar from '../components/Sidebar';
import QuizModal from '../components/QuizModal';
import { formatTimestamp, ChatHistory } from '../utils/helpers';

const SUGGESTIONS = {
  'Data Science': ['What is data cleaning?', 'Explain correlation vs causation', 'How do I handle missing values?'],
  'Machine Learning': ['What is gradient descent?', 'Explain overfitting', 'What are ensemble methods?'],
  'Deep Learning': ['What is backpropagation?', 'Explain CNN architecture', 'How do transformers work?'],
};

const STORAGE_PREFIX = 'adaptiveai';
const profilePicKey = (userKey) => `${STORAGE_PREFIX}:${userKey}:profilePic`;

const TONE_DROPDOWN_VALUES = ['auto', 'friendly', 'professional', 'socratic', 'concise'];
const MODE_DROPDOWN_VALUES = ['auto', 'direct', 'supportive', 'socratic', 'supportive_socratic'];

const MODE_REASON_KEY_MAP = {
  'stable understanding detected': 'chat.modeReasons.stableUnderstanding',
  'user selected tutoring mode': 'chat.modeReasons.userSelectedMode',
  'identity lookup request': 'chat.identityLookupReason',
};

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

function widthFromLabel(label, minCh = 5) {
  const text = (label || '').toString().trim();
  const widthCh = Math.max(minCh, text.length + 2.2);
  return `${widthCh}ch`;
}

function toSkillLabel(value) {
  const v = (value || '').toString().trim().toLowerCase();
  if (!v) return '';
  if (v === 'beginner' || v === 'intermediate' || v === 'advanced') {
    return v.charAt(0).toUpperCase() + v.slice(1);
  }
  return '';
}

export default function Chat() {
  const { t, i18n } = useTranslation();
  const { user, profile, setProfile, chatMessages, setChatMessages, saveContext, selectedTone } = useAuth();

  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [currentSession, setCurrentSession] = useState(null);
  const [activeMode, setActiveMode] = useState('direct');
  const [modeReason, setModeReason] = useState('stable understanding detected');
  const [analysisComplexity, setAnalysisComplexity] = useState('');
  const [toneChoice, setToneChoice] = useState('auto');
  const [modeChoice, setModeChoice] = useState('auto');
  const [isListening, setIsListening] = useState(false);
  const [attachedFile, setAttachedFile] = useState(null);
  const [isDeepResearchMode, setIsDeepResearchMode] = useState(false);

  const [showQuizModal, setShowQuizModal] = useState(false);
  const [quizTriggerReason, setQuizTriggerReason] = useState('direct_request');
  const [quizUserMessage, setQuizUserMessage] = useState('');

  // ✅ One state controls sidebar + overlay + chat layout
  const [sidebarOpen, setSidebarOpen] = useState(true);

  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);
  const fileInputRef = useRef(null);
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const cancelVoiceRef = useRef(false);

  const userKey = useMemo(() => (user?.id || user?.email || 'guest'), [user?.id, user?.email]);

  const strongest = profile?.domain_analysis?.strongest_domain || 'Machine Learning';
  const suggestions = SUGGESTIONS[strongest] || SUGGESTIONS['Machine Learning'];

  const toneDropdownOptions = useMemo(
    () => TONE_DROPDOWN_VALUES.map((value) => ({
      value,
      label: t(`chat.toneOptions.${value}`),
    })),
    [t]
  );

  const modeDropdownOptions = useMemo(
    () => MODE_DROPDOWN_VALUES.map((value) => ({
      value,
      label: t(`chat.modeOptions.${value}`),
    })),
    [t]
  );

  const localizedModeReason = useMemo(() => {
    const normalized = (modeReason || '').toString().trim().toLowerCase();
    const key = MODE_REASON_KEY_MAP[normalized];
    if (!key) return modeReason;
    return t(key);
  }, [modeReason, t]);

  const selectedToneLabel = useMemo(
    () => toneDropdownOptions.find((opt) => opt.value === toneChoice)?.label || '',
    [toneDropdownOptions, toneChoice]
  );

  const selectedModeLabel = useMemo(
    () => modeDropdownOptions.find((opt) => opt.value === modeChoice)?.label || '',
    [modeDropdownOptions, modeChoice]
  );

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

      const endpoint = isDeepResearchMode ? '/research/deep-research' : '/chat/groq';
      const payload = isDeepResearchMode ? {
        user_id: user?.id,
        message: userMsg,
        topic: userMsg,
        depth: 'medium',
        max_sources: 10
      } : {
        user_id: user?.id,
        message: userMsg,
        profile: profilePayload,
        chat_history: chatHistory,
      };

      const { data } = await api.post(endpoint, payload);

      setIsTyping(false);

      if (data.success && data.report) {
         const aiMsg = {
           role: 'agent',
           content: data.report,
           blocks: [],
           messageType: 'legacy_text',
           timestamp: Date.now(),
         };
         setChatMessages((prev) => [...prev, aiMsg]);
         ChatHistory.addMessage(userKey, session.id, { text: data.report, sender: 'agent', timestamp: new Date().toISOString() });
      } else if (data.success && data.response) {
        const aiMsg = {
          role: 'agent',
          content: data.response,
          blocks: Array.isArray(data.content_blocks) ? data.content_blocks : [],
          messageType: data.message_type || 'legacy_text',
          timestamp: Date.now(),
        };
        setChatMessages((prev) => [...prev, aiMsg]);

        if (data.mode) setActiveMode(data.mode);
        if (data.reason) setModeReason(data.reason);
        
        // Handle incoming quiz trigger metadata
        if (data.quiz_recommended) {
            setQuizTriggerReason(data.quiz_trigger_reason || 'direct_request');
            setQuizUserMessage(data.quiz_user_message || userMsg);
            setShowQuizModal(true);
        }

        if (data.analysis?.complexity) {
          const nextSkill = String(data.analysis.complexity);
          setAnalysisComplexity(nextSkill);
          setProfile((prev) => prev ? {
            ...prev,
            estimated_skill_level: nextSkill,
            skill_level: nextSkill,
          } : prev);
        }

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

  const handleQuizComplete = (quizData, userAnswers) => {
    if (!quizData || !quizData.score) {
        setShowQuizModal(false);
        return;
    }

    setShowQuizModal(false);

    const wrongQuestions = quizData.questions.filter(q => userAnswers[q.question_id] !== q.correct_answer);
    
    if (wrongQuestions.length > 0) {
        let prompt = `I just completed a knowledge check on ${quizData.topic} and scored ${quizData.score.percentage}%. I got the following questions wrong:\n\n`;
        wrongQuestions.forEach((q, idx) => {
          prompt += `${idx + 1}. ${q.question}\n`;
          (q.options || []).forEach(opt => { prompt += `   ${opt}\n`; });
          prompt += `- My Answer: ${userAnswers[q.question_id]}\n- Correct Answer: ${q.correct_answer}\n\n`;
        });
        prompt += `Could you please explain these concepts to me?`;
        
        setTimeout(() => sendMessage(prompt), 300);
    } else {
        let prompt = `I just completed a knowledge check on ${quizData.topic} and scored 100%! I got all questions correct. I'm ready to move on to the next topic, or you can test me more deeply on this one later.`;
        setTimeout(() => sendMessage(prompt), 300);
    }
  };

  const profileScore =
    toSkillLabel(analysisComplexity)
    || toSkillLabel(profile?.estimated_skill_level)
    || toSkillLabel(profile?.skill_level)
    || toSkillLabel(profile?.python)
    || (profile?.domain_analysis
      ? `${(profile.domain_analysis.overall_accuracy || 0).toFixed(0)}%`
      : 'Beginner');

  useEffect(() => {
    const fallbackSkill =
      profile?.estimated_skill_level
      || profile?.skill_level
      || profile?.python
      || '';
    if (!analysisComplexity && fallbackSkill) {
      setAnalysisComplexity(String(fallbackSkill));
    }
  }, [analysisComplexity, profile?.estimated_skill_level, profile?.skill_level, profile?.python]);

  useEffect(() => {
    const uid = user?.id || user?.user_id;
    if (!uid) return;
    let cancelled = false;

    const syncFromLatestHistory = async () => {
      try {
        const { data } = await api.get(`/chat/history/${uid}`);
        const latest = Array.isArray(data?.history) ? data.history[0] : null;
        const historyComplexity = latest?.analysis?.complexity;
        if (!cancelled && historyComplexity && !analysisComplexity) {
          setAnalysisComplexity(String(historyComplexity));
          setProfile((prev) => prev ? {
            ...prev,
            estimated_skill_level: String(historyComplexity),
            skill_level: String(historyComplexity),
          } : prev);
        }
      } catch {
        // Non-blocking: fallback to profile-based badge when history is unavailable.
      }
    };

    syncFromLatestHistory();
    return () => {
      cancelled = true;
    };
  }, [user?.id, user?.user_id, analysisComplexity, setProfile]);

  useEffect(() => {
    let cancelled = false;

    const syncFromAnalytics = async () => {
      try {
        const { data } = await api.get('/analytics/summary');
        const analyticsLevel = data?.summary?.skill_level;
        if (!cancelled && analyticsLevel) {
          setAnalysisComplexity(String(analyticsLevel));
          setProfile((prev) => prev ? {
            ...prev,
            estimated_skill_level: String(analyticsLevel),
            skill_level: String(analyticsLevel),
          } : prev);
        }
      } catch {
        // Non-blocking fallback: badge can still sync from latest chat response/history.
      }
    };

    syncFromAnalytics();
    return () => {
      cancelled = true;
    };
  }, [user?.id, user?.user_id, setProfile]);

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
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
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

  const handleVoiceInput = async () => {
    if (isListening) {
      cancelVoiceRef.current = false;
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];
      cancelVoiceRef.current = false;

      mediaRecorder.onstart = () => {
        setIsListening(true);
      };

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        setIsListening(false);
        stream.getTracks().forEach((track) => track.stop());

        if (cancelVoiceRef.current) {
          audioChunksRef.current = [];
          cancelVoiceRef.current = false;
          return;
        }

        const audioBlob = new Blob(audioChunksRef.current, { type: mediaRecorder.mimeType || 'audio/webm' });
        audioChunksRef.current = [];

        if (audioBlob.size === 0) return;

        const lang = i18n.language?.startsWith('ar') ? 'ar' : 'en';
        const formData = new FormData();
        formData.append('file', audioBlob, `voice_memo_${Date.now()}.webm`);
        formData.append('language', lang);

        try {
          const response = await api.post('/stt/transcribe', formData, {
            headers: { 'Content-Type': 'multipart/form-data' },
          });

          if (response.data?.success && response.data?.text) {
            sendMessage(response.data.text);
          } else {
            pushLocalAgentMessage(response.data?.error || t('chat.voiceError'));
          }
        } catch (error) {
          console.error('[STT] Upload failed:', error);
          pushLocalAgentMessage(t('chat.voiceError'));
        }
      };

      mediaRecorder.start();
    } catch (error) {
      console.error('Microphone access denied or error:', error);
      pushLocalAgentMessage(t('chat.voiceNotSupported'));
    }
  };

  const cancelVoiceInput = () => {
    if (isListening) {
      cancelVoiceRef.current = true;
      if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
        mediaRecorderRef.current.stop();
      }
    }
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
              <label className="header-inline-control" title={t('chat.tooltips.chooseTone')}>
                <span className="header-inline-label">{t('chat.labels.tone')}:</span>
                <select
                  value={toneChoice}
                  onChange={handleToneChange}
                  aria-label={t('chat.aria.toneSelector')}
                  style={{ width: widthFromLabel(selectedToneLabel, 5) }}
                >
                  {toneDropdownOptions.map((opt) => (
                    <option key={opt.value} value={opt.value}>{opt.label}</option>
                  ))}
                </select>
              </label>
              <label className="header-inline-control" title={localizedModeReason || ''}>
                <span className="header-inline-label">{t('chat.labels.mode')}:</span>
                <select
                  value={modeChoice}
                  onChange={handleModeChange}
                  aria-label={t('chat.aria.modeSelector')}
                  style={{ width: widthFromLabel(selectedModeLabel, 6) }}
                >
                  {modeDropdownOptions.map((opt) => (
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

            <div className="chat-divider"></div>

            <button
              type="button"
              className={`deep-research-toggle ${isDeepResearchMode ? 'active' : ''}`}
              onClick={() => setIsDeepResearchMode(!isDeepResearchMode)}
              aria-label="Toggle Deep Research"
              aria-pressed={isDeepResearchMode}
            >
              <svg className="telescope-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M22.9 22.9l-5.6-5.6"></path>
                <path d="M12.2 12.2a4 4 0 105.7 5.7L22.9 22.9l-4.9-5-1-1a4 4 0 00-4.8 0L9.8 14.5a2 2 0 01-1.3.5 2 2 0 01-1.4-.6L1.1 8.4A2 2 0 011 5.6 2 2 0 013.8 5L9.8 11a4 4 0 002.4 1.2M13.2 2a9.9 9.9 0 003.5.7 9 9 0 005.1-1.5M10.8 19.3L15 23M3 13.8L5.5 16.5M1.3 10L6.8 15M7 6l4-4"></path>
              </svg>
              <span>Deep research</span>
            </button>

            <div className="chat-divider"></div>

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
            </button>

            {isListening && (
              <div className="voice-overlay">
                <div className="voice-overlay-content" onClick={handleVoiceInput} style={{ cursor: 'pointer' }}>
                  <button 
                    className="voice-close-btn" 
                    onClick={(e) => {
                      e.stopPropagation();
                      cancelVoiceInput();
                    }}
                    aria-label="Cancel recording"
                  >
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                      <line x1="18" y1="6" x2="6" y2="18" />
                      <line x1="6" y1="6" x2="18" y2="18" />
                    </svg>
                  </button>
                  <div className="voice-mic-icon">
                    <svg viewBox="0 0 24 24" fill="currentColor">
                      <path d="M12 14c1.66 0 3-1.34 3-3V5c0-1.66-1.34-3-3-3S9 3.34 9 5v6c0 1.66 1.34 3 3 3z"/>
                      <path d="M17 11c0 2.76-2.24 5-5 5s-5-2.24-5-5H5c0 3.53 2.61 6.43 6 6.92V21h2v-3.08c3.39-.49 6-3.39 6-6.92h-2z"/>
                    </svg>
                  </div>
                  <div className="voice-wave-container">
                      <div className="wave-bar"></div>
                      <div className="wave-bar"></div>
                      <div className="wave-bar"></div>
                      <div className="wave-bar"></div>
                      <div className="wave-bar"></div>
                      <div className="wave-bar"></div>
                      <div className="wave-bar"></div>
                      <div className="wave-bar"></div>
                      <div className="wave-bar"></div>
                  </div>
                </div>
              </div>
            )}
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

      {showQuizModal && (
        <QuizModal
          userMessage={quizUserMessage || userMsg}
          triggerReason={quizTriggerReason}
          onClose={() => setShowQuizModal(false)}
          onComplete={handleQuizComplete}
        />
      )}
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
        <div className="message-enhanced-content">
          {isUser ? message.content : <DynamicMessageContent message={message} />}
        </div>
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

function DynamicMessageContent({ message }) {
  const blocks = Array.isArray(message?.blocks) ? message.blocks : [];
  if (!blocks.length) {
    return message?.content || '';
  }

  return (
    <div className="dynamic-message-blocks">
      {blocks.map((block, idx) => (
        <div key={`${block?.type || 'text'}-${idx}`} className="dynamic-block-wrap">
          {idx > 0 ? <div className="dynamic-block-separator" aria-hidden="true" /> : null}
          <DynamicBlock block={block} />
        </div>
      ))}
    </div>
  );
}

function DynamicBlock({ block }) {
  const type = (block?.type || 'text').toLowerCase();
  const title = cleanMarkdownLine(block?.title || '');
  const text = block?.text || '';
  const items = Array.isArray(block?.items) ? block.items : [];
  const rows = Array.isArray(block?.rows) ? block.rows : [];

  if (type === 'code') {
    return (
      <div className="dynamic-block dynamic-block-code">
        {title ? <strong>{title}</strong> : null}
        <pre><code>{text}</code></pre>
      </div>
    );
  }

  if (type === 'steps' || type === 'quiz') {
    const lines = items.length
      ? items
      : text.split('\n').map((line) => line.trim()).filter(Boolean);
    return (
      <div className="dynamic-block dynamic-block-list">
        {title ? <strong>{title}</strong> : null}
        <ul>
          {lines.map((line, idx) => (
            <li key={`${type}-line-${idx}`}><RichTextLine text={cleanMarkdownLine(line.replace(/^[-*]\s*/, ''))} /></li>
          ))}
        </ul>
      </div>
    );
  }

  const parsedTable = rows.length ? { headers: Object.keys(rows[0] || {}), dataRows: rows } : parseMarkdownTable(text);
  if (type === 'comparison_table' && parsedTable.dataRows.length) {
    const headers = parsedTable.headers;
    return (
      <div className="dynamic-block dynamic-block-table">
        {title ? <strong>{title}</strong> : null}
        <table>
          <thead>
            <tr>
              {headers.map((h) => <th key={h}><RichTextLine text={cleanMarkdownLine(h)} /></th>)}
            </tr>
          </thead>
          <tbody>
            {parsedTable.dataRows.map((row, ridx) => (
              <tr key={`row-${ridx}`}>
                {headers.map((h) => (
                  <td key={`${ridx}-${h}`}>
                    <RichTextLine text={cleanMarkdownLine(String(row[h] || ''))} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div className="dynamic-block dynamic-block-text">
      {title ? <strong>{title}</strong> : null}
      <div className="dynamic-text-lines">
        {text
          .split('\n')
          .map((line) => line.trim())
          .filter(Boolean)
          .map((line, idx) => (
            <div key={`txt-${idx}`}>
              <RichTextLine text={cleanMarkdownLine(line)} />
            </div>
          ))}
      </div>
    </div>
  );
}

function cleanMarkdownLine(raw) {
  return (raw || '')
    .replace(/^#{1,6}\s*/, '')
    .replace(/`/g, '')
    .trim();
}

function RichTextLine({ text }) {
  const parts = String(text || '').split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  if (!parts.length) return null;
  return (
    <>
      {parts.map((part, idx) => {
        const isBold = /^\*\*[^*]+\*\*$/.test(part);
        if (isBold) {
          return <strong key={`b-${idx}`}>{part.slice(2, -2)}</strong>;
        }
        return <span key={`t-${idx}`}>{part}</span>;
      })}
    </>
  );
}

function parseMarkdownTable(text) {
  const lines = String(text || '')
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.includes('|'));

  if (lines.length < 2) return { headers: [], dataRows: [] };

  const rawRows = lines
    .map((line) => line.replace(/^\||\|$/g, '').split('|').map((cell) => cell.trim()))
    .filter((cells) => cells.length >= 2);

  if (rawRows.length < 2) return { headers: [], dataRows: [] };

  const isSeparator = (cells) => cells.every((cell) => /^:?-{3,}:?$/.test(cell));
  const header = rawRows[0];
  const bodyRows = rawRows.slice(1).filter((cells) => !isSeparator(cells));
  if (!bodyRows.length) return { headers: [], dataRows: [] };

  const headers = header.map((h) => cleanMarkdownLine(h));
  const dataRows = bodyRows.map((cells) => {
    const row = {};
    headers.forEach((h, idx) => {
      row[h] = cleanMarkdownLine(cells[idx] || '');
    });
    return row;
  });

  return { headers, dataRows };
}
