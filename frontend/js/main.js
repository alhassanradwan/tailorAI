/**
 * Main Application Functions
 * Onboarding, Quiz, Chat, and Analytics
 */

// === ONBOARDING FUNCTIONS ===
function goToStep(stepNumber) {
  // Validation for Step 1
  if (window.currentStep === 1 && stepNumber > 1) {
    const name = $('name').value.trim();
    const major = $('major').value.trim();
    const level = $('level').value;
    
    if (!name || !major || !level) {
      alert('⚠️ Please fill in all required fields (Name, Major, and Academic Level)');
      return;
    }
  }
  
  // Validation for Step 2
  if (window.currentStep === 2 && stepNumber > 2) {
    if (!window.selectedTone) {
      alert('⚠️ Please select your learning style');
      return;
    }
  }
  
  document.querySelectorAll('.onboarding-step').forEach(step => step.classList.remove('active'));
  $('step' + stepNumber).classList.add('active');
  window.currentStep = stepNumber;
  
  // Save context when step changes
  saveContext();
  
  const progress = (stepNumber / 2) * 100;
  $('progressFill').style.width = progress + '%';
  $('progressPercent').textContent = Math.round(progress);
  
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function selectCard(card, type) {
  card.parentElement.querySelectorAll('.selection-card').forEach(c => c.classList.remove('selected'));
  card.classList.add('selected');
  
  if (type === 'tone') {
    window.selectedTone = card.getAttribute('data-value');
  }
}

function updateSkillLabel(type, value) {
  const labels = ['Beginner', 'Intermediate', 'Advanced'];
  $(type + 'Level').textContent = labels[value];
}

// NEW: Skip quiz, go straight to chat
function startLearning() {
  if (!$('consentCheck').checked) {
    alert('⚠️ Please consent to learning analytics to proceed');
    return;
  }
  
  const pyValue = $('pySlider').value;
  const mathValue = $('mathSlider').value;
  const levels = ['Beginner', 'Intermediate', 'Advanced'];
  
  // Build user profile from onboarding
  window.profile = {
    email: window.userEmail,
    name: $('name').value.trim() || window.userName,
    major: $('major').value.trim(),
    level: $('level').value,
    tone: window.selectedTone || 'Friendly',
    python: levels[pyValue],
    math: levels[mathValue],
    consent: true,
    created_at: new Date().toISOString(),
    preferences: {
      learning_style: window.selectedTone || 'Friendly',
      skill_levels: {
        python: levels[pyValue],
        mathematics: levels[mathValue]
      }
    },
    // Start with estimated skill level (will be refined by AI)
    estimated_skill_level: levels[pyValue],
    strong_topics: [],
    weak_topics: [],
    conversation_count: 0,
    
    // Phase 1: Behavioral Analytics
    behavioral_analytics: {
      question_types: {
        definition: 0, how_to: 0, why: 0,
        comparison: 0, debugging: 0, code_request: 0, general: 0
      },
      topics_discussed: {},
      complexity_distribution: { beginner: 0, intermediate: 0, advanced: 0 },
      skill_progression: [],
      engagement_metrics: {
        total_messages: 0,
        avg_message_length: 0,
        follow_up_rate: 0,
        code_requests: 0,
        uncertainty_count: 0
      },
      last_analyzed: null
    },
    
    // Phase 4: Knowledge State & Misconceptions
    knowledge_state: {},
    misconceptions: {},
    conversation_preferences: {
      explanation_style: '',
      prefers_examples: false,
      prefers_code: false,
      prefers_analogies: false
    },
    current_adaptations: {
      socratic_mode: false,
      emotional_state: 'neutral',
      suggested_approach: 'explain_simply',
      comprehension_check: null
    }
  };
  
  // Save profile to backend
  saveContext();
  
  // Save profile to localStorage for offline access
  saveUserProfile();
  
  // Go directly to chat
  showView('chat');
  initializeChat();
  
  console.log('✅ Profile created! AI will learn about you through conversation.');
}

// Save user profile to localStorage
function saveUserProfile() {
  if (window.userEmail) {
    const existingUsers = JSON.parse(localStorage.getItem('adaptiveai_users') || '{}');
    if (existingUsers[window.userEmail]) {
      existingUsers[window.userEmail].profile = window.profile;
      existingUsers[window.userEmail].last_login = new Date().toISOString();
      localStorage.setItem('adaptiveai_users', JSON.stringify(existingUsers));
      console.log('✅ Profile saved for ' + window.profile.name);
    }
  }
}

// === CHAT INTERFACE ===
function initializeChat() {
  $('studentNameDisplay').textContent = window.userName || window.profile.name || 'Student';
  
  // Set default values for profile display
  let strongest = 'Machine Learning'; // default
  if (window.profile.domain_analysis) {
    strongest = window.profile.domain_analysis.strongest_domain;
    const accuracy = window.profile.domain_analysis.overall_accuracy || 0;
    $('profileScore').textContent = accuracy.toFixed(0) + '%';
    $('profileStrongest').textContent = strongest.split(' ')[0];
  } else {
    // User skipped quiz - use default values
    $('profileScore').textContent = window.profile.estimated_skill_level || 'Beginner';
    $('profileStrongest').textContent = 'General';
  }
  $('profileTone').textContent = window.profile.tone || window.profile.preferences?.learning_style || 'Friendly';
  
  // Auto-select agent based on strongest domain
  window.profile.selectedAgent = strongest;
  
  // Set simple professional placeholder
  $('chatInput').placeholder = 'Just ask...';
  
  // Update suggestions
  updateSuggestions(strongest);
}

function updateSuggestions(strongestDomain) {
  const suggestions = {
    'Data Science': [
      'What is data cleaning?',
      'Explain correlation vs causation',
      'How do I handle missing values?'
    ],
    'Machine Learning': [
      'What is gradient descent?',
      'Explain overfitting',
      'What are ensemble methods?'
    ],
    'Deep Learning': [
      'What is backpropagation?',
      'Explain CNN architecture',
      'How do transformers work?'
    ]
  };
  
  const chipContainer = document.querySelector('.chat-suggestions');
  if (!chipContainer) return;
  
  chipContainer.innerHTML = '';
  
  const domainSuggestions = suggestions[strongestDomain] || suggestions['Machine Learning'];
  
  domainSuggestions.forEach(text => {
    const chip = document.createElement('button');
    chip.className = 'suggestion-chip';
    chip.textContent = text;
    chip.onclick = () => insertSuggestion(chip);
    chipContainer.appendChild(chip);
  });
}

async function sendMessage(event) {
  event.preventDefault();
  
  const input = $('chatInput');
  const message = input.value.trim();
  
  if (!message) return;
  
  addMessage(message, 'user');
  input.value = '';
  input.style.height = 'auto';
  
  // Show loading indicator with favicon
  const typingDiv = document.createElement('div');
  typingDiv.className = 'message-enhanced agent-message';
  typingDiv.innerHTML = `
    <div class="message-enhanced-avatar">
      <svg viewBox="0 0 32 32" fill="none" stroke="url(#hexGradient)" stroke-width="2">
        <defs>
          <linearGradient id="hexGradient" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#667eea"/>
            <stop offset="100%" style="stop-color:#764ba2"/>
          </linearGradient>
        </defs>
        <path d="M16 2 L28 9 L28 23 L16 30 L4 23 L4 9 Z"/>
      </svg>
    </div>
    <div class="message-enhanced-wrapper">
      <div class="message-enhanced-content loading-message">
        <img src="favicon.svg" class="loading-icon" alt="Loading..."/>
      </div>
    </div>
  `;
  $('chatMessages').appendChild(typingDiv);
  $('chatMessages').scrollTop = $('chatMessages').scrollHeight;
  
  try {
    // Build chat history for API context (last 10 messages)
    const chatHistory = window.chatMessages.slice(-10).map(msg => ({
      role: msg.role === 'user' ? 'user' : 'assistant',
      content: msg.content
    }));
    
    // Increment conversation count
    if (window.profile) {
      window.profile.conversation_count = (window.profile.conversation_count || 0) + 1;
    }
    
    // Prepare profile data (send full profile for better assessment)
    const profile = {
      ...window.profile,
      skill_level: window.profile?.python || window.profile?.estimated_skill_level || 'intermediate',
      learning_tone: window.profile?.tone || 'Friendly',
      strongest_domain: window.profile?.strongestDomain || window.profile?.major || 'general'
    };
    
    // Try Groq API first
    const response = await apiRequest('/chat/groq', {
      method: 'POST',
      body: JSON.stringify({
        user_id: window.currentUserId,
        message: message,
        profile: profile,
        chat_history: chatHistory
      })
    });
    
    const data = await response.json();
    
    // Remove typing indicator
    typingDiv.remove();
    
    if (data.success && data.response) {
      addMessage(data.response, 'agent');
      console.log(`✅ Response from ${data.model || 'Groq API'} (${data.tokens_used || 0} tokens)`);
      
      // Phase 1+2: Analyze conversation and update profile
      await analyzeAndUpdateProfile(message, data.response);
      
      // Save updated profile with conversation count
      saveContext();
    } else {
      throw new Error(data.error || 'API error');
    }
  } catch (error) {
    console.log('Groq API unavailable, using local fallback:', error.message);
    typingDiv.remove();
    
    // Fallback to local generated response
    const selectedAgent = window.profile?.selectedAgent || 'general';
    const fallbackResponse = generateAIResponse(message, selectedAgent);
    addMessage(fallbackResponse, 'agent');
  }
}

function addMessage(text, type) {
  const messagesContainer = $('chatMessages');
  
  const welcomeMsg = messagesContainer.querySelector('.welcome-message');
  if (welcomeMsg) welcomeMsg.remove();
  
  addMessageToUI(text, type);
  
  messagesContainer.scrollTop = messagesContainer.scrollHeight;
  
  window.chatMessages.push({ role: type, content: text, timestamp: Date.now() });
  
  // Save to chat history
  if (typeof saveMessageToHistory === 'function') {
    saveMessageToHistory(text, type);
  }
  
  // Save context after adding message
  saveContext();
}

// ==============================
// ALL 4 PHASES: Conversation Analysis & Profile Update
// ==============================

async function analyzeAndUpdateProfile(userMessage, aiResponse) {
  try {
    console.log('📊 Analyzing conversation...');
    
    const response = await apiRequest('/adaptive/analyze', {
      method: 'POST',
      body: JSON.stringify({
        message: userMessage,
        profile: window.profile
      })
    });
    
    const data = await response.json();
    
    if (!data.success || !data.analysis) {
      console.log('⚠️ Analysis skipped:', data.error || 'No analysis');
      return;
    }
    
    const analysis = data.analysis;
    console.log('📊 Analysis result:', {
      topics: analysis.topics,
      complexity: analysis.complexity,
      type: analysis.question_type,
      method: analysis.analysis_method
    });
    
    // Initialize behavioral_analytics if missing
    if (!window.profile.behavioral_analytics) {
      window.profile.behavioral_analytics = {
        question_types: { definition: 0, how_to: 0, why: 0, comparison: 0, debugging: 0, code_request: 0, general: 0 },
        topics_discussed: {},
        complexity_distribution: { beginner: 0, intermediate: 0, advanced: 0 },
        skill_progression: [],
        engagement_metrics: { total_messages: 0, avg_message_length: 0, follow_up_rate: 0, code_requests: 0, uncertainty_count: 0 },
        last_analyzed: null
      };
    }
    if (!window.profile.knowledge_state) window.profile.knowledge_state = {};
    if (!window.profile.misconceptions) window.profile.misconceptions = {};
    if (!window.profile.conversation_preferences) {
      window.profile.conversation_preferences = { explanation_style: '', prefers_examples: false, prefers_code: false, prefers_analogies: false, preferred_tone: '', preferred_length: '' };
    }
    if (!window.profile.current_adaptations) {
      window.profile.current_adaptations = { socratic_mode: false, emotional_state: 'neutral', suggested_approach: 'explain_simply', comprehension_check: null };
    }
    
    const ba = window.profile.behavioral_analytics;
    const meta = analysis.message_analysis || {};
    const recs = analysis.recommendations || {};
    
    // === PHASE 1: Update behavioral analytics ===
    
    // Question type
    if (analysis.question_type && ba.question_types[analysis.question_type] !== undefined) {
      ba.question_types[analysis.question_type]++;
    }
    
    // Complexity distribution
    if (analysis.complexity && ba.complexity_distribution[analysis.complexity] !== undefined) {
      ba.complexity_distribution[analysis.complexity]++;
    }
    
    // Topics discussed with mastery tracking
    analysis.topics.forEach(topic => {
      if (!ba.topics_discussed[topic]) {
        ba.topics_discussed[topic] = {
          count: 0,
          first_seen: new Date().toISOString(),
          last_seen: new Date().toISOString(),
          complexity_levels: { beginner: 0, intermediate: 0, advanced: 0 },
          verified: false
        };
      }
      ba.topics_discussed[topic].count++;
      ba.topics_discussed[topic].last_seen = new Date().toISOString();
      if (analysis.complexity) {
        ba.topics_discussed[topic].complexity_levels[analysis.complexity]++;
      }
    });
    
    // Engagement metrics
    ba.engagement_metrics.total_messages++;
    const prevTotal = ba.engagement_metrics.avg_message_length * (ba.engagement_metrics.total_messages - 1);
    ba.engagement_metrics.avg_message_length = (prevTotal + (meta.word_count || 0)) / ba.engagement_metrics.total_messages;
    if (meta.has_code) ba.engagement_metrics.code_requests++;
    if (meta.uncertainty_markers) ba.engagement_metrics.uncertainty_count += meta.uncertainty_markers;
    
    ba.last_analyzed = new Date().toISOString();
    
    // === PHASE 2: Apply recommendations (strong/weak topics) ===
    
    if (recs.add_to_strong_topics) {
      recs.add_to_strong_topics.forEach(t => {
        if (!window.profile.strong_topics.includes(t)) {
          window.profile.strong_topics.push(t);
          console.log(`✅ Strong topic: ${t}`);
        }
      });
    }
    if (recs.add_to_weak_topics) {
      recs.add_to_weak_topics.forEach(t => {
        if (!window.profile.weak_topics.includes(t) && !window.profile.strong_topics.includes(t)) {
          window.profile.weak_topics.push(t);
          console.log(`⚠️ Learning topic: ${t}`);
        }
      });
    }
    if (recs.move_to_strong_topics) {
      recs.move_to_strong_topics.forEach(t => {
        const idx = window.profile.weak_topics.indexOf(t);
        if (idx > -1) {
          window.profile.weak_topics.splice(idx, 1);
          if (!window.profile.strong_topics.includes(t)) {
            window.profile.strong_topics.push(t);
            console.log(`📈 Promoted: ${t}`);
          }
        }
      });
    }
    if (recs.update_skill_level && recs.update_skill_level !== window.profile.skill_level) {
      const old = window.profile.skill_level || window.profile.python;
      window.profile.skill_level = recs.update_skill_level;
      ba.skill_progression.push({ from: old, to: recs.update_skill_level, timestamp: new Date().toISOString() });
      console.log(`🎓 Skill: ${old} → ${recs.update_skill_level}`);
    }
    
    // === PHASE 3: Knowledge state mastery scoring ===
    
    analysis.topics.forEach(topic => {
      const tdata = ba.topics_discussed[topic];
      if (tdata && tdata.count >= 2) {
        const cl = tdata.complexity_levels;
        const total = cl.beginner + cl.intermediate + cl.advanced;
        const mastery = total > 0 ? Math.min(1.0, (cl.beginner * 0.2 + cl.intermediate * 0.5 + cl.advanced * 0.9) / total + Math.min(0.15, tdata.count * 0.015)) : 0.1;
        window.profile.knowledge_state[topic] = {
          mastery_level: Math.round(mastery * 100) / 100,
          interactions: tdata.count,
          last_complexity: analysis.complexity,
          last_seen: new Date().toISOString()
        };
      }
    });
    
    // === PHASE 4: Misconception tracking ===
    
    if (recs.misconception_detected) {
      const miscTopic = recs.misconception_topic || analysis.topics[0] || 'general';
      if (!window.profile.misconceptions[miscTopic]) {
        window.profile.misconceptions[miscTopic] = {
          count: 0,
          detail: recs.misconception_detail || 'Possible misunderstanding detected',
          first_seen: new Date().toISOString(),
          corrected: false
        };
      }
      window.profile.misconceptions[miscTopic].count++;
      window.profile.misconceptions[miscTopic].last_seen = new Date().toISOString();
      console.log(`🚨 Misconception: ${miscTopic}`);
    }
    
    // === PHASE 4: Update current adaptations for next AI response ===
    
    window.profile.current_adaptations = {
      socratic_mode: recs.trigger_socratic_mode || false,
      emotional_state: recs.emotional_state || 'neutral',
      suggested_approach: recs.suggested_approach || 'explain_simply',
      comprehension_check: recs.comprehension_check_topic || null
    };
    
    // === PHASE 1: Detect conversation style preferences ===
    
    const msg = userMessage.toLowerCase();
    if (msg.includes('give me an example') || msg.includes('for example') || msg.includes('show me example')) {
      window.profile.conversation_preferences.prefers_examples = true;
    }
    if (msg.includes('show me code') || msg.includes('write code') || msg.includes('code example') || meta.has_code) {
      window.profile.conversation_preferences.prefers_code = true;
    }
    if (msg.includes('analogy') || msg.includes('like what') || msg.includes('think of it as') || msg.includes('eli5') || msg.includes('explain like')) {
      window.profile.conversation_preferences.prefers_analogies = true;
    }
    if (msg.includes('explain simply') || msg.includes('simple terms') || msg.includes('dumbed down') || msg.includes('plain english')) {
      window.profile.conversation_preferences.explanation_style = 'simple';
    } else if (msg.includes('technically') || msg.includes('in depth') || msg.includes('detailed') || msg.includes('mathematically')) {
      window.profile.conversation_preferences.explanation_style = 'technical';
    }

    // Tone preferences (persisted across sessions)
    if (msg.includes('friendly') || msg.includes('casual') || msg.includes('informal') || msg.includes('chill')) {
      window.profile.conversation_preferences.preferred_tone = 'friendly';
      console.log('🎯 Tone preference saved: friendly');
    } else if (msg.includes('formal') || msg.includes('professional') || msg.includes('academic')) {
      window.profile.conversation_preferences.preferred_tone = 'formal';
      console.log('🎯 Tone preference saved: formal');
    }

    // Brevity preferences (persisted across sessions)
    if (msg.includes('short') || msg.includes('brief') || msg.includes('concise') || msg.includes('keep it short') || msg.includes('to the point') || msg.includes('don\'t be too long') || msg.includes('shorter')) {
      window.profile.conversation_preferences.preferred_length = 'short';
      console.log('🎯 Length preference saved: short');
    } else if (msg.includes('long') || msg.includes('detailed') || msg.includes('in depth') || msg.includes('explain more') || msg.includes('go deeper') || msg.includes('elaborate')) {
      window.profile.conversation_preferences.preferred_length = 'detailed';
      console.log('🎯 Length preference saved: detailed');
    }
    
    // Update analytics panel UI
    updateAnalyticsPanel();
    
    // Save updated profile
    saveContext();
    
  } catch (error) {
    console.log('⚠️ Analysis failed (non-critical):', error.message);
  }
}

// ==============================
// Analytics Panel UI Update
// ==============================

function updateAnalyticsPanel() {
  if (!window.profile) return;
  const ba = window.profile.behavioral_analytics;
  if (!ba) return;
  
  // Skill level
  const skillEl = document.getElementById('analyticsSkillLevel');
  if (skillEl) skillEl.textContent = window.profile.skill_level || window.profile.python || 'Beginner';
  
  // Questions count
  const qEl = document.getElementById('analyticsQuestions');
  if (qEl) qEl.textContent = ba.engagement_metrics?.total_messages || 0;
  
  // Topics count
  const tEl = document.getElementById('analyticsTopicsCount');
  if (tEl) tEl.textContent = Object.keys(ba.topics_discussed || {}).length;
  
  // Sessions count
  const sessionsEl = document.getElementById('analyticsSessions');
  if (sessionsEl) sessionsEl.textContent = window.profile.conversation_count || 0;
  
  // Complexity bars - Enhanced version
  const cd = ba.complexity_distribution || { beginner: 0, intermediate: 0, advanced: 0 };
  const total = cd.beginner + cd.intermediate + cd.advanced;
  
  if (total > 0) {
    // Update counts and percentages
    const beginnerPercent = (cd.beginner / total * 100).toFixed(0);
    const intermediatePercent = (cd.intermediate / total * 100).toFixed(0);
    const advancedPercent = (cd.advanced / total * 100).toFixed(0);
    
    // Update enhanced bars
    const beginnerFill = document.getElementById('complexityBeginnerFill');
    const intermediateFill = document.getElementById('complexityIntermediateFill');
    const advancedFill = document.getElementById('complexityAdvancedFill');
    
    if (beginnerFill) beginnerFill.style.width = beginnerPercent + '%';
    if (intermediateFill) intermediateFill.style.width = intermediatePercent + '%';
    if (advancedFill) advancedFill.style.width = advancedPercent + '%';
    
    // Update counts
    const beginnerCount = document.getElementById('complexityBeginnerCount');
    const intermediateCount = document.getElementById('complexityIntermediateCount');
    const advancedCount = document.getElementById('complexityAdvancedCount');
    
    if (beginnerCount) beginnerCount.textContent = cd.beginner;
    if (intermediateCount) intermediateCount.textContent = cd.intermediate;
    if (advancedCount) advancedCount.textContent = cd.advanced;
    
    // Update percentages
    const beginnerPercentEl = document.getElementById('complexityBeginnerPercent');
    const intermediatePercentEl = document.getElementById('complexityIntermediatePercent');
    const advancedPercentEl = document.getElementById('complexityAdvancedPercent');
    
    if (beginnerPercentEl) beginnerPercentEl.textContent = beginnerPercent + '%';
    if (intermediatePercentEl) intermediatePercentEl.textContent = intermediatePercent + '%';
    if (advancedPercentEl) advancedPercentEl.textContent = advancedPercent + '%';
  }
  
  // Strong topics
  const strongEl = document.getElementById('analyticsStrongTopics');
  if (strongEl) {
    const st = window.profile.strong_topics || [];
    strongEl.innerHTML = st.length > 0
      ? st.slice(0, 8).map(t => `<span class="topic-tag strong">✅ ${t.replace(/_/g, ' ')}</span>`).join('')
      : '<span class="analytics-empty">No mastered topics yet. Keep learning!</span>';
  }
  
  // Weak topics
  const weakEl = document.getElementById('analyticsWeakTopics');
  if (weakEl) {
    const wt = window.profile.weak_topics || [];
    weakEl.innerHTML = wt.length > 0
      ? wt.slice(0, 8).map(t => `<span class="topic-tag weak">📚 ${t.replace(/_/g, ' ')}</span>`).join('')
      : '<span class="analytics-empty">No topics in progress yet</span>';
  }
  
  // Misconceptions
  const miscEl = document.getElementById('analyticsMisconceptions');
  if (miscEl) {
    const misc = window.profile.misconceptions || {};
    const active = Object.entries(misc).filter(([_, v]) => v && !v.corrected);
    miscEl.innerHTML = active.length > 0
      ? active.slice(0, 6).map(([t, v]) => `<span class="topic-tag misconception">🚨 ${t.replace(/_/g, ' ')}</span>`).join('')
      : '<span class="analytics-empty">✅ No misconceptions detected</span>';
  }
  
  // Adaptation status - Enhanced version
  const adaptEl = document.getElementById('analyticsAdaptation');
  if (adaptEl) {
    const adapts = window.profile.current_adaptations || {};
    let badgeClass = 'normal';
    let badgeIcon = '<polyline points="20 6 9 17 4 12"/>';
    let badgeText = 'Normal Mode';
    let description = 'AI is providing balanced explanations tailored to your level';
    
    if (adapts.socratic_mode) {
      badgeClass = 'socratic';
      badgeIcon = '<circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/>';
      badgeText = 'Socratic Mode';
      description = 'AI is using guided questioning to help you discover answers';
    } else if (adapts.emotional_state === 'frustrated') {
      badgeText = 'Support Mode';
      description = 'AI is providing extra encouragement and simplified explanations';
    } else if (adapts.emotional_state === 'curious') {
      badgeText = 'Exploration Mode';
      description = 'AI is offering deeper insights and advanced topics';
    }
    
    adaptEl.innerHTML = `
      <div class="adaptation-badge ${badgeClass}">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          ${badgeIcon}
        </svg>
        <span>${badgeText}</span>
      </div>
      <p class="adaptation-description">${description}</p>
    `;
  }
  
  // Update quiz history if exists
  renderQuizHistory();
}

// Helper function to add message to UI
function addMessageToUI(text, sender, animate = true, messageTimestamp = null) {
  const messagesContainer = $('chatMessages');
  
  const messageDiv = document.createElement('div');
  messageDiv.className = `message-enhanced ${sender === 'user' ? 'user-message' : 'agent-message'}`;
  if (animate) {
    messageDiv.classList.add('message-enter');
  }
  
  const avatar = document.createElement('div');
  avatar.className = 'message-enhanced-avatar';
  
  if (sender === 'agent') {
    // AI hexagon logo - outline only with favicon gradient
    avatar.innerHTML = `
      <svg viewBox="0 0 32 32" fill="none">
        <path d="M16 3L27 9.5V22.5L16 29L5 22.5V9.5L16 3Z" stroke="url(#hexStroke)" stroke-width="2" fill="none"/>
        <defs>
          <linearGradient id="hexStroke" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#667eea"/>
            <stop offset="50%" style="stop-color:#764ba2"/>
            <stop offset="100%" style="stop-color:#f093fb"/>
          </linearGradient>
        </defs>
      </svg>
    `;
  } else {
    // User avatar - show profile picture or initials
    const profilePicture = localStorage.getItem('userProfilePicture');
    if (profilePicture) {
      avatar.style.backgroundImage = `url(${profilePicture})`;
      avatar.style.backgroundSize = 'cover';
      avatar.style.backgroundPosition = 'center';
    } else {
      avatar.innerHTML = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>';
    }
  }
  
  const contentWrapper = document.createElement('div');
  contentWrapper.className = 'message-enhanced-wrapper';
  
  const contentDiv = document.createElement('div');
  contentDiv.className = 'message-enhanced-content';
  contentDiv.textContent = text;
  
  const timestamp = document.createElement('div');
  timestamp.className = 'message-enhanced-timestamp';
  // Use provided timestamp or create new one
  const timestampValue = messageTimestamp || new Date().toISOString();
  timestamp.textContent = formatTimestamp(timestampValue);
  
  contentWrapper.appendChild(contentDiv);
  contentWrapper.appendChild(timestamp);
  
  if (sender === 'agent') {
    messageDiv.appendChild(avatar);
    messageDiv.appendChild(contentWrapper);
  } else {
    messageDiv.appendChild(contentWrapper);
    messageDiv.appendChild(avatar);
  }
  
  messagesContainer.appendChild(messageDiv);
}

function generateAIResponse(userMessage, agent) {
  const agentNames = {
    'Data Science': 'Data Science',
    'Machine Learning': 'Machine Learning',
    'Deep Learning': 'Deep Learning'
  };
  
  const responses = {
    'gradient descent': `Great question! Based on your ${window.profile.preferences.skill_levels.python} Python level and ${window.profile.tone} learning style, here is a friendly explanation of gradient descent...`,
    'overfitting': `Overfitting is when your model memorizes the training data instead of learning patterns. With your current level (${window.profile.domain_analysis.detected_level}), examples from ${window.profile.domain_analysis.strongest_domain} will help.`,
    'default': `That is an interesting question about ${agentNames[agent]}! Taking into account your learning style (${window.profile.tone}) and detected level (${window.profile.domain_analysis.detected_level}), here is a tailored explanation...`
  };
  
  for (let key in responses) {
    if (userMessage.toLowerCase().includes(key)) return responses[key];
  }
  
  return responses['default'];
}

function insertSuggestion(chip) {
  const text = chip.textContent.trim();
  $('chatInput').value = text;
  $('chatInput').focus();
}

function handleChatKeypress(event) {
  if (event.key === 'Enter' && !event.shiftKey) {
    event.preventDefault();
    sendMessage(event);
  }
}

// Auto-resize textarea
window.addEventListener('DOMContentLoaded', function() {
  const chatInput = $('chatInput');
  if (chatInput) {
    chatInput.addEventListener('input', function() {
      this.style.height = 'auto';
      this.style.height = Math.min(this.scrollHeight, 120) + 'px';
    });
  }
});

// === ANALYTICS HELPERS ===
function calculateAvgTimeByDomain(analytics) {
  const byDomain = { 
    'Data Science': [], 
    'Machine Learning': [], 
    'Deep Learning': [] 
  };
  
  analytics.forEach(log => {
    if (log.total_time_ms && !log.skipped) {
      byDomain[log.domain].push(log.total_time_ms);
    }
  });
  
  const result = {};
  for (let domain in byDomain) {
    result[domain] =
      byDomain[domain].length > 0
        ? (byDomain[domain].reduce((a, b) => a + b, 0) / byDomain[domain].length / 1000).toFixed(1)
        : 0;
  }
  return result;
}

function calculateAccuracyByDomain(analytics) {
  const byDomain = { 
    'Data Science': { correct: 0, total: 0 }, 
    'Machine Learning': { correct: 0, total: 0 }, 
    'Deep Learning': { correct: 0, total: 0 } 
  };
  
  analytics.forEach(log => {
    if (!log.skipped) {
      byDomain[log.domain].total++;
      if (log.final_correct) byDomain[log.domain].correct++;
    }
  });
  
  const result = {};
  for (let domain in byDomain) {
    result[domain] =
      byDomain[domain].total > 0
        ? ((byDomain[domain].correct / byDomain[domain].total) * 100).toFixed(1)
        : 0;
  }
  return result;
}

function calculateAvgTimeByDifficulty(analytics) {
  const byDifficulty = { easy: [], medium: [], hard: [] };
  
  analytics.forEach(log => {
    if (log.total_time_ms && !log.skipped) {
      byDifficulty[log.difficulty].push(log.total_time_ms);
    }
  });
  
  return {
    easy:
      byDifficulty.easy.length > 0
        ? (byDifficulty.easy.reduce((a, b) => a + b, 0) / byDifficulty.easy.length / 1000).toFixed(1)
        : 0,
    medium:
      byDifficulty.medium.length > 0
        ? (byDifficulty.medium.reduce((a, b) => a + b, 0) / byDifficulty.medium.length / 1000).toFixed(1)
        : 0,
    hard:
      byDifficulty.hard.length > 0
        ? (byDifficulty.hard.reduce((a, b) => a + b, 0) / byDifficulty.hard.length / 1000).toFixed(1)
        : 0
  };
}

function calculateAccuracyByDifficulty(analytics) {
  const byDifficulty = { 
    easy: { correct: 0, total: 0 }, 
    medium: { correct: 0, total: 0 }, 
    hard: { correct: 0, total: 0 } 
  };
  
  analytics.forEach(log => {
    if (!log.skipped) {
      byDifficulty[log.difficulty].total++;
      if (log.final_correct) byDifficulty[log.difficulty].correct++;
    }
  });
  
  return {
    easy:
      byDifficulty.easy.total > 0
        ? ((byDifficulty.easy.correct / byDifficulty.easy.total) * 100).toFixed(1)
        : 0,
    medium:
      byDifficulty.medium.total > 0
        ? ((byDifficulty.medium.correct / byDifficulty.medium.total) * 100).toFixed(1)
        : 0,
    hard:
      byDifficulty.hard.total > 0
        ? ((byDifficulty.hard.correct / byDifficulty.hard.total) * 100).toFixed(1)
        : 0
  };
}

function calculateEngagementScore(analytics) {
  let engagementScore = 100;
  
  const skippedCount = analytics.filter(log => log.skipped).length;
  const avgFocusLoss =
    analytics.reduce((sum, log) => sum + log.focus_events.filter(e => e.type === 'blur').length, 0) /
    Math.max(analytics.length, 1);
  
  engagementScore -= skippedCount * 5;
  engagementScore -= avgFocusLoss * 10;
  
  return Math.max(0, Math.min(100, engagementScore)).toFixed(0);
}
