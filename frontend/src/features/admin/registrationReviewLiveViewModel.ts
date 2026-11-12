/** AR-6C7E.1: UI-only decisions. Backend is always the authority. */
import type {
  PendingRegistrationItem,
  RegistrationReviewAction,
  RegistrationReviewRole,
} from './registrationReviewApiContract.ts';

export const REGISTRATION_READ = 'accounts.registration_requests.read';
export const REGISTRATION_APPROVE = 'accounts.registration_requests.approve';
export const REGISTRATION_REJECT = 'accounts.registration_requests.reject';

export type PageRoleFilter = 'All' | RegistrationReviewRole;

/** Role names and session permission hints affect presentation only. */
export function mayShowReviewPanel(
  roles: readonly string[],
  permissions: readonly string[],
  apiEnabled: boolean,
): boolean {
  return apiEnabled && roles.includes('Admin') && permissions.includes(REGISTRATION_READ);
}

export function mayShowDecision(
  permissions: readonly string[],
  action: RegistrationReviewAction,
): boolean {
  if (!permissions.includes(REGISTRATION_READ)) return false;
  return action === 'approve' ? permissions.includes(REGISTRATION_APPROVE)
    : action === 'reject' && permissions.includes(REGISTRATION_REJECT);
}

/** The API has only page/status query parameters. These filters apply to the current page. */
export function filterCurrentPage(
  rows: readonly PendingRegistrationItem[],
  schoolIdSearch: string,
  role: PageRoleFilter,
): PendingRegistrationItem[] {
  const term = schoolIdSearch.trim().toLowerCase();
  return rows.filter((row) => (role === 'All' || row.requested_role === role)
    && row.school_id.toLowerCase().includes(term));
}

/** Never display arbitrary response/error text from an unknown server or proxy. */
export function safeReviewError(error: unknown): string {
  const code = error && typeof error === 'object' && 'code' in error
    ? (error as { code?: unknown }).code : undefined;
  switch (code) {
    case 'review_unavailable': return 'Registration Review is not available yet.';
    case 'authentication_required': return 'Your session has expired. Sign in again.';
    case 'access_denied': return 'You no longer have permission to complete this action.';
    case 'request_unavailable': return 'This request may have been processed or is no longer available. Refresh the list.';
    case 'rate_limited': return 'Too many requests. Try again later.';
    case 'invalid_response': return 'The server returned an unexpected response. Please refresh.';
    default: return 'The result could not be confirmed. Refresh the list before trying again.';
  }
}
