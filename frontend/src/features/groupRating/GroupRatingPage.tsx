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

interface RatingMemberRow {
  school_id: string;
  name: string;
}

interface RatingGroupDetail {
  id: number;
  name: string;
  leader: RatingMemberRow;
  members: RatingMemberRow[];
  submission_count?: number;
  member_count?: number;
  submitted_school_ids?: string[];
}

interface GroupRatingDetails {
  groups: RatingGroupDetail[];
  own_result: { scores: Record<string, number>; final_score: string; released_at: string } | null;
}

export default function GroupRatingPage() {
  const [sessions, setSessions] = useState<RatingSession[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);
  const [title, setTitle] = useState('');
  const [deadline, setDeadline] = useState('');
  const [criteria, setCriteria] = useState('Teamwork\nCommunication\nReliability');
  const [details, setDetails] = useState<Record<number, GroupRatingDetails>>({});
  const [publishLeader, setPublishLeader] = useState('');
  const [publishGroupName, setPublishGroupName] = useState('');
  const [memberIds, setMemberIds] = useState('');
  const [ratings, setRatings] = useState<Record<string, Record<string, number>>>({});
  const [canCreate, setCanCreate] = useState(false);

  const load = async () => {
    try {
      const body = await getJSON('/api/v1/group-rating/') as {
        sessions: RatingSession[];
        details: Record<number, GroupRatingDetails>;
        capabilities: { create: boolean; publish: boolean };
      };
      setSessions(body.sessions);
      setDetails(body.details);
      setCanCreate(body.capabilities.create);
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

  const publishSession = async (sessionId: number) => {
    setBusy(true);
    setError('');
    try {
      await postJSON(`/api/v1/group-rating/sessions/${sessionId}/publish/`, {
        groups: [{ name: publishGroupName, leader_school_id: publishLeader }],
      });
      await load();
      setPublishGroupName('');
      setPublishLeader('');
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to publish the session.');
    } finally {
      setBusy(false);
    }
  };

  const confirmMembers = async (sessionId: number) => {
    setBusy(true);
    setError('');
    try {
      await postJSON(`/api/v1/group-rating/sessions/${sessionId}/members/`, {
        school_ids: memberIds.split(',').map((item) => item.trim()).filter(Boolean),
      });
      setMemberIds('');
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to confirm members.');
    } finally {
      setBusy(false);
    }
  };

  const submitRatings = async (sessionId: number) => {
    setBusy(true);
    setError('');
    try {
      await postJSON(`/api/v1/group-rating/sessions/${sessionId}/submit/`, { ratings });
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to submit ratings.');
    } finally {
      setBusy(false);
    }
  };

  const releaseResults = async (sessionId: number) => {
    setBusy(true);
    setError('');
    try {
      await postJSON(`/api/v1/group-rating/sessions/${sessionId}/release/`, {});
      await load();
    } catch (caught) {
      setError(caught instanceof ApiError ? caught.message : 'Unable to release results.');
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

      {canCreate && <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
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
      </section>}

      <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
        <h2 className="dashboard-heading text-lg font-semibold">Rating sessions</h2>
        {sessions.length === 0 ? (
          <p className="dashboard-muted mt-3 text-sm">No rating sessions are available to your account.</p>
        ) : (
          <div className="mt-4 space-y-4">
            {sessions.map((session) => {
              const detail = details[session.id];
              const group = detail?.groups[0];
              return (
                <article key={session.id} className="rounded-xl border p-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <h3 className="dashboard-heading font-semibold">{session.title}</h3>
                      <p className="dashboard-muted mt-1 text-sm">
                        {session.role} · {session.status} · Due {new Date(session.deadline).toLocaleString()}
                      </p>
                    </div>
                  </div>

                  {session.role === 'professor' && session.status === 'draft' && (
                    <div className="mt-4 grid gap-3 sm:grid-cols-2">
                      <input className="rounded-lg border px-3 py-2" value={publishGroupName}
                        onChange={(event) => setPublishGroupName(event.target.value)} placeholder="Group name" />
                      <input className="rounded-lg border px-3 py-2" value={publishLeader}
                        onChange={(event) => setPublishLeader(event.target.value)} placeholder="Group leader CTU-G ID" />
                      <button type="button" className="w-fit rounded-lg bg-green-700 px-4 py-2 text-sm font-semibold text-white"
                        disabled={busy || !publishGroupName.trim() || !publishLeader.trim()}
                        onClick={() => void publishSession(session.id)}>Publish session</button>
                    </div>
                  )}

                  {session.role === 'professor' && session.status !== 'draft' && (
                    <div className="mt-4">
                      <h4 className="dashboard-heading font-semibold">Group progress</h4>
                      {detail?.groups.length ? detail.groups.map((item) => (
                        <p key={item.id} className="dashboard-muted mt-2 text-sm">
                          {item.name}: {item.submission_count}/{item.member_count} members submitted
                        </p>
                      )) : <p className="dashboard-muted mt-2 text-sm">No groups published.</p>}
                      {session.status !== 'released' && (
                        <button type="button" className="mt-3 rounded-lg bg-green-700 px-4 py-2 text-sm font-semibold text-white"
                          disabled={busy} onClick={() => void releaseResults(session.id)}>Release individual results</button>
                      )}
                    </div>
                  )}

                  {session.role === 'leader' && (
                    <div className="mt-4">
                      <label className="dashboard-heading block text-sm font-medium">
                        Member CTU-G IDs (comma separated)
                        <input className="mt-2 w-full rounded-lg border px-3 py-2" value={memberIds}
                          onChange={(event) => setMemberIds(event.target.value)} placeholder="STUDENT-DEMO-001, 2026-..." />
                      </label>
                      <button type="button" className="mt-3 rounded-lg bg-green-700 px-4 py-2 text-sm font-semibold text-white"
                        disabled={busy || !memberIds.trim()} onClick={() => void confirmMembers(session.id)}>Confirm member list</button>
                      {group && (
                        <p className="dashboard-muted mt-3 text-sm">
                          {group.submission_count}/{group.member_count} confirmed members submitted.
                        </p>
                      )}
                    </div>
                  )}

                  {session.role === 'student' && session.status === 'published' && !session.submitted && (
                    <div className="mt-4 overflow-x-auto">
                      <table className="w-full min-w-[600px] border-collapse text-sm">
                        <thead>
                          <tr className="border-b text-left">
                            <th className="px-3 py-2">Group member</th>
                            {session.criteria.map((criterion) => <th key={criterion} className="px-3 py-2">{criterion}</th>)}
                          </tr>
                        </thead>
                        <tbody>
                          {group?.members.map((member) => (
                            <tr key={member.school_id} className="border-b">
                              <td className="px-3 py-2">{member.name}</td>
                              {session.criteria.map((criterion) => (
                                <td key={criterion} className="px-3 py-2">
                                  <select className="rounded border px-2 py-1"
                                    value={ratings[member.school_id]?.[criterion] ?? ''}
                                    onChange={(event) => setRatings((current) => ({
                                      ...current,
                                      [member.school_id]: {
                                        ...current[member.school_id],
                                        [criterion]: Number(event.target.value),
                                      },
                                    }))}>
                                    <option value="">Select</option>
                                    {[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value}</option>)}
                                  </select>
                                </td>
                              ))}
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      <button type="button" className="mt-4 rounded-lg bg-green-700 px-4 py-2 text-sm font-semibold text-white"
                        disabled={busy} onClick={() => void submitRatings(session.id)}>Submit and lock ratings</button>
                    </div>
                  )}

                  {session.role === 'student' && session.submitted && (
                    <p className="dashboard-muted mt-4 text-sm">Your rating form is locked after submission.</p>
                  )}

                  {session.role === 'student' && detail?.own_result && (
                    <div className="mt-4 rounded-xl border p-4">
                      <h4 className="dashboard-heading font-semibold">Your released result</h4>
                      <p className="mt-2 text-sm">Final score: <strong>{detail.own_result.final_score}</strong></p>
                      {Object.entries(detail.own_result.scores).map(([criterion, score]) => (
                        <p key={criterion} className="dashboard-muted mt-1 text-sm">{criterion}: {score}</p>
                      ))}
                    </div>
                  )}
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
