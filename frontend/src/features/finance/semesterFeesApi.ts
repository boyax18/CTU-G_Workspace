/** Semester fee client: strict parsing, fixed error copy, single-send POSTs (never retried). */
import { ApiError, initializeCSRF, timeoutSignal } from '../../api/client.ts';
import { notifyAuthenticationRequired } from '../../utils/sessionSignals.ts';
import { SEMESTER_FEE_APPROVAL_ENABLED, SEMESTER_FEE_CONFIGURATION_ENABLED, SEMESTER_FEES_ROUTE_ROOT } from './semesterFeesConfig.ts';

export type FeeState = 'not_configured' | 'draft' | 'approved' | 'approved_with_draft';
export type RevisionStatus = 'Draft' | 'Approved' | 'Superseded' | 'Withdrawn';
export interface SemesterRef { semester_id: number; term: 'first' | 'second'; label: string; status: string;
  school_year_id: number; school_year_label: string }
export interface Revision { revision_id: number; revision_number: number; currency: 'PHP'; amount: string; status: RevisionStatus;
  version: number; change_reason: string | null; configured_by: string | null; configured_at: string | null;
  approved_by: string | null; approved_at: string | null; superseded_at: string | null; withdrawn_at: string | null }
export interface Readiness { key: 'approved_fee'; status: 'ready' | 'missing' | 'unavailable'; reason: string }
export interface Features { configuration: boolean; approval: boolean }
export interface SemesterFee { semester: SemesterRef; state: FeeState; current_approved: Revision | null; draft: Revision | null;
  revisions: Revision[]; editable: boolean; reason_required: boolean; readiness: Readiness; features: Features }
export interface SemesterFeeSummary { semester: SemesterRef; state: FeeState; approved_amount: string | null;
  current_revision_number: number | null }
export interface Impact { status: 'not_applicable' | 'evaluated' | 'unavailable'; count: number | null; reason: string }
export interface ApprovalPreview { semester: SemesterRef; proposed: Revision | null; current_approved: Revision | null; impact: Impact;
  warnings: string[]; blockers: string[]; feature_enabled: boolean; can_confirm: boolean }
export interface HistoryEntry { event: string; occurred_at: string | null; actor: string | null }

// ---- Errors --------------------------------------------------------------------------------

export interface FeeErrorDetail { status: number; code: string; reason: string; fields: Record<string, string> }
export class FeeApiError extends ApiError {
  detail: FeeErrorDetail;
  constructor(message: string, detail: FeeErrorDetail, outcomeUnknown = false) {
    super(message, detail.status, detail.code, {}, { outcomeUnknown });
    this.name = 'FeeApiError';
    this.detail = detail;
  }
}

export const REASON_TEXT: Record<string, string> = {
  period_closed: 'Closed and Archived semesters keep their fee history; it cannot be changed here.',
  draft_exists: 'This semester already has a Draft fee. Edit it instead.',
  no_draft: 'There is no Draft fee to change or approve. Reload and try again.',
  stale_version: 'This fee was changed by someone else. Reload and try again.',
  no_change: 'Nothing changed.',
  reason_required: 'Explain why the approved fee is being revised.',
  approved_changed: 'The approved fee changed. Review it again.',
  confirmation_required: 'Confirm the approval to continue.',
  zero_confirmation_required: 'Confirm that the full fee for this semester is ₱0.00.',
  warnings_changed: 'The warnings changed. Review them again.',
  impact_unavailable: 'The effect on existing student fee obligations cannot be checked yet, so this revision cannot be approved.',
  obligations_assessed: 'Student fee obligations already use the approved fee. A financial adjustment process is required.',
  transition_conflict: 'The change could not be applied. Reload and try again.',
};
const FIELD_TEXT = new Set(['Enter the full fee in pesos, from 0.00 to 100,000.00, with up to two decimal places.',
  'Explain the change in 10 to 500 characters.', 'Reload and try again.', 'Review the warnings again.',
  'Confirm the zero amount explicitly.', 'Enter the fee amount. ₱0.00 must be entered explicitly.']);
const FIELDS = ['amount', 'change_reason', 'expected_draft_version', 'expected_version', 'revision_id',
  'expected_current_approved_revision_id', 'acknowledged_warnings', 'confirm_zero_amount'];
const CODES: Record<number, string> = { 400: 'invalid_request', 401: 'authentication_required', 403: 'access_denied', 404: 'not_found',
  409: 'fee_conflict', 429: 'rate_limited', 503: 'semester_fees_unavailable' };
const isRecord = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);

export function parseFeeError(status: number, body: unknown): FeeErrorDetail {
  const error = isRecord(body) && isRecord(body.error) ? body.error : {};
  let code = CODES[status] ?? 'request_failed';
  if (status === 403 && error.code === 'csrf_failed') code = 'csrf_failed';
  if (status === 503 && error.code === 'feature_disabled') code = 'feature_disabled';
  let reason = '';
  if (status === 409 && typeof error.reason === 'string' && error.reason in REASON_TEXT) reason = error.reason;
  if (status === 403 && error.reason === 'admin_context_required') reason = 'admin_context_required';
  const fields: Record<string, string> = {};
  if (status === 400 && isRecord(error.fields)) {
    for (const name of FIELDS) {
      const values = error.fields[name];
      if (Array.isArray(values) && values.length) {
        fields[name] = typeof values[0] === 'string' && FIELD_TEXT.has(values[0]) ? values[0] : 'Check this value.';
      }
    }
  }
  return { status, code, reason, fields };
}

export function feeErrorText(error: unknown): string {
  const detail = error instanceof FeeApiError ? error.detail : null;
  if (!detail) return 'The request could not be completed. Reload and try again.';
  switch (detail.code) {
    case 'outcome_unknown': return 'We could not confirm the change. Reload to see the current state before trying again.';
    case 'authentication_required': return 'Your session has ended. Sign in again to continue.';
    case 'access_denied': return detail.reason === 'admin_context_required'
      ? 'Switch to your School Admin role, then try again.'
      : 'Setting the semester fee is a School Admin responsibility and needs a fee-setting permission that your access does not include.';
    case 'csrf_failed': return 'Security check failed. Refresh the page and try again.';
    case 'feature_disabled': return 'Fee approval is not enabled on the server.';
    case 'semester_fees_unavailable': return 'Semester fee configuration is not available right now.';
    case 'rate_limited': return 'Too many requests. Wait a minute, then try again.';
    case 'not_found': return 'This semester is no longer available. Reload the list.';
    case 'fee_conflict': return REASON_TEXT[detail.reason] ?? 'The change conflicts with the current fee. Reload and try again.';
    case 'invalid_request': return 'Check the highlighted details.';
    default: return 'The request could not be completed. Reload and try again.';
  }
}

// ---- Transport -----------------------------------------------------------------------------

const off = () => new FeeApiError('Semester fees are not available.', { status: 503, code: 'semester_fees_unavailable', reason: '', fields: {} });
const unknown = () => new FeeApiError('We could not confirm the change.', { status: 0, code: 'outcome_unknown', reason: '', fields: {} }, true);

async function read(response: Response, mutation: boolean): Promise<unknown> {
  let body: unknown;
  try { body = await response.json(); } catch {
    if (mutation && (response.ok || response.status >= 500)) throw unknown();
    throw new FeeApiError('Unexpected response.', { status: response.status, code: 'invalid_response', reason: '', fields: {} });
  }
  if (!response.ok) {
    const detail = parseFeeError(response.status, body);
    if (response.status === 401) notifyAuthenticationRequired();
    if (mutation && response.status >= 500 && detail.code !== 'feature_disabled' && detail.code !== 'semester_fees_unavailable') throw unknown();
    throw new FeeApiError('The request could not be completed.', detail);
  }
  return body;
}

export async function feeGet(suffix: string, enabled = SEMESTER_FEE_CONFIGURATION_ENABLED): Promise<unknown> {
  if (!enabled) throw off(); // MUST stay first: no request while switched off
  let response: Response;
  try {
    response = await fetch(`${SEMESTER_FEES_ROUTE_ROOT}${suffix}`, { method: 'GET', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json' }, signal: timeoutSignal() });
  } catch {
    throw new FeeApiError('Unable to connect.', { status: 0, code: 'network_error', reason: '', fields: {} });
  }
  return read(response, false);
}

export async function feePost(suffix: string, body: unknown, enabled = SEMESTER_FEE_CONFIGURATION_ENABLED): Promise<unknown> {
  if (!enabled) throw off();
  const csrfToken = await initializeCSRF();
  let response: Response;
  try {
    response = await fetch(`${SEMESTER_FEES_ROUTE_ROOT}${suffix}`, { method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(body), signal: timeoutSignal() });
  } catch {
    throw unknown();
  }
  return read(response, true);
}

// ---- Strict parsing ------------------------------------------------------------------------

const invalid = () => new FeeApiError('Unexpected response.', { status: 0, code: 'invalid_response', reason: '', fields: {} });
const rec = (v: unknown) => { if (!isRecord(v)) throw invalid(); return v; };
const id = (v: unknown) => { if (typeof v !== 'number' || !Number.isInteger(v) || v < 1) throw invalid(); return v; };
const optText = (v: unknown, max = 500) => { if (v === null) return null; if (typeof v !== 'string' || !v || v.length > max) throw invalid(); return v; };
const oneOf = <T extends string>(v: unknown, values: readonly T[]): T => { if (typeof v !== 'string' || !values.includes(v as T)) throw invalid(); return v as T; };
const AMOUNT = /^\d{1,6}\.\d{2}$/;
const amount = (v: unknown) => { if (typeof v !== 'string' || !AMOUNT.test(v)) throw invalid(); return v; };
const CODE = /^[a-z][a-z_]{0,59}$/;
const codes = (v: unknown) => {
  if (!Array.isArray(v) || v.length > 10 || !v.every((x) => typeof x === 'string' && CODE.test(x))) throw invalid();
  return v as string[];
};
const STATES = ['not_configured', 'draft', 'approved', 'approved_with_draft'] as const;

function parseSemester(value: unknown): SemesterRef {
  const v = rec(value);
  return { semester_id: id(v.semester_id), term: oneOf(v.term, ['first', 'second'] as const), label: optText(v.label, 40) ?? '',
    status: oneOf(v.status, ['Draft', 'Active', 'Closed', 'Archived'] as const), school_year_id: id(v.school_year_id),
    school_year_label: optText(v.school_year_label, 20) ?? '' };
}

export function parseRevision(value: unknown): Revision {
  const v = rec(value);
  if (v.currency !== 'PHP') throw invalid();
  return { revision_id: id(v.revision_id), revision_number: id(v.revision_number), currency: 'PHP', amount: amount(v.amount),
    status: oneOf(v.status, ['Draft', 'Approved', 'Superseded', 'Withdrawn'] as const), version: id(v.version),
    change_reason: optText(v.change_reason), configured_by: optText(v.configured_by, 40), configured_at: optText(v.configured_at, 40),
    approved_by: optText(v.approved_by, 40), approved_at: optText(v.approved_at, 40), superseded_at: optText(v.superseded_at, 40),
    withdrawn_at: optText(v.withdrawn_at, 40) };
}

const parseFeatures = (value: unknown): Features => {
  const v = isRecord(value) ? value : {};
  return { configuration: v.configuration === true, approval: v.approval === true }; // fail closed
};

export function parseSemesterFee(value: unknown): SemesterFee {
  const v = rec(value); const r = rec(v.readiness);
  if (!Array.isArray(v.revisions) || typeof v.editable !== 'boolean' || typeof v.reason_required !== 'boolean') throw invalid();
  const current = v.current_approved === null ? null : parseRevision(v.current_approved);
  const draft = v.draft === null ? null : parseRevision(v.draft);
  if ((current && current.status !== 'Approved') || (draft && draft.status !== 'Draft')) throw invalid();
  return { semester: parseSemester(v.semester), state: oneOf(v.state, STATES), current_approved: current, draft,
    revisions: v.revisions.map(parseRevision), editable: v.editable, reason_required: v.reason_required,
    readiness: { key: 'approved_fee', status: oneOf(r.status, ['ready', 'missing', 'unavailable'] as const),
      reason: typeof r.reason === 'string' && r.reason.length <= 60 ? r.reason : '' },
    features: parseFeatures(v.features) };
}

export function parsePreview(value: unknown): ApprovalPreview {
  const v = rec(value); const i = rec(v.impact);
  if (typeof v.feature_enabled !== 'boolean' || typeof v.can_confirm !== 'boolean') throw invalid();
  const status = oneOf(i.status, ['not_applicable', 'evaluated', 'unavailable'] as const);
  const count = status === 'evaluated' ? (typeof i.count === 'number' && Number.isInteger(i.count) && i.count >= 0 ? i.count : NaN) : null;
  if (Number.isNaN(count)) throw invalid();
  return { semester: parseSemester(v.semester), proposed: v.proposed === null ? null : parseRevision(v.proposed),
    current_approved: v.current_approved === null ? null : parseRevision(v.current_approved),
    impact: { status, count, reason: typeof i.reason === 'string' ? i.reason : '' }, warnings: codes(v.warnings),
    blockers: codes(v.blockers), feature_enabled: v.feature_enabled, can_confirm: v.can_confirm };
}

// ---- Operations ----------------------------------------------------------------------------

export async function listSemesterFees() {
  const v = rec(await feeGet(''));
  if (!Array.isArray(v.results)) throw invalid();
  return { results: v.results.map((item): SemesterFeeSummary => {
    const r = rec(item);
    return { semester: parseSemester(r.semester), state: oneOf(r.state, STATES),
      approved_amount: r.approved_amount === null ? null : amount(r.approved_amount),
      current_revision_number: r.current_revision_number === null ? null : id(r.current_revision_number) };
  }), features: parseFeatures(v.features) };
}
export const getSemesterFee = async (semesterId: number) => parseSemesterFee(await feeGet(`${semesterId}/`));
export const saveDraft = async (semesterId: number, body: { amount: string; expected_draft_version: number | null; change_reason?: string }) =>
  parseSemesterFee(await feePost(`${semesterId}/draft/`, body));
export const withdrawDraft = async (semesterId: number, expectedDraftVersion: number) =>
  parseSemesterFee(await feePost(`${semesterId}/draft/withdraw/`, { expected_draft_version: expectedDraftVersion }));
export const getApprovalPreview = async (semesterId: number) => parsePreview(await feeGet(`${semesterId}/approval/`));
export async function approveFee(semesterId: number, preview: ApprovalPreview, confirmZero: boolean,
  enabled = SEMESTER_FEE_APPROVAL_ENABLED): Promise<SemesterFee> {
  if (!enabled) throw new FeeApiError('Fee approval is not enabled.', { status: 503, code: 'feature_disabled', reason: '', fields: {} });
  if (!preview.proposed) throw invalid();
  return parseSemesterFee(await feePost(`${semesterId}/approval/`, {
    revision_id: preview.proposed.revision_id, expected_version: preview.proposed.version,
    expected_current_approved_revision_id: preview.current_approved?.revision_id ?? null,
    acknowledged_warnings: [...preview.warnings], confirmed: true, confirm_zero_amount: confirmZero }, enabled));
}
export async function getFeeHistory(semesterId: number): Promise<HistoryEntry[]> {
  const v = rec(await feeGet(`${semesterId}/history/`));
  if (!Array.isArray(v.results)) throw invalid();
  return v.results.map((item) => {
    const r = rec(item);
    return { event: optText(r.event, 60) ?? '', occurred_at: optText(r.occurred_at, 40),
      actor: r.actor === 'You' || r.actor === 'An administrator' ? r.actor : null };
  });
}

/** Client-side mirror of the server's amount rule (early feedback only): explicit, exact, bounded. */
export function normalizeAmount(raw: string): string | null {
  const text = raw.trim();
  if (!/^\d{1,6}(\.\d{1,2})?$/.test(text)) return null;
  const [whole, fraction = ''] = text.split('.');
  const value = `${String(Number(whole))}.${fraction.padEnd(2, '0')}`;
  const [w, f] = value.split('.');
  if (Number(w) > 100000 || (Number(w) === 100000 && f !== '00')) return null;
  return value;
}

/** "1500.00" -> "₱1,500.00" from the exact string (display only; no floating-point arithmetic). */
export function peso(amount: string): string {
  const [whole, fraction = '00'] = amount.split('.');
  return `₱${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${fraction}`;
}
