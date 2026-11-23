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

// ---- WF-02.02 Verify and review applicant information (read-only detail) ----

export type EmailEvidenceState = 'verified' | 'no_proof' | 'address_changed' | 'no_email';
export type ApplicantDataNote = 'missing_profile' | 'missing_first_name' | 'missing_last_name';

export interface ApplicantDetail {
  account_id: number;
  school_id: string;
  id_label: 'CTU-G ID';
  name: { first: string | null; middle: string | null; last: string | null; suffix: string | null };
  full_name: string | null;
  /** D-38: the full address, shown only in this authorized detail. */
  email: string | null;
  requested_role: RegistrationReviewRole;
  request_status: 'Pending';
  created_at: string;
  email_evidence: { state: EmailEvidenceState; verified_at: string | null };
  institutional_check: { subject: 'enrollment' | 'employment'; verified_by_workspace: false };
  data_notes: ApplicantDataNote[];
}

const EVIDENCE_STATES: readonly EmailEvidenceState[] = ['verified', 'no_proof', 'address_changed', 'no_email'];
const DATA_NOTES: readonly ApplicantDataNote[] = ['missing_profile', 'missing_first_name', 'missing_last_name'];
const ID_LABEL: ApplicantDetail['id_label'] = 'CTU-G ID';
const SUBJECT: Record<RegistrationReviewRole, ApplicantDetail['institutional_check']['subject']> = {
  Student: 'enrollment', Instructor: 'employment',
};

/** The `applicant` query value as an account ID, or null when it is not a valid ID. */
export function parseApplicantId(raw: string | null): number | null {
  if (typeof raw !== 'string' || !/^[1-9][0-9]{0,9}$/.test(raw)) return null;
  const id = Number(raw);
  return isAccountId(id) ? id : null;
}

/** GET-only plan for one application. The ID is validated before any request. */
export function buildApplicantDetailRequest(root: string, accountId: number): PendingReviewRequestPlan {
  const base = validateRoot(root);
  assertAccountId(accountId);
  return { method: 'GET', path: `${base}${accountId}/` };
}

const optionalText = (value: unknown, max: number): value is string | null =>
  value === null || (typeof value === 'string' && value.length >= 1 && value.length <= max);

/** Strict parser: exact keys and consistent values; any extra field (password, token…) is refused. */
export function parseApplicantDetail(value: unknown, expectedId: number): ApplicantDetail {
  assertAccountId(expectedId);
  const fail = () => { throw new Error(INVALID_RESPONSE); };
  if (!isRecord(value) || !hasExactKeys(value, ['account_id', 'school_id', 'id_label', 'name', 'full_name', 'email',
    'requested_role', 'request_status', 'created_at', 'email_evidence', 'institutional_check', 'data_notes'])) fail();
  const v = value as Record<string, unknown>;
  const role = v.requested_role;
  if (v.account_id !== expectedId || role !== 'Student' && role !== 'Instructor') fail();
  const r = role as RegistrationReviewRole;
  if (typeof v.school_id !== 'string' || v.school_id.length < 1 || v.school_id.length > 50
    || v.id_label !== ID_LABEL || v.request_status !== 'Pending' || !isServerTimestamp(v.created_at)
    || !optionalText(v.full_name, 400) || !optionalText(v.email, 150)
    || (typeof v.email === 'string' && !v.email.includes('@'))) fail();
  const name = v.name;
  if (!isRecord(name) || !hasExactKeys(name, ['first', 'middle', 'last', 'suffix'])
    || !optionalText(name.first, 100) || !optionalText(name.middle, 100)
    || !optionalText(name.last, 100) || !optionalText(name.suffix, 20)) fail();
  const evidence = v.email_evidence;
  if (!isRecord(evidence) || !hasExactKeys(evidence, ['state', 'verified_at'])
    || typeof evidence.state !== 'string' || !EVIDENCE_STATES.includes(evidence.state as EmailEvidenceState)) fail();
  const state = (evidence as Record<string, unknown>).state as EmailEvidenceState;
  const verifiedAt = (evidence as Record<string, unknown>).verified_at;
  if (state === 'verified' ? !isServerTimestamp(verifiedAt) : verifiedAt !== null) fail();
  if ((state === 'no_email') !== (v.email === null)) fail();
  const check = v.institutional_check;
  if (!isRecord(check) || !hasExactKeys(check, ['subject', 'verified_by_workspace'])
    || check.subject !== SUBJECT[r] || check.verified_by_workspace !== false) fail();
  const notes = v.data_notes;
  if (!Array.isArray(notes) || new Set(notes).size !== notes.length
    || notes.some((note) => !DATA_NOTES.includes(note as ApplicantDataNote))) fail();
  const n = name as Record<string, string | null>;
  return {
    account_id: expectedId,
    school_id: v.school_id as string,
    id_label: ID_LABEL,
    name: { first: n.first, middle: n.middle, last: n.last, suffix: n.suffix },
    full_name: v.full_name as string | null,
    email: v.email as string | null,
    requested_role: r,
    request_status: 'Pending',
    created_at: v.created_at as string,
    email_evidence: { state, verified_at: verifiedAt as string | null },
    institutional_check: { subject: SUBJECT[r], verified_by_workspace: false },
    data_notes: notes as ApplicantDataNote[],
  };
}

// ---- WF-02.03 Approve applicant account (D-44, D-45, D-47) ----

export type EligibilitySource = 'ctu_main_system_records' | 'institutional_employment_records';
export type ApprovalRefusalReason = 'email_unverified' | 'eligibility_unconfirmed';

/** D-45: the ONE fixed source a reviewer may cite for each requested role. */
export const ELIGIBILITY_SOURCE_FOR_ROLE: Readonly<Record<RegistrationReviewRole, EligibilitySource>> = {
  Student: 'ctu_main_system_records',
  Instructor: 'institutional_employment_records',
};
export const ELIGIBILITY_SOURCE_LABELS: Readonly<Record<EligibilitySource, string>> = {
  ctu_main_system_records: 'CTU main system enrollment records',
  institutional_employment_records: 'Institutional employment records',
};

export interface ApprovalRequestPlan {
  method: 'POST';
  path: string;
  body: { eligibility_confirmed: true; eligibility_source: EligibilitySource };
}

/** POST plan carrying ONLY the reviewer's attestation; the role is never sent (the server decides it). */
export function buildApprovalRequest(root: string, accountId: number, source: EligibilitySource): ApprovalRequestPlan {
  const base = validateRoot(root);
  assertAccountId(accountId);
  if (source !== 'ctu_main_system_records' && source !== 'institutional_employment_records') {
    throw new Error('Choose the institutional source you checked.');
  }
  return { method: 'POST', path: `${base}${accountId}/approve/`, body: { eligibility_confirmed: true, eligibility_source: source } };
}

/** D-47: a 409 refusal carries one fixed reason; anything else is not a recognised refusal. */
export function parseApprovalRefusal(value: unknown): ApprovalRefusalReason | null {
  if (!isRecord(value) || !hasExactKeys(value, ['error']) || !isRecord(value.error)) return null;
  const error = value.error;
  if (error.code !== 'approval_not_allowed') return null;
  return error.reason === 'email_unverified' || error.reason === 'eligibility_unconfirmed' ? error.reason : null;
}

// ---- WF-02.04 Reject applicant (D-54, D-55 revised, D-56, D-58) ----

export type RejectionRefusalReason = 'recipient_unverified' | 'direct_permissions' | 'protected_history';

/** D-56: the exact public wording the applicant receives for each fixed code (backend REJECTION_LABELS). */
export const REJECTION_PUBLIC_LABELS: Readonly<Record<RegistrationReviewRejectionCode, string>> = {
  incomplete_submission: 'Incomplete registration information',
  ineligible_registration: 'Registration eligibility could not be confirmed',
  identity_mismatch: 'Registration identity could not be verified',
  duplicate_request: 'Duplicate registration request',
};

export interface RejectionRequestPlan {
  method: 'POST';
  path: string;
  body: { rejection_code: RegistrationReviewRejectionCode };
}

export interface RejectionDecisionResult {
  account_id: number;
  status: 'Rejected';
  /** D-54: the email is queued in the same transaction; delivery is never claimed. */
  notification: 'queued';
}

/** POST plan carrying only one fixed reason code; never free text. */
export function buildRejectionRequest(root: string, accountId: number, code: RegistrationReviewRejectionCode): RejectionRequestPlan {
  const base = validateRoot(root);
  assertAccountId(accountId);
  if (typeof code !== 'string' || !REGISTRATION_REJECTION_CODES.includes(code)) {
    throw new Error('Choose one of the four rejection reasons.');
  }
  return { method: 'POST', path: `${base}${accountId}/reject/`, body: { rejection_code: code } };
}

/** The server must confirm this exact rejection AND that its email was queued. */
export function parseRejectionDecision(value: unknown, expectedId: number): RejectionDecisionResult {
  assertAccountId(expectedId);
  if (!isRecord(value) || !hasExactKeys(value, ['account_id', 'status', 'notification'])
    || value.account_id !== expectedId || value.status !== 'Rejected' || value.notification !== 'queued') {
    throw new Error(INVALID_RESPONSE);
  }
  return { account_id: expectedId, status: 'Rejected', notification: 'queued' };
}

/** D-58: a 409 conflict carries one fixed reason; anything else is not a recognised conflict. */
export function parseRejectionRefusal(value: unknown): RejectionRefusalReason | null {
  if (!isRecord(value) || !hasExactKeys(value, ['error']) || !isRecord(value.error)) return null;
  const error = value.error;
  if (error.code !== 'rejection_not_allowed') return null;
  return error.reason === 'recipient_unverified' || error.reason === 'direct_permissions' || error.reason === 'protected_history'
    ? error.reason : null;
}
