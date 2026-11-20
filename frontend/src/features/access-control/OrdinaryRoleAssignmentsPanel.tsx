/** D-100 ordinary responsibilities. Visible only with an S1 effective-permission hint;
 * the server independently rechecks real authority, eligibility and appointment evidence. */
import { useEffect, useId, useRef, useState } from 'react';
import type { FormEvent } from 'react';
import Modal from '../../components/common/Modal';
import { changeOrdinaryRole, listOrdinaryRoles } from './ordinaryRoleAssignmentApi.ts';
import type { OrdinaryAction, OrdinaryPage, OrdinaryRole, OrdinaryRoleRow } from './ordinaryRoleAssignmentApi.ts';
import { normalizeRoleSearch, ROLE_SEARCH_MAX } from './roleAssignmentContract.ts';

type Listing = { status: 'loading' } | { status: 'ready'; data: OrdinaryPage } | { status: 'failed'; code: string };
type Pending = { item: OrdinaryRoleRow; role: OrdinaryRole; action: OrdinaryAction };
const ring = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)] disabled:opacity-50';
const button = `dashboard-outline-button inline-flex min-h-11 items-center rounded-lg border px-3 py-2 text-sm font-medium ${ring}`;
const primary = `dashboard-primary-link inline-flex min-h-11 items-center rounded-lg px-4 py-2 text-sm font-medium ${ring}`;
const danger = `inline-flex min-h-11 items-center rounded-lg bg-[#b91c1c] px-4 py-2 text-sm font-medium text-white ${ring}`;
const codeOf = (error: unknown) => error && typeof error === 'object' && 'code' in error ? String((error as {code: unknown}).code) : 'request_failed';

export default function OrdinaryRoleAssignmentsPanel() {
  const uid = useId();
  const inFlight = useRef(false);
  const noticeRef = useRef<HTMLDivElement>(null);
  const [draft, setDraft] = useState('');
  const [query, setQuery] = useState('');
  const [page, setPage] = useState(1);
  const [version, setVersion] = useState(0);
  const [searchError, setSearchError] = useState('');
  const [listing, setListing] = useState<Listing>({ status: 'loading' });
  const [pending, setPending] = useState<Pending | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [problem, setProblem] = useState('');
  const [uncertain, setUncertain] = useState(false);

  useEffect(() => {
    let cancelled = false;
    listOrdinaryRoles(page, query)
      .then(data => { if (!cancelled) setListing({ status: 'ready', data }); })
      .catch((error: unknown) => { if (!cancelled) setListing({ status: 'failed', code: codeOf(error) }); });
    return () => { cancelled = true; };
  }, [page, query, version]);
  useEffect(() => { if (notice || problem) noticeRef.current?.focus(); }, [notice, problem]);

  function reload(q = query, p = page) {
    setPending(null); setUncertain(false); setListing({ status: 'loading' });
    setQuery(q); setPage(p); setVersion(v => v + 1);
  }
  function search(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();
    try { const value = normalizeRoleSearch(draft); setSearchError(''); reload(value, 1); }
    catch (error: unknown) { setSearchError(error instanceof Error ? error.message : 'Invalid search.'); }
  }
  async function confirm() {
    if (!pending || inFlight.current) return;
    inFlight.current = true; setBusy(true);
    const { item, role, action } = pending;
    try {
      await changeOrdinaryRole(item.account_id, role, action);
      setProblem('');
      setNotice(`${role} ${action === 'assign' ? 'assigned to' : 'removed from'} ${item.full_name ?? item.school_id}. Earlier sessions ended.`);
      reload();
    } catch (error: unknown) {
      const code = codeOf(error);
      setNotice('');
      setProblem(code === 'outcome_unknown' ? 'The outcome is unknown. Reload the list before any further change.'
        : code === 'state_changed' ? 'This account changed. Reload before trying again.'
        : code === 'review_unavailable' ? 'Ordinary roles are unavailable until governance and appointment evidence are approved.'
        : code === 'access_denied' ? 'Your account lacks the exact ordinary-role management permission.'
        : code === 'not_eligible' ? 'This account or role combination is not eligible.'
        : 'The role could not be changed. Check the account and reload the list.');
      setUncertain(code === 'outcome_unknown'); setPending(null);
    } finally { inFlight.current = false; setBusy(false); }
  }

  const rows = listing.status === 'ready' ? listing.data.results : [];
  return (
    <section className="dashboard-panel rounded-2xl border p-4 sm:p-6" aria-labelledby={`${uid}-title`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 id={`${uid}-title`} className="dashboard-heading text-lg font-semibold">Ordinary responsibilities</h2>
          <p className="dashboard-muted mt-1 text-sm">Treasurer requires an approved Student and a reviewed appointment. SSG Advisor requires an approved Instructor and an independently verified appointment. The base role remains assigned.</p>
          <p className="dashboard-muted mt-1 text-xs">Assignments are unavailable until an approved appointment verifier is connected. No checkbox or typed reference can substitute for that evidence.</p>
        </div>
        <button className={button} type="button" disabled={busy} onClick={() => reload()}>Refresh</button>
      </div>
      <form className="mt-4 flex flex-wrap items-end gap-3" role="search" aria-label="Ordinary-role account search" onSubmit={search}>
        <label className="dashboard-muted flex min-w-0 flex-1 flex-col gap-1 text-xs">
          CTU-G ID or name
          <input type="search" value={draft} maxLength={ROLE_SEARCH_MAX} onChange={e => setDraft(e.target.value)}
            aria-invalid={!!searchError} className={`dashboard-panel min-h-11 rounded-lg border px-3 py-2 text-sm ${ring}`} />
        </label>
        <button type="submit" className={primary}>Search</button>
      </form>
      {searchError && <p role="alert" className="dashboard-error mt-2 text-sm">{searchError}</p>}
      {(notice || problem) && <div ref={noticeRef} tabIndex={-1} role={problem ? 'alert' : 'status'}
        className={`${problem ? 'dashboard-error-block' : 'dashboard-success'} mt-4 rounded-xl border p-3 text-sm`}>
        {problem || notice}
        {problem && <button type="button" className={`${button} ml-3`} onClick={() => { setProblem(''); reload(); }}>Reload</button>}
      </div>}
      {listing.status === 'loading' && <p role="status" className="dashboard-muted mt-4">Loading accounts…</p>}
      {listing.status === 'failed' && <p role="alert" className="dashboard-error mt-4 text-sm">{listing.code === 'access_denied'
        ? 'The server denied ordinary-role management.' : 'Ordinary-role assignments cannot be loaded. The feature may still be gated.'}</p>}
      {listing.status === 'ready' && rows.length === 0 && <p className="dashboard-muted mt-4 text-sm">No eligible accounts to show.</p>}
      <ul className="mt-4 divide-y" aria-label="Ordinary-role assignments">
        {rows.map(item => (
          <li key={item.account_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div className="min-w-0">
              <p className="dashboard-heading break-words text-sm font-semibold">{item.full_name ?? 'Name not recorded'}</p>
              <p className="dashboard-muted text-xs">CTU-G ID {item.school_id} · {item.roles.join(', ')}</p>
              {((item.roles.includes('Student') && !item.roles.includes('Treasurer') && !item.treasurer_action)
                || (item.roles.includes('Instructor') && !item.roles.includes('SSG Advisor') && !item.advisor_action))
                && <p className="dashboard-muted mt-1 text-xs">Assignment requires verified appointment evidence.</p>}
            </div>
            <div className="flex flex-wrap gap-2">
              {([['Treasurer', item.treasurer_action], ['SSG Advisor', item.advisor_action]] as [OrdinaryRole, OrdinaryAction | null][])
                .filter((pair): pair is [OrdinaryRole, OrdinaryAction] => pair[1] !== null)
                .map(([role, action]) => <button type="button" key={role} disabled={busy || uncertain}
                  className={action === 'revoke' ? danger : primary}
                  onClick={() => { setNotice(''); setProblem(''); setPending({ item, role, action }); }}>
                  {action === 'assign' ? 'Assign' : 'Remove'} {role}
                </button>)}
            </div>
          </li>
        ))}
      </ul>
      {listing.status === 'ready' && (page > 1 || listing.data.has_next) && <nav aria-label="Ordinary-role pages" className="mt-4 flex justify-between gap-3">
        <button type="button" className={button} disabled={page <= 1 || busy} onClick={() => reload(query, page - 1)}>Previous</button>
        <span className="dashboard-muted text-sm">Page {page}</span>
        <button type="button" className={button} disabled={!listing.data.has_next || busy} onClick={() => reload(query, page + 1)}>Next</button>
      </nav>}
      <Modal open={!!pending} busy={busy} onClose={() => setPending(null)} title={pending ? `${pending.action === 'assign' ? 'Assign' : 'Remove'} ${pending.role}?` : 'Confirm change'}
        actions={<>
          <button type="button" className={button} disabled={busy} onClick={() => setPending(null)}>Cancel</button>
          <button type="button" className={pending?.action === 'revoke' ? danger : primary} disabled={busy} onClick={confirm}>Confirm change</button>
        </>}>
        {pending && <p className="dashboard-heading text-sm">{pending.action === 'assign' ? 'Assign' : 'Remove'} {pending.role} {pending.action === 'assign' ? 'to' : 'from'} {pending.item.full_name ?? pending.item.school_id} (CTU-G ID {pending.item.school_id})? The base role remains, this action is audited, and earlier sessions will end.</p>}
      </Modal>
    </section>
  );
}
