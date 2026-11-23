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

/** WF-02.03 (D-46): the approval panel inside the WF-02.02 detail. Off unless the build sets
 * VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED=1, and then shown only to a session reporting the
 * approve permission. Approval is served only by the loopback local-review mode and the sandbox;
 * config.urls has no approve route, so a normal deployment answers 404/503 regardless. */
export const APPLICANT_APPROVAL_ENABLED: boolean =
  import.meta.env?.VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED === '1';

/** WF-02.04 (D-59, D-62): the rejection section inside the WF-02.02 detail. Off unless the build
 * sets VITE_WORKSPACE_REGISTRATION_REJECTION_ENABLED=1, and then shown only to a session reporting
 * the reject permission. Like approval it is served only by local review mode and the sandbox. */
export const APPLICANT_REJECTION_ENABLED: boolean =
  import.meta.env?.VITE_WORKSPACE_REGISTRATION_REJECTION_ENABLED === '1';

/** WF-02.03/02.04 bulk decisions stay off until the detached backend endpoint and release gates are approved. */
export const BULK_APPLICANT_DECISIONS_ENABLED: boolean =
  import.meta.env?.VITE_WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED === '1';
