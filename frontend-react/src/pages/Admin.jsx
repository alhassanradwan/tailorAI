import { useEffect, useState } from 'react';
import api from '../api/axios';

export default function Admin() {
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [summary, setSummary] = useState(null);
  const [users, setUsers] = useState([]);
  const [recentInteractions, setRecentInteractions] = useState([]);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedUserDetail, setSelectedUserDetail] = useState(null);
  const [userDetailLoading, setUserDetailLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        setLoadError('');
        const [sumRes, usersRes, recentRes] = await Promise.all([
          api.get('/admin/analytics/summary'),
          api.get('/admin/users'),
          api.get('/admin/interactions/recent'),
        ]);

        if (cancelled) return;
        if (sumRes.data?.success) setSummary(sumRes.data.summary);
        if (usersRes.data?.success) setUsers(usersRes.data.users || []);
        if (recentRes.data?.success) setRecentInteractions(recentRes.data.interactions || []);
      } catch (err) {
        console.error('Admin page load failed:', err);
        setLoadError('Unable to load admin data right now. Please refresh and try again.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const inspectUser = async (userId) => {
    setSelectedUserId(userId);
    setSelectedUserDetail(null);
    setUserDetailLoading(true);
    try {
      const { data } = await api.get(`/admin/user/${userId}`);
      if (data?.success) setSelectedUserDetail(data.user);
    } catch (err) {
      console.error('Failed to inspect user:', err);
    } finally {
      setUserDetailLoading(false);
    }
  };

  const formatDate = (value) => {
    if (!value) return '-';
    const parsed = new Date(value);
    if (Number.isNaN(parsed.getTime())) return String(value);
    return parsed.toLocaleString();
  };

  if (loading) {
    return (
      <section className="view active" id="admin">
        <div className="container" style={{ textAlign: 'center', padding: '80px 20px' }}>
          <h2>Loading Admin Dashboard...</h2>
        </div>
      </section>
    );
  }

  return (
    <section className="view active" id="admin">
      <div className="container" style={{ display: 'grid', gap: 20, paddingBottom: 40 }}>
        <div className="glass-effect" style={{ padding: 20, borderRadius: 16 }}>
          <h2 style={{ marginBottom: 8 }}>Admin Dashboard</h2>
          <p style={{ color: 'var(--text-secondary)' }}>System overview and learner monitoring</p>
        </div>

        <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
          <div className="glass-effect" style={{ padding: 18, borderRadius: 14 }}>
            <div style={{ color: 'var(--text-muted)' }}>Total Users</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{summary?.total_users ?? 0}</div>
          </div>
          <div className="glass-effect" style={{ padding: 18, borderRadius: 14 }}>
            <div style={{ color: 'var(--text-muted)' }}>Total Messages</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{summary?.total_messages ?? 0}</div>
          </div>
          <div className="glass-effect" style={{ padding: 18, borderRadius: 14 }}>
            <div style={{ color: 'var(--text-muted)' }}>Average Mastery</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{Math.round((summary?.average_mastery || 0) * 100)}%</div>
          </div>
        </div>

        {loadError && (
          <div className="glass-effect" style={{ padding: 14, borderRadius: 14, borderColor: 'rgba(248, 113, 113, 0.5)' }}>
            <p style={{ color: 'var(--error)' }}>{loadError}</p>
          </div>
        )}

        <div className="glass-effect" style={{ padding: 20, borderRadius: 16 }}>
          <h3 style={{ marginBottom: 14 }}>Top Topics</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {(summary?.top_topics || []).map((t) => (
              <span key={t.topic} className="stat-chip">
                {t.topic.replace(/_/g, ' ')} ({t.count})
              </span>
            ))}
            {(summary?.top_topics || []).length === 0 && (
              <span style={{ color: 'var(--text-secondary)' }}>No topic data yet</span>
            )}
          </div>
        </div>

        <div className="glass-effect" style={{ padding: 20, borderRadius: 16 }}>
          <h3 style={{ marginBottom: 14 }}>Users</h3>
          <div style={{ overflowX: 'auto' }}>
            <table className="admin-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ textAlign: 'start', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '10px 8px' }}>Email</th>
                  <th style={{ padding: '10px 8px' }}>Created</th>
                  <th style={{ padding: '10px 8px' }}>Admin</th>
                  <th style={{ padding: '10px 8px' }}>Messages</th>
                  <th style={{ padding: '10px 8px' }}>Mode</th>
                  <th style={{ padding: '10px 8px' }}></th>
                </tr>
              </thead>
              <tbody>
                {users.map((u) => (
                  <tr key={u.id} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '10px 8px' }}>{u.email || '-'}</td>
                    <td style={{ padding: '10px 8px' }}>{formatDate(u.created_at)}</td>
                    <td style={{ padding: '10px 8px' }}>
                      <span className={`admin-badge ${u.is_admin ? 'is-admin' : 'is-member'}`}>
                        {u.is_admin ? 'Admin' : 'Member'}
                      </span>
                    </td>
                    <td style={{ padding: '10px 8px' }}>{u.total_messages ?? 0}</td>
                    <td style={{ padding: '10px 8px' }}>
                      <span className="mode-badge">{u.current_tutoring_mode || '-'}</span>
                    </td>
                    <td style={{ padding: '10px 8px' }}>
                      <button className="btn-secondary" onClick={() => inspectUser(u.id)}>
                        {userDetailLoading && selectedUserId === u.id ? 'Inspecting...' : 'Inspect'}
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan="6" style={{ padding: 12, color: 'var(--text-secondary)' }}>
                      No users found
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="glass-effect" style={{ padding: 20, borderRadius: 16 }}>
          <h3 style={{ marginBottom: 14 }}>Recent Interactions</h3>
          <div style={{ overflowX: 'auto' }}>
            <table className="admin-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ textAlign: 'start', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '10px 8px' }}>User ID</th>
                  <th style={{ padding: '10px 8px' }}>Message</th>
                  <th style={{ padding: '10px 8px' }}>Mode</th>
                  <th style={{ padding: '10px 8px' }}>Timestamp</th>
                </tr>
              </thead>
              <tbody>
                {recentInteractions.map((r, idx) => (
                  <tr key={`${r.user_id}-${r.timestamp}-${idx}`} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '10px 8px' }}>{r.user_id || '-'}</td>
                    <td style={{ padding: '10px 8px', maxWidth: 480, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {r.user_message || '-'}
                    </td>
                    <td style={{ padding: '10px 8px' }}><span className="mode-badge">{r.tutoring_mode || '-'}</span></td>
                    <td style={{ padding: '10px 8px' }}>{formatDate(r.timestamp)}</td>
                  </tr>
                ))}
                {recentInteractions.length === 0 && (
                  <tr>
                    <td colSpan="4" style={{ padding: 12, color: 'var(--text-secondary)' }}>
                      No recent interactions
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="glass-effect" style={{ padding: 20, borderRadius: 16 }}>
          <h3 style={{ marginBottom: 12 }}>User Detail</h3>
          {!selectedUserId && <p style={{ color: 'var(--text-secondary)' }}>Select a user from the table above.</p>}
          {selectedUserId && !selectedUserDetail && <p style={{ color: 'var(--text-secondary)' }}>{userDetailLoading ? 'Loading user detail...' : 'Unable to load user detail.'}</p>}
          {selectedUserDetail && (
            <div style={{ display: 'grid', gap: 12 }}>
              <div><strong>User ID:</strong> {selectedUserDetail.user_id || '-'}</div>
              <div><strong>Email:</strong> {selectedUserDetail.email || '-'}</div>
              <div><strong>Mode History:</strong> {selectedUserDetail.mode_history?.length || 0} entries</div>
              <div><strong>Misconceptions:</strong> {selectedUserDetail.misconceptions?.length || 0}</div>
              <div><strong>Recent Interactions:</strong> {selectedUserDetail.recent_interactions?.length || 0}</div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
