/** WF-03.06 read-only audit view; backend verifies every request. */
export const ACCESS_AUDIT_ENABLED =
  import.meta.env?.VITE_WORKSPACE_WF0306_AUDIT_HISTORY_ENABLED === '1';
export const ACCESS_AUDIT_ROOT = '/api/v1/admin/access-audit/';
