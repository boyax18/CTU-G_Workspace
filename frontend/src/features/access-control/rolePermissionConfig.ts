/** WF-03.02 client visibility only; server authorization is independent. */
export const ROLE_PERMISSION_MANAGEMENT_ENABLED =
  import.meta.env?.VITE_WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED === '1';
export const ROLE_PERMISSION_API_ROOT = '/api/v1/admin/role-permissions/';
