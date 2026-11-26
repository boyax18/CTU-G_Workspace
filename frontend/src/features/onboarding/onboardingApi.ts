/** Student Semester Onboarding and CTU-verification client: strict parsing, fixed error copy and
 * single-send POSTs (never retried). The server decides everything; nothing here infers enrollment.
 */
import { ApiError, initializeCSRF, timeoutSignal } from '../../api/client.ts';
import { notifyAuthenticationRequired } from '../../utils/sessionSignals.ts';
import {
  ENROLLMENT_VERIFICATION_ENABLED, HISTORICAL_PARTICIPATION_CORRECTION_ENABLED, ONBOARDING_ROUTE_ROOT,
  STUDENT_ONBOARDING_ENABLED, STUDENT_ONBOARDING_FINALIZATION_ENABLED, VERIFICATION_ROUTE_ROOT,
} from './onboardingConfig.ts';

export type OnboardingState = 'no_active_semester' | 'clearance_required' | 'gap_verification_required' | 'history_unverified'
  | 'evidence_conflict' | 'onboarding' | 'pending_verification' | 'completed';
export type StudentType = 'Regular' | 'Irregular';
export interface PeriodRef { semester_id: number; label: string; status: string; school_year_label: string;
  start_date: string | null; end_date: string | null }
export interface CourseRef { course_id: number; code: string; name: string }
export interface Option { offering_id: number; subject: { subject_id: number; code: string; title: string; lecture_units: string | null;
  lab_units: string | null }; section: { section_id: number; name: string; year_level: number; course_code: string };
  instructor: string | null; ready_for_confirmation: boolean }
export interface Draft { status: 'Draft' | 'PendingVerification' | 'Completed' | null; student_type: StudentType | null;
  course: CourseRef | null; year_level: number | null; subjects: Option[]; subjects_confirmed: boolean; course_confirmed: boolean;
  version: number | null; next_step: 1 | 2 | 3 | 4 }
export interface Eligibility { status: string; basis: string; previous_semester: PeriodRef | null; missing_gaps: PeriodRef[];
  older_uncleared: PeriodRef[] }
export interface Requirement { kind: 'subject_instructor' | 'treasurer_fee' | 'school_admin_final'; status: 'Pending' | 'Signed';
  subject: { code: string; title: string } | null; signatory: string | null }
export interface Clearance { status: 'Uncleared' | 'Cleared'; requirements: Requirement[]; pending_count: number }
export interface Fee { amount: string; currency: 'PHP'; status: string }
export interface Result { participation_id: number; student_type: StudentType; course: CourseRef; year_level: number;
  subjects: { subject_id: number; code: string; title: string; section: string; instructor: string | null }[];
  clearance: Clearance | null; fee: Fee | null }
export interface Status { state: OnboardingState; semester: PeriodRef | null; dashboard_unlocked: boolean;
  student: { ctug_id: string; full_name: string | null } | null; finalization_enabled: boolean;
  eligibility: Eligibility | null; correction_instructions: string; previous_clearance: { semester: PeriodRef; clearance: Clearance | null;
    fee: Fee | null } | null; onboarding: Draft | null; prefill: { course_id: number; year_level: number; source: string } | null;
  verified_record_available: boolean; result: Result | null; outcome: string | null }
export interface ContextCourse extends CourseRef { year_levels: number[]; sections: { section_id: number; name: string; year_level: number }[] }
export interface Review { semester: PeriodRef; student: { ctug_id: string; full_name: string | null }; onboarding: Draft;
  fee: { revision_id: number; amount: string; currency: 'PHP' } | null; verification: 'verified' | 'mismatch' | 'not_recorded';
  mismatched: string[]; blockers: string[]; can_confirm: boolean; correction_instructions: string }

// ---- Errors --------------------------------------------------------------------------------------

export interface OnboardingErrorDetail { status: number; code: string; reason: string; state: string; fields: Record<string, string> }
export class OnboardingApiError extends ApiError {
  detail: OnboardingErrorDetail;
  constructor(message: string, detail: OnboardingErrorDetail, outcomeUnknown = false) {
    super(message, detail.status, detail.code, {}, { outcomeUnknown });
    this.name = 'OnboardingApiError';
    this.detail = detail;
  }
}

export const REASON_TEXT: Record<string, string> = {
  no_active_semester: 'There is no active semester right now.',
  semester_changed: 'The active semester changed. Start onboarding for the current semester.',
  already_completed: 'You already completed onboarding for this semester.',
  stale_version: 'Your onboarding changed in another window. Reload and try again.',
  type_required: 'Choose Regular or Irregular first.',
  subjects_required: 'Confirm your subjects and your course and year level first.',
  subjects_changed: 'Your subjects no longer match your course or year level. Confirm your subjects again.',
  subject_unavailable: 'A selected subject is no longer offered this semester. Confirm your subjects again.',
  instructor_unassigned: 'A selected subject has no assigned instructor yet. Visit the School Admin in person.',
  duplicate_subject: 'Choose each subject only once.',
  section_mismatch: 'The selected subjects do not belong to your course, year level or section.',
  incomplete_section: 'Regular students confirm every subject prepared for their section. Confirm the full list again.',
  course_unavailable: 'This course is not available. Visit the School Admin in person.',
  fee_unavailable: 'The semester fee is not approved yet. Try again later.',
  fee_changed: 'The semester fee changed. Review it again before confirming.',
  eligibility_blocked: 'Onboarding is not available until the previous requirement is resolved.',
  confirmation_required: 'Confirm your onboarding to continue.',
  finalization_conflict: 'Your onboarding could not be completed. Reload and try again.',
  // School Admin verification and historical correction
  period_not_open: 'Records can be verified only for an Active, Closed or Archived semester.',
  period_not_historical: 'Only a Closed or Archived semester can be used here.',
  evidence_changed: 'The verified record changed. Reload and try again.',
  participation_exists: 'The student already has a finalized participation for this semester.',
  evidence_in_use: 'This record supports a finalized participation and cannot be revoked.',
  gap_conflict: 'A verified non-enrollment gap exists for this semester.',
  evidence_conflict: 'A verified enrollment record exists for this semester.',
  already_revoked: 'This record is already revoked.',
  self_verification: 'You cannot verify or change your own enrollment records.',
  evidence_required: 'Record the verified CTU enrollment for this semester first.',
  subjects_mismatch: 'The offerings must match the verified subjects exactly.',
  historical_fee_unavailable: 'The semester has no approved original fee, so no obligation can be created.',
  correction_conflict: 'The correction could not be applied. Reload and try again.',
};
const CONFLICT_CODES = new Set(['onboarding_conflict', 'verification_conflict', 'historical_correction_conflict']);
const UNAVAILABLE_CODES = new Set(['student_onboarding_unavailable', 'verification_unavailable', 'historical_correction_unavailable']);
const FIELDS = ['student_type', 'course_id', 'year_level', 'section_id', 'offering_ids', 'expected_version', 'expected_fee_revision_id',
  'confirmed', 'student_account_id', 'semester_id', 'entry_classification', 'subject_ids', 'source_reference', 'source_as_of',
  'expected_evidence_id', 'reason_code', 'reason_note', 'q'];
const FIELD_TEXT: Record<string, string> = {
  source_reference: 'Enter the CTU record reference (3 to 80 letters, digits, spaces, . - / #).',
  source_as_of: 'Enter a valid date that is not in the future.',
  reason_note: 'Explain the correction in 10 to 500 characters.',
  subject_ids: 'Choose 1 to 20 different subjects.',
  offering_ids: 'Choose 1 to 20 different offered subjects.',
};
const isRecord = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);

export function parseOnboardingError(status: number, body: unknown, unavailable = 'student_onboarding_unavailable'): OnboardingErrorDetail {
  const error = isRecord(body) && isRecord(body.error) ? body.error : {};
  const raw = typeof error.code === 'string' ? error.code : '';
  let code = ({ 400: 'invalid_request', 401: 'authentication_required', 403: 'access_denied', 404: 'not_found', 429: 'rate_limited' } as
    Record<number, string>)[status] ?? 'request_failed';
  if (status === 403 && raw === 'csrf_failed') code = 'csrf_failed';
  if (status === 409 && (CONFLICT_CODES.has(raw) || raw === 'onboarding_required')) code = raw;
  if (status === 503) code = raw === 'feature_disabled' ? 'feature_disabled' : UNAVAILABLE_CODES.has(raw) ? raw : unavailable;
  const reason = status === 409 && typeof error.reason === 'string' && error.reason in REASON_TEXT ? error.reason
    : status === 403 && (error.reason === 'student_context_required' || error.reason === 'admin_context_required') ? error.reason : '';
  const state = code === 'onboarding_required' && typeof error.state === 'string' && /^[a-z_]{1,40}$/.test(error.state) ? error.state : '';
  const fields: Record<string, string> = {};
  if (status === 400 && isRecord(error.fields)) {
    for (const name of FIELDS) {
      const values = error.fields[name];
      if (Array.isArray(values) && values.length) fields[name] = FIELD_TEXT[name] ?? 'Check this value.';
    }
  }
  return { status, code, reason, state, fields };
}

export function onboardingErrorText(error: unknown): string {
  const detail = error instanceof OnboardingApiError ? error.detail : null;
  if (!detail) return 'The request could not be completed. Reload and try again.';
  switch (detail.code) {
    case 'outcome_unknown': return 'We could not confirm the result. Reload to see the current state before trying again.';
    case 'authentication_required': return 'Your session has ended. Sign in again to continue.';
    case 'access_denied': return detail.reason === 'student_context_required' ? 'Switch to your Student role, then try again.'
      : detail.reason === 'admin_context_required' ? 'Switch to your School Admin role, then try again.'
        : 'Your current access does not include this action.';
    case 'csrf_failed': return 'Security check failed. Refresh the page and try again.';
    case 'feature_disabled': return 'This action is not enabled on the server.';
    case 'student_onboarding_unavailable': return 'Student Semester Onboarding is not available right now.';
    case 'verification_unavailable': return 'Official verification recording is not available right now.';
    case 'historical_correction_unavailable': return 'Historical participation correction is not available right now.';
    case 'onboarding_required': return 'Complete Student Semester Onboarding first.';
    case 'rate_limited': return 'Too many requests. Wait a minute, then try again.';
    case 'not_found': return 'The requested record is unavailable. Reload and try again.';
    case 'invalid_request': return 'Check the highlighted details.';
    default: return CONFLICT_CODES.has(detail.code)
      ? REASON_TEXT[detail.reason] ?? 'The change conflicts with the current records. Reload and try again.'
      : 'The request could not be completed. Reload and try again.';
  }
}

// ---- Transport ------------------------------------------------------------------------------------

const fail = (code: string, status = 503) => new OnboardingApiError('Unavailable.', { status, code, reason: '', state: '', fields: {} });
const unknown = () => new OnboardingApiError('We could not confirm the result.',
  { status: 0, code: 'outcome_unknown', reason: '', state: '', fields: {} }, true);

async function read(response: Response, mutation: boolean, unavailable: string): Promise<unknown> {
  let body: unknown;
  try { body = await response.json(); } catch {
    if (mutation && (response.ok || response.status >= 500)) throw unknown();
    throw fail('invalid_response', response.status);
  }
  if (!response.ok) {
    const detail = parseOnboardingError(response.status, body, unavailable);
    if (response.status === 401) notifyAuthenticationRequired();
    if (mutation && response.status >= 500 && detail.code !== 'feature_disabled' && !UNAVAILABLE_CODES.has(detail.code)) throw unknown();
    throw new OnboardingApiError('The request could not be completed.', detail);
  }
  return body;
}

interface Target { root: string; enabled: boolean; unavailable: string }
const STUDENT = (): Target => ({ root: ONBOARDING_ROUTE_ROOT, enabled: STUDENT_ONBOARDING_ENABLED, unavailable: 'student_onboarding_unavailable' });
const ADMIN = (): Target => ({ root: VERIFICATION_ROUTE_ROOT, enabled: ENROLLMENT_VERIFICATION_ENABLED, unavailable: 'verification_unavailable' });
const HISTORICAL = (): Target => ({ root: VERIFICATION_ROUTE_ROOT, enabled: HISTORICAL_PARTICIPATION_CORRECTION_ENABLED,
  unavailable: 'historical_correction_unavailable' });

export async function get(target: Target, suffix: string, query: Record<string, string | number> = {}): Promise<unknown> {
  if (!target.enabled) throw fail(target.unavailable); // MUST stay first: no request while switched off
  const params = new URLSearchParams(Object.entries(query).map(([k, v]) => [k, String(v)])).toString();
  let response: Response;
  try {
    response = await fetch(`${target.root}${suffix}${params ? `?${params}` : ''}`, { method: 'GET', credentials: 'same-origin',
      cache: 'no-store', headers: { Accept: 'application/json' }, signal: timeoutSignal() });
  } catch {
    throw fail('network_error', 0);
  }
  return read(response, false, target.unavailable);
}

export async function send(target: Target, suffix: string, body: unknown): Promise<unknown> {
  if (!target.enabled) throw fail(target.unavailable);
  const csrfToken = await initializeCSRF();
  let response: Response;
  try {
    response = await fetch(`${target.root}${suffix}`, { method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(body), signal: timeoutSignal() });
  } catch {
    throw unknown(); // never retried: the Student or School Admin reloads to see the real state
  }
  return read(response, true, target.unavailable);
}

// ---- Strict parsing -------------------------------------------------------------------------------

const invalid = () => fail('invalid_response', 0);
const rec = (v: unknown) => { if (!isRecord(v)) throw invalid(); return v; };
const id = (v: unknown) => { if (typeof v !== 'number' || !Number.isInteger(v) || v < 1) throw invalid(); return v; };
const int = (v: unknown, min: number, max: number) => {
  if (typeof v !== 'number' || !Number.isInteger(v) || v < min || v > max) throw invalid(); return v;
};
const text = (v: unknown, max = 200) => { if (typeof v !== 'string' || !v || v.length > max) throw invalid(); return v; };
const optText = (v: unknown, max = 200) => (v === null || v === undefined ? null : text(v, max));
const bool = (v: unknown) => v === true; // fail closed
const oneOf = <T extends string>(v: unknown, values: readonly T[]): T => {
  if (typeof v !== 'string' || !values.includes(v as T)) throw invalid(); return v as T;
};
const list = <T>(v: unknown, parse: (x: unknown) => T, max = 50): T[] => {
  if (!Array.isArray(v) || v.length > max) throw invalid(); return v.map(parse);
};
const AMOUNT = /^\d{1,6}\.\d{2}$/;
const amount = (v: unknown) => { if (typeof v !== 'string' || !AMOUNT.test(v)) throw invalid(); return v; };
const CODE = /^[a-z][a-z_]{0,59}$/;
const codes = (v: unknown) => list(v, (x) => { if (typeof x !== 'string' || !CODE.test(x)) throw invalid(); return x; }, 10);
const STATES = ['no_active_semester', 'clearance_required', 'gap_verification_required', 'history_unverified', 'evidence_conflict',
  'onboarding', 'pending_verification', 'completed'] as const;

export function parsePeriod(value: unknown): PeriodRef {
  const v = rec(value);
  return { semester_id: id(v.semester_id), label: text(v.label, 40), status: oneOf(v.status, ['Draft', 'Active', 'Closed', 'Archived'] as const),
    school_year_label: text(v.school_year_label, 20), start_date: optText(v.start_date, 10), end_date: optText(v.end_date, 10) };
}
const parseCourse = (value: unknown): CourseRef => {
  const v = rec(value); return { course_id: id(v.course_id), code: text(v.code, 20), name: optText(v.name, 150) ?? '' };
};
export function parseOption(value: unknown): Option {
  const v = rec(value); const s = rec(v.subject); const sec = rec(v.section);
  return { offering_id: id(v.offering_id),
    subject: { subject_id: id(s.subject_id), code: text(s.code, 20), title: text(s.title), lecture_units: optText(s.lecture_units, 6),
      lab_units: optText(s.lab_units, 6) },
    section: { section_id: id(sec.section_id), name: text(sec.name, 20), year_level: int(sec.year_level, 1, 6),
      course_code: text(sec.course_code, 20) },
    instructor: optText(v.instructor), ready_for_confirmation: bool(v.ready_for_confirmation) && v.instructor_assigned === true };
}
export function parseDraft(value: unknown): Draft {
  const v = rec(value);
  return { status: v.status === null ? null : oneOf(v.status, ['Draft', 'PendingVerification', 'Completed'] as const),
    student_type: v.student_type === null ? null : oneOf(v.student_type, ['Regular', 'Irregular'] as const),
    course: v.course === null ? null : parseCourse(v.course), year_level: v.year_level === null ? null : int(v.year_level, 1, 6),
    subjects: list(v.subjects, parseOption, 20), subjects_confirmed: bool(v.subjects_confirmed), course_confirmed: bool(v.course_confirmed),
    version: v.version === null ? null : id(v.version), next_step: int(v.next_step, 1, 4) as Draft['next_step'] };
}
const parseEligibility = (value: unknown): Eligibility => {
  const v = rec(value);
  return { status: text(v.status, 40), basis: typeof v.basis === 'string' ? v.basis : '',
    previous_semester: v.previous_semester === null ? null : parsePeriod(v.previous_semester),
    missing_gaps: list(v.missing_gaps, parsePeriod), older_uncleared: list(v.older_uncleared, parsePeriod) };
};
export function parseClearance(value: unknown): Clearance | null {
  if (value === null) return null;
  const v = rec(value);
  return { status: oneOf(v.status, ['Uncleared', 'Cleared'] as const), pending_count: int(v.pending_count, 0, 100),
    requirements: list(v.requirements, (item) => {
      const r = rec(item);
      return { kind: oneOf(r.kind, ['subject_instructor', 'treasurer_fee', 'school_admin_final'] as const),
        status: oneOf(r.status, ['Pending', 'Signed'] as const),
        subject: r.subject === null ? null : { code: text(rec(r.subject).code, 20), title: text(rec(r.subject).title) },
        signatory: optText(r.signatory) };
    }, 30) };
}
export function parseFee(value: unknown): Fee | null {
  if (value === null || value === undefined) return null;
  const v = rec(value);
  if (v.currency !== 'PHP') throw invalid();
  return { amount: amount(v.amount), currency: 'PHP', status: text(v.status, 20) };
}
export function parseResult(value: unknown): Result {
  const v = rec(value);
  return { participation_id: id(v.participation_id), student_type: oneOf(v.student_type, ['Regular', 'Irregular'] as const),
    course: parseCourse(v.course), year_level: int(v.year_level, 1, 6),
    subjects: list(v.subjects, (item) => {
      const s = rec(item);
      return { subject_id: id(s.subject_id), code: text(s.code, 20), title: text(s.title), section: text(s.section, 20),
        instructor: optText(s.instructor) };
    }, 20),
    clearance: parseClearance(v.clearance ?? null), fee: parseFee(v.fee) };
}
const parseStudent = (value: unknown) => {
  if (value === undefined || value === null) return null;
  const v = rec(value); return { ctug_id: text(v.ctug_id, 40), full_name: optText(v.full_name) };
};

export function parseStatus(value: unknown): Status {
  const v = rec(value);
  const features = isRecord(v.features) ? v.features : {};
  const previous = isRecord(v.previous_clearance) ? v.previous_clearance : null;
  const prefill = isRecord(v.prefill) ? v.prefill : null;
  return { state: oneOf(v.state, STATES), semester: v.semester ? parsePeriod(v.semester) : null,
    dashboard_unlocked: bool(v.dashboard_unlocked), student: parseStudent(v.student),
    finalization_enabled: bool(features.finalization_enabled) && STUDENT_ONBOARDING_FINALIZATION_ENABLED,
    eligibility: v.eligibility ? parseEligibility(v.eligibility) : null,
    correction_instructions: typeof v.correction_instructions === 'string' ? v.correction_instructions.slice(0, 500) : '',
    previous_clearance: previous ? { semester: parsePeriod(previous.semester), clearance: parseClearance(previous.clearance ?? null),
      fee: parseFee(previous.fee) } : null,
    onboarding: v.onboarding ? parseDraft(v.onboarding) : null,
    prefill: prefill ? { course_id: id(prefill.course_id), year_level: int(prefill.year_level, 1, 6),
      source: oneOf(prefill.source, ['verified_record', 'previous_semester'] as const) } : null,
    verified_record_available: bool(v.verified_record_available),
    result: v.result ? parseResult(v.result) : null,
    outcome: v.outcome === 'completed' || v.outcome === 'pending_verification' ? v.outcome : null };
}

export function parseReview(value: unknown): Review {
  const v = rec(value);
  const fee = v.fee === null ? null : rec(v.fee);
  if (fee && fee.currency !== 'PHP') throw invalid();
  return { semester: parsePeriod(v.semester), student: parseStudent(v.student) ?? { ctug_id: '', full_name: null },
    onboarding: parseDraft(v.onboarding),
    fee: fee ? { revision_id: id(fee.revision_id), amount: amount(fee.amount), currency: 'PHP' } : null,
    verification: oneOf(v.verification, ['verified', 'mismatch', 'not_recorded'] as const),
    mismatched: codes(v.mismatched), blockers: codes(v.blockers), can_confirm: bool(v.can_confirm),
    correction_instructions: typeof v.correction_instructions === 'string' ? v.correction_instructions.slice(0, 500) : '' };
}

// ---- Student operations (own records only; no student identifier is ever sent) ---------------------

export const getStatus = async () => parseStatus(await get(STUDENT(), 'status/'));
export async function getContext(): Promise<ContextCourse[]> {
  const v = rec(await get(STUDENT(), 'context/'));
  return list(v.courses, (item) => {
    const c = rec(item);
    return { ...parseCourse(c), year_levels: list(c.year_levels, (y) => int(y, 1, 6), 6),
      sections: list(c.sections, (s) => { const r = rec(s); return { section_id: id(r.section_id), name: text(r.name, 20),
        year_level: int(r.year_level, 1, 6) }; }, 100) };
  }, 100);
}
export async function getSubjectOptions(query: { course_id: number; year_level?: number; section_id?: number }) {
  const v = rec(await get(STUDENT(), 'subject-options/', query));
  return { options: list(v.options, parseOption, 200), complete: bool(v.complete) };
}
export const saveStudentType = async (studentType: StudentType, expectedVersion: number | null) =>
  parseStatus(await send(STUDENT(), 'type/', expectedVersion === null ? { student_type: studentType }
    : { student_type: studentType, expected_version: expectedVersion }));
export const confirmSubjects = async (body: { course_id: number; year_level: number; offering_ids: number[]; expected_version: number }) =>
  parseStatus(await send(STUDENT(), 'subjects/', body));
export const confirmCourse = async (body: { course_id: number; year_level: number; expected_version: number }) =>
  parseStatus(await send(STUDENT(), 'course/', body));
/** null when the server reports the onboarding already completed (the caller reloads the status). */
export async function getReview(): Promise<Review | null> {
  const v = rec(await get(STUDENT(), 'review/'));
  return v.state === 'completed' ? null : parseReview(v);
}
export async function finalizeOnboarding(review: Review): Promise<Status> {
  if (!STUDENT_ONBOARDING_FINALIZATION_ENABLED) throw fail('feature_disabled');
  if (!review.fee || review.onboarding.version === null) throw invalid();
  return parseStatus(await send(STUDENT(), 'finalize/', { expected_version: review.onboarding.version,
    expected_fee_revision_id: review.fee.revision_id, confirmed: true }));
}
export async function getMySemester() {
  const v = rec(await get(STUDENT(), 'my-semester/'));
  return { semester: parsePeriod(v.semester), result: parseResult(v.result) };
}
export async function getMyHistory() {
  const v = rec(await get(STUDENT(), 'my-history/'));
  return list(v.results, (item) => {
    const r = rec(item);
    return { semester: parsePeriod(r.semester), course_code: text(r.course_code, 20), year_level: int(r.year_level, 1, 6),
      clearance: parseClearance(r.clearance ?? null), fee: parseFee(r.fee) };
  }, 20);
}

// ---- School Admin operations ----------------------------------------------------------------------

export interface StudentRef { account_id: number; ctug_id: string; full_name: string | null }
export interface Evidence { evidence_id: number; semester_id: number; source_type: 'in_person' | 'ctu_integration';
  entry_classification: string; course: { course_id: number; code: string }; year_level: number; status: string; version: number;
  subjects: { subject_id: number; code: string; title: string }[]; verified_by: string }
export interface PeriodRecord { semester: PeriodRef; evidence: Evidence | null; gap: { gap_id: number; version: number } | null;
  participation: { participation_id: number; source: string } | null; clearance_status: string | null; fee: Fee | null;
  onboarding_status: string | null }

const parseStudentRef = (value: unknown): StudentRef => {
  const v = rec(value); return { account_id: id(v.account_id), ctug_id: text(v.ctug_id, 40), full_name: optText(v.full_name) };
};
export function parseEvidence(value: unknown): Evidence | null {
  if (value === null) return null;
  const v = rec(value); const c = rec(v.course);
  return { evidence_id: id(v.evidence_id), semester_id: id(v.semester_id),
    source_type: oneOf(v.source_type, ['in_person', 'ctu_integration'] as const),
    entry_classification: oneOf(v.entry_classification, ['continuing', 'returning', 'newcomer', 'transferee'] as const),
    course: { course_id: id(c.course_id), code: text(c.code, 20) }, year_level: int(v.year_level, 1, 6),
    status: text(v.status, 20), version: id(v.version),
    subjects: list(v.subjects, (s) => { const r = rec(s); return { subject_id: id(r.subject_id), code: text(r.code, 20), title: text(r.title) }; }, 20),
    verified_by: v.verified_by === 'A School Admin' ? 'A School Admin' : 'CTU integration' };
}
export async function searchStudents(q: string): Promise<StudentRef[]> {
  const v = rec(await get(ADMIN(), 'students/', q ? { q } : {}));
  return list(v.results, parseStudentRef, 20);
}
export async function getStudentRecord(studentId: number): Promise<{ student: StudentRef; periods: PeriodRecord[] }> {
  const v = rec(await get(ADMIN(), `students/${studentId}/`));
  return { student: parseStudentRef(v.student), periods: list(v.periods, (item) => {
    const r = rec(item); const gap = r.gap === null ? null : rec(r.gap); const p = r.participation === null ? null : rec(r.participation);
    return { semester: parsePeriod(r.semester), evidence: parseEvidence(r.evidence ?? null),
      gap: gap ? { gap_id: id(gap.gap_id), version: id(gap.version) } : null,
      participation: p ? { participation_id: id(p.participation_id), source: text(p.source, 30) } : null,
      clearance_status: optText(r.clearance_status, 20), fee: parseFee(r.fee), onboarding_status: optText(r.onboarding_status, 30) };
  }, 20) };
}
export interface EvidenceInput { student_account_id: number; semester_id: number; entry_classification: string; course_id: number;
  year_level: number; subject_ids: number[]; source_reference: string; source_as_of: string | null; expected_evidence_id: number | null }
export const recordEvidence = async (body: EvidenceInput) => parseEvidence(await send(ADMIN(), 'evidence/', body));
export const revokeEvidence = async (evidenceId: number, expectedVersion: number, reasonCode: string) =>
  send(ADMIN(), `evidence/${evidenceId}/revoke/`, { expected_version: expectedVersion, reason_code: reasonCode });
export const recordGap = async (body: { student_account_id: number; semester_id: number; source_reference: string }) =>
  send(ADMIN(), 'gaps/', body);
export const revokeGap = async (gapId: number, expectedVersion: number) => send(ADMIN(), `gaps/${gapId}/revoke/`, { expected_version: expectedVersion });

export interface HistoricalPreview { semester: PeriodRef; evidence: Evidence | null; options: Option[];
  fee: { revision_id: number; amount: string } | null; blockers: string[]; can_confirm: boolean }
export async function getHistoricalPreview(studentId: number, semesterId: number): Promise<HistoricalPreview> {
  const v = rec(await get(HISTORICAL(), 'historical-participation/', { student_account_id: studentId, semester_id: semesterId }));
  const fee = v.fee === null ? null : rec(v.fee);
  return { semester: parsePeriod(v.semester), evidence: parseEvidence(v.evidence ?? null), options: list(v.options, parseOption, 100),
    fee: fee ? { revision_id: id(fee.revision_id), amount: amount(fee.amount) } : null, blockers: codes(v.blockers),
    can_confirm: bool(v.can_confirm) };
}
export const correctHistoricalParticipation = async (body: { student_account_id: number; semester_id: number;
  expected_evidence_id: number; student_type: StudentType; offering_ids: number[]; reason_note: string }) =>
  send(HISTORICAL(), 'historical-participation/confirm/', { ...body, confirmed: true });

/** "1500.00" -> "₱1,500.00" from the exact string (display only; no floating-point arithmetic). */
export function peso(value: string): string {
  const [whole, fraction = '00'] = value.split('.');
  return `₱${whole.replace(/\B(?=(\d{3})+(?!\d))/g, ',')}.${fraction}`;
}
