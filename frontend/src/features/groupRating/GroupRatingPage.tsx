import { useEffect, useState } from 'react';
import { ApiError, getJSON, postJSON } from '../../api/client';

interface RatingGroup {
  id: number;
  name: string;
}

interface RatingSession {
  id: number;
  title: string;
  deadline: string;
  status: string;
  criteria: string[];
  role: 'leader' | 'student' | 'professor';
  group: RatingGroup | null;
  submitted: boolean;
}

export default function GroupRatingPage() {
  const [sessions, setSessions] = useState<RatingSession[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState('');
  const [deadline, setDeadline] = useState('');
  const [criteria, setCriteria] = useState('Teamwork\nCommunication\nReliability');

  const load = async () => {
    try {
      const body = await getJSON('/api/v1/group-rating/') as { sessions: RatingSession[] };
      setSessions(body.sessions);
      setError('');
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to load rating sessions.');
    }
  };

  useEffect(() => { void load(); }, []);

  const createSession = async () => {
    setBusy(true);
    setError('');
    try {
      await postJSON('/api/v1/group-rating/sessions/', {
        title,
        deadline,
        criteria: criteria.split('\n').map((item) => item.trim()).filter(Boolean),
      });
      setTitle('');
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to create the rating session.');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      {error && (
        <div className="dashboard-panel rounded-xl border px-4 py-3 text-sm" role="alert">
          {error}
        </div>
      )}

      <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
        <h2 className="dashboard-heading text-lg font-semibold">Create rating session</h2>
        <p className="dashboard-muted mt-1 text-sm">Defines the session title, deadline and Excel-style criteria.</p>
        <div className="mt-5 grid gap-4 lg:grid-cols-2">
          <label className="dashboard-heading text-sm font-medium">
            Session title
            <input className="mt-2 w-full rounded-lg border px-3 py-2" value={title}
              onChange={(event) => setTitle(event.target.value)} placeholder="Midterm Peer Rating" />
          </label>
          <label className="dashboard-heading text-sm font-medium">
            Deadline
            <input className="mt-2 w-full rounded-lg border px-3 py-2" type="datetime-local"
              value={deadline} onChange={(event) => setDeadline(event.target.value)} />
          </label>
          <label className="dashboard-heading text-sm font-medium lg:col-span-2">
            Criteria (one per line)
            <textarea className="mt-2 min-h-28 w-full rounded-lg border px-3 py-2"
              value={criteria} onChange={(event) => setCriteria(event.target.value)} />
          </label>
        </div>
        <button type="button" className="mt-4 rounded-lg bg-green-700 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          disabled={busy || !title.trim() || !deadline} onClick={() => void createSession()}>
          Create session
        </button>
      </section>

      <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
        <h2 className="dashboard-heading text-lg font-semibold">Rating sessions</h2>
        {sessions.length === 0 ? (
          <p className="dashboard-muted mt-3 text-sm">No rating sessions are available to your account.</p>
        ) : (
          <div className="mt-4 overflow-x-auto">
            <table className="w-full min-w-[700px] border-collapse text-sm">
              <thead>
                <tr className="border-b text-left">
                  <th className="px-3 py-3">Session</th>
                  <th className="px-3 py-3">Role</th>
                  <th className="px-3 py-3">Status</th>
                  <th className="px-3 py-3">Deadline</th>
                  <th className="px-3 py-3">Criteria</th>
                </tr>
              </thead>
              <tbody>
                {sessions.map((session) => (
                  <tr key={session.id} className="border-b">
                    <td className="px-3 py-3 font-medium">{session.title}</td>
                    <td className="px-3 py-3 capitalize">{session.role}</td>
                    <td className="px-3 py-3">{session.status}</td>
                    <td className="px-3 py-3">{new Date(session.deadline).toLocaleString()}</td>
                    <td className="px-3 py-3">{session.criteria.join(' · ')}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
}
