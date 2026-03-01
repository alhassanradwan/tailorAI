
//##################3##############################################################################3


import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
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
  const { user, profile, setProfile, chatMessages, setChatMessages, saveContext, selectedTone } = useAuth();

  const [input, setInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [currentSession, setCurrentSession] = useState(null);

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

  // Analyze & update profile
  // eslint-disable-next-line no-unused-vars
  const analyzeAndUpdateProfile = async (userMessage, _aiResponse) => {
    try {
      const { data } = await api.post('/adaptive/analyze', { message: userMessage, profile });
      if (!data.success || !data.analysis) return;

      const analysis = data.analysis;
      const recs = analysis.recommendations || {};
      const meta = analysis.message_analysis || {};

      setProfile((prev) => {
        const p = { ...prev };
        const ba = { ...p.behavioral_analytics };

        if (analysis.question_type && ba.question_types[analysis.question_type] !== undefined) {
          ba.question_types[analysis.question_type]++;
        }
        if (analysis.complexity && ba.complexity_distribution[analysis.complexity] !== undefined) {
          ba.complexity_distribution[analysis.complexity]++;
        }

        const topics = { ...ba.topics_discussed };
        (analysis.topics || []).forEach((t) => {
          if (!topics[t]) {
            topics[t] = {
              count: 0,
              first_seen: new Date().toISOString(),
              last_seen: new Date().toISOString(),
              complexity_levels: { beginner: 0, intermediate: 0, advanced: 0 },
              verified: false,
            };
          }
          topics[t] = { ...topics[t], count: topics[t].count + 1, last_seen: new Date().toISOString() };
          if (analysis.complexity) {
            topics[t].complexity_levels = {
              ...topics[t].complexity_levels,
              [analysis.complexity]: (topics[t].complexity_levels[analysis.complexity] || 0) + 1,
            };
          }
        });
        ba.topics_discussed = topics;

        const eng = { ...ba.engagement_metrics };
        eng.total_messages++;
        const prevTotal = eng.avg_message_length * (eng.total_messages - 1);
        eng.avg_message_length = (prevTotal + (meta.word_count || 0)) / eng.total_messages;
        if (meta.has_code) eng.code_requests++;
        if (meta.uncertainty_markers) eng.uncertainty_count += meta.uncertainty_markers;
        ba.engagement_metrics = eng;

        ba.last_analyzed = new Date().toISOString();
        p.behavioral_analytics = ba;

        const strong = [...(p.strong_topics || [])];
        const weak = [...(p.weak_topics || [])];

        (recs.add_to_strong_topics || []).forEach((t) => { if (!strong.includes(t)) strong.push(t); });
        (recs.add_to_weak_topics || []).forEach((t) => { if (!weak.includes(t) && !strong.includes(t)) weak.push(t); });
        (recs.move_to_strong_topics || []).forEach((t) => {
          const idx = weak.indexOf(t);
          if (idx > -1) { weak.splice(idx, 1); if (!strong.includes(t)) strong.push(t); }
        });

        p.strong_topics = strong;
        p.weak_topics = weak;

        if (recs.update_skill_level && recs.update_skill_level !== p.skill_level) {
          const sp = [...(ba.skill_progression || [])];
          sp.push({ from: p.skill_level || p.python, to: recs.update_skill_level, timestamp: new Date().toISOString() });
          ba.skill_progression = sp;
          p.skill_level = recs.update_skill_level;
        }

        const ks = { ...p.knowledge_state };
        (analysis.topics || []).forEach((topic) => {
          const td = topics[topic];
          if (td && td.count >= 2) {
            const cl = td.complexity_levels;
            const total = cl.beginner + cl.intermediate + cl.advanced;
            const mastery = total > 0
              ? Math.min(
                1.0,
                (cl.beginner * 0.2 + cl.intermediate * 0.5 + cl.advanced * 0.9) / total + Math.min(0.15, td.count * 0.015)
              )
              : 0.1;

            ks[topic] = {
              mastery_level: Math.round(mastery * 100) / 100,
              interactions: td.count,
              last_complexity: analysis.complexity,
              last_seen: new Date().toISOString(),
            };
          }
        });
        p.knowledge_state = ks;

        if (recs.misconception_detected) {
          const misc = { ...p.misconceptions };
          const mt = recs.misconception_topic || (analysis.topics || [])[0] || 'general';
          if (!misc[mt]) {
            misc[mt] = {
              count: 0,
              detail: recs.misconception_detail || 'Possible misunderstanding detected',
              first_seen: new Date().toISOString(),
              corrected: false,
            };
          }
          misc[mt] = { ...misc[mt], count: misc[mt].count + 1, last_seen: new Date().toISOString() };
          p.misconceptions = misc;
        }

        p.current_adaptations = {
          socratic_mode: recs.trigger_socratic_mode || false,
          emotional_state: recs.emotional_state || 'neutral',
          suggested_approach: recs.suggested_approach || 'explain_simply',
          comprehension_check: recs.comprehension_check_topic || null,
        };

        const msg = userMessage.toLowerCase();
        const cp = { ...p.conversation_preferences };
        if (msg.includes('give me an example') || msg.includes('for example') || msg.includes('show me example')) cp.prefers_examples = true;
        if (msg.includes('show me code') || msg.includes('write code') || msg.includes('code example') || meta.has_code) cp.prefers_code = true;
        if (msg.includes('analogy') || msg.includes('like what') || msg.includes('eli5')) cp.prefers_analogies = true;
        if (msg.includes('explain simply') || msg.includes('simple terms')) cp.explanation_style = 'simple';
        else if (msg.includes('technically') || msg.includes('in depth') || msg.includes('detailed')) cp.explanation_style = 'technical';
        if (msg.includes('friendly') || msg.includes('casual')) cp.preferred_tone = 'friendly';
        else if (msg.includes('formal') || msg.includes('professional')) cp.preferred_tone = 'formal';
        if (msg.includes('short') || msg.includes('brief') || msg.includes('concise')) cp.preferred_length = 'short';
        else if (msg.includes('long') || msg.includes('elaborate')) cp.preferred_length = 'detailed';
        p.conversation_preferences = cp;

        return p;
      });
    } catch {
      console.log('Analysis failed (non-critical)');
    }
  };

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

        ChatHistory.addMessage(userKey, session.id, { text: data.response, sender: 'agent', timestamp: new Date().toISOString() });

        await analyzeAndUpdateProfile(userMsg, data.response);
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
              aria-label="Open sidebar"
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
            <h3 id="studentNameDisplay">{user?.name || profile?.name || 'Student'}</h3>
            <div className="chat-header-stats">
              <span className="stat-chip">{profileScore}</span>
              <span className="stat-chip">{profileStrongest}</span>
              <span className="stat-chip">{profileTone}</span>
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
              <h3>Welcome, {user?.name || 'Student'}!</h3>
              <p>I'm your Personalized AI tutor. Ask me anything about Data Science, Machine Learning, or Deep Learning.</p>
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
                  <img src="/favicon.svg" className="loading-icon" alt="Loading..." />
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
            placeholder="Just ask..."
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
