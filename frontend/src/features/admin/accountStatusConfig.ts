/** WF-02.05 (D-69): the Account directory and its status controls. Off unless the build sets
 * VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED=1. Django's own default-off WORKSPACE_ACCOUNT_STATUS_ENABLED
 * gate, the exact effective permissions and the account rules remain the authority. */
export const ACCOUNT_STATUS_ENABLED: boolean =
  import.meta.env?.VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED === '1';

/** Independent read-only directory/detail/history integration; never enables a status POST. */
export const ACCOUNT_DIRECTORY_ENABLED: boolean = ACCOUNT_STATUS_ENABLED ||
  import.meta.env?.VITE_WORKSPACE_ACCOUNT_DIRECTORY_ENABLED === '1';

/** Normal read-only mount; status POSTs remain local-review/sandbox only. */
export const ACCOUNT_STATUS_ROUTE_ROOT = '/api/v1/admin/school-accounts/';
