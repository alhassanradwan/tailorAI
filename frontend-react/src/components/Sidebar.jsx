import { useState, useRef, useEffect, useMemo, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import { ChatHistory, formatTimestamp } from '../utils/helpers';

const STORAGE_PREFIX = 'adaptiveai';
const profilePicKey = (userKey) => `${STORAGE_PREFIX}:${userKey}:profilePic`;
const chatHistoryKey = (userKey) => `${STORAGE_PREFIX}:${userKey}:chat_history`;

export default function Sidebar({
  onNewChat,
  onLoadSession,
  onDeleteSession,
  currentSessionId,
  sidebarOpen,
  setSidebarOpen,
}) {
  const { user, logout, loading } = useAuth();
  const navigate = useNavigate();
  const [dropdownOpen, setDropdownOpen] = useState(false);
  const fileInputRef = useRef(null);

  const userKey = useMemo(() => (user?.id || user?.email || 'guest'), [user?.id, user?.email]);

  const [profilePic, setProfilePic] = useState(() => localStorage.getItem(profilePicKey(userKey)));
  const initials = (user?.name || 'U')
    .split(' ')
    .map((n) => n[0])
    .join('')
    .substring(0, 2)
    .toUpperCase();

  const [grouped, setGrouped] = useState(() => ChatHistory.groupByDate(userKey));

  const refreshHistory = useCallback(() => {
    setGrouped(ChatHistory.groupByDate(userKey));
  }, [userKey]);

  useEffect(() => {
    setProfilePic(localStorage.getItem(profilePicKey(userKey)));
    setGrouped(ChatHistory.groupByDate(userKey));
  }, [userKey]);

  useEffect(() => {
    const handler = (e) => {
      if (!e || !e.key) {
        refreshHistory();
        setProfilePic(localStorage.getItem(profilePicKey(userKey)));
        return;
      }

      if (e.key === chatHistoryKey(userKey)) refreshHistory();
      if (e.key === profilePicKey(userKey)) setProfilePic(localStorage.getItem(profilePicKey(userKey)));
    };

    window.addEventListener('storage', handler);
    window.addEventListener('chatHistoryUpdated', refreshHistory);

    return () => {
      window.removeEventListener('storage', handler);
      window.removeEventListener('chatHistoryUpdated', refreshHistory);
    };
  }, [userKey, refreshHistory]);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const handleProfilePicUpload = (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.type.startsWith('image/')) return alert('Please select a valid image file');
    if (file.size > 2 * 1024 * 1024) return alert('Image must be less than 2MB');

    const reader = new FileReader();
    reader.onload = (ev) => {
      localStorage.setItem(profilePicKey(userKey), ev.target.result);
      setProfilePic(ev.target.result);
      setDropdownOpen(false);
    };
    reader.readAsDataURL(file);
  };

  const displayName = loading ? 'Loading...' : (user?.name || user?.email?.split('@')[0] || 'User');

  // const closeSidebar = () => setSidebarOpen(false);
  const toggleSidebar = () => setSidebarOpen((v) => !v);

  return (
    <>
      {/* Sidebar */}
      <aside className={`sidebar ${sidebarOpen ? '' : 'collapsed'}`} id="appSidebar">
        <div className="sidebar-header">
          <div className="sidebar-brand">
            <svg width="28" height="28" viewBox="0 0 32 32" fill="none">
              <path
                d="M16 2L28 9V23L16 30L4 23V9L16 2Z"
                stroke="url(#sidebarGrad)"
                strokeWidth="2"
                fill="none"
              />
              <defs>
               <linearGradient id="sidebarGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" style={{ stopColor: '#667EEA' }} />
                <stop offset="50%" style={{ stopColor: '#764BA2' }} />
                <stop offset="100%" style={{ stopColor: '#F093FB' }} />
               </linearGradient>

              </defs>
            </svg>
            <span>Tailor<strong>AI</strong></span>
          </div>

          {/* Toggle INSIDE sidebar */}
          <button className="sidebar-toggle" onClick={toggleSidebar} aria-label="Toggle sidebar">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="3" y1="6" x2="21" y2="6" />
              <line x1="3" y1="12" x2="21" y2="12" />
              <line x1="3" y1="18" x2="21" y2="18" />
            </svg>
          </button>
        </div>

        <button className="new-chat-btn" onClick={onNewChat}>
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <line x1="12" y1="5" x2="12" y2="19" />
            <line x1="5" y1="12" x2="19" y2="12" />
          </svg>
          New Chat
        </button>

        <div className="sidebar-history">
          <div id="chatHistoryContainer">
            {grouped.today.length > 0 && (
              <div className="history-group">
                <div className="history-group-label">Today</div>
                <div className="history-items">
                  {grouped.today.map((session) => (
                    <ChatHistoryItem
                      key={session.id}
                      session={session}
                      isActive={currentSessionId === session.id}
                      onLoad={() => onLoadSession(session.id)}
                      onDelete={(e) => { e.stopPropagation(); onDeleteSession(session.id); }}
                      onRename={(newTitle) => {
                        ChatHistory.renameSession(userKey, session.id, newTitle);
                        refreshHistory();
                      }}
                    />
                  ))}
                </div>
              </div>
            )}

            {grouped.last30Days.length > 0 && (
              <div className="history-group">
                <div className="history-group-label">Last 30 Days</div>
                <div className="history-items">
                  {grouped.last30Days.map((session) => (
                    <ChatHistoryItem
                      key={session.id}
                      session={session}
                      isActive={currentSessionId === session.id}
                      onLoad={() => onLoadSession(session.id)}
                      onDelete={(e) => { e.stopPropagation(); onDeleteSession(session.id); }}
                      onRename={(newTitle) => {
                        ChatHistory.renameSession(userKey, session.id, newTitle);
                        refreshHistory();
                      }}
                    />
                  ))}
                </div>
              </div>
            )}

            {grouped.today.length === 0 && grouped.last30Days.length === 0 && (
              <div className="history-empty">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
                </svg>
                <p>No chat history yet.<br />Start a conversation!</p>
              </div>
            )}
          </div>
        </div>

        <div className="sidebar-user">
          <div className="user-profile-btn" onClick={() => setDropdownOpen(!dropdownOpen)}>
            <div
              className="user-avatar"
              style={profilePic ? { backgroundImage: `url(${profilePic})`, backgroundSize: 'cover', backgroundPosition: 'center' } : {}}
            >
              {!profilePic && initials}
            </div>

            <div className="user-info">
              <div className="user-name" id="userProfileName">{displayName}</div>
              <div className="user-email" id="userProfileEmail">{user?.email || ''}</div>
            </div>

            <svg
              viewBox="0 0 24 24"
              fill="none"
              stroke="currentColor"
              strokeWidth="2"
              style={{
                width: '16px',
                height: '16px',
                marginLeft: 'auto',
                transition: 'transform 0.2s',
                transform: dropdownOpen ? 'rotate(180deg)' : 'rotate(0deg)',
              }}
            >
              <polyline points="6 9 12 15 18 9" />
            </svg>
          </div>

          {dropdownOpen && (
            <div className="user-dropdown active" id="userDropdown">
              <button className="dropdown-item" onClick={() => fileInputRef.current?.click()}>
                Change Photo
              </button>
              <button className="dropdown-item" onClick={() => { navigate('/analytics'); setDropdownOpen(false); }}>
                Analytics
              </button>
              <hr style={{ border: 'none', borderTop: '1px solid var(--border)', margin: '0.25rem 0' }} />
              <button className="dropdown-item logout" onClick={handleLogout}>
                Logout
              </button>
            </div>
          )}

          <input
            ref={fileInputRef}
            type="file"
            accept="image/*"
            style={{ display: 'none' }}
            onChange={handleProfilePicUpload}
          />
        </div>
      </aside>
    </>
  );
}

function ChatHistoryItem({ session, isActive, onLoad, onDelete, onRename }) {
  const [isEditing, setIsEditing] = useState(false);
  const [editedTitle, setEditedTitle] = useState(session.title);

  const handleRename = (e) => {
    e.stopPropagation();
    setIsEditing(true);
  };

  const handleSaveRename = (e) => {
    e.stopPropagation();
    if (editedTitle.trim()) {
      onRename(editedTitle.trim());
      setIsEditing(false);
    }
  };

  const handleCancelRename = (e) => {
    e.stopPropagation();
    setEditedTitle(session.title);
    setIsEditing(false);
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') handleSaveRename(e);
    else if (e.key === 'Escape') handleCancelRename(e);
  };

  return (
    <div className={`history-item ${isActive ? 'active' : ''}`} onClick={isEditing ? undefined : onLoad}>
      <svg className="history-item-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
        <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
      </svg>

      <div className="history-item-content">
        {isEditing ? (
          <input
            type="text"
            className="history-item-edit-input"
            value={editedTitle}
            onChange={(e) => setEditedTitle(e.target.value)}
            onKeyDown={handleKeyDown}
            onBlur={handleSaveRename}
            onClick={(e) => e.stopPropagation()}
            autoFocus
          />
        ) : (
          <div className="history-item-title">{session.title}</div>
        )}
        <div className="history-item-meta">{session.messageCount} messages • {formatTimestamp(session.timestamp)}</div>
      </div>

      <div className="history-item-actions">
        {!isEditing && (
          <button className="history-item-rename" onClick={handleRename} title="Rename">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
              <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
            </svg>
          </button>
        )}

        <button className="history-item-delete" onClick={onDelete} title="Delete">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <path d="M3 6h18M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
          </svg>
        </button>
      </div>
    </div>
  );
}
