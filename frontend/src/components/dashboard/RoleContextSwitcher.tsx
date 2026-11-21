/** D-117 role switching applies immediately on selection; server confirms the context. */
import { useEffect, useState } from 'react';
import type { WorkspaceRoleContext } from '../../features/auth/session';

interface Props {
  context: WorkspaceRoleContext;
  switching: boolean;
  error: string;
  onSwitch: (roleId: number) => void;
}

const roleLabel = (name: string) => name === 'Admin' ? 'School Admin' : name;

export default function RoleContextSwitcher({ context, switching, error, onSwitch }: Props) {
  const [selection, setSelection] = useState(context.active_role_id ?? 0);
  useEffect(() => setSelection(context.active_role_id ?? 0), [context.active_role_id]);
  // A rejected POST must not leave an unconfirmed role looking selected.
  useEffect(() => {
    if (error) setSelection(context.active_role_id ?? 0);
  }, [error, context.active_role_id]);
  const active = context.choices.find((role) => role.role_id === context.active_role_id);

  return (
    <div className="dashboard-sidebar-card mb-4 rounded-xl p-3">
      <label htmlFor="workspace-role-context" className="dashboard-sidebar-strong block text-xs font-semibold">Active role</label>
      <select id="workspace-role-context" value={selection} disabled={switching}
        onChange={(event) => {
          const nextId = Number(event.target.value);
          setSelection(nextId);
          if (Number.isSafeInteger(nextId) && nextId > 0 && nextId !== context.active_role_id) onSwitch(nextId);
        }}
        aria-describedby="workspace-role-context-status"
        className="dashboard-glass dashboard-heading mt-2 w-full min-w-0 rounded-lg border px-2 py-2 text-sm">
        {context.active_role_id === null && <option value={0}>Choose role</option>}
        {context.choices.map((item) => <option key={item.role_id} value={item.role_id}>{roleLabel(item.role_name)}</option>)}
      </select>
      <p id="workspace-role-context-status" aria-live="polite" className="dashboard-muted mt-2 text-xs">
        {switching ? 'Confirming selected role…' : active ? `Currently using: ${roleLabel(active.role_name)}` : 'Choose an assigned role'}
      </p>
      {error && <p role="alert" className="dashboard-muted mt-2 text-xs">{error}</p>}
    </div>
  );
}
