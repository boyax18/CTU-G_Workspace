/** WF-03.05: read-only, server-evaluated access and service state inspector. */
import { useMemo, useRef, useState } from 'react';
import { ApiError } from '../../api/client.ts';
import { findAccessAccounts, getAccessRoles, getAccessSnapshot } from './effectiveAccessApi.ts';
import type { AccessSnapshot, InspectAccount, InspectRole } from './effectiveAccessApi.ts';

const field = 'dashboard-panel mt-2 block min-h-11 w-full rounded-lg border px-3 py-2 text-sm';
const button = 'dashboard-panel min-h-11 rounded-lg border px-4 py-2 text-sm font-medium';
const primary = 'dashboard-primary-link min-h-11 rounded-lg px-4 py-2 text-sm font-semibold';
function describe(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 401) return 'Your session ended. Sign in again.';
    if (error.status === 403) return 'Your active role does not have permission to inspect effective access.';
    if (error.status === 404) return 'The account or role is no longer available.';
    if (error.status === 503) return 'Access inspection is not enabled in this configuration.';
    return error.message;
  }
  return 'Could not load the current access snapshot. Try again.';
}

export default function EffectiveAccessPanel({permissions}: {permissions: readonly string[]}) {
  const [query,setQuery] = useState('');
  const [matches,setMatches] = useState<InspectAccount[]>([]);
  const [account,setAccount] = useState<InspectAccount|null>(null);
  const [roles,setRoles] = useState<InspectRole[]>([]);
  const [roleId,setRoleId] = useState<number|null>(null);
  const [snapshot,setSnapshot] = useState<AccessSnapshot|null>(null);
  const [filter,setFilter] = useState('');
  const [show,setShow] = useState('all');
  const [busy,setBusy] = useState(false);
  const [error,setError] = useState('');
  const request = useRef(0);
  const rows = useMemo(() => snapshot?.permissions.filter(p =>
    (show === 'all' || (show === 'effective' ? p.effective : !p.effective)) &&
    `${p.permission_code} ${p.permission_name} ${p.service_code}`.toLowerCase().includes(filter.toLowerCase())
  ) ?? [],[snapshot,filter,show]);

  async function search() {
    const version=++request.current;
    setBusy(true);setError('');setMatches([]);setAccount(null);setRoles([]);setRoleId(null);setSnapshot(null);
    try { const result=await findAccessAccounts(query.trim());if(version===request.current)setMatches(result); }
    catch(e){if(version===request.current)setError(describe(e));}
    finally{if(version===request.current)setBusy(false);}
  }
  async function selectAccount(selected: InspectAccount) {
    const version=++request.current;
    setBusy(true);setError('');setAccount(selected);setRoles([]);setRoleId(null);setSnapshot(null);
    try {const data=await getAccessRoles(selected.account_id);
      if(version===request.current){setAccount(data.account);setRoles(data.roles);}}
    catch(e){if(version===request.current)setError(describe(e));}
    finally{if(version===request.current)setBusy(false);}
  }
  async function selectRole(next: number) {
    const version=++request.current;
    setRoleId(next);setSnapshot(null);setError('');setBusy(true);
    try { if(!account) return;
      const data=await getAccessSnapshot(account.account_id,next);
      if(version===request.current)setSnapshot(data);}
    catch(e){if(version===request.current)setError(describe(e));}
    finally{if(version===request.current)setBusy(false);}
  }

  if(!permissions.includes('access_control.effective_permissions.inspect'))
    return <p role="alert" className="dashboard-muted text-sm">Access inspection is not available in this role context.</p>;
  return <div className="space-y-5">
    <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
      <h2 className="dashboard-heading text-lg font-bold">Effective access inspection</h2>
      <p className="dashboard-muted mt-2 text-sm">Read-only snapshot: inspect a CTU-G account under a selected, assigned role. Results come from the backend permission evaluator; they do not change roles or service states.</p>
      <form onSubmit={e=>{e.preventDefault();void search();}} className="mt-4 flex flex-wrap items-end gap-3">
        <label className="dashboard-muted min-w-48 flex-1 text-sm">CTU-G ID prefix
          <input className={field} value={query} maxLength={64} onChange={e=>setQuery(e.target.value)} placeholder="At least 3 characters" /></label>
        <button type="submit" className={primary} disabled={busy || query.trim().length < 3}>Find account</button>
      </form>
      {matches.length>0 && <ul aria-label="Matching accounts" className="mt-4 space-y-2">{matches.map(a=><li key={a.account_id}>
        <button className={`${button} w-full text-left`} type="button" disabled={busy} onClick={()=>void selectAccount(a)}>{a.ctug_id} · {a.full_name}</button>
      </li>)}</ul>}
      {account && <div className="mt-4 space-y-2">
        <p className="dashboard-heading text-sm font-semibold">{account.ctug_id} · {account.full_name}</p>
        <label className="dashboard-muted block text-sm">Role to inspect
          <select className={field} value={roleId ?? ''} disabled={busy || roles.length===0}
            onChange={e=>{const value=Number(e.target.value);if(value>0)void selectRole(value);}}>
            <option value="">Select assigned role</option>
            {roles.map(r=><option key={r.role_id} value={r.role_id}>{r.role_name==='Admin'?'School Admin':r.role_name}</option>)}
          </select></label>
        {roles.length===0 && !busy && <p className="dashboard-muted text-sm">No eligible role contexts found.</p>}
      </div>}
    </section>
    {busy && <p role="status" className="dashboard-muted text-sm">Loading current access…</p>}
    {error && <p role="alert" className="dashboard-error-block rounded-xl border p-4 text-sm">{error}</p>}
    {snapshot && <>
      <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
        <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="dashboard-heading text-lg font-bold">{snapshot.role.role_name==='Admin'?'School Admin':snapshot.role.role_name} access</h3>
          <button className={button} onClick={()=>{if(roleId)void selectRole(roleId);}} type="button" disabled={busy}>Refresh snapshot</button></div>
        <p className="dashboard-muted mt-2 text-sm">{snapshot.effective_count} of {snapshot.permissions.length} catalogue permissions effective. {snapshot.inherited_role_ids.length ? 'Stored permissions inherited from another assigned role are included.' : 'No additional role inheritance.'}</p>
        <h4 className="dashboard-heading mt-5 font-semibold">Service states</h4>
        <ul aria-label="Service status" className="mt-3 grid gap-2 sm:grid-cols-2 lg:grid-cols-3">{snapshot.services.map(s=><li key={s.service_code} className="rounded-xl border p-3 text-sm">
          <strong className="dashboard-heading">{s.service_name}</strong><p className="dashboard-muted text-xs">{s.service_code}</p>
          <p className="mt-1 text-xs">{s.is_active?'Active':'Disabled — related permissions unavailable'}</p></li>)}</ul>
      </section>
      <section className="dashboard-panel rounded-2xl border p-5 sm:p-6">
        <h4 className="dashboard-heading text-lg font-bold">Permissions by selected role</h4>
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
          <label className="dashboard-muted text-sm">Filter by permission or service<input className={field} value={filter} maxLength={120} onChange={e=>setFilter(e.target.value)} type="search" /></label>
          <label className="dashboard-muted text-sm">Status
            <select className={field} value={show} onChange={e=>setShow(e.target.value)}><option value="all">All</option><option value="effective">Effective</option><option value="inactive">Not effective</option></select>
          </label>
        </div>
        <ul className="mt-4 divide-y" aria-label="Effective permissions">{rows.map(p=><li className="flex flex-wrap items-center justify-between gap-3 py-3" key={p.permission_id}>
          <div className="min-w-0 flex-1"><p className="dashboard-heading break-all text-sm font-semibold">{p.permission_code}</p>
          <p className="dashboard-muted text-xs">{p.permission_name} · {p.service_code}</p>
          {!p.service_active && <p className="dashboard-muted text-xs">Service disabled</p>}
          {p.explicit_deny && <p className="dashboard-muted text-xs">Explicit account Deny</p>}
          {p.role_grant_recorded && <p className="dashboard-muted text-xs">Stored role grant exists (other restrictions may apply)</p>}
          </div><strong className="text-xs">{p.effective?'Effective':'Not effective'}</strong>
        </li>)}</ul>
        {rows.length===0 && <p className="dashboard-muted mt-4 text-sm">No permissions match.</p>}
        <p className="dashboard-muted mt-4 border-t pt-3 text-xs">This is a point-in-time explanation, not an authorization token. Every protected API still checks permissions when it executes.</p>
      </section>
    </>}
  </div>;
}
