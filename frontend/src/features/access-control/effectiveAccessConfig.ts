/** WF-03.05 read-only access inspector; server enforces authorization. */
export const EFFECTIVE_ACCESS_INSPECT_ENABLED =
  import.meta.env?.VITE_WORKSPACE_WF0305_EFFECTIVE_ACCESS_INSPECT_ENABLED === '1';
export const EFFECTIVE_ACCESS_ROOT = '/api/v1/admin/effective-access/';
