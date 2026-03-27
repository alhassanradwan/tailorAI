/** Format a timestamp string into human-readable relative time */
export function formatTimestamp(timestamp, options = {}) {
  const locale = (options.locale || 'en').split('-')[0] === 'ar' ? 'ar' : 'en';
  const date = new Date(timestamp);
  const now = new Date();
  const diffMs = now - date;
  const diffMins = Math.floor(diffMs / 60000);
  const diffHours = Math.floor(diffMs / 3600000);

  if (diffMins < 1) return locale === 'ar' ? 'الآن' : 'Just now';
  if (diffMins < 60) {
    if (locale === 'ar') {
      return `منذ ${diffMins} دقيقة`;
    }
    return `${diffMins} minute${diffMins === 1 ? '' : 's'} ago`;
  }

  if (diffHours < 24 && date.getDate() === now.getDate()) {
    return locale === 'ar' ? `اليوم ${fmtClock(date, locale)}` : `Today at ${fmtClock(date, locale)}`;
  }

  const yesterday = new Date(now);
  yesterday.setDate(yesterday.getDate() - 1);
  if (date.getDate() === yesterday.getDate() && date.getMonth() === yesterday.getMonth()) {
    return locale === 'ar' ? `أمس ${fmtClock(date, locale)}` : `Yesterday at ${fmtClock(date, locale)}`;
  }

  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  if (date.getFullYear() === now.getFullYear()) {
    if (locale === 'ar') {
      return new Intl.DateTimeFormat('ar', {
        month: 'short',
        day: 'numeric',
        hour: 'numeric',
        minute: '2-digit',
      }).format(date);
    }
    return `${months[date.getMonth()]} ${date.getDate()} at ${fmtClock(date, locale)}`;
  }

  if (locale === 'ar') {
    return new Intl.DateTimeFormat('ar', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    }).format(date);
  }

  return `${months[date.getMonth()]} ${date.getDate()}, ${date.getFullYear()}`;
}

function fmtClock(date, locale = 'en') {
  if (locale === 'ar') {
    return new Intl.DateTimeFormat('ar', {
      hour: 'numeric',
      minute: '2-digit',
    }).format(date);
  }

  const hours = date.getHours();
  const mins = date.getMinutes();
  const ampm = hours >= 12 ? 'PM' : 'AM';
  const displayHours = hours % 12 || 12;
  return `${displayHours}:${String(mins).padStart(2, '0')} ${ampm}`;
}

// ─────────────────────────────────────────────────────────────
// Chat history storage (per-user, localStorage) — ISOLATED
// userKey = user.id (best) OR user.email (fallback)
// ─────────────────────────────────────────────────────────────
const STORAGE_PREFIX = 'adaptiveai';

export const ChatHistory = {
  _key(userKey) {
    const safe = userKey || 'guest';
    return `${STORAGE_PREFIX}:${safe}:chat_history`;
  },

  getSessions(userKey) {
    const stored = localStorage.getItem(this._key(userKey));
    return stored ? JSON.parse(stored) : [];
  },

  saveSession(userKey, session) {
    const sessions = this.getSessions(userKey);
    const idx = sessions.findIndex((s) => s.id === session.id);

    if (idx >= 0) sessions[idx] = session;
    else sessions.unshift(session);

    localStorage.setItem(this._key(userKey), JSON.stringify(sessions.slice(0, 50)));

    // Notify components of update
    window.dispatchEvent(new Event('chatHistoryUpdated'));
    return session;
  },

  createSession(agent = 'Adaptive Agent') {
    return {
      id: 'chat_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9),
      title: 'New Chat',
      agent,
      timestamp: new Date().toISOString(),
      messages: [],
      messageCount: 0,
      lastMessage: '',
    };
  },

  addMessage(userKey, sessionId, message) {
    const sessions = this.getSessions(userKey);
    const session = sessions.find((s) => s.id === sessionId);
    if (!session) return null;

    session.messages.push(message);
    session.messageCount = session.messages.length;
    session.lastMessage = message.text.substring(0, 100);
    session.timestamp = new Date().toISOString();

    if (session.title === 'New Chat' && message.sender === 'user') {
      session.title = message.text.substring(0, 50) + (message.text.length > 50 ? '...' : '');
    }

    this.saveSession(userKey, session);
    return session;
  },

  deleteSession(userKey, sessionId) {
    const sessions = this.getSessions(userKey).filter((s) => s.id !== sessionId);
    localStorage.setItem(this._key(userKey), JSON.stringify(sessions));
    window.dispatchEvent(new Event('chatHistoryUpdated'));
  },

  getSession(userKey, sessionId) {
    return this.getSessions(userKey).find((s) => s.id === sessionId) || null;
  },

  renameSession(userKey, sessionId, newTitle) {
    const sessions = this.getSessions(userKey);
    const session = sessions.find((s) => s.id === sessionId);
    if (session) {
      session.title = newTitle.trim() || 'Untitled Chat';
      this.saveSession(userKey, session);
    }
  },

  groupByDate(userKey) {
    const sessions = this.getSessions(userKey);
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);

    const grouped = { today: [], last30Days: [] };
    sessions.forEach((s) => {
      const d = new Date(s.timestamp);
      const day = new Date(d.getFullYear(), d.getMonth(), d.getDate());
      if (day.getTime() === today.getTime()) grouped.today.push(s);
      else if (d >= monthAgo) grouped.last30Days.push(s);
    });

    return grouped;
  },
};

// ─────────────────────────────────────────────────────────────
// Migration: old chat history key → new isolated key
// old: adaptiveai_chat_history_<email>
// new: adaptiveai:<userKey>:chat_history
// ─────────────────────────────────────────────────────────────
export function migrateChatHistory(userKey, email) {
  if (!userKey || !email) return false;

  const oldKey = `adaptiveai_chat_history_${email}`;
  const newKey = `adaptiveai:${userKey}:chat_history`;

  const oldData = localStorage.getItem(oldKey);
  if (!oldData) return false;

  // If new already exists, don't overwrite
  const newData = localStorage.getItem(newKey);
  if (newData) {
    localStorage.removeItem(oldKey);
    return true;
  }

  try {
    JSON.parse(oldData); // validate JSON
    localStorage.setItem(newKey, oldData);
    localStorage.removeItem(oldKey);
    console.log(`✅ Migrated chat history from ${oldKey} to ${newKey}`);
    return true;
  } catch (err) {
    console.error('❌ Migration failed: invalid old chat history format', err);
    return false;
  }
}

// ─────────────────────────────────────────────────────────────
// Migration: old profile pic key → new isolated key
// old: userProfilePicture_<userId/email>
// new: adaptiveai:<userKey>:profilePic
// ─────────────────────────────────────────────────────────────
export function migrateProfilePicture(userKey) {
  if (!userKey) return false;

  const oldKey = `userProfilePicture_${userKey}`;
  const newKey = `adaptiveai:${userKey}:profilePic`;

  const oldPic = localStorage.getItem(oldKey);
  if (!oldPic) return false;

  const newPic = localStorage.getItem(newKey);
  if (newPic) {
    localStorage.removeItem(oldKey);
    return true;
  }

  try {
    localStorage.setItem(newKey, oldPic);
    localStorage.removeItem(oldKey);
    console.log(`✅ Migrated profile picture from ${oldKey} to ${newKey}`);
    return true;
  } catch (err) {
    console.error('❌ Profile picture migration failed', err);
    return false;
  }
}
