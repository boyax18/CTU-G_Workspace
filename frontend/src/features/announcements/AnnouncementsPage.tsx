import { useEffect, useState } from 'react';
import { ApiError, getJSON } from '../../api/client';

interface Announcement {
  id: number;
  title: string;
  body: string;
  author_name: string | null;
  created_at: string;
}

export default function AnnouncementsPage() {
  const [items, setItems] = useState<Announcement[] | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let cancelled = false;
    getJSON('/api/v1/announcements/')
      .then((result) => { if (!cancelled) setItems(Array.isArray(result) ? result as Announcement[] : []); })
      .catch((caught) => {
        if (!cancelled) setError(caught instanceof ApiError ? caught.message : 'Unable to load announcements.');
      });
    return () => { cancelled = true; };
  }, []);

  if (error) return <p className="dashboard-error" role="alert">{error}</p>;
  if (!items) return <p className="dashboard-muted" role="status">Loading announcements...</p>;
  if (items.length === 0) return <p className="dashboard-muted">No announcements yet.</p>;

  return (
    <div className="space-y-4">
      {items.map((item) => (
        <article key={item.id} className="dashboard-panel rounded-2xl border p-5 sm:p-6">
          <h2 className="dashboard-heading text-lg font-semibold">{item.title}</h2>
          <p className="dashboard-muted mt-1 text-sm">
            {item.author_name || 'Admin Office'} · {Number.isNaN(Date.parse(item.created_at)) ? '-' : new Date(item.created_at).toLocaleString()}
          </p>
          <p className="dashboard-heading mt-4 whitespace-pre-line text-sm leading-relaxed">{item.body}</p>
        </article>
      ))}
    </div>
  );
}
