/** WF-03.02 role-permission matrix. All action hints are server-computed;
 * the server performs the actual authorization again inside guarded writes. */
import { useEffect, useMemo, useState } from 'react';
import Modal from '../../components/common/Modal.tsx';
import { ApiError } from '../../api/client.ts';
import { getRoleChoices, getRolePermissions, setRolePermission } from './rolePermissionApi.ts';
import type { RoleChoice, PermissionChoice, PermissionDirectory } from './rolePermissionApi.ts';

const button = 'dashboard-outline-button min-h-11 rounded-lg border px-3 py-2 text-sm font-medium disabled:opacity-50';
const primary = 'dashboard-primary-link min-h-11 rounded-lg px-3 py-2 text-sm font-semibold disabled:opacity-50';
type Pending = { permission: PermissionChoice; action: 'grant' | 'revoke' };

function message(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.outcomeUnknown || error.code === 'outcome_unknown') return 'Change outcome uncertain. Reload the role permissions before trying again.';
    if (error.status === 409) return 'Permissions changed elsewhere. Reload before continuing.';
    if (error.status === 403) return 'This account is not authorized to manage these permissions.';
    if (error.status === 503) return 'Role-permission management is not available in this configuration.';
    if (error.status === 401) return 'Your session has ended. Sign in again.';
  }
  return 'Unable to load or update role permissions. Check the connection and try again.';
}

export default function RolePermissionsPanel({ permissions }: { permissions: readonly string[] }) {
  const [roles, setRoles] = useState<RoleChoice[]>([]);
  const [rolesRetry, setRolesRetry] = useState(0);
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [directory, setDirectory] = useState<PermissionDirectory | null>(null);
  const [loadingRoles, setLoadingRoles] = useState(true);
  const [loadingPermissions, setLoadingPermissions] = useState(false);
  const [busy, setBusy] = useState(false);
  const [locked, setLocked] = useState(false);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [query, setQuery] = useState('');
  const [pending, setPending] = useState<Pending | null>(null);

  useEffect(() => {
    let live = true;
    getRoleChoices().then(items => {
      if (!live) return;
      setRoles(items);
      setSelectedId(items.length ? items[0].role_id : null);
      setLoadingRoles(false);
    }).catch(err => { if (live) { setError(message(err)); setLoadingRoles(false); } });
    return () => { live = false; };
  }, [rolesRetry]);

  useEffect(() => {
    if (selectedId === null) return;
    let live = true;
    setLoadingPermissions(true);
    setDirectory(null);
    setError('');
    setNotice('');
    setLocked(false);
    getRolePermissions(selectedId).then(data => {
      if (live) { setDirectory(data); setLoadingPermissions(false); }
    }).catch(err => { if (live) { setError(message(err)); setLoadingPermissions(false); } });
    return () => { live = false; };
  }, [selectedId]);

  const filtered = useMemo(() => {
    const term = query.trim().toLocaleLowerCase();
    return (directory?.permissions ?? []).filter(p => !term ||
      `${p.permission_code} ${p.permission_name} ${p.service_code}`.toLocaleLowerCase().includes(term));
  }, [directory, query]);
  const chosen = roles.find(role => role.role_id === selectedId);
  const assignedCount = directory?.permissions.filter(p => p.assigned).length ?? 0;
  const mayOpen = permissions.includes('access_control.role_permissions.manage');

  async function reload(): Promise<boolean> {
    if (selectedId === null) return false;
    setError(''); setNotice(''); setLoadingPermissions(true); setDirectory(null);
    try {
      setDirectory(await getRolePermissions(selectedId));
      setLocked(false);
      return true;
    } catch (err) {
      setError(message(err));
      setLocked(true);
      return false;
    } finally { setLoadingPermissions(false); }
  }

  async function confirm() {
    if (!pending || selectedId === null || busy || locked) return;
    setBusy(true); setError(''); setNotice('');
    const { action, permission } = pending;
    setPending(null);
    try {
      await setRolePermission(selectedId, permission.permission_id, action, permission.assigned);
      // Always refresh rather than guessing the database state after a write.
      if (await reload()) setNotice(`${action === 'grant' ? 'Granted' : 'Revoked'} ${permission.permission_code}.`);
    } catch (err) {
      setError(message(err));
      setLocked(true);
    } finally { setBusy(false); }
  }

  if (!mayOpen) return <p role="alert" className="dashboard-muted text-sm">Role-permission management is not available to this session.</p>;
  return (
    <div className="space-y-5">
      <section className="dashboard-panel rounded-2xl border p-5 sm:p-6" aria-labelledby="wf0302-heading">
        <h2 id="wf0302-heading" className="dashboard-heading text-lg font-bold">Role permission assignments</h2>
        <p className="dashboard-muted mt-1 text-sm">Review the stored permissions for each role. Only independently authorized, non-governance assignments can be changed.</p>
        {loadingRoles && <p role="status" className="dashboard-muted mt-4 text-sm">Loading roles…</p>}
        {!loadingRoles && roles.length === 0 && !error && <p className="dashboard-muted mt-4 text-sm">No roles are available.</p>}
        {roles.length > 0 && (
          <div className="mt-5 flex flex-wrap gap-2" aria-label="Select role">
            {roles.map(role => <button key={role.role_id} type="button" disabled={busy || loadingPermissions}
              aria-pressed={selectedId === role.role_id}
              className={`${button} ${selectedId === role.role_id ? 'dashboard-heading font-bold' : 'dashboard-muted'}`}
              onClick={() => { setQuery(''); setSelectedId(role.role_id); }}>
              {role.role_name}{!role.is_active ? ' · Inactive' : ''}{role.protected ? ' · Protected' : ''}
            </button>)}
          </div>
        )}
      </section>

      {error && <div role="alert" className="dashboard-error-block rounded-xl border p-4 text-sm">
        {error}<button type="button" className={`${button} ml-3`} onClick={selectedId === null ? () => { setError(''); setLoadingRoles(true); setRolesRetry(value => value + 1); } : reload} disabled={busy || loadingRoles}>Reload</button>
      </div>}
      {notice && <p role="status" className="dashboard-success rounded-lg border p-3 text-sm">{notice}</p>}
      {chosen && <section className="dashboard-panel rounded-2xl border p-5 sm:p-6" aria-labelledby="wf0302-selected">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div><h3 id="wf0302-selected" className="dashboard-heading font-semibold">{chosen.role_name}</h3>
            <p className="dashboard-muted text-xs">{assignedCount} assigned permissions · Changes require approved delegation and backend authorization.</p></div>
          <button type="button" className={button} onClick={reload} disabled={busy || loadingPermissions}>Refresh</button>
        </div>
        {chosen.protected && <p className="dashboard-muted mt-3 text-sm">Protected administration roles are read-only here. School Admin and Technical Super Admin governance bindings cannot be edited through ordinary delegation.</p>}
        <label className="dashboard-muted mt-4 block text-sm">Filter permissions
          <input type="search" value={query} maxLength={100} onChange={e => setQuery(e.target.value)}
            placeholder="Permission code, name, or service"
            className="dashboard-panel mt-2 block min-h-11 w-full rounded-lg border px-3 py-2 text-sm" />
        </label>
        {loadingPermissions && <p role="status" className="dashboard-muted mt-4 text-sm">Loading permissions…</p>}
        {directory && <ul aria-label="Role permissions" className="mt-3 divide-y">
          {filtered.map(permission => <li key={permission.permission_id} className="flex flex-wrap items-center justify-between gap-3 py-3">
            <div className="min-w-0 flex-1"><p className="dashboard-heading break-all text-sm font-semibold">{permission.permission_code}</p>
              <p className="dashboard-muted text-xs">{permission.permission_name} · {permission.service_code} · {permission.assigned ? 'Assigned' : 'Not assigned'}</p></div>
            {permission.change_allowed && !locked ? <button type="button" disabled={busy} className={button}
              onClick={() => setPending({ permission, action: permission.assigned ? 'revoke' : 'grant' })}>
              {permission.assigned ? 'Revoke' : 'Grant'}</button> :
              <span className="dashboard-muted text-xs">Read only</span>}
          </li>)}
          {filtered.length === 0 && <li className="dashboard-muted py-6 text-sm">No matching permissions.</li>}
        </ul>}
        {locked && <p className="dashboard-muted mt-2 text-sm">Updates are paused until a successful refresh.</p>}
      </section>}
      <Modal open={pending !== null} busy={busy} onClose={() => setPending(null)}
        title={pending?.action === 'grant' ? 'Grant permission?' : 'Revoke permission?'}
        actions={<><button type="button" className={button} disabled={busy} onClick={() => setPending(null)}>Cancel</button>
          <button type="button" className={primary} disabled={busy} onClick={confirm}>{busy ? 'Saving…' : 'Confirm change'}</button></>}>
        <p className="dashboard-heading text-sm">{pending?.permission.permission_code} — {chosen?.role_name}</p>
        <p className="dashboard-muted mt-2 text-sm">This change affects accounts holding the role. The server will recheck authorization and record any change in the access audit log.</p>
      </Modal>
    </div>
  );
}
