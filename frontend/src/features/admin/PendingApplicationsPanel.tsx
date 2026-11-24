/** WF-02.01 View pending applications (and the WF-02.02 entry point).
 *
 * Search (debounced ~300 ms), the dropdown filters and the sort apply automatically and together
 * through the existing server-side query; every change returns to page 1 and clears the selection.
 *
 * `?applicant={id}` opens the WF-02.02 detail inside this same view; the list state (filters,
 * sort, page and loaded rows) stays in memory, so Back to pending applications restores it.
 *
 * Decision controls appear only when the frontend switches, the session permission hints and the
 * server's request-local availability header (route, gate, outbox, executor) all allow them.
 * Selecting ONE applicant uses the individual approve/reject endpoint (WF-02.03/02.04); selecting
 * two to twenty uses the bounded bulk endpoint. The backend rechecks every selected applicant.
 * The session permission hint only decides navigation; Django checks the Admin assignment and the
 * exact effective permission on every request, and this view shows only what the server returns.
 */
import { useEffect, useEffectEvent, useId, useRef, useState } from 'react';
import type { FormEvent, MouseEvent } from 'react';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import Modal from '../../components/common/Modal';
import ApplicantDetailPanel from './ApplicantDetailPanel';
import { approveApplication, decideBulkApplications, listPendingApplications, rejectApplication } from './registrationReviewApi.ts';
import { normalizePendingSearch, PENDING_APPLICATION_SEARCH_MAX } from './registrationReviewApiContract.ts';
import type {
  BulkRegistrationDecisionResult,
  PendingApplicationProofFilter,
  PendingApplicationSort,
  PendingApplicationsQuery,
  PendingRegistrationItem,
  PendingRegistrationPage,
  RegistrationReviewRejectionCode,
  RegistrationReviewRole,
} from './registrationReviewApiContract.ts';
import {
  ELIGIBILITY_SOURCE_FOR_ROLE, ELIGIBILITY_SOURCE_LABELS, REJECTION_PUBLIC_LABELS, REGISTRATION_REJECTION_CODES,
} from './registrationReviewApiContract.ts';
import {
  APPLICANT_APPROVAL_ENABLED, APPLICANT_REJECTION_ENABLED, BULK_APPLICANT_DECISIONS_ENABLED,
} from './pendingApplicationsConfig.ts';

interface Filters {
  q: string;
  role: '' | RegistrationReviewRole;
  proof: '' | PendingApplicationProofFilter;
  sort: PendingApplicationSort;
}

type Listing =
  // `previous` keeps the last results visible, dimmed and inert, while newer ones load.
  | { status: 'loading'; previous?: PendingRegistrationPage }
  | { status: 'failed'; code: string }
  | { status: 'ready'; data: PendingRegistrationPage };

type BulkAction = 'approve' | 'reject';
type BulkSummary = Pick<BulkRegistrationDecisionResult, 'action' | 'requested' | 'processed' | 'remaining' | 'interrupted' | 'counts'>
  & { results: Array<{ school_id: string | null; outcome: string; notification?: 'queued' }> };

const APPROVE_PERMISSION = 'accounts.registration_requests.approve';
const REJECT_PERMISSION = 'accounts.registration_requests.reject';
const MAX_BULK = 20;

/** Fixed messages for definite refusals of ONE decision; server text is never displayed. */
function decisionRefusal(code: string, action: BulkAction): string {
  switch (code) {
    case 'email_unverified': return 'Approval is not allowed: the applicant has no verified email for the address on file.';
    case 'eligibility_unconfirmed': return 'Approval needs the eligibility confirmation for this applicant.';
    case 'recipient_unverified': return 'Rejection is not allowed: there is no verified email address to notify.';
    case 'direct_permissions':
    case 'protected_history': return 'Rejection is not allowed for this application. Review it for details.';
    case 'request_unavailable': return 'This application is no longer pending. The list has been refreshed.';
    case 'access_denied': return 'You are no longer authorized to perform this decision.';
    case 'authentication_required': return 'Your session has ended. Sign in again to continue.';
    case 'rate_limited': return 'Too many requests. Wait before trying again.';
    default: return `The ${action === 'approve' ? 'approval' : 'rejection'} could not be completed. No automatic retry was made.`;
  }
}

const DEFAULT_FILTERS: Filters = { q: '', role: '', proof: '', sort: 'submitted' };
const SEARCH_DEBOUNCE_MS = 300;

function sameFilters(a: Filters, b: Filters): boolean {
  return a.q === b.q && a.role === b.role && a.proof === b.proof && a.sort === b.sort;
}
const SORT_LABELS: Record<PendingApplicationSort, string> = {
  submitted: 'Oldest submitted first',
  '-submitted': 'Newest submitted first',
  school_id: 'CTU-G ID, ascending',
  '-school_id': 'CTU-G ID, descending',
};
const NO_PROOF = 'No email proof on record';

const fieldClass = 'dashboard-panel min-h-11 rounded-lg border px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]';
const primaryButton = 'dashboard-primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)] disabled:cursor-not-allowed disabled:opacity-50';
const focusRing = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]';
// Same destructive confirm style as ApplicantRejectionPanel (PATTERNS.md §4: destructive confirm for reject).
const destructiveButton = `inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#b91c1c] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#991b1b] disabled:cursor-not-allowed disabled:opacity-50 ${focusRing}`;
const secondaryButton = 'dashboard-outline-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)] disabled:cursor-not-allowed disabled:opacity-50';
const badgeClass = 'inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium whitespace-nowrap';

function toQuery(filters: Filters): PendingApplicationsQuery {
  const query: PendingApplicationsQuery = {};
  if (filters.q) query.q = filters.q;
  if (filters.role) query.role = filters.role;
  if (filters.proof) query.proof = filters.proof;
  if (filters.sort !== 'submitted') query.sort = filters.sort;
  return query;
}

function hasActiveFilters(filters: Filters): boolean {
  return Boolean(filters.q || filters.role || filters.proof);
}

/** Fixed, non-sensitive messages; server text is never displayed. */
function failureMessage(code: string): { title: string; detail: string; retry: boolean } {
  switch (code) {
    case 'authentication_required':
      return { title: 'Your session has ended.', detail: 'Sign in again to continue.', retry: false };
    case 'access_denied':
      return { title: 'You do not have permission to view applications.', detail: 'Ask a School Admin to check your account access.', retry: false };
    case 'invalid_request':
      return { title: 'The search or filters could not be used.', detail: 'Check the search and filters, then apply them again.', retry: false };
    case 'rate_limited':
      return { title: 'Too many requests.', detail: 'Wait a minute, then try again.', retry: true };
    case 'review_unavailable':
      return { title: 'Pending applications are not available right now.', detail: 'Try again later.', retry: true };
    default:
      return { title: 'Applications could not be loaded.', detail: 'Check your connection, then try again.', retry: true };
  }
}

function formatDate(value: string): string {
  return new Date(value).toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' });
}

function formatTimestamp(value: string): string {
  return new Date(value).toLocaleString('en-PH', { dateStyle: 'medium', timeStyle: 'short' });
}

function ProofBadge({ verified }: { verified: boolean }) {
  return verified ? (
    <span className={`${badgeClass} dashboard-heading`}><span aria-hidden="true">✓</span>Email verified</span>
  ) : (
    <span className={`${badgeClass} dashboard-muted border-dashed`}><span aria-hidden="true">!</span>{NO_PROOF}</span>
  );
}

function ApplicantName({ name }: { name: string | null }) {
  return name ? <span className="break-words">{name}</span> : <span className="dashboard-muted italic">Not recorded</span>;
}

function Submitted({ value }: { value: string }) {
  return <time dateTime={value} title={formatTimestamp(value)}>{formatDate(value)}</time>;
}

const reviewLinkClass = 'dashboard-accent inline-flex min-h-11 items-center gap-1 rounded-lg px-1 text-sm font-semibold underline-offset-2 hover:underline focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]';

/** A real link (new tab works); a plain click opens the detail inside this view. */
function ReviewLink({ item, onOpen }: { item: PendingRegistrationItem; onOpen: (id: number) => void }) {
  const label = 'CTU-G ID';
  const follow = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onOpen(item.account_id);
  };
  return (
    <a href={`/dashboard?view=registration-review&applicant=${item.account_id}`} data-review-link={item.account_id}
      onClick={follow} className={reviewLinkClass}>
      Review application<span className="sr-only"> for {label} {item.school_id}</span>
    </a>
  );
}

export default function PendingApplicationsPanel() {
  const ids = useId();
  const { search, openSubpage, session } = useDashboardContext();
  const applicant = new URLSearchParams(search).get('applicant');
  const lastOpened = useRef<number | null>(null);
  // True while the open detail was reached from this list in this tab, so Back can pop history.
  const openedFromList = useRef(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState<Filters>(DEFAULT_FILTERS);
  const [applied, setApplied] = useState<Filters>(DEFAULT_FILTERS);
  const appliedRef = useRef<Filters>(DEFAULT_FILTERS);
  const appliedSearchRaw = useRef('');
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [listing, setListing] = useState<Listing>({ status: 'loading' });
  const [searchError, setSearchError] = useState('');
  const [selectedIds, setSelectedIds] = useState<Set<number>>(() => new Set());
  const [bulkAction, setBulkAction] = useState<BulkAction | null>(null);
  const [bulkEligibilityConfirmed, setBulkEligibilityConfirmed] = useState(false);
  const [bulkRejectionCode, setBulkRejectionCode] = useState<RegistrationReviewRejectionCode | ''>('');
  const [bulkSubmitting, setBulkSubmitting] = useState(false);
  const [bulkError, setBulkError] = useState('');
  const [bulkSummary, setBulkSummary] = useState<BulkSummary | null>(null);
  const bulkInFlight = useRef(false);

  useEffect(() => {
    let cancelled = false;
    // GET only. Never retried automatically; stale responses are discarded.
    listPendingApplications(page, toQuery(applied))
      .then((data) => { if (!cancelled) setListing({ status: 'ready', data }); })
      .catch((error: unknown) => {
        const code = error && typeof error === 'object' && 'code' in error ? String((error as { code: unknown }).code) : '';
        if (!cancelled) setListing({ status: 'failed', code });
      });
    return () => { cancelled = true; };
  }, [applied, page, version]);

  // Returning from a detail: put keyboard focus back on the link that opened it.
  useEffect(() => {
    if (applicant !== null) return;
    openedFromList.current = false;
    if (lastOpened.current === null) return;
    const links = document.querySelectorAll<HTMLElement>(`[data-review-link="${lastOpened.current}"]`);
    [...links].find((link) => link.offsetParent !== null)?.focus();
    lastOpened.current = null;
  }, [applicant, listing.status]);

  function openApplicant(id: number) {
    lastOpened.current = id;
    openedFromList.current = true;
    openSubpage({ applicant: String(id) });
  }

  function backToList() {
    // Reached from the list: go back in history so Forward keeps working and no duplicate
    // entries pile up. Opened directly (bookmark, new tab): push the list instead.
    if (openedFromList.current) {
      openedFromList.current = false;
      window.history.back();
    } else {
      openSubpage(null);
    }
  }

  function load(next: { filters?: Filters; page?: number }, preserveBulkSummary = false) {
    setListing((current) => ({
      status: 'loading',
      previous: current.status === 'ready' ? current.data : current.status === 'loading' ? current.previous : undefined,
    }));
    setSelectedIds(new Set());
    setBulkAction(null);
    setBulkEligibilityConfirmed(false);
    setBulkRejectionCode('');
    setBulkError('');
    if (!preserveBulkSummary) setBulkSummary(null);
    if (next.filters) {
      appliedRef.current = next.filters;
      setApplied(next.filters);
    }
    if (next.page !== undefined) setPage(next.page);
    if (!next.filters && next.page === undefined) setVersion((current) => current + 1);
  }

  /** Apply the current control values (already-applied values are not re-requested). */
  function commitFilters(values: Filters) {
    let q: string;
    try {
      q = normalizePendingSearch(values.q);
    } catch (error: unknown) {
      // Invalid search text never reaches the server; the current results stay as they are.
      setSearchError(error instanceof Error ? error.message : 'Check the search text.');
      return;
    }
    setSearchError('');
    appliedSearchRaw.current = values.q;
    const filters = { ...values, q };
    if (!sameFilters(filters, appliedRef.current)) load({ filters, page: 1 });
  }

  const commitDraft = useEffectEvent((values: Filters) => commitFilters(values));

  // Dropdowns and sort apply at once; typing is debounced. Stale responses are discarded by
  // the listing effect, so a slower earlier request can never overwrite newer results.
  useEffect(() => {
    const typing = draft.q !== appliedSearchRaw.current;
    const timer = window.setTimeout(() => commitDraft(draft), typing ? SEARCH_DEBOUNCE_MS : 0);
    return () => window.clearTimeout(timer);
  }, [draft]);

  function submitSearch(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); // Enter applies immediately instead of waiting for the debounce
    commitFilters(draft);
  }

  function clearFilters() {
    setSearchError('');
    appliedSearchRaw.current = '';
    setDraft(DEFAULT_FILTERS);
    if (!sameFilters(DEFAULT_FILTERS, appliedRef.current)) load({ filters: DEFAULT_FILTERS, page: 1 });
  }

  const loading = listing.status === 'loading';
  const rows: readonly PendingRegistrationItem[] = listing.status === 'ready' ? listing.data.results : [];
  const shown = listing.status === 'ready' ? listing.data : listing.status === 'loading' ? listing.previous : undefined;
  const tableRows: readonly PendingRegistrationItem[] = shown?.results ?? [];
  const refreshing = loading && tableRows.length > 0;
  const filtered = hasActiveFilters(applied);
  const searchHint = `${ids}-search-hint`;
  const searchErrorId = `${ids}-search-error`;
  const failure = listing.status === 'failed' ? failureMessage(listing.code) : null;
  const available = shown?.available_actions ?? [];
  const permissions = session.permissions;
  const individualApprove = APPLICANT_APPROVAL_ENABLED && available.includes('approve') && permissions.includes(APPROVE_PERMISSION);
  const individualReject = APPLICANT_REJECTION_ENABLED && available.includes('reject') && permissions.includes(REJECT_PERMISSION);
  const bulkApproveAvailable = BULK_APPLICANT_DECISIONS_ENABLED && available.includes('bulk-approve');
  const bulkRejectAvailable = BULK_APPLICANT_DECISIONS_ENABLED && available.includes('bulk-reject');
  // Checkboxes exist only when at least one decision can actually be performed in this session.
  const selectionEnabled = individualApprove || individualReject || bulkApproveAvailable || bulkRejectAvailable;
  const selectedRows = rows.filter((item) => selectedIds.has(item.account_id));
  const count = selectedRows.length;
  const allRowsSelected = rows.length > 0 && rows.every((item) => selectedIds.has(item.account_id));
  const someRowsSelected = count > 0 && !allRowsSelected;
  const canDecide = (action: BulkAction) => {
    if (count === 1) return action === 'approve' ? individualApprove || bulkApproveAvailable : individualReject || bulkRejectAvailable;
    return count > 1 && count <= MAX_BULK && (action === 'approve' ? bulkApproveAvailable : bulkRejectAvailable);
  };
  const single = count === 1 ? selectedRows[0] : null;

  function toggleSelected(accountId: number, checked: boolean) {
    setSelectedIds((current) => {
      const next = new Set(current);
      if (checked) next.add(accountId);
      else next.delete(accountId);
      return next;
    });
    setBulkError('');
  }

  function selectAllOnPage(checked: boolean) {
    setSelectedIds(checked ? new Set(rows.map((item) => item.account_id)) : new Set());
    setBulkError('');
  }

  function openConfirmation(action: BulkAction) {
    if (bulkInFlight.current || !canDecide(action)) return;
    setBulkEligibilityConfirmed(false);
    setBulkRejectionCode('');
    setBulkError('');
    setBulkAction(action);
  }

  function closeConfirmation() {
    setBulkAction(null);
    setBulkEligibilityConfirmed(false);
    setBulkRejectionCode('');
  }

  function unconfirmed(action: BulkAction, items: readonly PendingRegistrationItem[]) {
    setBulkSummary({
      action, requested: items.length, processed: items.length, remaining: 0, interrupted: true,
      counts: { Approved: 0, Rejected: 0, Skipped: 0, Failed: 0, Unconfirmed: items.length },
      results: items.map((item) => ({ school_id: item.school_id, outcome: 'Unconfirmed' })),
    });
    setSelectedIds(new Set());
    setBulkAction(null);
    load({}, true);
  }

  /** ONE applicant: the individual endpoint. POST once, never retried. */
  async function decideOne(action: BulkAction, item: PendingRegistrationItem, code: RegistrationReviewRejectionCode | '') {
    try {
      if (action === 'approve') await approveApplication(item.account_id, ELIGIBILITY_SOURCE_FOR_ROLE[item.requested_role]);
      else await rejectApplication(item.account_id, code as RegistrationReviewRejectionCode);
      setBulkSummary({
        action, requested: 1, processed: 1, remaining: 0, interrupted: false,
        counts: { Approved: action === 'approve' ? 1 : 0, Rejected: action === 'reject' ? 1 : 0, Skipped: 0, Failed: 0, Unconfirmed: 0 },
        results: [{ school_id: item.school_id, outcome: action === 'approve' ? 'Approved' : 'Rejected', notification: 'queued' }],
      });
      setSelectedIds(new Set());
      setBulkAction(null);
      load({}, true);
    } catch (error: unknown) {
      const errorCode = error && typeof error === 'object' && 'code' in error ? String((error as { code: unknown }).code) : '';
      if (errorCode === 'outcome_unknown') { unconfirmed(action, [item]); return; }
      setBulkAction(null);
      setBulkError(decisionRefusal(errorCode, action));
      if (errorCode === 'request_unavailable') load({}, true);
    }
  }

  /** Two to twenty applicants: the bounded bulk endpoint. */
  async function decideMany(action: BulkAction, items: readonly PendingRegistrationItem[], code: RegistrationReviewRejectionCode | '') {
    try {
      const result = await decideBulkApplications(items.map((item) => item.account_id), action,
        action === 'reject' ? code || undefined : undefined);
      const labels = new Map(items.map((item) => [item.account_id, item.school_id]));
      setBulkSummary({
        action: result.action, requested: result.requested, processed: result.processed, remaining: result.remaining,
        interrupted: result.interrupted, counts: result.counts,
        results: result.results.map((item) => ({
          school_id: labels.get(item.account_id) ?? null,
          outcome: item.outcome,
          ...(item.notification ? { notification: item.notification } : {}),
        })),
      });
      setSelectedIds(new Set());
      setBulkAction(null);
      load({}, true);
    } catch (error: unknown) {
      const errorCode = error && typeof error === 'object' && 'code' in error ? String((error as { code: unknown }).code) : '';
      if (errorCode === 'outcome_unknown') { unconfirmed(action, items); return; }
      setBulkAction(null);
      setBulkError(errorCode === 'access_denied' ? 'You are no longer authorized to perform this bulk decision.'
        : errorCode === 'authentication_required' ? 'Your session has ended. Sign in again to continue.'
          : errorCode === 'rate_limited' ? 'Too many requests. Wait before trying again.'
            : 'The bulk decision could not be completed. No automatic retry was made.');
    }
  }

  async function confirmDecision() {
    if (!bulkAction || bulkInFlight.current || !canDecide(bulkAction)) return;
    if (bulkAction === 'approve' && !bulkEligibilityConfirmed) return;
    if (bulkAction === 'reject' && !bulkRejectionCode) return;
    const items = [...selectedRows];
    const action = bulkAction;
    bulkInFlight.current = true;
    setBulkSubmitting(true);
    setBulkError('');
    try {
      const individual = items.length === 1 && (action === 'approve' ? individualApprove : individualReject);
      if (individual) await decideOne(action, items[0], bulkRejectionCode);
      else await decideMany(action, items, bulkRejectionCode);
    } finally {
      bulkInFlight.current = false;
      setBulkSubmitting(false);
    }
  }

  const approveLabel = allRowsSelected ? 'Approve All' : 'Approve';
  const rejectLabel = allRowsSelected ? 'Reject All' : 'Reject';
  const subject = single ? `${single.school_id}${single.full_name ? ` (${single.full_name})` : ''}` : `${count} applicants`;

  if (applicant !== null) {
    // WF-02.02: the server re-checks access and eligibility; the ID is validated before any request.
    return <ApplicantDetailPanel key={applicant} raw={applicant} onBack={backToList} onDecided={() => load({})} />;
  }

  return (
    <div className="space-y-5">
      {/* The shared shell renders the breadcrumbs and the page h1 ("Applicant reviews"). */}
      <section className="dashboard-panel rounded-2xl border p-4 sm:p-6" aria-labelledby={`${ids}-queue`} aria-busy={loading}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 id={`${ids}-queue`} className="dashboard-heading text-lg font-semibold">Pending applications</h2>
            <p className="dashboard-muted mt-1 text-xs">Search, filters and sorting apply to all pending applications. Up to 20 are shown per page.</p>
          </div>
          <button type="button" className={secondaryButton} disabled={loading || bulkSubmitting} onClick={() => load({})}>Refresh list</button>
        </div>

        <form role="search" aria-label="Pending applications" noValidate onSubmit={submitSearch}
          className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))]">
          <label className="dashboard-muted flex min-w-0 flex-col gap-1 text-xs font-medium sm:col-span-2 lg:col-span-1">
            Search CTU-G ID or name
            <input ref={searchRef} type="search" value={draft.q} maxLength={PENDING_APPLICATION_SEARCH_MAX}
              autoComplete="off" spellCheck={false} placeholder="e.g. 7240001 or Santos"
              aria-describedby={searchError ? `${searchErrorId} ${searchHint}` : searchHint}
              aria-invalid={searchError ? true : undefined}
              onChange={(event) => { setDraft({ ...draft, q: event.target.value }); if (searchError) setSearchError(''); }}
              className={`${fieldClass} w-full`} />
          </label>
          <label className="dashboard-muted flex min-w-0 flex-col gap-1 text-xs font-medium">
            Requested role
            <select value={draft.role} className={fieldClass}
              onChange={(event) => setDraft({ ...draft, role: event.target.value as Filters['role'] })}>
              <option value="">All roles</option>
              <option value="Student">Student</option>
              <option value="Instructor">Instructor</option>
            </select>
          </label>
          <label className="dashboard-muted flex min-w-0 flex-col gap-1 text-xs font-medium">
            Email proof
            <select value={draft.proof} className={fieldClass}
              onChange={(event) => setDraft({ ...draft, proof: event.target.value as Filters['proof'] })}>
              <option value="">All applications</option>
              <option value="verified">Email verified</option>
              <option value="legacy">{NO_PROOF}</option>
            </select>
          </label>
          <label className="dashboard-muted flex min-w-0 flex-col gap-1 text-xs font-medium">
            Sort by
            <select value={draft.sort} className={fieldClass}
              onChange={(event) => setDraft({ ...draft, sort: event.target.value as PendingApplicationSort })}>
              {(Object.keys(SORT_LABELS) as PendingApplicationSort[]).map((value) => (
                <option key={value} value={value}>{SORT_LABELS[value]}</option>
              ))}
            </select>
          </label>
          <p id={searchHint} className="dashboard-muted text-xs sm:col-span-2 lg:col-span-4">
            CTU-G IDs match from the start; names match any part. Results update as you type or choose a filter.
          </p>
          {searchError && (
            // Existing tokens only: --db-error is still Proposed (TOKENS.md §1.4). Not colour-only.
            <p id={searchErrorId} role="alert" className="dashboard-heading flex gap-2 text-sm font-semibold sm:col-span-2 lg:col-span-4">
              <span aria-hidden="true">!</span>{searchError}
            </p>
          )}
          {(hasActiveFilters(draft) || filtered) && (
            <div className="flex flex-wrap gap-3 sm:col-span-2 lg:col-span-4">
              <button type="button" className={secondaryButton} onClick={clearFilters}>Clear filters</button>
            </div>
          )}
        </form>

        {listing.status === 'ready' && rows.length > 0 && !selectionEnabled && (
          <p className="dashboard-muted mt-5 text-sm">
            Approve and Reject are not available in this session. You can still open each application to review it.
          </p>
        )}

        {listing.status === 'ready' && rows.length > 0 && selectionEnabled && count === 0 && (
          <section aria-label="Decisions for selected applicants" className="dashboard-panel mt-5 rounded-xl border p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p className="dashboard-heading text-sm font-semibold">Select applicants to approve or reject them.</p>
              <button type="button" className={secondaryButton} disabled={loading || bulkSubmitting}
                onClick={() => selectAllOnPage(true)}>
                Select All on Current Page
              </button>
            </div>
          </section>
        )}

        {listing.status === 'ready' && selectionEnabled && count > 0 && (
          <section aria-label="Decisions for selected applicants" className="dashboard-panel mt-5 rounded-xl border p-4">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <p role="status" aria-live="polite" className="dashboard-heading text-sm font-semibold">
                {count} {count === 1 ? 'applicant' : 'applicants'} selected on this page
              </p>
              <div className="flex flex-wrap gap-2">
                <button type="button" className={primaryButton} disabled={!canDecide('approve') || bulkSubmitting || loading}
                  onClick={() => openConfirmation('approve')}>
                  {approveLabel}
                </button>
                <button type="button" className={secondaryButton} disabled={!canDecide('reject') || bulkSubmitting || loading}
                  onClick={() => openConfirmation('reject')}>
                  {rejectLabel}
                </button>
                {!allRowsSelected && (
                  <button type="button" className={secondaryButton} disabled={bulkSubmitting || loading}
                    onClick={() => selectAllOnPage(true)}>
                    Select All on Current Page
                  </button>
                )}
                <button type="button" className={secondaryButton} disabled={bulkSubmitting}
                  onClick={() => selectAllOnPage(false)}>
                  Unselect All
                </button>
              </div>
            </div>
            {count > MAX_BULK && (
              <p className="dashboard-muted mt-2 text-xs">Select at most {MAX_BULK} applicants per decision.</p>
            )}
            {count > 1 && count <= MAX_BULK && (!bulkApproveAvailable || !bulkRejectAvailable) && (
              <p className="dashboard-muted mt-2 text-xs">
                Decisions for several applicants at once are not available in this session. Select one applicant at a time.
              </p>
            )}
          </section>
        )}

        {bulkError && <p role="alert" className="dashboard-error-block mt-4 rounded-lg border p-3 text-sm">{bulkError}</p>}
        {bulkSummary && (
          <section role="status" aria-live="polite" aria-label="Decision results"
            className="dashboard-panel mt-4 rounded-xl border p-4">
            <h3 className="dashboard-heading font-semibold">
              {bulkSummary.action === 'approve' ? 'Approval' : 'Rejection'} {bulkSummary.requested === 1 ? 'result' : 'results'}
            </h3>
            <p className="dashboard-muted mt-2 text-sm">
              Approved {bulkSummary.counts.Approved}; rejected {bulkSummary.counts.Rejected}; skipped {bulkSummary.counts.Skipped};
              failed {bulkSummary.counts.Failed}; unconfirmed {bulkSummary.counts.Unconfirmed}.
            </p>
            <p className="dashboard-muted mt-2 text-sm">
              Successful decisions have individual email notifications queued. Delivery is separate and is not confirmed here.
            </p>
            {(bulkSummary.interrupted || bulkSummary.remaining > 0) && (
              <p className="dashboard-warning mt-2 text-sm">
                Processing stopped. {bulkSummary.remaining} applicant(s) were not attempted. Unconfirmed decisions are not retried automatically.
              </p>
            )}
            {bulkSummary.results.length > 0 && (
              <ul className="mt-3 space-y-1 text-sm">
                {bulkSummary.results.map((item, index) => (
                  <li key={`${item.school_id ?? 'unknown'}-${index}`}>
                    {item.school_id ?? 'Selected applicant'} — {item.outcome}
                    {item.notification === 'queued' ? ' (email queued; delivery not confirmed)' : ''}
                  </li>
                ))}
              </ul>
            )}
          </section>
        )}

        <div className="mt-5 border-t pt-4">
          {loading && !refreshing && (
            <p role="status" className="dashboard-muted py-8 text-sm">Loading pending applications…</p>
          )}
          {refreshing && (
            <p role="status" className="dashboard-muted pb-3 text-xs">Updating results…</p>
          )}

          {failure && (
            <div role="alert" className="py-6">
              <p className="dashboard-heading font-semibold">{failure.title}</p>
              <p className="dashboard-muted mt-1 text-sm">{failure.detail}</p>
              {failure.retry && <button type="button" className={`${secondaryButton} mt-4`} onClick={() => load({})}>Try again</button>}
            </div>
          )}

          {listing.status === 'ready' && rows.length === 0 && (
            <div className="py-6">
              <h3 className="dashboard-heading font-semibold">
                {filtered ? 'No applications match these filters.' : page > 1 ? 'No more applications.' : 'No pending applications.'}
              </h3>
              <p className="dashboard-muted mt-1 text-sm">
                {filtered ? 'Change or clear the search and filters to see other applications.'
                  : 'New Student and Instructor registrations appear here after email verification.'}
              </p>
              {filtered && <button type="button" className={`${secondaryButton} mt-4`} onClick={clearFilters}>Clear filters</button>}
            </div>
          )}

          {tableRows.length > 0 && (listing.status === 'ready' || refreshing) && (
            <div aria-busy={refreshing}
              className={refreshing ? 'pointer-events-none opacity-60 transition-opacity motion-reduce:transition-none' : 'transition-opacity motion-reduce:transition-none'}>
              <p className="sr-only" role="status">Showing {tableRows.length} pending {tableRows.length === 1 ? 'application' : 'applications'} on page {page}.</p>
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full min-w-[580px] text-left text-sm">
                  <caption className="sr-only">Pending applications, page {page}</caption>
                  <thead>
                    <tr className="dashboard-muted border-b text-xs uppercase tracking-wide">
                      {selectionEnabled && (
                        <th scope="col" className="w-10 px-2 py-3">
                          <input type="checkbox" checked={allRowsSelected} disabled={loading || bulkSubmitting}
                            ref={(element) => { if (element) element.indeterminate = someRowsSelected; }}
                            aria-label="Select all applicants on this page"
                            onChange={(event) => selectAllOnPage(event.target.checked)} />
                        </th>
                      )}
                      <th scope="col" className="px-2 py-3">CTU-G ID</th>
                      <th scope="col" className="px-2 py-3">Name</th>
                      <th scope="col" className="px-2 py-3">Requested role</th>
                      <th scope="col" className="px-2 py-3">Submitted</th>
                      <th scope="col" className="px-2 py-3">Email proof</th>
                      <th scope="col" className="px-2 py-3">Status</th>
                      <th scope="col" className="px-2 py-3 text-right">Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {tableRows.map((item) => (
                      <tr key={item.account_id} className="border-b last:border-0">
                        {selectionEnabled && (
                          <td className="px-2 py-3">
                            <input type="checkbox" checked={selectedIds.has(item.account_id)}
                              disabled={loading || bulkSubmitting}
                              aria-label={`Select CTU-G ID ${item.school_id}`}
                              onChange={(event) => toggleSelected(item.account_id, event.target.checked)} />
                          </td>
                        )}
                        <td className="dashboard-heading px-2 py-3 font-semibold">{item.school_id}</td>
                        <td className="px-2 py-3"><ApplicantName name={item.full_name} /></td>
                        <td className="px-2 py-3">{item.requested_role}</td>
                        <td className="dashboard-muted px-2 py-3"><Submitted value={item.created_at} /></td>
                        <td className="px-2 py-3"><ProofBadge verified={item.email_verified} /></td>
                        <td className="dashboard-muted px-2 py-3">Pending review</td>
                        <td className="px-2 py-1 text-right"><ReviewLink item={item} onOpen={openApplicant} /></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <ul className="space-y-3 md:hidden" aria-label={`Pending applications, page ${page}`}>
                {tableRows.map((item) => (
                  <li key={item.account_id} className="rounded-xl border p-4">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      {selectionEnabled ? (
                        <label className="dashboard-heading flex min-h-11 min-w-0 items-center gap-3 font-semibold break-words">
                          <input type="checkbox" checked={selectedIds.has(item.account_id)}
                            disabled={loading || bulkSubmitting}
                            aria-label={`Select CTU-G ID ${item.school_id}`}
                            onChange={(event) => toggleSelected(item.account_id, event.target.checked)} />
                          {item.school_id}
                        </label>
                      ) : (
                        <p className="dashboard-heading min-w-0 font-semibold break-words">{item.school_id}</p>
                      )}
                      <ProofBadge verified={item.email_verified} />
                    </div>
                    <dl className="mt-3 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 text-sm">
                      <dt className="dashboard-muted">Name</dt><dd className="min-w-0"><ApplicantName name={item.full_name} /></dd>
                      <dt className="dashboard-muted">Requested role</dt><dd>{item.requested_role}</dd>
                      <dt className="dashboard-muted">Submitted</dt><dd><Submitted value={item.created_at} /></dd>
                      <dt className="dashboard-muted">Status</dt><dd>Pending review</dd>
                    </dl>
                    <div className="mt-2 border-t pt-1"><ReviewLink item={item} onOpen={openApplicant} /></div>
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <nav aria-label="Pending applications pages" className="mt-4 flex items-center justify-between gap-3 border-t pt-3 text-sm">
          <button type="button" className={secondaryButton} disabled={loading || bulkSubmitting || page <= 1} onClick={() => load({ page: page - 1 })}>Previous</button>
          <span className="dashboard-muted">Page {page}</span>
          <button type="button" className={secondaryButton}
            disabled={listing.status !== 'ready' || !listing.data.has_next || page >= 10000 || bulkSubmitting}
            onClick={() => load({ page: page + 1 })}>Next</button>
        </nav>

        <p className="dashboard-muted mt-4 text-xs leading-relaxed">
          Applications marked “{NO_PROOF}” were created without a recorded email verification for their current address.
          This is not proof of eligibility. Django verifies your permission on every request.
        </p>
      </section>

      <Modal open={bulkAction !== null}
        title={bulkAction === 'approve'
          ? (count === 1 ? 'Confirm approval?' : `Confirm approval of ${count} applicants?`)
          : (count === 1 ? 'Confirm rejection?' : `Confirm rejection of ${count} applicants?`)}
        busy={bulkSubmitting} onClose={closeConfirmation} actions={(
          <>
            <button type="button" className={secondaryButton} disabled={bulkSubmitting} onClick={closeConfirmation}>
              Cancel
            </button>
            <button type="button" className={bulkAction === 'reject' ? destructiveButton : primaryButton}
              disabled={bulkSubmitting || (bulkAction === 'approve' && !bulkEligibilityConfirmed)
                || (bulkAction === 'reject' && !bulkRejectionCode)}
              onClick={() => { void confirmDecision(); }}>
              {bulkSubmitting ? 'Processing…'
                : bulkAction === 'approve' ? (count === 1 ? 'Confirm approval' : 'Confirm bulk approval')
                  : (count === 1 ? 'Confirm rejection' : 'Confirm bulk rejection')}
            </button>
          </>
        )}>
        <p className="dashboard-heading">
          {count === 1 ? `This decides the application of ${subject}.`
            : `This will process ${count} selected applicants independently.`}
        </p>
        {bulkAction === 'approve' && (
          <>
            <p className="dashboard-muted">
              {count === 1 ? 'Approval' : 'Each successful approval'} activates the account, assigns its requested base role,
              records an audit entry and queues an approval email. Queueing does not confirm delivery.
            </p>
            <label className="dashboard-heading flex min-h-11 items-start gap-3">
              <input type="checkbox" checked={bulkEligibilityConfirmed} disabled={bulkSubmitting}
                onChange={(event) => setBulkEligibilityConfirmed(event.target.checked)} />
              <span>
                {single
                  ? `I checked this applicant's current ${single.requested_role === 'Student' ? 'enrollment' : 'employment'} in ${ELIGIBILITY_SOURCE_LABELS[ELIGIBILITY_SOURCE_FOR_ROLE[single.requested_role]]}.`
                  : 'I checked the current enrollment or employment eligibility of every selected applicant using the required source, and confirm each eligible selection individually.'}
              </span>
            </label>
          </>
        )}
        {bulkAction === 'reject' && (
          <>
            <p className="dashboard-error">
              Irreversible: {count === 1 ? 'rejection' : 'each successful rejection'} queues a notification email and deletes
              the registration account and its registration data. The applicant may register again with the same CTU-G ID and email.
            </p>
            <label className="dashboard-heading block">{count === 1 ? 'Reason' : 'Reason for every selected applicant'}
              <select className={`${fieldClass} mt-2 block w-full`}
                value={bulkRejectionCode}
                disabled={bulkSubmitting}
                onChange={(event) => setBulkRejectionCode(event.target.value as RegistrationReviewRejectionCode | '')}>
                <option value="">Choose a reason</option>
                {REGISTRATION_REJECTION_CODES.map((code) => (
                  <option key={code} value={code}>{REJECTION_PUBLIC_LABELS[code]}</option>
                ))}
              </select>
            </label>
          </>
        )}
      </Modal>
    </div>
  );
}
