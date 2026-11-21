/** WF-03.04. Account-level Deny takes precedence in every active role. */
import { useMemo, useState } from 'react';
import Modal from '../../components/common/Modal';
import { ApiError } from '../../api/client.ts';
import {
  findRestrictionAccounts, getRestrictionDirectory, changeRestriction,
} from './accountRestrictionApi.ts';
import type { AccountMatch, RestrictionAction, RestrictionDirectory, RestrictionPermission } from './accountRestrictionApi.ts';

const btn = 'dashboard-panel min-h-11 rounded-lg border px-3 py-2 text-sm font-medium';
const actionButton = 'dashboard-primary-link min-h-11 rounded-lg px-4 py-2 text-sm font-semibold';
function describe(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 403) return 'You are not authorized to manage this account or permission.';
    if (error.status === 409) return 'The permission changed. Reload the account and try again.';
    if (error.status === 503) return 'Permission restrictions are not available in this development configuration.';
    return error.message;
  }
  return 'Could not confirm the result. Reload before continuing.';
}
const names: Record<RestrictionAction,string> = {
  deny: 'Deny permission', revoke_grant: 'Revoke individual Grant', remove_deny: 'Remove Deny',
};

export default function AccountRestrictionsPanel({permissions}: {permissions: readonly string[]}) {
  const [q,setQ] = useState('');
  const [matches,setMatches] = useState<AccountMatch[]>([]);
  const [directory,setDirectory] = useState<RestrictionDirectory | null>(null);
  const [filter,setFilter] = useState('');
  const [busy,setBusy] = useState(false);
  const [loading,setLoading] = useState(false);
  const [locked,setLocked] = useState(false);
  const [error,setError] = useState('');
  const [success,setSuccess] = useState('');
  const [pending,setPending] = useState<{permission:RestrictionPermission;action:RestrictionAction}|null>(null);
  const rows = useMemo(() => directory?.permissions.filter(p =>
    `${p.permission_code} ${p.permission_name} ${p.service_code}`.toLowerCase().includes(filter.toLowerCase()),
  ) ?? [], [directory,filter]);

  async function search() {
    setMatches([]); setDirectory(null); setError(''); setSuccess(''); setLocked(false); setLoading(true);
    try { setMatches(await findRestrictionAccounts(q.trim())); }
    catch(e) { setError(describe(e)); }
    finally { setLoading(false); }
  }
  async function choose(accountId: number) {
    setError(''); setSuccess(''); setDirectory(null); setLoading(true); setLocked(false);
    try { setDirectory(await getRestrictionDirectory(accountId)); }
    catch(e) { setError(describe(e)); setLocked(true); }
    finally { setLoading(false); }
  }
  async function refresh() {
    if (!directory) return;
    const accountId = directory.account.account_id;
    setError(''); setLoading(true);
    try { setDirectory(await getRestrictionDirectory(accountId)); setLocked(false); }
    catch(e) { setError(describe(e)); setLocked(true); }
    finally { setLoading(false); }
  }
  async function confirm() {
    if (!pending || !directory || busy || locked) return;
    const {permission,action} = pending;
    const accountId = directory.account.account_id;
    setPending(null); setBusy(true); setError(''); setSuccess('');
    // Even a successful response is followed by a fresh read. Until then,
    // block further mutations to avoid issuing commands on stale state.
    setLocked(true);
    try {
      await changeRestriction(accountId,permission,action);
      const latest = await getRestrictionDirectory(accountId);
      setDirectory(latest); setLocked(false);
      setSuccess(`${names[action]} completed for ${permission.permission_code}.`);
    } catch(e) { setError(describe(e)); }
    finally { setBusy(false); }
  }

  if (!permissions.includes('access_control.account_permissions.manage'))
    return <p role="alert" className="dashboard-muted text-sm">Account restrictions are not available to this session.</p>;

  return <div className="space-y-5">
    <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
      <h2 className="dashboard-heading text-lg font-bold">Account-specific permission restrictions</h2>
      <p className="dashboard-muted mt-1 text-sm">Find an approved account by CTU-G ID. A Deny applies to the account across all selected roles and overrides role or direct Grants.</p>
      <form className="mt-4 flex flex-wrap gap-2" onSubmit={e => {e.preventDefault(); void search();}}>
        <label className="dashboard-muted flex-1 text-sm">CTU-G ID prefix
          <input value={q} maxLength={64} placeholder="Enter at least 3 characters" onChange={e => setQ(e.target.value)}
            className="dashboard-panel mt-2 block min-h-11 w-full rounded-lg border px-3 py-2 text-sm" />
        </label>
        <button type="submit" className={actionButton} disabled={busy || loading || q.trim().length < 3}>Find account</button>
      </form>
      {matches.length > 0 && <ul className="mt-4 space-y-2" aria-label="Matching accounts">
        {matches.map(account => <li key={account.account_id}><button type="button" className={`${btn} w-full text-left`}
          disabled={busy || loading} onClick={() => void choose(account.account_id)}>{account.ctug_id} · {account.full_name}</button></li>)}
      </ul>}
    </section>
    {error && <div role="alert" className="dashboard-error-block rounded-xl border p-4 text-sm">{error}
      {directory && <button type="button" className={`${btn} ml-3`} onClick={() => void refresh()} disabled={busy || loading}>Reload</button>}
    </div>}
    {success && <p role="status" className="dashboard-success rounded-lg border p-3 text-sm">{success}</p>}
    {loading && <p role="status" className="dashboard-muted text-sm">Loading…</p>}
    {directory && <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <h3 className="dashboard-heading text-lg font-bold">{directory.account.ctug_id} · {directory.account.full_name}</h3>
        <button type="button" className={btn} disabled={busy || loading} onClick={() => void refresh()}>Refresh</button>
      </div>
      <label className="dashboard-muted mt-4 block text-sm">Filter permissions
        <input type="search" maxLength={100} value={filter} onChange={e=>setFilter(e.target.value)}
          className="dashboard-panel mt-2 block min-h-11 w-full rounded-lg border px-3 py-2 text-sm" />
      </label>
      <ul className="mt-3 divide-y" aria-label="Individual restrictions">
        {rows.map(p => <li key={p.permission_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
          <div className="min-w-0 flex-1"><p className="dashboard-heading break-all text-sm font-semibold">{p.permission_code}</p>
            <p className="dashboard-muted text-xs">{p.permission_name} · {p.service_code} · {p.effect ?? 'No override'}
              {p.scope_role_id ? ` · Grant role #${p.scope_role_id}` : ''}</p></div>
          {!locked && <div className="flex flex-wrap gap-2">
            {p.can_deny && <button type="button" className={btn} disabled={busy} onClick={() => setPending({permission:p,action:'deny'})}>Deny</button>}
            {p.can_revoke_grant && <button type="button" className={btn} disabled={busy} onClick={() => setPending({permission:p,action:'revoke_grant'})}>Revoke Grant</button>}
            {p.can_remove_deny && <button type="button" className={btn} disabled={busy} onClick={() => setPending({permission:p,action:'remove_deny'})}>Remove Deny</button>}
            {!p.can_deny && !p.can_revoke_grant && !p.can_remove_deny && <span className="dashboard-muted text-xs">Read only</span>}
          </div>}
        </li>)}
      </ul>
      {locked && <p className="dashboard-muted mt-3 text-sm">Changes are paused until the account is reloaded.</p>}
    </section>}
    <Modal open={pending !== null} title={pending ? `${names[pending.action]}?` : 'Confirm permission change'}
      onClose={() => setPending(null)} busy={busy} actions={<>
        <button type="button" className={btn} disabled={busy} onClick={() => setPending(null)}>Cancel</button>
        <button type="button" className={actionButton} disabled={busy} onClick={() => void confirm()}>Confirm</button>
      </>}>
      <p>Account: <strong>{directory?.account.ctug_id}</strong></p>
      <p className="break-all">Permission: <strong>{pending?.permission.permission_code}</strong></p>
      {pending?.action === 'deny' && <p>This will block this permission in every active role context, even if a role normally grants it.</p>}
      {pending?.action === 'revoke_grant' && <p>This removes only this account's individual Grant. Any independent role permissions remain unchanged.</p>}
      {pending?.action === 'remove_deny' && <p><strong>Warning:</strong> removing this Deny can restore access from a role Grant. Make sure the restriction should end.</p>}
    </Modal>
  </div>;
}
