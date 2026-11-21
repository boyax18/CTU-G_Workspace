/** WF-03.04: frontend visibility only, always backed by server authorization. */
export const ACCOUNT_RESTRICTIONS_ENABLED =
  import.meta.env?.VITE_WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED === '1';
export const ACCOUNT_RESTRICTIONS_ROOT = '/api/v1/admin/account-restrictions/';
