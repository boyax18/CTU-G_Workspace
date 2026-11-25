import { useEffect, useState } from 'react';
import { ApiError, getJSON, postJSON } from '../../api/client';

interface NotificationItem {
  id: number;
  title: string;
  body: string;
  is_read: boolean;
  created_at: string;
}

export default function NotificationsPage() {
  const [items, setItems] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);

  const load = async () => {
    try {
      const body = await getJSON('/api/v1/notifications/') as { notifications: NotificationItem[]; unread_count: number };
      setItems(body.notifications);
      setUnreadCount(body.unread_count);
      setError('');
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to load notifications.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { void load(); }, []);

  const markRead = async (id: number) => {
    await postJSON(`/api/v1/notifications/${id}/read/`, {});
    await load();
    window.dispatchEvent(new Event('notifications-updated'));
  };

  const markAllRead = async () => {
    await postJSON('/api/v1/notifications/read-all/', {});
    await load();
    window.dispatchEvent(new Event('notifications-updated'));
  };

  if (loading) return <p className="dashboard-muted" role="status">Loading notifications...</p>;
  if (error) return <p className="dashboard-error" role="alert">{error}</p>;

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <p className="dashboard-muted text-sm">{unreadCount} unread</p>
        {unreadCount > 0 && (
          <button type="button" className="dashboard-primary-link rounded-lg px-3 py-2 text-sm" onClick={() => void markAllRead()}>
            Mark all as read
          </button>
        )}
      </div>
      {items.length === 0 ? (
        <p className="dashboard-muted">No notifications yet.</p>
      ) : items.map((item) => (
        <button
          key={item.id}
          type="button"
          onClick={() => void markRead(item.id)}
          className={`dashboard-panel block w-full rounded-2xl border p-5 text-left ${item.is_read ? 'opacity-60' : ''}`}
        >
          <h2 className="dashboard-heading font-semibold">{item.title}</h2>
          {item.body && <p className="dashboard-muted mt-2 whitespace-pre-line text-sm">{item.body}</p>}
          <p className="dashboard-muted mt-2 text-xs">
            {Number.isNaN(Date.parse(item.created_at)) ? '-' : new Date(item.created_at).toLocaleString()} · {item.is_read ? 'Read' : 'Unread'}
          </p>
        </button>
      ))}
    </div>
  );
}
