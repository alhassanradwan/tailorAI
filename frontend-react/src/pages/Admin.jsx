import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';
import api from '../api/axios';

const RECENT_INTERACTIONS_MAX_HEIGHT = 520;

export default function Admin() {
  const { t } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState('');
  const [summary, setSummary] = useState(null);
  const [users, setUsers] = useState([]);
  const [userInteractions, setUserInteractions] = useState([]);
  const [interactionsLoading, setInteractionsLoading] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState('');
  const [selectedUserDetail, setSelectedUserDetail] = useState(null);
  const [userDetailLoading, setUserDetailLoading] = useState(false);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        setLoadError('');
        const [sumRes, usersRes] = await Promise.all([
          api.get('/admin/analytics/summary'),
          api.get('/admin/users'),
        ]);

        if (cancelled) return;
        if (sumRes.data?.success) setSummary(sumRes.data.summary);
        if (usersRes.data?.success) setUsers(usersRes.data.users || []);
      } catch (err) {
        console.error('Admin page load failed:', err);
        setLoadError(t('admin.loadError'));
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [t]);

  const inspectUser = async (userId) => {
    setSelectedUserId(userId);
    setSelectedUserDetail(null);
    setUserInteractions([]);
    setUserDetailLoading(true);
    setInteractionsLoading(true);
    try {
      const [detailRes, interactionsRes] = await Promise.all([
        api.get(`/admin/user/${userId}`),
        api.get(`/admin/interactions/user/${userId}?limit=60`),
      ]);

      if (detailRes.data?.success) setSelectedUserDetail(detailRes.data.user);
      if (interactionsRes.data?.success) setUserInteractions(interactionsRes.data.interactions || []);
    } catch (err) {
      console.error('Failed to inspect user:', err);
    } finally {
      setUserDetailLoading(false);
      setInteractionsLoading(false);
    }
  };

  const summarizeTopics = (topics) => {
    if (!Array.isArray(topics) || topics.length === 0) return '-';
    return topics.slice(0, 3).join(', ');
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
          <h2>{t('admin.loading')}</h2>
        </div>
      </section>
    );
  }

  return (
    <section className="view active" id="admin">
      <div className="container" style={{ display: 'grid', gap: 20, paddingBottom: 40, maxWidth: '100%', overflowX: 'hidden' }}>
        <div className="glass-effect" style={{ padding: 20, borderRadius: 16, minWidth: 0 }}>
          <h2 style={{ marginBottom: 8 }}>{t('admin.title')}</h2>
          <p style={{ color: 'var(--text-secondary)' }}>{t('admin.subtitle')}</p>
        </div>

        <div style={{ display: 'grid', gap: 16, gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))' }}>
          <div className="glass-effect" style={{ padding: 18, borderRadius: 14, minWidth: 0 }}>
            <div style={{ color: 'var(--text-muted)' }}>{t('admin.cards.totalUsers')}</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{summary?.total_users ?? 0}</div>
          </div>
          <div className="glass-effect" style={{ padding: 18, borderRadius: 14, minWidth: 0 }}>
            <div style={{ color: 'var(--text-muted)' }}>{t('admin.cards.totalMessages')}</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{summary?.total_messages ?? 0}</div>
          </div>
          <div className="glass-effect" style={{ padding: 18, borderRadius: 14, minWidth: 0 }}>
            <div style={{ color: 'var(--text-muted)' }}>{t('admin.cards.averageMastery')}</div>
            <div style={{ fontSize: 28, fontWeight: 700 }}>{Math.round((summary?.average_mastery || 0) * 100)}%</div>
          </div>
        </div>

        {loadError && (
          <div className="glass-effect" style={{ padding: 14, borderRadius: 14, borderColor: 'rgba(248, 113, 113, 0.5)' }}>
            <p style={{ color: 'var(--error)' }}>{loadError}</p>
          </div>
        )}

        <div className="glass-effect" style={{ padding: 20, borderRadius: 16, minWidth: 0 }}>
          <h3 style={{ marginBottom: 14 }}>{t('admin.topTopics')}</h3>
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10 }}>
            {(summary?.top_topics || []).map((t) => (
              <span key={t.topic} className="stat-chip">
                {t.topic.replace(/_/g, ' ')} ({t.count})
              </span>
            ))}
            {(summary?.top_topics || []).length === 0 && (
              <span style={{ color: 'var(--text-secondary)' }}>{t('admin.noTopicData')}</span>
            )}
          </div>
        </div>

        <div className="glass-effect" style={{ padding: 20, borderRadius: 16, minWidth: 0 }}>
          <h3 style={{ marginBottom: 14 }}>{t('admin.users')}</h3>
          <div style={{ overflowX: 'auto', width: '100%', maxWidth: '100%' }}>
            <table className="admin-table" style={{ width: '100%', minWidth: 980, borderCollapse: 'collapse', tableLayout: 'fixed' }}>
              <thead>
                <tr style={{ textAlign: 'start', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '10px 8px' }}>{t('admin.table.email')}</th>
                  <th style={{ padding: '10px 8px' }}>{t('admin.table.created')}</th>
                  <th style={{ padding: '10px 8px' }}>{t('admin.table.admin')}</th>
                  <th style={{ padding: '10px 8px' }}>{t('admin.table.messages')}</th>
                  <th style={{ padding: '10px 8px' }}>{t('admin.table.mode')}</th>
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
                        {u.is_admin ? t('admin.roles.admin') : t('admin.roles.member')}
                      </span>
                    </td>
                    <td style={{ padding: '10px 8px' }}>{u.total_messages ?? 0}</td>
                    <td style={{ padding: '10px 8px' }}>
                      <span className="mode-badge">{u.current_tutoring_mode || '-'}</span>
                    </td>
                    <td style={{ padding: '10px 8px' }}>
                      <button className="btn-secondary" onClick={() => inspectUser(u.id)}>
                        {userDetailLoading && selectedUserId === u.id ? t('admin.inspecting') : t('admin.inspect')}
                      </button>
                    </td>
                  </tr>
                ))}
                {users.length === 0 && (
                  <tr>
                    <td colSpan="6" style={{ padding: 12, color: 'var(--text-secondary)' }}>
                      {t('admin.noUsersFound')}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="glass-effect" style={{ padding: 20, borderRadius: 16, minWidth: 0 }}>
          <h3 style={{ marginBottom: 14 }}>{t('admin.recentInteractions')}</h3>
          {!selectedUserId && (
            <p style={{ color: 'var(--text-secondary)', marginBottom: 12 }}>{t('admin.userDetail.selectPrompt')}</p>
          )}

          <div style={{ overflow: 'auto', width: '100%', maxWidth: '100%', maxHeight: RECENT_INTERACTIONS_MAX_HEIGHT }}>
            <table className="admin-table" style={{ width: '100%', minWidth: 1100, borderCollapse: 'collapse', tableLayout: 'fixed' }}>
              <thead>
                <tr style={{ textAlign: 'start', color: 'var(--text-muted)' }}>
                  <th style={{ padding: '10px 8px' }}>{t('admin.table.userId')}</th>
                  <th style={{ padding: '10px 8px' }}>{t('admin.table.message')}</th>
                  <th style={{ padding: '10px 8px' }}>{t('admin.table.topics')}</th>
                  <th style={{ padding: '10px 8px' }}>{t('admin.table.mode')}</th>
                  <th style={{ padding: '10px 8px' }}>{t('admin.table.complexity')}</th>
                  <th style={{ padding: '10px 8px' }}>{t('admin.table.timestamp')}</th>
                </tr>
              </thead>
              <tbody>
                {userInteractions.map((r, idx) => (
                  <tr key={`${r.user_id}-${r.timestamp}-${idx}`} style={{ borderTop: '1px solid var(--border)' }}>
                    <td style={{ padding: '10px 8px' }}>{r.user_id || '-'}</td>
                    <td style={{ padding: '10px 8px', maxWidth: 520, whiteSpace: 'normal', overflowWrap: 'anywhere' }}>
                      {r.user_message || '-'}
                    </td>
                    <td style={{ padding: '10px 8px' }}>{summarizeTopics(r.topics)}</td>
                    <td style={{ padding: '10px 8px' }}><span className="mode-badge">{r.tutoring_mode || '-'}</span></td>
                    <td style={{ padding: '10px 8px' }}>{r.complexity || '-'}</td>
                    <td style={{ padding: '10px 8px' }}>{formatDate(r.timestamp)}</td>
                  </tr>
                ))}
                {(interactionsLoading || userInteractions.length === 0) && (
                  <tr>
                    <td colSpan="6" style={{ padding: 12, color: 'var(--text-secondary)' }}>
                      {interactionsLoading ? t('admin.userDetail.loading') : t('admin.noRecentInteractions')}
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        <div className="glass-effect" style={{ padding: 20, borderRadius: 16, minWidth: 0 }}>
          <h3 style={{ marginBottom: 12 }}>{t('admin.userDetail.title')}</h3>
          {!selectedUserId && <p style={{ color: 'var(--text-secondary)' }}>{t('admin.userDetail.selectPrompt')}</p>}
          {selectedUserId && !selectedUserDetail && <p style={{ color: 'var(--text-secondary)' }}>{userDetailLoading ? t('admin.userDetail.loading') : t('admin.userDetail.unable')}</p>}
          {selectedUserDetail && (
            <div style={{ display: 'grid', gap: 12 }}>
              <div><strong>{t('admin.userDetail.userId')}:</strong> {selectedUserDetail.user_id || '-'}</div>
              <div><strong>{t('admin.userDetail.email')}:</strong> {selectedUserDetail.email || '-'}</div>
              <div><strong>{t('admin.userDetail.modeHistory')}:</strong> {selectedUserDetail.mode_history?.length || 0} {t('admin.userDetail.entries')}</div>
              <div><strong>{t('admin.userDetail.misconceptions')}:</strong> {selectedUserDetail.misconceptions?.length || 0}</div>
              <div><strong>{t('admin.userDetail.recentInteractions')}:</strong> {userInteractions.length || selectedUserDetail.recent_interactions?.length || 0}</div>
            </div>
          )}
        </div>
      </div>
    </section>
  );
}
