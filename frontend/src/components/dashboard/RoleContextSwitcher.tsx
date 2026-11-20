/** D-113 accessible role selector. Options are returned by the server, not role-name guesses. */
import { useEffect, useState } from 'react';
import type { WorkspaceRoleContext } from '../../features/auth/session';

interface Props {
  context: WorkspaceRoleContext;
  switching: boolean;
  error: string;
  onSwitch: (roleId: number) => void;
}

export default function RoleContextSwitcher({ context, switching, error, onSwitch }: Props) {
  const [selection, setSelection] = useState(context.active_role_id ?? 0);
  useEffect(() => setSelection(context.active_role_id ?? 0), [context.active_role_id]);
  return (
    <div className="dashboard-sidebar-card mb-4 rounded-xl p-3">
      <label htmlFor="workspace-role-context" className="dashboard-sidebar-strong block text-xs font-semibold">Active role</label>
      <select id="workspace-role-context" value={selection} disabled={switching}
        onChange={(event) => setSelection(Number(event.target.value))}
        className="dashboard-glass dashboard-heading mt-2 w-full min-w-0 rounded-lg border px-2 py-2 text-sm">
        {context.active_role_id === null && <option value={0}>Choose role</option>}
        {context.choices.map((item) => <option key={item.role_id} value={item.role_id}>{item.role_name === 'Admin' ? 'School Admin' : item.role_name}</option>)}
      </select>
      <button type="button" disabled={switching || selection === 0 || selection === context.active_role_id}
        className="dashboard-primary-link mt-2 min-h-9 w-full rounded-lg px-2 py-1.5 text-sm font-medium disabled:opacity-50"
        onClick={() => onSwitch(selection)}>
        {switching ? 'Switching…' : 'Switch role'}
      </button>
      {error && <p role="alert" className="dashboard-muted mt-2 text-xs">{error}</p>}
    </div>
  );
}
