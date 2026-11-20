/** WF-02.05 (D-69): the Account directory and its status controls. Off unless the build sets
 * VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED=1. Django's own default-off WORKSPACE_ACCOUNT_STATUS_ENABLED
 * gate, the exact effective permissions and the account rules remain the authority. */
export const ACCOUNT_STATUS_ENABLED: boolean =
  import.meta.env?.VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED === '1';

/** Proposed local-review/sandbox mount; mounting it is a separately authorized change (never config.urls). */
export const ACCOUNT_STATUS_ROUTE_ROOT = '/api/v1/admin/school-accounts/';
