import { useMemo, useState } from 'react';
import {
  applySimulatedDecision,
  canSimulateDecision,
  DEMO_REGISTRATIONS,
  filterPendingRegistrations,
  REJECTION_OPTIONS,
} from './registrationReviewPreviewModel';
import type {
  DemoRegistration,
  RejectionCode,
  ReviewDecision,
  ReviewRole,
} from './registrationReviewPreviewModel';

interface Selection { accountId: number; action: ReviewDecision }

/** Fictional UI rehearsal only. Does not fetch, post, or mutate account records. */
export default function RegistrationReviewPreview({ permissions }: { permissions: readonly string[] }) {
  const [records, setRecords] = useState<DemoRegistration[]>(() => DEMO_REGISTRATIONS.map((item) => ({ ...item })));
  const [search, setSearch] = useState('');
  const [role, setRole] = useState<'All' | ReviewRole>('All');
  const [selected, setSelected] = useState<Selection | null>(null);
  const [reason, setReason] = useState<RejectionCode | ''>('');
  const [notice, setNotice] = useState('');
  const visible = useMemo(() => filterPendingRegistrations(records, search, role), [records, search, role]);
  const pendingCount = records.filter((item) => item.status === 'Pending').length;
  const selectedRecord = selected ? records.find((item) => item.account_id === selected.accountId) : undefined;

  const choose = (accountId: number, action: ReviewDecision) => {
    if (!canSimulateDecision(permissions, action)) return;
    setSelected({ accountId, action });
    setReason('');
    setNotice('');
  };

  const confirm = () => {
    if (!selected || !canSimulateDecision(permissions, selected.action)) return;
    if (selected.action === 'reject' && !reason) return;
    try {
      setRecords((previous) => applySimulatedDecision(
        previous, selected.accountId, selected.action,
        selected.action === 'reject' ? reason as RejectionCode : undefined,
      ));
      setNotice(`Demo only: registration ${selected.accountId} marked ${selected.action === 'approve' ? 'Approved' : 'Rejected'} locally. No account was changed.`);
      setSelected(null);
      setReason('');
    } catch {
      setNotice('The fictional request was already processed. Refresh this preview to reset it.');
      setSelected(null);
    }
  };

  return (
    <div className="space-y-5">
      <header>
        <p className="dashboard-eyebrow">Administration · UI rehearsal</p>
        <h2 className="dashboard-heading mt-1 text-2xl font-bold sm:text-3xl">Registration review</h2>
        <p className="dashboard-muted mt-2 text-sm">Preview the request list, filters and decision flow. Nothing here is connected to your database.</p>
      </header>

      <section role="status" aria-label="Preview safety notice" className="rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950">
        <strong>Fictional data · Disabled feature preview.</strong> All School IDs below are invented. Decisions are simulated in your browser only; no approval, rejection, notification or audit record is submitted.
      </section>

      <section className="dashboard-panel grid gap-4 rounded-2xl border p-5 sm:grid-cols-3" aria-label="Mock registration summary">
        <div><p className="dashboard-muted text-xs">Pending (fictional)</p><p className="dashboard-heading mt-2 text-2xl font-bold">{pendingCount}</p></div>
        <div><p className="dashboard-muted text-xs">Simulated approvals</p><p className="dashboard-heading mt-2 text-2xl font-bold">{records.filter((item) => item.status === 'Approved').length}</p></div>
        <div><p className="dashboard-muted text-xs">Simulated rejections</p><p className="dashboard-heading mt-2 text-2xl font-bold">{records.filter((item) => item.status === 'Rejected').length}</p></div>
      </section>

      <section className="dashboard-panel rounded-2xl border p-4 sm:p-6" aria-labelledby="mock-queue-heading">
        <div className="mb-5 flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
          <div>
            <h3 id="mock-queue-heading" className="dashboard-heading text-lg font-semibold">Pending registrations</h3>
            <p className="dashboard-muted mt-1 text-xs">This is not a live Admin queue.</p>
          </div>
          <div className="flex flex-wrap gap-2">
            <label className="dashboard-muted flex flex-col gap-1 text-xs">
              Search fictional School ID
              <input className="dashboard-panel w-48 rounded-lg border px-3 py-2 text-sm" value={search} onChange={(event) => setSearch(event.target.value)} maxLength={50} placeholder="Search ID" />
            </label>
            <label className="dashboard-muted flex flex-col gap-1 text-xs">
              Requested role
              <select className="dashboard-panel rounded-lg border px-3 py-2 text-sm" value={role} onChange={(event) => setRole(event.target.value as 'All' | ReviewRole)}>
                <option value="All">All</option>
                <option value="Student">Student</option>
                <option value="Instructor">Instructor</option>
              </select>
            </label>
          </div>
        </div>
        {visible.length === 0 ? (
          <p className="dashboard-muted rounded-lg border p-5 text-sm">No matching fictional pending requests.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[580px] text-left text-sm">
              <thead><tr className="dashboard-muted border-b text-xs uppercase tracking-wide"><th scope="col" className="px-2 py-3">School ID</th><th scope="col" className="px-2 py-3">Requested role</th><th scope="col" className="px-2 py-3">Submitted</th><th scope="col" className="px-2 py-3">Demo actions</th></tr></thead>
              <tbody>{visible.map((item) => (
                <tr key={item.account_id} className="border-b last:border-0">
                  <td className="dashboard-heading px-2 py-3 font-semibold">{item.school_id}</td>
                  <td className="px-2 py-3">{item.requested_role}</td>
                  <td className="dashboard-muted px-2 py-3">{new Date(item.created_at).toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' })}</td>
                  <td className="px-2 py-3">
                    <div className="flex gap-2">
                      <button type="button" disabled={!canSimulateDecision(permissions, 'approve')} onClick={() => choose(item.account_id, 'approve')} className="dashboard-primary-link rounded-lg px-3 py-2 text-xs disabled:cursor-not-allowed disabled:opacity-40">Simulate approve</button>
                      <button type="button" disabled={!canSimulateDecision(permissions, 'reject')} onClick={() => choose(item.account_id, 'reject')} className="rounded-lg border px-3 py-2 text-xs disabled:cursor-not-allowed disabled:opacity-40">Simulate reject</button>
                    </div>
                  </td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
      </section>

      {notice && <p role="status" className="dashboard-panel rounded-lg border p-3 text-sm">{notice}</p>}
      {selected && selectedRecord && (
        <section role="dialog" aria-modal="true" aria-labelledby="mock-confirm-title" className="dashboard-panel rounded-2xl border-2 border-amber-300 p-5">
          <h3 id="mock-confirm-title" className="dashboard-heading text-lg font-bold">Simulate {selected.action === 'approve' ? 'approval' : 'rejection'}?</h3>
          <p className="dashboard-muted mt-2 text-sm">Fictional School ID {selectedRecord.school_id}. This changes preview data only; it will NOT affect a real account.</p>
          {selected.action === 'reject' && (
            <label className="mt-4 block text-sm font-medium">Mock rejection reason
              <select className="dashboard-panel mt-2 block w-full max-w-md rounded-lg border p-3" value={reason} onChange={(event) => setReason(event.target.value as RejectionCode | '')}>
                <option value="">Select a reason</option>
                {REJECTION_OPTIONS.map((item) => <option key={item.code} value={item.code}>{item.label}</option>)}
              </select>
            </label>
          )}
          <div className="mt-5 flex flex-wrap gap-3">
            <button type="button" className="dashboard-primary-link rounded-lg px-4 py-2 text-sm disabled:opacity-40" disabled={selected.action === 'reject' && !reason} onClick={confirm}>Confirm simulation only</button>
            <button type="button" className="rounded-lg border px-4 py-2 text-sm" onClick={() => { setSelected(null); setReason(''); }}>Cancel</button>
          </div>
        </section>
      )}
    </div>
  );
}
