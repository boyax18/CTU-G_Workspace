/** AR-6C7E.1: Real-data review UI, but UNMOUNTED and hard-disabled until release.
 * This component must not be used to authorize a request. Django rechecks everything.
 */
import { useEffect, useMemo, useState } from 'react';
import {
  approveRegistrationRequest,
  listPendingRegistrationRequests,
  rejectRegistrationRequest,
} from './registrationReviewApi.ts';
import type {
  PendingRegistrationItem,
  PendingRegistrationPage,
  RegistrationReviewAction,
  RegistrationReviewRejectionCode,
} from './registrationReviewApiContract.ts';
import { REGISTRATION_REVIEW_LIVE_API_ENABLED } from './registrationReviewApiGate.ts';
import { REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT } from './registrationReviewLiveConfig.ts';
import { REJECTION_OPTIONS } from './registrationReviewPreviewModel.ts';
import {
  filterCurrentPage,
  mayShowDecision,
  mayShowReviewPanel,
  safeReviewError,
} from './registrationReviewLiveViewModel.ts';
import type { PageRoleFilter } from './registrationReviewLiveViewModel.ts';

type FetchState =
  | { status: 'loading' }
  | { status: 'failed'; message: string }
  | { status: 'ready'; data: PendingRegistrationPage };

type PendingDecision = { item: PendingRegistrationItem; action: RegistrationReviewAction };

interface Props {
  roles: readonly string[];
  permissions: readonly string[];
}

/** Hard-disabled in current builds; no hooks or network calls in the disabled branch. */
export default function RegistrationReviewLivePanel({ roles, permissions }: Props) {
  if (!mayShowReviewPanel(roles, permissions, REGISTRATION_REVIEW_LIVE_API_ENABLED)
    || !REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT) {
    return (
      <section role="status" className="dashboard-panel rounded-2xl border p-6">
        <h2 className="dashboard-heading text-xl font-semibold">Registration Review unavailable</h2>
        <p className="dashboard-muted mt-2 text-sm">This module has not been activated or you do not have the required access.</p>
      </section>
    );
  }
  return <AuthorizedReviewPanel permissions={permissions} routeRoot={REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT} />;
}

function AuthorizedReviewPanel({ permissions, routeRoot }: { permissions: readonly string[]; routeRoot: string }) {
  const [page, setPage] = useState(1);
  const [refreshVersion, setRefreshVersion] = useState(0);
  const [listing, setListing] = useState<FetchState>({ status: 'loading' });
  const [search, setSearch] = useState('');
  const [roleFilter, setRoleFilter] = useState<PageRoleFilter>('All');
  const [selection, setSelection] = useState<PendingDecision | null>(null);
  const [reason, setReason] = useState<RegistrationReviewRejectionCode | ''>('');
  const [submitting, setSubmitting] = useState(false);
  const [notice, setNotice] = useState('');

  useEffect(() => {
    let cancelled = false;
    // Loading and refresh must never reuse stale records as live authorization evidence.
    listPendingRegistrationRequests(routeRoot, page)
      .then((data) => { if (!cancelled) setListing({ status: 'ready', data }); })
      .catch((error: unknown) => {
        if (!cancelled) setListing({ status: 'failed', message: safeReviewError(error) });
      });
    return () => { cancelled = true; };
  }, [page, refreshVersion, routeRoot]);

  const rows = listing.status === 'ready' ? listing.data.results : [];
  const filtered = useMemo(() => filterCurrentPage(rows, search, roleFilter), [rows, search, roleFilter]);
  const canApprove = mayShowDecision(permissions, 'approve');
  const canReject = mayShowDecision(permissions, 'reject');

  function reload() {
    if (submitting) return;
    setSelection(null);
    setReason('');
    setNotice('');
    setListing({ status: 'loading' });
    setRefreshVersion((current) => current + 1);
  }

  function startDecision(item: PendingRegistrationItem, action: RegistrationReviewAction) {
    if (submitting || !mayShowDecision(permissions, action)) return;
    if (listing.status !== 'ready' || !listing.data.results.some((row) => row.account_id === item.account_id)) return;
    setSelection({ item, action });
    setReason('');
    setNotice('');
  }

  async function confirmDecision() {
    if (!selection || submitting || !mayShowDecision(permissions, selection.action)) return;
    if (selection.action === 'reject' && !reason) return;
    setSubmitting(true);
    setNotice('');
    try {
      if (selection.action === 'approve') {
        await approveRegistrationRequest(routeRoot, selection.item.account_id);
      } else {
        await rejectRegistrationRequest(
          routeRoot,
          selection.item.account_id,
          reason as RegistrationReviewRejectionCode,
        );
      }
      setNotice(`Server confirmed ${selection.action === 'approve' ? 'approval' : 'rejection'} of School ID ${selection.item.school_id}.`);
      setSelection(null);
      setReason('');
      setListing({ status: 'loading' });
      setRefreshVersion((current) => current + 1);
    } catch (error: unknown) {
      setNotice(safeReviewError(error));
      // An ambiguous POST is NEVER automatically retried. User must refresh first.
      setSelection(null);
      setReason('');
      setListing({ status: 'failed', message: 'Refresh to check the current request state before another action.' });
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section className="space-y-5" aria-label="Registration Review">
      <header>
        <p className="dashboard-eyebrow">Administration · Account Management</p>
        <h2 className="dashboard-heading mt-1 text-2xl font-bold sm:text-3xl">Pending registrations</h2>
        <p className="dashboard-muted mt-2 text-sm">Student and Instructor self-registration requests, verified by the protected Django API.</p>
      </header>

      {notice && <p role="status" aria-live="polite" className="dashboard-panel rounded-lg border p-3 text-sm">{notice}</p>}

      <div className="dashboard-panel rounded-2xl border p-4 sm:p-6">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <h3 className="dashboard-heading text-lg font-semibold">Review queue</h3>
            <p className="dashboard-muted mt-1 text-xs">Filters search only the current page; the server returns up to 20 requests per page.</p>
          </div>
          <button type="button" disabled={submitting} className="rounded-lg border px-4 py-2 text-sm disabled:opacity-50" onClick={reload}>Refresh list</button>
        </div>
        <div className="my-4 flex flex-wrap gap-3">
          <label className="dashboard-muted flex flex-col gap-1 text-xs">
            Filter School ID on this page
            <input value={search} maxLength={50} onChange={(event) => setSearch(event.target.value)} placeholder="School ID" className="dashboard-panel w-52 rounded-lg border px-3 py-2 text-sm" />
          </label>
          <label className="dashboard-muted flex flex-col gap-1 text-xs">
            Filter requested role on this page
            <select value={roleFilter} onChange={(event) => setRoleFilter(event.target.value as PageRoleFilter)} className="dashboard-panel rounded-lg border px-3 py-2 text-sm">
              <option value="All">All roles</option>
              <option value="Student">Student</option>
              <option value="Instructor">Instructor</option>
            </select>
          </label>
        </div>
        {listing.status === 'loading' ? (
          <p role="status" className="dashboard-muted py-8 text-sm">Loading pending requests…</p>
        ) : listing.status === 'failed' ? (
          <p role="alert" className="dashboard-muted py-8 text-sm">{listing.message}</p>
        ) : filtered.length === 0 ? (
          <p className="dashboard-muted py-8 text-sm">No matching pending registrations on this page.</p>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full min-w-[590px] text-left text-sm">
              <thead><tr className="dashboard-muted border-b text-xs uppercase tracking-wide"><th scope="col" className="px-2 py-3">School ID</th><th scope="col" className="px-2 py-3">Requested role</th><th scope="col" className="px-2 py-3">Submitted</th><th scope="col" className="px-2 py-3">Actions</th></tr></thead>
              <tbody>{filtered.map((item) => (
                <tr key={item.account_id} className="border-b last:border-0">
                  <td className="dashboard-heading px-2 py-3 font-semibold">{item.school_id}</td>
                  <td className="px-2 py-3">{item.requested_role}</td>
                  <td className="dashboard-muted px-2 py-3">{new Date(item.created_at).toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' })}</td>
                  <td className="px-2 py-3"><div className="flex gap-2">
                    <button type="button" disabled={submitting || !canApprove} className="dashboard-primary-link rounded-lg px-3 py-2 text-xs disabled:opacity-40" onClick={() => startDecision(item, 'approve')}>Approve</button>
                    <button type="button" disabled={submitting || !canReject} className="rounded-lg border px-3 py-2 text-xs disabled:opacity-40" onClick={() => startDecision(item, 'reject')}>Reject</button>
                  </div></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        )}
        <div className="mt-4 flex items-center justify-between border-t pt-3 text-sm">
          <button type="button" disabled={page <= 1 || submitting} className="rounded-lg border px-3 py-2 disabled:opacity-40" onClick={() => { setPage((p) => p - 1); setSelection(null); setListing({ status: 'loading' }); }}>Previous</button>
          <span className="dashboard-muted">Page {page}</span>
          <button type="button" disabled={listing.status !== 'ready' || rows.length < 20 || submitting || page >= 10000} className="rounded-lg border px-3 py-2 disabled:opacity-40" onClick={() => { setPage((p) => p + 1); setSelection(null); setListing({ status: 'loading' }); }}>Next</button>
        </div>
      </div>

      {selection && (
        <section role="dialog" aria-modal="true" aria-labelledby="review-decision-heading" className="dashboard-panel rounded-2xl border-2 border-emerald-600 p-5">
          <h3 id="review-decision-heading" className="dashboard-heading text-lg font-bold">Confirm {selection.action === 'approve' ? 'approval' : 'rejection'}?</h3>
          <p className="dashboard-muted mt-2 text-sm">School ID {selection.item.school_id} · {selection.item.requested_role}. This is a real account action and will be audited.</p>
          {selection.action === 'reject' && (
            <label className="mt-4 block text-sm font-medium">Rejection reason
              <select className="dashboard-panel mt-2 block w-full max-w-md rounded-lg border p-3" value={reason} onChange={(event) => setReason(event.target.value as RegistrationReviewRejectionCode | '')}>
                <option value="">Choose a reason</option>
                {REJECTION_OPTIONS.map((entry) => <option key={entry.code} value={entry.code}>{entry.label}</option>)}
              </select>
            </label>
          )}
          <div className="mt-5 flex flex-wrap gap-3">
            <button type="button" className="dashboard-primary-link rounded-lg px-4 py-2 text-sm disabled:opacity-40" disabled={submitting || (selection.action === 'reject' && !reason)} onClick={() => { void confirmDecision(); }}>{submitting ? 'Submitting…' : 'Confirm decision'}</button>
            <button type="button" disabled={submitting} className="rounded-lg border px-4 py-2 text-sm disabled:opacity-40" onClick={() => { setSelection(null); setReason(''); }}>Cancel</button>
          </div>
        </section>
      )}
    </section>
  );
}
