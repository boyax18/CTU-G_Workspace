/** WF-03.01 Access control → Role assignments (D-79, D-82, D-86): Technical Super Admin only.
 *
 * Lists approved Instructor and School Admin accounts the server says this actor may see and offers
 * exactly one change per account: make an approved Instructor a School Admin, or remove School Admin
 * (the Instructor role always stays). Technical Super Admin is never granted or removed here (Django
 * Superuser only), and ordinary-role controls remain separately gated pending independent appointment evidence and S1 governance adoption.
 * Buttons are hints; Django re-checks the profile, the exact permission and every rule inside the
 * lock. One POST per confirmation, never repeated; an uncertain result pauses until reload.
 */
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Modal from '../../components/common/Modal';
import OrdinaryRoleAssignmentsPanel from './OrdinaryRoleAssignmentsPanel.tsx';
import { ORDINARY_ROLE_ENABLED } from './ordinaryRoleAssignmentApi.ts';
import { changeSchoolAdmin, listRoleAssignments } from './roleAssignmentApi.ts';
import { ROLE_SEARCH_MAX, normalizeRoleSearch } from './roleAssignmentContract.ts';
import type { RoleAssignmentItem, RoleAssignmentPage, RoleRestriction, SchoolAdminAction } from './roleAssignmentContract.ts';

type Listing = { status: 'loading' } | { status: 'failed'; code: string } | { status: 'ready'; data: RoleAssignmentPage };
interface Pending { item: RoleAssignmentItem; action: SchoolAdminAction }
interface Problem { code: string; title: string; detail: string; reload: boolean }

const ring = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)] disabled:cursor-not-allowed disabled:opacity-50';
const fieldClass = `dashboard-panel min-h-11 rounded-lg border px-3 py-2 text-sm ${ring}`;
const primaryButton = `dashboard-primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${ring}`;
const secondaryButton = `dashboard-outline-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${ring}`;
const destructiveButton = `inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#b91c1c] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#991b1b] ${ring}`;

const errorCode = (error: unknown) => error && typeof error === 'object' && 'code' in error ? String((error as { code: unknown }).code) : '';

const RESTRICTION_TEXT: Record<RoleRestriction, string> = {
  not_instructor: 'Only approved Instructors can become School Admin.',
  technical_super_admin: 'Technical Super Admin. Only the Django Superuser manages this account’s administrator roles.',
  legacy_admin: 'Protected School Admin account. It cannot be changed here.',
  last_school_admin: 'The last School Admin cannot be removed.',
};

function loadFailure(code: string) {
  switch (code) {
    case 'authentication_required': return { title: 'Your session has ended.', detail: 'Sign in again to continue.', retry: false };
    case 'access_denied': return { title: 'You do not have permission to manage role assignments.', detail: 'Only a Technical Super Admin can use this page.', retry: false };
    case 'invalid_request': return { title: 'The search could not be used.', detail: 'Check it, then search again.', retry: false };
    case 'rate_limited': return { title: 'Too many requests.', detail: 'Wait a minute, then try again.', retry: true };
    case 'review_unavailable': return { title: 'Role assignments are not available right now.', detail: 'Try again later.', retry: true };
    default: return { title: 'Role assignments could not be loaded.', detail: 'Check your connection, then try again.', retry: true };
  }
}

function changeFailure(code: string): Problem {
  const p = (title: string, detail: string, reload = false) => ({ code, title, detail, reload });
  switch (code) {
    case 'state_changed': return p('This account’s roles changed since the list was loaded.', 'Nothing was changed. Reload the list to see the current roles.', true);
    case 'not_eligible': return p('This account is not eligible.', 'Only an active, approved Instructor can become School Admin. Nothing was changed.');
    case 'protected_account': return p('This account is protected.', 'Technical Super Admin and protected School Admin accounts cannot be changed here. Nothing was changed.');
    case 'last_school_admin': return p('The last School Admin cannot be removed.', 'Nothing was changed. Assign another School Admin first.');
    case 'request_unavailable': return p('This account is not available.', 'It may have changed. Nothing was changed.', true);
    case 'access_denied': return p('You do not have permission to change role assignments.', 'Nothing was changed.');
    case 'authentication_required': return p('Your session has ended.', 'Nothing was changed. Sign in again to continue.');
    case 'rate_limited': return p('Too many requests.', 'Nothing was changed. Wait a minute, then try again.');
    case 'review_unavailable': return p('Role changes are not available right now.', 'Nothing was changed. Try again later.');
    case 'invalid_request': return p('The request was not accepted.', 'Nothing was changed. Reload the list, then try again.', true);
    case 'outcome_unknown': return p('We could not confirm the change.', 'Do not try again yet. Reload the list to check the current roles first.', true);
    default: return p('The change could not be sent.', 'Nothing was changed. Check your connection, then try again.');
  }
}

export default function RoleAssignmentsPanel({ permissions }: { permissions: readonly string[] }) {
  const ids = useId();
  const searchRef = useRef<HTMLInputElement>(null);
  const noticeRef = useRef<HTMLDivElement>(null);
  const inFlight = useRef(false);
  const [draft, setDraft] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [listing, setListing] = useState<Listing>({ status: 'loading' });
  const [searchError, setSearchError] = useState('');
  const [pending, setPending] = useState<Pending | null>(null);
  const [busy, setBusy] = useState(false);
  const [problem, setProblem] = useState<Problem | null>(null);
  const [notice, setNotice] = useState('');
  const locked = problem?.code === 'outcome_unknown';

  useEffect(() => {
    let cancelled = false;
    listRoleAssignments(page, query)
      .then((data) => { if (!cancelled) setListing({ status: 'ready', data }); })
      .catch((error: unknown) => { if (!cancelled) setListing({ status: 'failed', code: errorCode(error) }); });
    return () => { cancelled = true; };
  }, [query, page, version]);
  useEffect(() => { if ((notice || problem) && !pending) noticeRef.current?.focus(); }, [notice, problem, pending]);

  function reload(next: { q?: string; page?: number } = {}) {
    setListing({ status: 'loading' });
    if (next.q !== undefined) setQuery(next.q);
    if (next.page !== undefined) setPage(next.page);
    if (next.q === undefined && next.page === undefined) setVersion((v) => v + 1);
  }

  function search(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    let q: string;
    try { q = normalizeRoleSearch(draft); } catch (error: unknown) {
      setSearchError(error instanceof Error ? error.message : 'Check the search text.');
      searchRef.current?.focus();
      return;
    }
    setSearchError('');
    setDraft(q);
    reload({ q, page: 1 });
  }

  async function confirm() {
    if (!pending || inFlight.current) return; // duplicate-submit guard
    inFlight.current = true;
    setBusy(true);
    const { item, action } = pending;
    try {
      await changeSchoolAdmin(item.account_id, action, action === 'revoke');
      setProblem(null);
      setNotice(action === 'assign'
        ? `${item.full_name ?? item.school_id} is now a School Admin and keeps the Instructor role. Their earlier sign-ins have ended.`
        : `School Admin was removed from ${item.full_name ?? item.school_id}. The Instructor role stays. Their earlier sign-ins have ended.`);
      setPending(null);
      reload();
    } catch (error: unknown) {
      setNotice('');
      setProblem(changeFailure(errorCode(error)));
      setPending(null);
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  const loading = listing.status === 'loading';
  const rows = listing.status === 'ready' ? listing.data.results : [];
  const failure = listing.status === 'failed' ? loadFailure(listing.code) : null;
  const target = pending?.item;
  const name = target ? (target.full_name ?? 'this account') : '';

  return (
    <div className="space-y-5">
      {ORDINARY_ROLE_ENABLED && permissions.includes('access_control.role_assignments.ordinary.manage') && <OrdinaryRoleAssignmentsPanel />}
      <section className="dashboard-panel rounded-2xl border p-4 sm:p-6" aria-labelledby={`${ids}-title`} aria-busy={loading}>
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <h2 id={`${ids}-title`} className="dashboard-heading text-lg font-semibold">Role assignments</h2>
            <p className="dashboard-muted mt-1 text-xs leading-relaxed">Make an approved Instructor a School Admin, or remove School Admin. The Instructor role always stays. Only the Django Superuser can grant or remove Technical Super Admin. Up to 20 accounts are shown per page.</p>
          </div>
          <button type="button" className={secondaryButton} disabled={loading} onClick={() => { setProblem(null); setNotice(''); reload(); }}>Refresh list</button>
        </div>
        <form role="search" aria-label="Role assignments" noValidate onSubmit={search} className="mt-4 grid gap-3 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-end">
          <label className="dashboard-muted flex min-w-0 flex-col gap-1 text-xs font-medium">
            Search CTU-G ID or name
            <input ref={searchRef} type="search" value={draft} maxLength={ROLE_SEARCH_MAX} autoComplete="off" spellCheck={false}
              aria-invalid={searchError ? true : undefined} aria-describedby={searchError ? `${ids}-search-error` : undefined}
              onChange={(e) => { setDraft(e.target.value); setSearchError(''); }} className={`${fieldClass} w-full`} />
          </label>
          <button type="submit" className={primaryButton} disabled={loading}>Search accounts</button>
        </form>
        {searchError && <p id={`${ids}-search-error`} className="dashboard-error mt-2 text-xs">{searchError}</p>}

        {(notice || problem) && (
          <div ref={noticeRef} tabIndex={-1} role={problem ? 'alert' : 'status'}
            className={`${problem ? 'dashboard-error-block' : 'dashboard-success'} mt-4 rounded-xl border p-4 text-sm focus:outline-none`}>
            {problem ? (
              <>
                <p className="font-semibold"><span aria-hidden="true">! </span>{problem.title}</p>
                <p className="mt-1">{problem.detail}</p>
                {problem.reload && <button type="button" className={`${secondaryButton} mt-3`} onClick={() => { setProblem(null); reload(); }}>Reload list</button>}
              </>
            ) : <p className="font-semibold"><span aria-hidden="true">✓ </span>{notice}</p>}
          </div>
        )}

        {loading && <p role="status" className="dashboard-muted py-8 text-sm">Loading accounts…</p>}
        {failure && (
          <div role="alert" className="mt-5">
            <p className="dashboard-heading font-semibold">{failure.title}</p>
            <p className="dashboard-muted mt-1 text-sm">{failure.detail}</p>
            {failure.retry && <button type="button" className={`${secondaryButton} mt-3`} onClick={() => reload()}>Try again</button>}
          </div>
        )}
        {listing.status === 'ready' && rows.length === 0 && (
          <p role="status" className="dashboard-muted py-8 text-sm">{query ? 'No accounts match this search.' : 'There are no Instructor or School Admin accounts to show.'}</p>
        )}
        {rows.length > 0 && (
          <ul className="mt-4 divide-y" aria-label="Accounts and roles">
            {rows.map((item) => (
              <li key={item.account_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
                <div className="min-w-0">
                  <p className="dashboard-heading break-words text-sm font-semibold">{item.full_name ?? 'Name not recorded'}</p>
                  <p className="dashboard-muted text-xs">CTU-G ID {item.school_id} · Roles: {item.roles.length ? item.roles.join(', ') : 'none'}</p>
                  {item.restriction && <p className="dashboard-muted mt-1 text-xs">{RESTRICTION_TEXT[item.restriction]}</p>}
                </div>
                {item.school_admin_action && (
                  <button type="button" disabled={busy || locked}
                    className={item.school_admin_action === 'assign' ? primaryButton : secondaryButton}
                    onClick={() => { setProblem(null); setNotice(''); setPending({ item, action: item.school_admin_action as SchoolAdminAction }); }}>
                    {item.school_admin_action === 'assign' ? 'Make School Admin' : 'Remove School Admin'}
                    <span className="sr-only"> for {item.full_name ?? item.school_id}</span>
                  </button>
                )}
              </li>
            ))}
          </ul>
        )}
        {locked && <p className="dashboard-muted mt-2 text-xs">Changes are paused until you reload the list.</p>}
        {listing.status === 'ready' && (page > 1 || listing.data.has_next) && (
          <nav aria-label="Pages" className="mt-4 flex items-center justify-between gap-3">
            <button type="button" className={secondaryButton} disabled={page <= 1} onClick={() => reload({ page: page - 1 })}>Previous</button>
            <span className="dashboard-muted text-sm">Page {page}</span>
            <button type="button" className={secondaryButton} disabled={!listing.data.has_next} onClick={() => reload({ page: page + 1 })}>Next</button>
          </nav>
        )}
      </section>

      <p className="dashboard-muted text-xs leading-relaxed">Django verifies your Technical Super Admin profile, the exact permission and the account rules on every request. Every change is audited.</p>

      <Modal open={pending !== null} busy={busy} onClose={() => setPending(null)}
        title={pending?.action === 'revoke' ? 'Remove School Admin?' : 'Make this account a School Admin?'}
        actions={(
          <>
            <button type="button" className={secondaryButton} disabled={busy} onClick={() => setPending(null)}>Cancel</button>
            <button type="button" className={pending?.action === 'revoke' ? destructiveButton : primaryButton} disabled={busy} onClick={confirm}>
              {busy ? (pending?.action === 'revoke' ? 'Removing…' : 'Assigning…') : (pending?.action === 'revoke' ? 'Confirm removal' : 'Confirm School Admin')}
            </button>
          </>
        )}>
        {target && (
          <>
            <p className="dashboard-heading">{pending?.action === 'revoke' ? 'Remove School Admin from' : 'Give School Admin to'} {name} (CTU-G ID {target.school_id})?</p>
            <p className="dashboard-muted">
              {pending?.action === 'revoke'
                ? 'They lose School Admin operations and keep the Instructor role. They are signed out on every device. It is audited.'
                : 'They gain School Admin school operations (applicant review and school accounts) and keep the Instructor role. They are signed out on every device and must sign in again. It is audited.'}
            </p>
            {busy && <p role="status" className="dashboard-muted">{pending?.action === 'revoke' ? 'Removing School Admin…' : 'Assigning School Admin…'}</p>}
          </>
        )}
      </Modal>
    </div>
  );
}
