/** WF-02.05: read-only account detail with the Deactivate / Reactivate control.
 *
 * The control appears only with the exact permission hint (accounts.school_accounts.suspend or
 * .activate); Django re-checks it, the account rules and the confirmed state on every request.
 * Only the active state changes: approval, roles, permissions, identity and records are kept.
 * One POST per confirmation, never repeated; an uncertain result pauses until the account is
 * reloaded.
 *
 * WF-02.06 (D-72 to D-77): the Account status section shows the current state from the account
 * row with its recorded dates ("Not recorded" when absent), and Status history lists only the
 * events Django allows (registration approval, deactivation, reactivation), 20 per page, newest
 * first, with the actor as "You" or "An administrator". Read-only; Django checks every request.
 */
import { useEffect, useId, useRef, useState } from 'react';
import type { ReactNode } from 'react';
import Modal from '../../components/common/Modal';
import { useDashboardContext } from '../../hooks/useDashboardContext';
import AccountStatusBadge from './AccountStatusBadge';
import { changeAccountStatus, getSchoolAccount, getSchoolAccountHistory } from './accountStatusApi.ts';
import { parseAccountParam } from './accountStatusContract.ts';
import type { AccountStatusAction, SchoolAccountDetail, StatusHistoryEntry } from './accountStatusContract.ts';

const SUSPEND = 'accounts.school_accounts.suspend';
const ACTIVATE = 'accounts.school_accounts.activate';
const ring = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)] disabled:cursor-not-allowed disabled:opacity-50';
const secondaryButton = `dashboard-outline-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors ${ring}`;
const primaryButton = `dashboard-primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors ${ring}`;
const destructiveButton = `inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#b91c1c] px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-[#991b1b] ${ring}`;

type Loaded = { status: 'loading' } | { status: 'failed'; code: string } | { status: 'ready'; data: SchoolAccountDetail };
type Phase = 'idle' | 'confirming' | 'submitting';
interface Problem { code: string; title: string; detail: string; reload: boolean }

const errorCode = (error: unknown) => error && typeof error === 'object' && 'code' in error ? String((error as { code: unknown }).code) : '';

function loadFailure(code: string) {
  switch (code) {
    case 'request_unavailable': return { title: 'This account is not available.', detail: 'It may have changed, or the link is not valid.', retry: false };
    case 'authentication_required': return { title: 'Your session has ended.', detail: 'Sign in again to continue.', retry: false };
    case 'access_denied': return { title: 'You do not have permission to view school accounts.', detail: 'Ask a School Admin to check your account access.', retry: false };
    case 'rate_limited': return { title: 'Too many requests.', detail: 'Wait a minute, then try again.', retry: true };
    case 'review_unavailable': return { title: 'School accounts are not available right now.', detail: 'Try again later.', retry: true };
    default: return { title: 'The account could not be loaded.', detail: 'Check your connection, then try again.', retry: true };
  }
}

function changeFailure(code: string): Problem {
  const p = (title: string, detail: string, reload = false) => ({ code, title, detail, reload });
  switch (code) {
    case 'state_changed': return p("This account's status changed since you opened it.", 'Nothing was changed. Reload the account to see its current status.', true);
    case 'protected_account': return p('This account is protected.', 'Administrator and governance accounts cannot be changed here. Nothing was changed.');
    case 'no_operational_role': return p('This account cannot be reactivated here.', 'It has no active role. Nothing was changed; roles are managed separately.');
    case 'access_denied': return p('You do not have permission to change this account.', 'Nothing was changed. Ask a School Admin to check your account access.');
    case 'authentication_required': return p('Your session has ended.', 'Nothing was changed. Sign in again to continue.');
    case 'rate_limited': return p('Too many requests.', 'Nothing was changed. Wait a minute, then try again.');
    case 'review_unavailable': return p('Account changes are not available right now.', 'Nothing was changed. Try again later.');
    case 'invalid_request': return p('The request was not accepted.', 'Nothing was changed. Reload the account, then try again.', true);
    case 'outcome_unknown': return p('We could not confirm the change.', 'Do not try again yet. Reload the account to check its current status first.', true);
    default: return p('The change could not be sent.', 'Nothing was changed. Check your connection, then try again.');
  }
}

const fmt = (value: string) => new Date(value).toLocaleString('en-PH', { dateStyle: 'medium', timeStyle: 'short' });
const notRecorded = <span className="dashboard-muted italic">Not recorded</span>;
const byActor = (actor: StatusHistoryEntry['actor']) => (actor === 'You' ? 'By you' : 'By an administrator');
const stateWord = (active: boolean) => (active ? 'Active' : 'Inactive');

function historyFailure(code: string) {
  switch (code) {
    case 'request_unavailable': return { title: "This account's history is not available.", detail: 'It may have changed, or the link is not valid.', retry: false };
    case 'authentication_required': return { title: 'Your session has ended.', detail: 'Sign in again to continue.', retry: false };
    case 'access_denied': return { title: 'You do not have permission to view this history.', detail: 'Ask a School Admin to check your account access.', retry: false };
    case 'rate_limited': return { title: 'Too many requests.', detail: 'Wait a minute, then try again.', retry: true };
    case 'review_unavailable': return { title: 'Status history is not available right now.', detail: 'The account status above is still current. Try again later.', retry: true };
    default: return { title: "We couldn't load the history.", detail: 'The account status above is still current. Check your connection, then try again.', retry: true };
  }
}

type HistoryState =
  | { status: 'loading' }
  | { status: 'failed'; code: string }
  | { status: 'ready'; entries: StatusHistoryEntry[]; page: number; hasNext: boolean; more: string };

/** WF-02.06: permitted status history, newest first; older pages only on request. */
function StatusHistory({ accountId, version, headingId }: { accountId: number; version: number; headingId: string }) {
  const [state, setState] = useState<HistoryState>({ status: 'loading' });
  const [attempt, setAttempt] = useState(0);
  const inFlight = useRef(false);
  useEffect(() => {
    let cancelled = false;
    getSchoolAccountHistory(accountId, 1)
      .then((page) => { if (!cancelled) setState({ status: 'ready', entries: page.results, page: 1, hasNext: page.has_next, more: 'idle' }); })
      .catch((error: unknown) => { if (!cancelled) setState({ status: 'failed', code: errorCode(error) }); });
    return () => { cancelled = true; };
  }, [accountId, version, attempt]);

  function retry() {
    setState({ status: 'loading' });
    setAttempt((a) => a + 1);
  }

  async function loadOlder() {
    if (state.status !== 'ready' || inFlight.current) return; // one request at a time
    inFlight.current = true;
    const next = state.page + 1;
    setState({ ...state, more: 'loading' });
    try {
      const page = await getSchoolAccountHistory(accountId, next);
      setState((s) => (s.status === 'ready'
        ? { status: 'ready', entries: [...s.entries, ...page.results], page: next, hasNext: page.has_next, more: 'idle' } : s));
    } catch (error: unknown) {
      setState((s) => (s.status === 'ready' ? { ...s, more: errorCode(error) || 'network_error' } : s));
    } finally {
      inFlight.current = false;
    }
  }

  const busy = state.status === 'loading' || (state.status === 'ready' && state.more === 'loading');
  const failure = state.status === 'failed' ? historyFailure(state.code) : null;
  return (
    <section aria-labelledby={headingId} aria-busy={busy} className="dashboard-panel rounded-2xl border p-5 sm:p-6">
      <h3 id={headingId} className="dashboard-heading text-lg font-semibold">Status history</h3>
      <p className="dashboard-muted mt-1 text-sm leading-relaxed">Registration approval, deactivation and reactivation, newest first.</p>
      {state.status === 'loading' && <p role="status" className="dashboard-muted py-6 text-sm">Loading the status history…</p>}
      {failure && (
        <div role="alert" className="dashboard-error-block mt-4 rounded-xl border p-4 text-sm">
          <p className="font-semibold"><span aria-hidden="true">! </span>{failure.title}</p>
          <p className="mt-1">{failure.detail}</p>
          {failure.retry && <button type="button" className={`${secondaryButton} mt-3`} onClick={retry}>Try again</button>}
        </div>
      )}
      {state.status === 'ready' && state.entries.length === 0 && (
        <div className="mt-4">
          <h4 className="dashboard-heading font-semibold">No status changes recorded</h4>
          <p className="dashboard-muted mt-1 text-sm">No approval, deactivation or reactivation has been recorded for this account.</p>
        </div>
      )}
      {state.status === 'ready' && state.entries.length > 0 && (
        <>
          <ol aria-label="Status history" className="mt-3 divide-y">
            {state.entries.map((entry, index) => (
              <li key={`${entry.occurred_at}-${entry.event}-${index}`} className="py-3">
                <p className="dashboard-heading text-sm font-semibold">{entry.description}</p>
                <p className="dashboard-muted mt-0.5 text-sm"><time dateTime={entry.occurred_at}>{fmt(entry.occurred_at)}</time> · {byActor(entry.actor)}</p>
                {typeof entry.previous_is_active === 'boolean' && typeof entry.new_is_active === 'boolean' && (
                  <p className="dashboard-muted mt-0.5 text-sm">{stateWord(entry.previous_is_active)} to {stateWord(entry.new_is_active)}</p>
                )}
              </li>
            ))}
          </ol>
          <p role="status" className="dashboard-muted mt-2 text-xs">
            {state.hasNext
              ? `Showing the ${state.entries.length} most recent entries.`
              : `Showing all ${state.entries.length} ${state.entries.length === 1 ? 'entry' : 'entries'}.`}
          </p>
          {state.more !== 'idle' && state.more !== 'loading' && (
            <p role="alert" className="dashboard-error-block mt-3 rounded-xl border p-3 text-sm">{historyFailure(state.more).title} The entries above are unchanged.</p>
          )}
          {state.hasNext && (
            <button type="button" className={`${secondaryButton} mt-3`} disabled={state.more === 'loading'} onClick={loadOlder}>
              {state.more === 'loading' ? 'Loading older entries…' : 'Show older entries'}
            </button>
          )}
        </>
      )}
    </section>
  );
}

function Row({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div className="grid gap-1 py-2.5 sm:grid-cols-[11rem_minmax(0,1fr)] sm:gap-4">
      <dt className="dashboard-muted text-xs font-medium uppercase tracking-wider sm:pt-0.5">{label}</dt>
      <dd className="dashboard-heading min-w-0 break-words text-sm">{children}</dd>
    </div>
  );
}

interface Props { raw: string; onBack: () => void; onChanged: () => void }

export default function AccountDetailPanel({ raw, onBack, onChanged }: Props) {
  const ids = useId();
  const { session, setSubpage } = useDashboardContext();
  const accountId = parseAccountParam(raw);
  const heading = useRef<HTMLHeadingElement>(null);
  const noticeRef = useRef<HTMLDivElement>(null);
  const inFlight = useRef(false);
  const [loaded, setLoaded] = useState<Loaded>(accountId === null ? { status: 'failed', code: 'request_unavailable' } : { status: 'loading' });
  const [version, setVersion] = useState(0);
  const [phase, setPhase] = useState<Phase>('idle');
  const [problem, setProblem] = useState<Problem | null>(null);
  const [notice, setNotice] = useState('');
  const [historyVersion, setHistoryVersion] = useState(0);
  const locked = problem?.code === 'outcome_unknown';

  useEffect(() => {
    if (accountId === null) return;
    let cancelled = false;
    getSchoolAccount(accountId)
      .then((data) => {
        if (cancelled) return;
        setLoaded({ status: 'ready', data });
        setSubpage({ label: `${data.id_label} ${data.school_id}`, description: 'One school account. Only its active status can be changed here.' });
      })
      .catch((error: unknown) => { if (!cancelled) setLoaded({ status: 'failed', code: errorCode(error) }); });
    return () => { cancelled = true; };
  }, [accountId, version, setSubpage]);
  useEffect(() => () => setSubpage(null), [setSubpage]);
  useEffect(() => { if (loaded.status === 'ready' && !notice && !problem) heading.current?.focus(); }, [loaded.status, notice, problem]);
  useEffect(() => { if ((notice || problem) && phase === 'idle') noticeRef.current?.focus(); }, [notice, problem, phase]);

  function reload() {
    setProblem(null);
    setNotice('');
    setLoaded({ status: 'loading' });
    setVersion((v) => v + 1);
  }

  const back = (
    <button type="button" className={secondaryButton} onClick={onBack}><span aria-hidden="true">←</span>Back to school accounts</button>
  );
  if (loaded.status === 'loading') return <div className="space-y-5">{back}<p role="status" className="dashboard-muted py-8 text-sm">Loading the account…</p></div>;
  if (loaded.status === 'failed') {
    const message = loadFailure(loaded.code);
    return (
      <div className="space-y-5">
        {back}
        <section role="alert" className="dashboard-panel rounded-2xl border p-6 sm:p-8">
          <h2 className="dashboard-heading text-lg font-semibold">{message.title}</h2>
          <p className="dashboard-muted mt-2 text-sm">{message.detail}</p>
          {message.retry && <button type="button" className={`${secondaryButton} mt-5`} onClick={reload}>Try again</button>}
        </section>
      </div>
    );
  }

  const data = loaded.data;
  const action: AccountStatusAction = data.is_active ? 'suspend' : 'activate';
  const allowed = session.permissions.includes(action === 'suspend' ? SUSPEND : ACTIVATE);
  const busy = phase === 'submitting';
  const name = data.full_name ?? 'this account';

  async function confirm() {
    if (inFlight.current || loaded.status !== 'ready') return; // duplicate-submit guard
    inFlight.current = true;
    setPhase('submitting');
    try {
      const result = await changeAccountStatus(data.account_id, action, data.is_active);
      setLoaded({ status: 'ready', data: { ...data, is_active: result.is_active } });
      setProblem(null);
      setNotice(result.is_active ? 'Account reactivated. They can sign in again with their existing roles.'
        : 'Account deactivated. They are signed out everywhere and cannot sign in until it is reactivated.');
      onChanged();
      // WF-02.06: re-read the recorded dates and history from Django; nothing is inferred locally.
      setHistoryVersion((v) => v + 1);
      getSchoolAccount(data.account_id)
        .then((fresh) => setLoaded((current) => (current.status === 'ready' ? { status: 'ready', data: fresh } : current)))
        .catch(() => { /* the confirmed state above stays; Reload account re-reads everything */ });
    } catch (error: unknown) {
      const code = errorCode(error);
      if (code === 'request_unavailable') { setLoaded({ status: 'failed', code }); onChanged(); return; }
      setNotice('');
      setProblem(changeFailure(code));
    } finally {
      inFlight.current = false;
      setPhase('idle');
    }
  }

  return (
    <div className="space-y-5">
      {back}
      <div>
        <h2 ref={heading} tabIndex={-1} className="dashboard-heading text-xl font-bold focus:outline-none sm:text-2xl">{data.full_name ?? 'Name not recorded'}</h2>
        <p className="dashboard-muted mt-1 text-sm">{data.id_label} {data.school_id} · <AccountStatusBadge active={data.is_active} /></p>
      </div>

      <section aria-labelledby={`${ids}-info`} className="dashboard-panel rounded-2xl border p-5 sm:p-6">
        <h3 id={`${ids}-info`} className="dashboard-heading text-lg font-semibold">Account information</h3>
        <dl className="mt-3 divide-y">
          <Row label={data.id_label}><span className="font-semibold">{data.school_id}</span></Row>
          <Row label="Name">{data.full_name ?? <span className="dashboard-muted italic">Not recorded</span>}</Row>
          <Row label="Roles">{data.roles.length ? data.roles.join(', ') : <span className="dashboard-muted italic">No active role</span>}</Row>
          <Row label="Account created"><time dateTime={data.created_at}>{fmt(data.created_at)}</time></Row>
        </dl>
        <p className="dashboard-muted mt-3 text-xs leading-relaxed">Roles and permissions are read-only here and are managed separately.</p>
      </section>

      <section aria-labelledby={`${ids}-account-status`} className="dashboard-panel rounded-2xl border p-5 sm:p-6">
        <h3 id={`${ids}-account-status`} className="dashboard-heading text-lg font-semibold">Account status</h3>
        <dl className="mt-3 divide-y">
          <Row label="Status">{data.is_active ? 'Active: can sign in' : 'Inactive: cannot sign in'}</Row>
          <Row label="Registration">Approved</Row>
          <Row label="Approved on">{data.approved_at ? <time dateTime={data.approved_at}>{fmt(data.approved_at)}</time> : notRecorded}</Row>
          <Row label="Last status change">
            {data.last_status_change ? (
              <>
                {data.last_status_change.description} · <time dateTime={data.last_status_change.occurred_at}>{fmt(data.last_status_change.occurred_at)}</time>
                {' · '}{byActor(data.last_status_change.actor)}
              </>
            ) : notRecorded}
          </Row>
        </dl>
        <p className="dashboard-muted mt-3 text-xs leading-relaxed">Registration approval and the active status are separate. Workspace status is not academic enrollment.</p>
      </section>

      {(notice || problem) && (
        <div ref={noticeRef} tabIndex={-1} role={problem ? 'alert' : 'status'}
          className={`${problem ? 'dashboard-error-block' : 'dashboard-success'} rounded-xl border p-4 text-sm focus:outline-none`}>
          {problem ? (
            <>
              <p className="font-semibold"><span aria-hidden="true">! </span>{problem.title}</p>
              <p className="mt-1">{problem.detail}</p>
              {problem.reload && <button type="button" className={`${secondaryButton} mt-3`} onClick={reload}>Reload account</button>}
            </>
          ) : <p className="font-semibold"><span aria-hidden="true">✓ </span>{notice}</p>}
        </div>
      )}

      {allowed && (
        <section aria-labelledby={`${ids}-status`} className="dashboard-panel rounded-2xl border p-5 sm:p-6">
          <h3 id={`${ids}-status`} className="dashboard-heading text-lg font-semibold">{data.is_active ? 'Deactivate account' : 'Reactivate account'}</h3>
          <p className="dashboard-muted mt-1 text-sm leading-relaxed">
            {data.is_active
              ? 'Deactivating signs this person out on every device and blocks sign-in until the account is reactivated. Their approval, roles and records are kept.'
              : 'Reactivating lets this person sign in again with their existing roles. Sign-ins from before the deactivation stay signed out.'}
          </p>
          {!data.is_active && !data.can_reactivate ? (
            <p role="status" className="dashboard-warning mt-4 rounded-xl border p-4 text-sm">This account has no active role, so it cannot be reactivated here.</p>
          ) : (
            <button type="button" className={`${data.is_active ? secondaryButton : primaryButton} mt-4`} disabled={busy || locked}
              onClick={() => { setProblem(null); setNotice(''); setPhase('confirming'); }}>
              {data.is_active ? 'Deactivate account' : 'Reactivate account'}
            </button>
          )}
          {locked && <p className="dashboard-muted mt-2 text-xs">Changes are paused until you reload the account.</p>}
        </section>
      )}

      <StatusHistory accountId={data.account_id} version={historyVersion} headingId={`${ids}-history`} />

      <p className="dashboard-muted text-xs leading-relaxed">Django verifies your permission and the account rules on every request.</p>

      <Modal open={phase !== 'idle'} title={data.is_active ? 'Deactivate this account?' : 'Reactivate this account?'} busy={busy}
        onClose={() => setPhase('idle')}
        actions={(
          <>
            <button type="button" className={secondaryButton} disabled={busy} onClick={() => setPhase('idle')}>Cancel</button>
            <button type="button" className={data.is_active ? destructiveButton : primaryButton} disabled={busy} onClick={confirm}>
              {busy ? (data.is_active ? 'Deactivating…' : 'Reactivating…') : (data.is_active ? 'Confirm deactivation' : 'Confirm reactivation')}
            </button>
          </>
        )}>
        <p className="dashboard-heading">{data.is_active ? 'Deactivate' : 'Reactivate'} {name} ({data.id_label} {data.school_id})?</p>
        <p className="dashboard-muted">
          {data.is_active
            ? 'They will be signed out on every device and cannot sign in until the account is reactivated. It is audited.'
            : 'They can sign in again with their existing roles; earlier sign-ins are not restored. It is audited.'}
        </p>
        {busy && <p role="status" className="dashboard-muted">{data.is_active ? 'Deactivating the account…' : 'Reactivating the account…'}</p>}
      </Modal>
    </div>
  );
}
