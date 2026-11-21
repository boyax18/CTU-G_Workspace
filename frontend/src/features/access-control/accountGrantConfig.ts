/** WF-03.03 UI visibility only; Django authorizes every read and mutation. */
export const ACCOUNT_GRANTS_ENABLED =
  import.meta.env?.VITE_WORKSPACE_WF0303_ACCOUNT_GRANTS_ENABLED === '1';
export const ACCOUNT_GRANTS_ROOT = '/api/v1/admin/account-grants/';
