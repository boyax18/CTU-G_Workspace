/** WF-11.01 academic-period contract: strict response parsing, request builders and the
 * client-side mirror of the server's date rules (for early feedback only; Django decides). */
import { ApiError } from '../../api/client.ts';

export type SemesterStatus = 'Draft' | 'Active' | 'Closed' | 'Archived';
export type SchoolYearStatus = 'Draft' | 'Active' | 'Between semesters' | 'Completed' | 'Archived';
export type SemesterTerm = 'first' | 'second';
export type ActivationRequirement = 'valid_dates' | 'approved_fee' | 'academic_offerings';

export interface Semester {
  semester_id: number;
  term: SemesterTerm;
  label: string;
  status: SemesterStatus;
  start_date: string | null;
  end_date: string | null;
  version: number;
  can_edit_dates: boolean;
  activation: { available: boolean; missing: ActivationRequirement[] };
  updated_at: string | null;
}

export interface SchoolYear {
  school_year_id: number;
  start_year: number;
  end_year: number;
  label: string;
  status: SchoolYearStatus;
  semesters: Semester[];
  can_delete: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface SchoolYearPage {
  results: SchoolYear[];
  page: number;
  page_size: number;
  has_next: boolean;
}

export interface DatesRequest {
  start_date: string | null;
  end_date: string | null;
  expected_version: number;
  acknowledge_cross_year_overlap?: boolean;
}

export const MIN_START_YEAR = 2000;
export const MAX_START_YEAR = 2100;
const SEMESTER_STATUSES: readonly string[] = ['Draft', 'Active', 'Closed', 'Archived'];
const YEAR_STATUSES: readonly string[] = ['Draft', 'Active', 'Between semesters', 'Completed', 'Archived'];
const REQUIREMENTS: readonly string[] = ['valid_dates', 'approved_fee', 'academic_offerings'];
const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;
const MAX_ID = 2_147_483_647;

const invalid = () => new ApiError('The server returned an unexpected response.', 0, 'invalid_response');
const isRecord = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value);
const isId = (value: unknown): value is number => typeof value === 'number' && Number.isInteger(value) && value >= 1 && value <= MAX_ID;
const isText = (value: unknown, max = 100): value is string => typeof value === 'string' && value.length > 0 && value.length <= max;
const isStamp = (value: unknown): value is string | null => value === null || isText(value, 40);

/** A real calendar date in strict YYYY-MM-DD form (rejects 2026-02-30). */
export function isIsoDate(value: unknown): value is string {
  if (typeof value !== 'string' || !ISO_DATE.test(value)) return false;
  const [y, m, d] = value.split('-').map(Number);
  const date = new Date(Date.UTC(y, m - 1, d));
  return date.getUTCFullYear() === y && date.getUTCMonth() === m - 1 && date.getUTCDate() === d;
}

const isOptionalDate = (value: unknown): value is string | null => value === null || isIsoDate(value);

function parseSemester(value: unknown): Semester {
  if (!isRecord(value) || !isRecord(value.activation)) throw invalid();
  const { activation } = value;
  if (!isId(value.semester_id) || (value.term !== 'first' && value.term !== 'second') || !isText(value.label)
    || typeof value.status !== 'string' || !SEMESTER_STATUSES.includes(value.status)
    || !isOptionalDate(value.start_date) || !isOptionalDate(value.end_date) || !isId(value.version)
    || typeof value.can_edit_dates !== 'boolean' || typeof activation.available !== 'boolean'
    || !Array.isArray(activation.missing) || activation.missing.length > REQUIREMENTS.length
    || !activation.missing.every((item) => typeof item === 'string' && REQUIREMENTS.includes(item))
    || !isStamp(value.updated_at)) {
    throw invalid();
  }
  return {
    semester_id: value.semester_id, term: value.term, label: value.label, status: value.status as SemesterStatus,
    start_date: value.start_date, end_date: value.end_date, version: value.version, can_edit_dates: value.can_edit_dates,
    activation: { available: activation.available, missing: [...activation.missing] as ActivationRequirement[] },
    updated_at: value.updated_at,
  };
}

export function parseSchoolYear(value: unknown): SchoolYear {
  if (!isRecord(value) || !Array.isArray(value.semesters) || value.semesters.length !== 2) throw invalid();
  const { start_year: start, end_year: end } = value;
  if (!isId(value.school_year_id) || typeof start !== 'number' || !Number.isInteger(start)
    || start < MIN_START_YEAR || start > MAX_START_YEAR || end !== start + 1 || !isText(value.label, 20)
    || typeof value.status !== 'string' || !YEAR_STATUSES.includes(value.status)
    || typeof value.can_delete !== 'boolean' || !isStamp(value.created_at) || !isStamp(value.updated_at)) {
    throw invalid();
  }
  const semesters = value.semesters.map(parseSemester);
  if (semesters[0].term !== 'first' || semesters[1].term !== 'second') throw invalid();
  return {
    school_year_id: value.school_year_id, start_year: start, end_year: end as number, label: value.label,
    status: value.status as SchoolYearStatus, semesters, can_delete: value.can_delete,
    created_at: value.created_at, updated_at: value.updated_at,
  };
}

export function parseSchoolYearPage(value: unknown, page: number): SchoolYearPage {
  if (!isRecord(value) || !Array.isArray(value.results) || value.page !== page || value.page_size !== 20
    || typeof value.has_next !== 'boolean' || value.results.length > 20) {
    throw invalid();
  }
  return { results: value.results.map(parseSchoolYear), page, page_size: 20, has_next: value.has_next };
}

export function parseDeletion(value: unknown, schoolYearId: number): void {
  if (!isRecord(value) || value.deleted !== true || value.school_year_id !== schoolYearId) throw invalid();
}

// ---- Request builders --------------------------------------------------------------------

export function buildListRequest(root: string, page: number): string {
  if (!Number.isInteger(page) || page < 1 || page > 500) throw new ApiError('Invalid page.', 0, 'invalid_request');
  return page === 1 ? `${root}school-years/` : `${root}school-years/?page=${page}`;
}

export function buildCreateRequest(root: string, startYear: number) {
  return { path: `${root}school-years/`, body: { start_year: startYear } };
}

export function buildDatesRequest(root: string, semesterId: number, request: DatesRequest) {
  if (!isId(semesterId)) throw new ApiError('Invalid semester.', 0, 'invalid_request');
  const body: DatesRequest = { start_date: request.start_date, end_date: request.end_date,
    expected_version: request.expected_version };
  if (request.acknowledge_cross_year_overlap === true) body.acknowledge_cross_year_overlap = true;
  return { path: `${root}semesters/${semesterId}/dates/`, body };
}

export function buildDeleteRequest(root: string, schoolYearId: number, expectedStartYear: number) {
  if (!isId(schoolYearId)) throw new ApiError('Invalid school year.', 0, 'invalid_request');
  return { path: `${root}school-years/${schoolYearId}/delete/`, body: { expected_start_year: expectedStartYear } };
}

// ---- Errors -------------------------------------------------------------------------------

export type ConflictReason = 'school_year_exists' | 'stale_version' | 'period_not_draft' | 'semesters_overlap'
  | 'cross_year_overlap' | 'period_in_use' | 'confirmation_mismatch';
const CONFLICTS: readonly string[] = ['school_year_exists', 'stale_version', 'period_not_draft', 'semesters_overlap',
  'cross_year_overlap', 'period_in_use', 'confirmation_mismatch'];
const CODES: Record<number, string> = {
  400: 'invalid_request', 401: 'authentication_required', 403: 'access_denied', 404: 'period_unavailable',
  405: 'method_not_allowed', 409: 'period_conflict', 415: 'unsupported_media_type', 429: 'rate_limited',
  503: 'academic_periods_unavailable',
};
export const FIELD_NAMES = ['start_year', 'start_date', 'end_date', 'expected_version', 'expected_start_year'] as const;
export type FieldName = typeof FIELD_NAMES[number];
const SAFE_FIELD_MESSAGES = new Set([
  'Enter a starting year from 2000 to 2100.', 'Enter a valid start date.', 'Enter a valid end date.',
  'Reload the semester and try again.', 'Confirm the school year you are deleting.',
  'Dates must fall within the two calendar years of this school year.', 'The end date must be after the start date.',
]);
const DEFAULT_FIELD_MESSAGES: Record<FieldName, string> = {
  start_year: 'Enter a starting year from 2000 to 2100.', start_date: 'Enter a valid start date.',
  end_date: 'Enter a valid end date.', expected_version: 'Reload the semester and try again.',
  expected_start_year: 'Confirm the school year you are deleting.',
};

export interface AcademicError {
  status: number;
  code: string;
  reason: string;
  fields: Partial<Record<FieldName, string>>;
}

/** Never renders server-provided text: codes and reasons are allowlisted; field text is matched. */
export function parseAcademicError(status: number, body: unknown): AcademicError {
  const error = isRecord(body) && isRecord(body.error) ? body.error : {};
  const fallback = CODES[status] ?? 'request_failed';
  let code = typeof error.code === 'string' ? error.code : fallback;
  if (status === 403 && code !== 'csrf_failed') code = 'access_denied';
  if (status !== 403 && code !== fallback) code = fallback;
  let reason = '';
  if (status === 409 && typeof error.reason === 'string' && CONFLICTS.includes(error.reason)) reason = error.reason;
  if (status === 403 && error.reason === 'admin_context_required') reason = 'admin_context_required';
  const fields: Partial<Record<FieldName, string>> = {};
  if (status === 400 && isRecord(error.fields)) {
    for (const name of FIELD_NAMES) {
      const values = error.fields[name];
      if (Array.isArray(values) && values.length) {
        fields[name] = typeof values[0] === 'string' && SAFE_FIELD_MESSAGES.has(values[0]) ? values[0] : DEFAULT_FIELD_MESSAGES[name];
      }
    }
  }
  return { status, code, reason, fields };
}

// ---- Client-side mirror of the server's rules (early feedback only) -----------------------

export function parseStartYear(raw: string): number | null {
  const text = raw.trim();
  if (!/^\d{4}$/.test(text)) return null;
  const year = Number(text);
  return year >= MIN_START_YEAR && year <= MAX_START_YEAR ? year : null;
}

export function schoolYearBounds(startYear: number): { min: string; max: string } {
  return { min: `${startYear}-01-01`, max: `${startYear + 1}-12-31` };
}

/** Field errors for one semester's own range, using the server's fixed messages. */
export function validateSemesterRange(start: string | null, end: string | null, startYear: number): Partial<Record<FieldName, string>> {
  const errors: Partial<Record<FieldName, string>> = {};
  const { min, max } = schoolYearBounds(startYear);
  if (start !== null && !isIsoDate(start)) errors.start_date = 'Enter a valid start date.';
  if (end !== null && !isIsoDate(end)) errors.end_date = 'Enter a valid end date.';
  if (errors.start_date || errors.end_date) return errors;
  const outside = 'Dates must fall within the two calendar years of this school year.';
  if (start !== null && (start < min || start > max)) errors.start_date = outside;
  if (end !== null && (end < min || end > max)) errors.end_date = outside;
  if (!errors.start_date && !errors.end_date && start !== null && end !== null && !(start < end)) {
    errors.end_date = 'The end date must be after the start date.';
  }
  return errors;
}

/** True unless every known First-semester date precedes every known Second-semester date. */
export function semestersOverlap(first: [string | null, string | null], second: [string | null, string | null]): boolean {
  const a = first.filter((d): d is string => d !== null);
  const b = second.filter((d): d is string => d !== null);
  if (!a.length || !b.length) return false;
  return !(a.reduce((x, y) => (x > y ? x : y)) < b.reduce((x, y) => (x < y ? x : y)));
}
