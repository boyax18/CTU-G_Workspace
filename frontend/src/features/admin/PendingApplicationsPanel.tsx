/** WF-02.01 View pending applications: strictly read-only.
 *
 * No approve, reject or delete controls exist here (WF-02.03/02.04 are separate, unmounted flows).
 * The session permission hint only decides navigation; Django checks the Admin assignment and the
 * exact effective permission on every request, and this view shows only what the server returns.
 */
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import { listPendingApplications } from './registrationReviewApi.ts';
import { normalizePendingSearch, PENDING_APPLICATION_SEARCH_MAX } from './registrationReviewApiContract.ts';
import type {
  PendingApplicationProofFilter,
  PendingApplicationSort,
  PendingApplicationsQuery,
  PendingRegistrationItem,
  PendingRegistrationPage,
  RegistrationReviewRole,
} from './registrationReviewApiContract.ts';

interface Filters {
  q: string;
  role: '' | RegistrationReviewRole;
  proof: '' | PendingApplicationProofFilter;
  sort: PendingApplicationSort;
}

type Listing =
  | { status: 'loading' }
  | { status: 'failed'; code: string }
  | { status: 'ready'; data: PendingRegistrationPage };

const DEFAULT_FILTERS: Filters = { q: '', role: '', proof: '', sort: 'submitted' };
const SORT_LABELS: Record<PendingApplicationSort, string> = {
  submitted: 'Oldest submitted first',
  '-submitted': 'Newest submitted first',
  school_id: 'School ID, ascending',
  '-school_id': 'School ID, descending',
};
const NO_PROOF = 'No email proof on record';

const fieldClass = 'dashboard-panel min-h-11 rounded-lg border px-3 py-2 text-sm focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]';
const primaryButton = 'dashboard-primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)] disabled:cursor-not-allowed disabled:opacity-50';
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

export default function PendingApplicationsPanel() {
  const ids = useId();
  const searchRef = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState<Filters>(DEFAULT_FILTERS);
  const [applied, setApplied] = useState<Filters>(DEFAULT_FILTERS);
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [listing, setListing] = useState<Listing>({ status: 'loading' });
  const [searchError, setSearchError] = useState('');

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

  function load(next: { filters?: Filters; page?: number }) {
    setListing({ status: 'loading' });
    if (next.filters) setApplied(next.filters);
    if (next.page !== undefined) setPage(next.page);
    if (!next.filters && next.page === undefined) setVersion((current) => current + 1);
  }

  function applyFilters(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    let q: string;
    try {
      q = normalizePendingSearch(draft.q);
    } catch (error: unknown) {
      setSearchError(error instanceof Error ? error.message : 'Check the search text.');
      searchRef.current?.focus();
      return;
    }
    setSearchError('');
    const filters = { ...draft, q };
    setDraft(filters);
    load({ filters, page: 1 });
  }

  function clearFilters() {
    setSearchError('');
    setDraft(DEFAULT_FILTERS);
    load({ filters: DEFAULT_FILTERS, page: 1 });
  }

  const loading = listing.status === 'loading';
  const rows: readonly PendingRegistrationItem[] = listing.status === 'ready' ? listing.data.results : [];
  const filtered = hasActiveFilters(applied);
  const searchHint = `${ids}-search-hint`;
  const searchErrorId = `${ids}-search-error`;
  const failure = listing.status === 'failed' ? failureMessage(listing.code) : null;

  return (
    <div className="space-y-5">
      {/* The shared shell renders the breadcrumbs and the page h1 ("Applicant reviews"). */}
      <section className="dashboard-panel rounded-2xl border p-4 sm:p-6" aria-labelledby={`${ids}-queue`} aria-busy={loading}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 id={`${ids}-queue`} className="dashboard-heading text-lg font-semibold">Pending applications</h2>
            <p className="dashboard-muted mt-1 text-xs">Search, filters and sorting apply to all pending applications. Up to 20 are shown per page.</p>
          </div>
          <button type="button" className={secondaryButton} disabled={loading} onClick={() => load({})}>Refresh list</button>
        </div>

        <form role="search" aria-label="Pending applications" noValidate onSubmit={applyFilters}
          className="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[minmax(0,2fr)_repeat(3,minmax(0,1fr))]">
          <label className="dashboard-muted flex min-w-0 flex-col gap-1 text-xs font-medium sm:col-span-2 lg:col-span-1">
            Search School ID or name
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
            School IDs match from the start; names match any part. Select Apply filters or press Enter to search.
          </p>
          {searchError && (
            // Existing tokens only: --db-error is still Proposed (TOKENS.md §1.4). Not colour-only.
            <p id={searchErrorId} role="alert" className="dashboard-heading flex gap-2 text-sm font-semibold sm:col-span-2 lg:col-span-4">
              <span aria-hidden="true">!</span>{searchError}
            </p>
          )}
          <div className="flex flex-wrap gap-3 sm:col-span-2 lg:col-span-4">
            <button type="submit" className={primaryButton} disabled={loading}>Apply filters</button>
            {(hasActiveFilters(draft) || filtered) && (
              <button type="button" className={secondaryButton} disabled={loading} onClick={clearFilters}>Clear filters</button>
            )}
          </div>
        </form>

        <div className="mt-5 border-t pt-4">
          {listing.status === 'loading' && (
            <p role="status" className="dashboard-muted py-8 text-sm">Loading pending applications…</p>
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

          {listing.status === 'ready' && rows.length > 0 && (
            <>
              <p className="sr-only" role="status">Showing {rows.length} pending {rows.length === 1 ? 'application' : 'applications'} on page {page}.</p>
              <div className="hidden overflow-x-auto md:block">
                <table className="w-full min-w-[580px] text-left text-sm">
                  <caption className="sr-only">Pending applications, page {page}</caption>
                  <thead>
                    <tr className="dashboard-muted border-b text-xs uppercase tracking-wide">
                      <th scope="col" className="px-2 py-3">School ID</th>
                      <th scope="col" className="px-2 py-3">Name</th>
                      <th scope="col" className="px-2 py-3">Requested role</th>
                      <th scope="col" className="px-2 py-3">Submitted</th>
                      <th scope="col" className="px-2 py-3">Email proof</th>
                      <th scope="col" className="px-2 py-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {rows.map((item) => (
                      <tr key={item.account_id} className="border-b last:border-0">
                        <td className="dashboard-heading px-2 py-3 font-semibold">{item.school_id}</td>
                        <td className="px-2 py-3"><ApplicantName name={item.full_name} /></td>
                        <td className="px-2 py-3">{item.requested_role}</td>
                        <td className="dashboard-muted px-2 py-3"><Submitted value={item.created_at} /></td>
                        <td className="px-2 py-3"><ProofBadge verified={item.email_verified} /></td>
                        <td className="dashboard-muted px-2 py-3">Pending review</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <ul className="space-y-3 md:hidden" aria-label={`Pending applications, page ${page}`}>
                {rows.map((item) => (
                  <li key={item.account_id} className="rounded-xl border p-4">
                    <div className="flex flex-wrap items-start justify-between gap-2">
                      <p className="dashboard-heading min-w-0 font-semibold break-words">{item.school_id}</p>
                      <ProofBadge verified={item.email_verified} />
                    </div>
                    <dl className="mt-3 grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 text-sm">
                      <dt className="dashboard-muted">Name</dt><dd className="min-w-0"><ApplicantName name={item.full_name} /></dd>
                      <dt className="dashboard-muted">Requested role</dt><dd>{item.requested_role}</dd>
                      <dt className="dashboard-muted">Submitted</dt><dd><Submitted value={item.created_at} /></dd>
                      <dt className="dashboard-muted">Status</dt><dd>Pending review</dd>
                    </dl>
                  </li>
                ))}
              </ul>
            </>
          )}
        </div>

        <nav aria-label="Pending applications pages" className="mt-4 flex items-center justify-between gap-3 border-t pt-3 text-sm">
          <button type="button" className={secondaryButton} disabled={loading || page <= 1} onClick={() => load({ page: page - 1 })}>Previous</button>
          <span className="dashboard-muted">Page {page}</span>
          <button type="button" className={secondaryButton}
            disabled={listing.status !== 'ready' || !listing.data.has_next || page >= 10000}
            onClick={() => load({ page: page + 1 })}>Next</button>
        </nav>

        <p className="dashboard-muted mt-4 text-xs leading-relaxed">
          Applications marked “{NO_PROOF}” were created without a recorded email verification for their current address.
          This is not proof of eligibility. Django verifies your permission on every request.
        </p>
      </section>
    </div>
  );
}
