/** WF-02.01 (D-31): read-only pending-applications list.
 *
 * Off unless the build sets VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED=1. Django's own
 * WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED gate and permission checks remain the authority;
 * this switch only decides whether the dashboard view calls the API at all.
 * It never enables approve/reject, which stay behind REGISTRATION_REVIEW_LIVE_API_ENABLED.
 */
export const PENDING_APPLICATIONS_LIST_ENABLED: boolean =
  import.meta.env?.VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED === '1';

/** The only review route mounted in config/urls.py (GET only). */
export const PENDING_APPLICATIONS_ROUTE_ROOT = '/api/v1/admin/registration-requests/';
