/** WF-03.03: selected role-scoped individual Grants, no role-wide changes. */
import { useMemo, useState } from 'react';
import Modal from '../../components/common/Modal.tsx';
import { ApiError } from '../../api/client.ts';
import {
  searchGrantAccounts, getAccountGrantDirectory, grantIndividualPermission,
} from './accountGrantApi.ts';
import type { AccountMatch, AccountGrantDirectory, AccountPermissionRow } from './accountGrantApi.ts';

const btn = 'dashboard-outline-button min-h-11 rounded-lg border px-3 py-2 text-sm font-medium disabled:opacity-50';
const action = 'dashboard-primary-link min-h-11 rounded-lg px-4 py-2 text-sm font-semibold disabled:opacity-50';
function errorText(err: unknown) {
  if (err instanceof ApiError) {
    if (err.outcomeUnknown) return 'The outcome is uncertain. Reload the account before another request.';
    if (err.status === 409) return 'Permissions changed elsewhere. Reload before continuing.';
    if (err.status === 503) return 'Account-specific Grants are unavailable in this configuration.';
    if (err.status === 403) return 'You are not authorized to grant this permission.';
    if (err.status === 401) return 'Session expired. Please sign in again.';
  }
  return 'The request failed. Check your connection and reload.';
}

type Pending = { permission: AccountPermissionRow; roleId: number };

export default function AccountGrantsPanel({ permissions }: { permissions: readonly string[] }) {
  const [q, setQ] = useState('');
  const [matches, setMatches] = useState<AccountMatch[]>([]);
  const [directory, setDirectory] = useState<AccountGrantDirectory | null>(null);
  const [filter, setFilter] = useState('');
  const [chosen, setChosen] = useState<Record<number, number>>({});
  const [pending, setPending] = useState<Pending | null>(null);
  const [loading, setLoading] = useState(false);
  const [busy, setBusy] = useState(false);
  const [locked, setLocked] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');

  const rows = useMemo(() => directory?.permissions.filter(row =>
    `${row.permission_code} ${row.permission_name} ${row.service_code}`.toLowerCase().includes(filter.toLowerCase())) ?? [],
  [directory, filter]);

  async function search() {
    setLoading(true); setError(''); setMatches([]); setDirectory(null); setSuccess(''); setLocked(false);
    try { setMatches(await searchGrantAccounts(q.trim())); }
    catch (err) { setError(errorText(err)); }
    finally { setLoading(false); }
  }

  async function selectAccount(id: number) {
    setLoading(true); setDirectory(null); setError(''); setSuccess(''); setLocked(false); setChosen({});
    try { setDirectory(await getAccountGrantDirectory(id)); }
    catch (err) { setError(errorText(err)); }
    finally { setLoading(false); }
  }

  async function reload() {
    if (!directory) return;
    setLoading(true); setError(''); setLocked(false);
    try { setDirectory(await getAccountGrantDirectory(directory.account.account_id)); }
    catch (err) { setLocked(true); setError(errorText(err)); }
    finally { setLoading(false); }
  }

  async function confirm() {
    if (!pending || !directory || busy || locked) return;
    const accountId = directory.account.account_id;
    const {permission, roleId} = pending;
    setPending(null); setBusy(true); setError(''); setSuccess('');
    try {
      await grantIndividualPermission(accountId, permission.permission_id, roleId);
      setLocked(true);
      const data = await getAccountGrantDirectory(accountId);
      setDirectory(data); setLocked(false);
      setSuccess(`Granted ${permission.permission_code} to the selected role context.`);
    } catch (err) { setLocked(true); setError(errorText(err)); }
    finally { setBusy(false); }
  }

  if (!permissions.includes('access_control.account_permissions.manage'))
    return <p role="alert" className="dashboard-muted text-sm">Account grant management is not available to this session.</p>;

  return <div className="space-y-5">
    <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
      <h2 className="dashboard-heading text-lg font-bold">Individual permission Grants</h2>
      <p className="dashboard-muted mt-1 text-sm">Look up an approved account by CTU-G ID. Grants apply only in the selected role context; no other accounts or roles are changed.</p>
      <form className="mt-4 flex flex-wrap gap-2" onSubmit={e => {e.preventDefault(); void search();}}>
        <label className="dashboard-muted flex-1 text-sm">CTU-G ID prefix
          <input value={q} onChange={e => setQ(e.target.value)} maxLength={64} placeholder="Enter at least 3 characters"
            className="dashboard-panel mt-2 block min-h-11 w-full rounded-lg border px-3 py-2 text-sm" />
        </label>
        <button type="submit" className={action} disabled={loading || busy || q.trim().length < 3}>Find account</button>
      </form>
      {matches.length > 0 && <ul className="mt-4 space-y-2" aria-label="Matching accounts">
        {matches.map(a => <li key={a.account_id}><button type="button" className={`${btn} w-full text-left`} disabled={loading || busy}
          onClick={() => void selectAccount(a.account_id)}>{a.ctug_id} · {a.full_name}</button></li>)}
      </ul>}
    </section>
    {error && <div role="alert" className="dashboard-error-block rounded-xl border p-4 text-sm">{error}
      <button type="button" className={`${btn} ml-3`} onClick={() => void reload()} disabled={!directory || loading || busy}>Reload</button>
    </div>}
    {success && <p role="status" className="dashboard-success rounded-lg border p-3 text-sm">{success}</p>}
    {loading && <p role="status" className="dashboard-muted text-sm">Loading…</p>}
    {directory && <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div><h3 className="dashboard-heading text-lg font-bold">{directory.account.ctug_id} · {directory.account.full_name}</h3>
          <p className="dashboard-muted mt-1 text-xs">Assign only to an eligible, active role already held by this account.</p></div>
        <button type="button" className={btn} disabled={loading || busy} onClick={() => void reload()}>Refresh</button>
      </div>
      <label className="dashboard-muted mt-4 block text-sm">Filter permissions
        <input type="search" maxLength={100} value={filter} onChange={e => setFilter(e.target.value)}
          className="dashboard-panel mt-2 block min-h-11 w-full rounded-lg border px-3 py-2 text-sm" />
      </label>
      <ul className="mt-3 divide-y" aria-label="Account permissions">
        {rows.map(p => <li key={p.permission_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
          <div className="min-w-0 flex-1"><p className="dashboard-heading break-all text-sm font-semibold">{p.permission_code}</p>
            <p className="dashboard-muted text-xs">{p.permission_name} · {p.service_code} · {p.effect ?? 'No override'}
              {p.scope_role_id ? ` · Role-bound #${p.scope_role_id}` : ''}</p></div>
          {p.grant_role_ids.length > 0 && !locked ? <div className="flex flex-wrap items-center gap-2">
            <select aria-label={`Grant context for ${p.permission_code}`} className={`${btn} min-w-32`} disabled={busy}
              value={chosen[p.permission_id] ?? p.grant_role_ids[0]}
              onChange={e => setChosen(v => ({...v, [p.permission_id]: Number(e.target.value)}))}>
              {p.grant_role_ids.map(id => <option key={id} value={id}>{directory.account.roles.find(r => r.role_id === id)?.role_name}</option>)}
            </select>
            <button type="button" className={btn} disabled={busy} onClick={() => setPending({permission:p, roleId:chosen[p.permission_id] ?? p.grant_role_ids[0]})}>Grant</button>
          </div> : <span className="dashboard-muted text-xs">Read only</span>}
        </li>)}
      </ul>
      {locked && <p className="dashboard-muted mt-3 text-sm">Updates paused until a successful refresh.</p>}
    </section>}
    <Modal open={pending !== null} title="Grant individual permission?" onClose={() => setPending(null)} busy={busy}
      actions={<><button type="button" className={btn} onClick={() => setPending(null)} disabled={busy}>Cancel</button>
        <button type="button" className={action} onClick={() => void confirm()} disabled={busy}>Confirm Grant</button></>}>
      <p>This affects only {directory?.account.ctug_id} under the selected active role. It does not change the role's default permissions.</p>
      <p className="break-all font-semibold">{pending?.permission.permission_code}</p>
    </Modal>
  </div>;
}
