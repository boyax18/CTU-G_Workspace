/** AR-6C7D.2: offline, typed contract matched to the unmounted Django review API. */
export type RegistrationReviewRole = 'Student' | 'Instructor';
export type RegistrationReviewStatus = 'Approved' | 'Rejected';
export type RegistrationReviewAction = 'approve' | 'reject';
export type RegistrationReviewRejectionCode =
  | 'incomplete_submission'
  | 'ineligible_registration'
  | 'identity_mismatch'
  | 'duplicate_request';

export interface PendingRegistrationItem {
  account_id: number;
  school_id: string;
  requested_role: RegistrationReviewRole;
  created_at: string;
}

export interface PendingRegistrationPage {
  results: PendingRegistrationItem[];
  page: number;
  page_size: 20;
}

export interface RegistrationReviewDecisionResult {
  account_id: number;
  status: RegistrationReviewStatus;
}

export interface PendingReviewRequestPlan {
  method: 'GET';
  path: string;
}

export interface RegistrationReviewDecisionPlan {
  method: 'POST';
  path: string;
  body: Record<string, never> | { rejection_code: RegistrationReviewRejectionCode };
}

export const REGISTRATION_REJECTION_CODES: readonly RegistrationReviewRejectionCode[] = [
  'incomplete_submission',
  'ineligible_registration',
  'identity_mismatch',
  'duplicate_request',
];

const MAX_ACCOUNT_ID = 2_147_483_647;
const PAGE_SIZE = 20;
const INVALID_RESPONSE = 'The registration review server returned an unexpected response.';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function hasExactKeys(value: Record<string, unknown>, expected: readonly string[]): boolean {
  const keys = Object.keys(value);
  return keys.length === expected.length && keys.every((key) => expected.includes(key));
}

function isAccountId(value: unknown): value is number {
  return typeof value === 'number' && Number.isInteger(value) && value >= 1 && value <= MAX_ACCOUNT_ID;
}

function assertAccountId(value: unknown): asserts value is number {
  if (!isAccountId(value)) throw new Error('Invalid registration review account ID.');
}

function assertPageNumber(value: unknown): asserts value is number {
  if (typeof value !== 'number' || !Number.isInteger(value) || value < 1 || value > 10_000) {
    throw new Error('Registration review page must be an integer from 1 to 10000.');
  }
}

function validateRoot(root: string): string {
  // No approved URL mount exists yet. Future callers must explicitly supply the reviewed route prefix.
  if (typeof root !== 'string' || !/^\/api\/(?:[A-Za-z0-9_-]+\/)+$/.test(root)) {
    throw new Error('An approved, same-origin API route prefix is required.');
  }
  return root;
}

function isServerTimestamp(value: unknown): value is string {
  return typeof value === 'string'
    && /^\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)$/.test(value)
    && Number.isFinite(Date.parse(value));
}

/** GET-only plan. Backend accepts only page/status and returns twenty or fewer results. */
export function buildPendingReviewRequest(root: string, page = 1): PendingReviewRequestPlan {
  const base = validateRoot(root);
  assertPageNumber(page);
  return { method: 'GET', path: `${base}?page=${page}&status=Pending` };
}

/** Plans exactly the existing approve/reject relative paths; never sends a request. */
export function buildReviewDecisionRequest(
  root: string,
  accountId: number,
  action: RegistrationReviewAction,
  rejectionCode?: RegistrationReviewRejectionCode,
): RegistrationReviewDecisionPlan {
  const base = validateRoot(root);
  assertAccountId(accountId);
  if (action === 'approve') {
    if (rejectionCode !== undefined) throw new Error('Approval must not include a rejection reason.');
    return { method: 'POST', path: `${base}${accountId}/approve/`, body: {} };
  }
  if (action === 'reject') {
    if (typeof rejectionCode !== 'string' || !REGISTRATION_REJECTION_CODES.includes(rejectionCode)) {
      throw new Error('Choose one of the four approved rejection codes.');
    }
    return { method: 'POST', path: `${base}${accountId}/reject/`, body: { rejection_code: rejectionCode } };
  }
  throw new Error('Unsupported registration review action.');
}

/** Strict server-response parser: no status, email, names, tokens or hashes in list data. */
export function parsePendingRegistrationPage(value: unknown): PendingRegistrationPage {
  if (!isRecord(value) || !hasExactKeys(value, ['results', 'page', 'page_size'])) {
    throw new Error(INVALID_RESPONSE);
  }
  const { results, page, page_size: pageSize } = value;
  if (!Array.isArray(results) || results.length > PAGE_SIZE || pageSize !== PAGE_SIZE) {
    throw new Error(INVALID_RESPONSE);
  }
  try {
    assertPageNumber(page);
  } catch {
    throw new Error(INVALID_RESPONSE);
  }
  const seen = new Set<number>();
  const items: PendingRegistrationItem[] = results.map((item: unknown) => {
    if (!isRecord(item) || !hasExactKeys(item, ['account_id', 'school_id', 'requested_role', 'created_at'])
      || !isAccountId(item.account_id)
      || typeof item.school_id !== 'string' || item.school_id.length < 1 || item.school_id.length > 50
      || typeof item.requested_role !== 'string' || !['Student', 'Instructor'].includes(item.requested_role)
      || !isServerTimestamp(item.created_at)
      || seen.has(item.account_id)) {
      throw new Error(INVALID_RESPONSE);
    }
    seen.add(item.account_id);
    return {
      account_id: item.account_id,
      school_id: item.school_id,
      requested_role: item.requested_role as RegistrationReviewRole,
      created_at: item.created_at,
    };
  });
  return { results: items, page: page as number, page_size: PAGE_SIZE };
}

/** Server confirms one exact account ID and one expected decision; no optimistic success. */
export function parseRegistrationReviewDecision(
  value: unknown,
  expectedId: number,
  expectedStatus: RegistrationReviewStatus,
): RegistrationReviewDecisionResult {
  assertAccountId(expectedId);
  if (expectedStatus !== 'Approved' && expectedStatus !== 'Rejected') throw new Error(INVALID_RESPONSE);
  if (!isRecord(value) || !hasExactKeys(value, ['account_id', 'status'])
    || value.account_id !== expectedId || value.status !== expectedStatus) {
    throw new Error(INVALID_RESPONSE);
  }
  return { account_id: expectedId, status: expectedStatus };
}

/** Stable, non-sensitive error interpretation for the GET adapter. */
export function parseRegistrationReviewError(status: number, value: unknown): { code: string; message: string } {
  const errors: Record<number, { code: string; message: string }> = {
    400: { code: 'invalid_request', message: 'Check the request data.' },
    401: { code: 'authentication_required', message: 'Sign in to continue.' },
    403: { code: 'access_denied', message: 'You cannot perform this action.' },
    404: { code: 'request_unavailable', message: 'Registration request is unavailable.' },
    405: { code: 'method_not_allowed', message: 'Method not supported.' },
    406: { code: 'not_acceptable', message: 'Request JSON.' },
    415: { code: 'unsupported_media_type', message: 'Send JSON.' },
    429: { code: 'rate_limited', message: 'Too many attempts. Try later.' },
    503: { code: 'review_unavailable', message: 'Registration review is unavailable.' },
  };
  const fallback = { code: 'request_failed', message: 'Request failed.' };
  const chosen = errors[status] ?? fallback;
  // Error data must match the expected backend envelope, but never display arbitrary server strings.
  if (!isRecord(value) || !isRecord(value.error) || typeof value.error.code !== 'string') return chosen;
  return value.error.code === chosen.code ? chosen : fallback;
}
