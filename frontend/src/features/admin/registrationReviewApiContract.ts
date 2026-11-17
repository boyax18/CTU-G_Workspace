/** AR-6C7D.2 typed contract for the Django review API; WF-02.01 adds the read-only list fields. */
export type RegistrationReviewRole = 'Student' | 'Instructor';
export type PendingApplicationProofFilter = 'verified' | 'legacy';
export type PendingApplicationSort = 'submitted' | '-submitted' | 'school_id' | '-school_id';
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
  /** WF-02.01 D-32: registered name from the profile, or null when none was recorded. */
  full_name: string | null;
  requested_role: RegistrationReviewRole;
  created_at: string;
  /** WF-02.01 D-34: proof recorded for the address now on file. False is never "verified". */
  email_verified: boolean;
}

export interface PendingRegistrationPage {
  results: PendingRegistrationItem[];
  page: number;
  page_size: 20;
  /** WF-02.01 D-33: the server looked one row ahead; no total count is disclosed. */
  has_next: boolean;
}

/** WF-02.01 D-33: server-side search, filters and sort. Omitted values use server defaults. */
export interface PendingApplicationsQuery {
  q?: string;
  role?: RegistrationReviewRole;
  proof?: PendingApplicationProofFilter;
  sort?: PendingApplicationSort;
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

export const PENDING_APPLICATION_SORTS: readonly PendingApplicationSort[] = ['submitted', '-submitted', 'school_id', '-school_id'];
export const PENDING_APPLICATION_SEARCH_MAX = 50;
const MAX_SEARCH_TERMS = 5;
const MAX_NAME_LENGTH = 400;
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

/** Trimmed search text the server accepts, or '' for none. Throws for anything else. */
export function normalizePendingSearch(value: string): string {
  if (typeof value !== 'string') throw new Error('Search must be text.');
  const term = value.trim();
  if (!term) return '';
  if (term.length > PENDING_APPLICATION_SEARCH_MAX || !/^[\x20-\x7E]+$/.test(term)
    || term.split(/\s+/).length > MAX_SEARCH_TERMS) {
    throw new Error(`Use up to ${PENDING_APPLICATION_SEARCH_MAX} letters, digits or punctuation (no accents), in at most ${MAX_SEARCH_TERMS} words.`);
  }
  return term;
}

/** GET-only plan. Backend accepts page/status plus the WF-02.01 q/role/proof/sort fields. */
export function buildPendingReviewRequest(
  root: string,
  page = 1,
  query: PendingApplicationsQuery = {},
): PendingReviewRequestPlan {
  const base = validateRoot(root);
  assertPageNumber(page);
  const raw: unknown = query; // callers from plain JS may pass anything
  if (!isRecord(raw) || Object.keys(raw).some((key) => !['q', 'role', 'proof', 'sort'].includes(key))) {
    throw new Error('Unsupported pending-application query.');
  }
  const params = new URLSearchParams({ page: String(page), status: 'Pending' });
  if (query.q !== undefined) {
    const term = normalizePendingSearch(query.q);
    if (term) params.set('q', term);
  }
  if (query.role !== undefined) {
    if (query.role !== 'Student' && query.role !== 'Instructor') throw new Error('Unsupported requested role.');
    params.set('role', query.role);
  }
  if (query.proof !== undefined) {
    if (query.proof !== 'verified' && query.proof !== 'legacy') throw new Error('Unsupported email-proof filter.');
    params.set('proof', query.proof);
  }
  if (query.sort !== undefined) {
    if (!PENDING_APPLICATION_SORTS.includes(query.sort)) throw new Error('Unsupported sort.');
    params.set('sort', query.sort);
  }
  // %20 rather than '+' so the encoding is unambiguous for every server.
  return { method: 'GET', path: `${base}?${params.toString().replace(/\+/g, '%20')}` };
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

/** Strict server-response parser: no email, tokens or hashes in list data; any extra field is refused. */
export function parsePendingRegistrationPage(value: unknown): PendingRegistrationPage {
  if (!isRecord(value) || !hasExactKeys(value, ['results', 'page', 'page_size', 'has_next'])) {
    throw new Error(INVALID_RESPONSE);
  }
  const { results, page, page_size: pageSize, has_next: hasNext } = value;
  if (!Array.isArray(results) || results.length > PAGE_SIZE || pageSize !== PAGE_SIZE
    || typeof hasNext !== 'boolean' || (hasNext && results.length !== PAGE_SIZE)) {
    throw new Error(INVALID_RESPONSE);
  }
  try {
    assertPageNumber(page);
  } catch {
    throw new Error(INVALID_RESPONSE);
  }
  const seen = new Set<number>();
  const items: PendingRegistrationItem[] = results.map((item: unknown) => {
    if (!isRecord(item)
      || !hasExactKeys(item, ['account_id', 'school_id', 'full_name', 'requested_role', 'created_at', 'email_verified'])
      || !isAccountId(item.account_id)
      || typeof item.school_id !== 'string' || item.school_id.length < 1 || item.school_id.length > 50
      || !(item.full_name === null || (typeof item.full_name === 'string'
        && item.full_name.length >= 1 && item.full_name.length <= MAX_NAME_LENGTH))
      || typeof item.requested_role !== 'string' || !['Student', 'Instructor'].includes(item.requested_role)
      || !isServerTimestamp(item.created_at)
      || typeof item.email_verified !== 'boolean'
      || seen.has(item.account_id)) {
      throw new Error(INVALID_RESPONSE);
    }
    seen.add(item.account_id);
    return {
      account_id: item.account_id,
      school_id: item.school_id,
      full_name: item.full_name as string | null,
      requested_role: item.requested_role as RegistrationReviewRole,
      created_at: item.created_at,
      email_verified: item.email_verified,
    };
  });
  return { results: items, page: page as number, page_size: PAGE_SIZE, has_next: hasNext };
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
