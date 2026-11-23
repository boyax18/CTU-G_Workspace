/** WF-02.05 Account directory (D-70): eligible school accounts, read-only, permission-filtered.
 *
 * Shows only what the server returns for accounts the reviewer may read (Approved, non-protected).
 * `?account={id}` opens the read-only detail with the status controls in this same view; the list
 * state stays in memory so Back restores it. Detail includes permitted WF-02.06 history;
 * roles and permissions are read-only.
 */
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent, MouseEvent } from 'react';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import AccountDetailPanel from './AccountDetailPanel';
import AccountStatusBadge from './AccountStatusBadge';
import { listSchoolAccounts } from './accountStatusApi.ts';
import { ACCOUNT_SEARCH_MAX, normalizeAccountSearch } from './accountStatusContract.ts';
import type { AccountsQuery, AccountStatusFilter, SchoolAccountItem, SchoolAccountPage } from './accountStatusContract.ts';

type Listing = { status: 'loading' } | { status: 'failed'; code: string } | { status: 'ready'; data: SchoolAccountPage };
interface Filters { q: string; status: '' | AccountStatusFilter }

const DEFAULT: Filters = { q: '', status: '' };
const ring = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]';
const fieldClass = `dashboard-panel min-h-11 rounded-lg border px-3 py-2 text-sm ${ring}`;
const primaryButton = `dashboard-primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${ring} disabled:cursor-not-allowed disabled:opacity-50`;
const secondaryButton = `dashboard-outline-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${ring} disabled:cursor-not-allowed disabled:opacity-50`;

function failureMessage(code: string): { title: string; detail: string; retry: boolean } {
  switch (code) {
    case 'authentication_required': return { title: 'Your session has ended.', detail: 'Sign in again to continue.', retry: false };
    case 'access_denied': return { title: 'You do not have permission to view school accounts.', detail: 'Ask a School Admin to check your account access.', retry: false };
    case 'invalid_request': return { title: 'The search or filter could not be used.', detail: 'Check them, then apply again.', retry: false };
    case 'rate_limited': return { title: 'Too many requests.', detail: 'Wait a minute, then try again.', retry: true };
    case 'review_unavailable': return { title: 'School accounts are not available right now.', detail: 'Try again later.', retry: true };
    default: return { title: 'School accounts could not be loaded.', detail: 'Check your connection, then try again.', retry: true };
  }
}

const errorCode = (error: unknown) => error && typeof error === 'object' && 'code' in error ? String((error as { code: unknown }).code) : '';

function AccountLink({ item, onOpen }: { item: SchoolAccountItem; onOpen: (id: number) => void }) {
  const follow = (event: MouseEvent<HTMLAnchorElement>) => {
    if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
    event.preventDefault();
    onOpen(item.account_id);
  };
  return (
    <a href={`/dashboard?view=account-directory&account=${item.account_id}`} data-account-link={item.account_id} onClick={follow}
      className={`dashboard-accent inline-flex min-h-11 items-center gap-1 rounded-lg px-1 text-sm font-semibold underline-offset-2 hover:underline ${ring}`}>
      View account<span className="sr-only"> for {item.id_label} {item.school_id}</span>
    </a>
  );
}

export default function AccountDirectoryPanel() {
  const ids = useId();
  const { search, openSubpage } = useDashboardContext();
  const accountParam = new URLSearchParams(search).get('account');
  const lastOpened = useRef<number | null>(null);
  const openedFromList = useRef(false);
  const searchRef = useRef<HTMLInputElement>(null);
  const [draft, setDraft] = useState<Filters>(DEFAULT);
  const [applied, setApplied] = useState<Filters>(DEFAULT);
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [listing, setListing] = useState<Listing>({ status: 'loading' });
  const [searchError, setSearchError] = useState('');

  useEffect(() => {
    let cancelled = false;
    const query: AccountsQuery = {};
    if (applied.q) query.q = applied.q;
    if (applied.status) query.status = applied.status;
    listSchoolAccounts(page, query)
      .then((data) => { if (!cancelled) setListing({ status: 'ready', data }); })
      .catch((error: unknown) => { if (!cancelled) setListing({ status: 'failed', code: errorCode(error) }); });
    return () => { cancelled = true; };
  }, [applied, page, version]);

  useEffect(() => {
    if (accountParam !== null) return;
    openedFromList.current = false;
    if (lastOpened.current === null) return;
    const links = document.querySelectorAll<HTMLElement>(`[data-account-link="${lastOpened.current}"]`);
    [...links].find((link) => link.offsetParent !== null)?.focus();
    lastOpened.current = null;
  }, [accountParam, listing.status]);

  function reload(next: { filters?: Filters; page?: number } = {}) {
    setListing({ status: 'loading' });
    if (next.filters) setApplied(next.filters);
    if (next.page !== undefined) setPage(next.page);
    if (!next.filters && next.page === undefined) setVersion((v) => v + 1);
  }

  function openAccount(id: number) {
    lastOpened.current = id;
    openedFromList.current = true;
    openSubpage({ account: String(id) });
  }

  function backToList() {
    if (openedFromList.current) { openedFromList.current = false; window.history.back(); } else openSubpage(null);
  }

  function apply(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    let q: string;
    try { q = normalizeAccountSearch(draft.q); } catch (error: unknown) {
      setSearchError(error instanceof Error ? error.message : 'Check the search text.');
      searchRef.current?.focus();
      return;
    }
    setSearchError('');
    const filters = { ...draft, q };
    setDraft(filters);
    reload({ filters, page: 1 });
  }

  if (accountParam !== null) {
    return <AccountDetailPanel key={accountParam} raw={accountParam} onBack={backToList} onChanged={() => reload()} />;
  }

  const loading = listing.status === 'loading';
  const rows = listing.status === 'ready' ? listing.data.results : [];
  const failure = listing.status === 'failed' ? failureMessage(listing.code) : null;
  const filtered = Boolean(applied.q || applied.status);

  return (
    <div className="space-y-5">
      <section className="dashboard-panel rounded-2xl border p-4 sm:p-6" aria-labelledby={`${ids}-title`} aria-busy={loading}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 id={`${ids}-title`} className="dashboard-heading text-lg font-semibold">School accounts</h2>
            <p className="dashboard-muted mt-1 text-xs">Approved Student, Instructor and Treasurer accounts you may manage. Administrator accounts are not listed. Up to 20 are shown per page.</p>
          </div>
          <button type="button" className={secondaryButton} disabled={loading} onClick={() => reload()}>Refresh list</button>
        </div>
        <form role="search" aria-label="School accounts" noValidate onSubmit={apply} className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto] sm:items-end">
          <label className="dashboard-muted flex min-w-0 flex-col gap-1 text-xs font-medium">
            Search CTU-G ID or name
            <input ref={searchRef} type="search" value={draft.q} maxLength={ACCOUNT_SEARCH_MAX} autoComplete="off" spellCheck={false}
              aria-invalid={searchError ? true : undefined} aria-describedby={searchError ? `${ids}-search-error` : undefined}
              onChange={(e) => { setDraft({ ...draft, q: e.target.value }); setSearchError(''); }} className={`${fieldClass} w-full`} />
          </label>
          <label className="dashboard-muted flex min-w-0 flex-col gap-1 text-xs font-medium">
            Status
            <select value={draft.status} className={`${fieldClass} w-full`}
              onChange={(e) => setDraft({ ...draft, status: e.target.value as Filters['status'] })}>
              <option value="">All statuses</option>
              <option value="active">Active</option>
              <option value="inactive">Inactive</option>
            </select>
          </label>
          <div className="flex flex-wrap gap-2">
            <button type="submit" className={primaryButton} disabled={loading}>Apply filters</button>
            {filtered && <button type="button" className={secondaryButton} disabled={loading}
              onClick={() => { setDraft(DEFAULT); setSearchError(''); reload({ filters: DEFAULT, page: 1 }); }}>Clear</button>}
          </div>
        </form>
        {searchError && <p id={`${ids}-search-error`} className="dashboard-error mt-2 text-xs">{searchError}</p>}

        {loading && <p role="status" className="dashboard-muted py-8 text-sm">Loading school accounts…</p>}
        {failure && (
          <div role="alert" className="mt-5">
            <p className="dashboard-heading font-semibold">{failure.title}</p>
            <p className="dashboard-muted mt-1 text-sm">{failure.detail}</p>
            {failure.retry && <button type="button" className={`${secondaryButton} mt-3`} onClick={() => reload()}>Try again</button>}
          </div>
        )}
        {listing.status === 'ready' && rows.length === 0 && (
          <p role="status" className="dashboard-muted py-8 text-sm">{filtered ? 'No school accounts match these filters.' : 'There are no school accounts to show.'}</p>
        )}
        {rows.length > 0 && (
          <ul className="mt-4 divide-y" aria-label="School accounts">
            {rows.map((item) => (
              <li key={item.account_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="dashboard-heading break-words text-sm font-semibold">{item.full_name ?? 'Name not recorded'}</p>
                  <p className="dashboard-muted text-xs">{item.id_label} {item.school_id} · {item.roles.length ? item.roles.join(', ') : 'No active role'}</p>
                </div>
                <div className="flex items-center gap-3">
                  <AccountStatusBadge active={item.is_active} />
                  <AccountLink item={item} onOpen={openAccount} />
                </div>
              </li>
            ))}
          </ul>
        )}
        {listing.status === 'ready' && (page > 1 || listing.data.has_next) && (
          <nav aria-label="Pages" className="mt-4 flex items-center justify-between gap-3">
            <button type="button" className={secondaryButton} disabled={page <= 1} onClick={() => reload({ page: page - 1 })}>Previous</button>
            <span className="dashboard-muted text-sm">Page {page}</span>
            <button type="button" className={secondaryButton} disabled={!listing.data.has_next} onClick={() => reload({ page: page + 1 })}>Next</button>
          </nav>
        )}
      </section>
    </div>
  );
}
