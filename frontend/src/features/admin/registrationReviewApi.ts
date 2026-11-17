/** AR-6C7D.2: guarded typed adapter for the existing, currently UNMOUNTED review API.
 * DO NOT import into the dashboard or turn on this gate before separate approvals.
 */
import { ApiError, postJSON } from '../../api/client.ts';
import {
  buildPendingReviewRequest,
  buildReviewDecisionRequest,
  parsePendingRegistrationPage,
  parseRegistrationReviewDecision,
  parseRegistrationReviewError,
} from './registrationReviewApiContract.ts';
import type {
  PendingApplicationsQuery,
  PendingRegistrationPage,
  RegistrationReviewDecisionResult,
  RegistrationReviewRejectionCode,
} from './registrationReviewApiContract.ts';
import { REGISTRATION_REVIEW_LIVE_API_ENABLED } from './registrationReviewApiGate.ts';
import { PENDING_APPLICATIONS_LIST_ENABLED, PENDING_APPLICATIONS_ROUTE_ROOT } from './pendingApplicationsConfig.ts';
import { notifyAuthenticationRequired } from '../../utils/sessionSignals.ts';

function requireApprovedActivation(): void {
  if (!REGISTRATION_REVIEW_LIVE_API_ENABLED) {
    throw new ApiError('Registration review is not activated.', 503, 'review_unavailable');
  }
}

async function getReviewJSON(path: string): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, {
      method: 'GET',
      credentials: 'same-origin',
      cache: 'no-store',
      headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(15_000),
    });
  } catch {
    throw new ApiError('Unable to connect to the registration review service.', 0, 'network_error');
  }
  let value: unknown;
  try {
    value = await response.json();
  } catch {
    throw new ApiError('The server returned an unexpected response.', response.status, 'invalid_response');
  }
  if (!response.ok) {
    const { code, message } = parseRegistrationReviewError(response.status, value);
    // WF-01.04 P-04: 401 means the session is gone; 403 is a permission denial and never signs anyone out.
    if (response.status === 401) notifyAuthenticationRequired();
    throw new ApiError(message, response.status, code);
  }
  return value;
}

/** No endpoint is hardcoded because registration_review_urls.py has no approved root mount. */
export async function listPendingRegistrationRequests(
  approvedRouteRoot: string,
  page = 1,
): Promise<PendingRegistrationPage> {
  requireApprovedActivation(); // MUST remain first: no fetch, CSRF request or path access while disabled.
  const plan = buildPendingReviewRequest(approvedRouteRoot, page);
  return parsePendingRegistrationPage(await getReviewJSON(plan.path));
}

/** WF-02.01: read-only list on the one mounted route. Its own gate; never the decision gate. */
export async function listPendingApplications(
  page = 1,
  query: PendingApplicationsQuery = {},
  enabled: boolean = PENDING_APPLICATIONS_LIST_ENABLED,
): Promise<PendingRegistrationPage> {
  // MUST remain first: no fetch or path access while the list is switched off.
  if (!enabled) throw new ApiError('Pending applications are not activated.', 503, 'review_unavailable');
  const plan = buildPendingReviewRequest(PENDING_APPLICATIONS_ROUTE_ROOT, page, query);
  return parsePendingRegistrationPage(await getReviewJSON(plan.path));
}

export async function approveRegistrationRequest(
  approvedRouteRoot: string,
  accountId: number,
): Promise<RegistrationReviewDecisionResult> {
  requireApprovedActivation();
  const plan = buildReviewDecisionRequest(approvedRouteRoot, accountId, 'approve');
  // Reuses the existing session + CSRF client; never retries an ambiguous POST.
  const value = await postJSON(plan.path, plan.body);
  return parseRegistrationReviewDecision(value, accountId, 'Approved');
}

export async function rejectRegistrationRequest(
  approvedRouteRoot: string,
  accountId: number,
  rejectionCode: RegistrationReviewRejectionCode,
): Promise<RegistrationReviewDecisionResult> {
  requireApprovedActivation();
  const plan = buildReviewDecisionRequest(approvedRouteRoot, accountId, 'reject', rejectionCode);
  const value = await postJSON(plan.path, plan.body);
  return parseRegistrationReviewDecision(value, accountId, 'Rejected');
}
