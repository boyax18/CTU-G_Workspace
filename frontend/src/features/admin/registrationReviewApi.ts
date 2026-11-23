/** AR-6C7D.2: guarded typed adapter for the existing, currently UNMOUNTED review API.
 * DO NOT import into the dashboard or turn on this gate before separate approvals.
 */
import { ApiError, initializeCSRF, postJSON, timeoutSignal } from '../../api/client.ts';
import {
  buildApplicantDetailRequest,
  buildApprovalRequest,
  buildBulkRegistrationDecisionRequest,
  buildPendingReviewRequest,
  buildRejectionRequest,
  buildReviewDecisionRequest,
  parseApplicantDetail,
  parseApprovalRefusal,
  parseBulkRegistrationDecision,
  parsePendingRegistrationPage,
  parseRegistrationReviewDecision,
  parseRegistrationReviewError,
  parseRejectionDecision,
  parseRejectionRefusal,
} from './registrationReviewApiContract.ts';
import type {
  ApplicantDetail,
  BulkRegistrationDecisionResult,
  EligibilitySource,
  PendingApplicationsQuery,
  PendingRegistrationPage,
  RegistrationReviewDecisionResult,
  RegistrationReviewRejectionCode,
  RejectionDecisionResult,
} from './registrationReviewApiContract.ts';
import { REGISTRATION_REVIEW_LIVE_API_ENABLED } from './registrationReviewApiGate.ts';
import {
  BULK_APPLICANT_DECISIONS_ENABLED,
  APPLICANT_APPROVAL_ENABLED,
  APPLICANT_REJECTION_ENABLED,
  PENDING_APPLICATIONS_LIST_ENABLED,
  PENDING_APPLICATIONS_ROUTE_ROOT,
} from './pendingApplicationsConfig.ts';
import { notifyAuthenticationRequired } from '../../utils/sessionSignals.ts';
import { availableActions } from './managementAvailability.ts';

function requireApprovedActivation(): void {
  if (!REGISTRATION_REVIEW_LIVE_API_ENABLED) {
    throw new ApiError('Registration review is not activated.', 503, 'review_unavailable');
  }
}

async function getReviewJSON(path: string, onResponse?: (response: Response) => void): Promise<unknown> {
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
  onResponse?.(response);
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
  let actions: string[] = [];
  const data = parsePendingRegistrationPage(
    await getReviewJSON(plan.path, (response) => { actions = availableActions(response); }),
  );
  return { ...data, available_actions: actions };
}

const bulkUncertain = () => new ApiError(
  'We could not confirm all selected outcomes. Do not submit the batch again; refresh the list and review each application.',
  0, 'outcome_unknown', {}, { outcomeUnknown: true },
);

/** WF-02.03/02.04 bulk decision; one same-origin CSRF POST, never automatically retried. */
export async function decideBulkApplications(
  accountIds: readonly number[],
  action: 'approve' | 'reject',
  rejectionCode?: RegistrationReviewRejectionCode,
  enabled: boolean = BULK_APPLICANT_DECISIONS_ENABLED,
): Promise<BulkRegistrationDecisionResult> {
  if (!enabled) throw new ApiError('Bulk applicant decisions are not activated.', 503, 'review_unavailable');
  const plan = buildBulkRegistrationDecisionRequest(
    PENDING_APPLICATIONS_ROUTE_ROOT, accountIds, action, rejectionCode,
  );
  const csrfToken = await initializeCSRF();
  let response: Response;
  try {
    response = await fetch(plan.path, {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(plan.body), signal: timeoutSignal(),
    });
  } catch {
    throw bulkUncertain();
  }
  let value: unknown;
  try {
    value = await response.json();
  } catch {
    if (response.ok || response.status >= 500) throw bulkUncertain();
    value = null;
  }
  if (response.ok) {
    try {
      return parseBulkRegistrationDecision(value, accountIds, action);
    } catch {
      throw bulkUncertain();
    }
  }
  const { code, message } = parseRegistrationReviewError(response.status, value);
  if (response.status >= 500 && !(response.status === 503 && code === 'review_unavailable')) {
    throw bulkUncertain();
  }
  if (response.status === 401) notifyAuthenticationRequired();
  throw new ApiError(message, response.status, code);
}

/** WF-02.02: one application, read-only, behind the same read switch (D-37). GET only. */
export async function getPendingApplication(
  accountId: number,
  enabled: boolean = PENDING_APPLICATIONS_LIST_ENABLED,
): Promise<ApplicantDetail> {
  // MUST remain first: no fetch or path access while the read switch is off.
  if (!enabled) throw new ApiError('Pending applications are not activated.', 503, 'review_unavailable');
  const plan = buildApplicantDetailRequest(PENDING_APPLICATIONS_ROUTE_ROOT, accountId);
  let actions: string[] = [];
  const value = await getReviewJSON(plan.path, (response) => { actions = availableActions(response); });
  return { ...parseApplicantDetail(value, accountId), available_actions: actions };
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

const uncertain = () => new ApiError(
  'We could not confirm whether the application was approved. Reload it to check its status before doing anything else.',
  0, 'outcome_unknown', {}, { outcomeUnknown: true },
);

/** WF-02.03: approve ONE application with the reviewer's attestation (D-45). POST, never retried.
 *
 * Definite refusals keep their codes: 409 `email_unverified` / `eligibility_unconfirmed` (D-47),
 * 404 `request_unavailable`, 400/401/403/429 and a 503 `review_unavailable` envelope (each is
 * answered before any write or after a rolled-back transaction). Anything that might have been
 * applied (no response after sending, another 5xx, or a reply that is not exactly the expected
 * decision) is `outcome_unknown`: the caller must re-read the application, never resend (D-48).
 */
export async function approveApplication(
  accountId: number,
  source: EligibilitySource,
  enabled: boolean = APPLICANT_APPROVAL_ENABLED,
): Promise<RegistrationReviewDecisionResult> {
  // MUST remain first: no CSRF request, fetch or path access while the approval switch is off.
  if (!enabled) throw new ApiError('Approval is not activated.', 503, 'review_unavailable');
  const plan = buildApprovalRequest(PENDING_APPLICATIONS_ROUTE_ROOT, accountId, source);
  const csrfToken = await initializeCSRF(); // fails before anything is sent: a definite non-approval
  let response: Response;
  try {
    response = await fetch(plan.path, {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(plan.body), signal: timeoutSignal(),
    });
  } catch {
    throw uncertain();
  }
  let value: unknown = null;
  try {
    value = await response.json();
  } catch {
    if (response.ok || response.status >= 500) throw uncertain();
  }
  if (response.ok) {
    try {
      return parseRegistrationReviewDecision(value, accountId, 'Approved');
    } catch {
      throw uncertain();
    }
  }
  if (response.status === 409) {
    throw new ApiError('Approval is not allowed for this application.', 409, parseApprovalRefusal(value) ?? 'approval_not_allowed');
  }
  const { code, message } = parseRegistrationReviewError(response.status, value);
  if (response.status >= 500 && !(response.status === 503 && code === 'review_unavailable')) throw uncertain();
  if (response.status === 401) notifyAuthenticationRequired();
  throw new ApiError(message, response.status, code);
}

const rejectionUncertain = () => new ApiError(
  'We could not confirm whether the application was rejected. Reload it to check its status before doing anything else.',
  0, 'outcome_unknown', {}, { outcomeUnknown: true },
);

/** WF-02.04: reject ONE application with one fixed reason (D-56). POST, never retried.
 *
 * Success requires the exact {account_id, status: "Rejected", notification: "queued"} reply: the
 * email is queued, never reported as delivered (D-54). Definite refusals keep their codes: 409
 * `recipient_unverified` / `direct_permissions` / `protected_history` (D-55, D-58), 404, 400, 401,
 * 403, 429 and a 503 `review_unavailable` envelope. Anything that might have been applied is
 * `outcome_unknown`, and the caller must re-read the application instead of sending again.
 */
export async function rejectApplication(
  accountId: number,
  code: RegistrationReviewRejectionCode,
  enabled: boolean = APPLICANT_REJECTION_ENABLED,
): Promise<RejectionDecisionResult> {
  // MUST remain first: no CSRF request, fetch or path access while the rejection switch is off.
  if (!enabled) throw new ApiError('Rejection is not activated.', 503, 'review_unavailable');
  const plan = buildRejectionRequest(PENDING_APPLICATIONS_ROUTE_ROOT, accountId, code);
  const csrfToken = await initializeCSRF(); // fails before anything is sent: a definite non-rejection
  let response: Response;
  try {
    response = await fetch(plan.path, {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(plan.body), signal: timeoutSignal(),
    });
  } catch {
    throw rejectionUncertain();
  }
  let value: unknown = null;
  try {
    value = await response.json();
  } catch {
    if (response.ok || response.status >= 500) throw rejectionUncertain();
  }
  if (response.ok) {
    try {
      return parseRejectionDecision(value, accountId);
    } catch {
      throw rejectionUncertain();
    }
  }
  if (response.status === 409) {
    throw new ApiError('Rejection is not allowed for this application.', 409, parseRejectionRefusal(value) ?? 'rejection_not_allowed');
  }
  const { code: errorCode, message } = parseRegistrationReviewError(response.status, value);
  if (response.status >= 500 && !(response.status === 503 && errorCode === 'review_unavailable')) throw rejectionUncertain();
  if (response.status === 401) notifyAuthenticationRequired();
  throw new ApiError(message, response.status, errorCode);
}
