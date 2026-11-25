/** Academic configuration client: strict response parsing, fixed error copy, single-send POSTs.
 *
 * GETs are never retried automatically; each POST gets a fresh CSRF token, is sent once, and an
 * ambiguous failure is `outcome_unknown` so the page reloads instead of resubmitting.
 */
import { ApiError, initializeCSRF, timeoutSignal } from '../../api/client.ts';
import { notifyAuthenticationRequired } from '../../utils/sessionSignals.ts';
import { ACADEMIC_CONFIGURATION_ENABLED, ACADEMIC_CONFIGURATION_ROUTE_ROOT } from './academicConfigurationConfig.ts';

export type DefinitionStatus = 'Active' | 'Inactive' | 'Retired';
export type CurriculumStatus = 'Draft' | 'Published' | 'Superseded';
export type Term = 'first' | 'second';

export interface Course { course_id: number; code: string; name: string; status: DefinitionStatus; version: number;
  in_use: boolean; references: { curricula: number; sections: number; offerings: number } }
export interface Subject { subject_id: number; code: string; title: string; classification: string | null;
  lecture_units: string | null; lab_units: string | null; status: DefinitionStatus; version: number; in_use: boolean;
  references: { curriculum_entries: number; offerings: number } }
export interface Section { section_id: number; course: { course_id: number; code: string }; year_level: number;
  name: string; status: DefinitionStatus; version: number; in_use: boolean; references: { offerings: number } }
export interface CurriculumEntry { curriculum_subject_id: number; year_level: number; term: Term;
  subject: { subject_id: number; code: string; title: string; lecture_units: string | null; lab_units: string | null;
    status: DefinitionStatus } }
export interface Curriculum { curriculum_id: number; course: { course_id: number; code: string; name: string };
  label: string; effective_start_year: number | null; status: CurriculumStatus; version: number; entry_count: number;
  offering_count: number; can_edit: boolean; entries?: CurriculumEntry[] }
export interface SemesterRef { semester_id: number; term: Term; label: string; status: string; school_year_id: number;
  school_year_label: string }
export interface Instructor { account_id: number; ctug_id: string; full_name: string | null }
export interface Assignment { assignment_id: number; status: 'Active' | 'Ended'; instructor: Instructor; eligible: boolean;
  assigned_at: string | null; ended_at: string | null; end_reason: string | null }
export interface Offering { offering_id: number; semester: SemesterRef;
  section: { section_id: number; name: string; year_level: number; course_code: string };
  subject: { subject_id: number; code: string; title: string }; curriculum: { curriculum_id: number; label: string };
  assignment: Assignment | null; ready_for_confirmation: boolean; can_remove: boolean }
export interface Candidate { curriculum_subject_id: number; curriculum: { curriculum_id: number; label: string };
  subject: { subject_id: number; code: string; title: string } }
export interface Features { curriculum_writes: boolean; offering_writes: boolean; teaching_assignments: boolean }
export interface Page<T> { results: T[]; page: number; has_next: boolean }

// ---- Errors --------------------------------------------------------------------------------

export interface ConfigErrorDetail { status: number; code: string; reason: string; fields: Record<string, string> }

export class ConfigApiError extends ApiError {
  detail: ConfigErrorDetail;

  constructor(message: string, detail: ConfigErrorDetail, outcomeUnknown = false) {
    super(message, detail.status, detail.code, {}, { outcomeUnknown });
    this.name = 'ConfigApiError';
    this.detail = detail;
  }
}

const REASONS = ['code_exists', 'label_exists', 'section_exists', 'entry_exists', 'offering_exists', 'stale_version',
  'in_use', 'invalid_transition', 'not_available', 'not_draft', 'not_published', 'curriculum_empty', 'period_closed',
  'period_not_draft', 'reference_mismatch', 'offering_in_use', 'assignment_changed', 'no_change',
  'instructor_ineligible', 'constraint_conflict'];
export const REASON_TEXT: Record<string, string> = {
  code_exists: 'This code is already used.',
  label_exists: 'This course already has a curriculum with that label.',
  section_exists: 'This section already exists for the course and year level.',
  entry_exists: 'This subject is already in the curriculum.',
  offering_exists: 'This subject is already offered to the section this semester.',
  stale_version: 'This record was changed by someone else. Reload and try again.',
  in_use: 'This record is already used by curricula or offerings, so this change is not allowed.',
  invalid_transition: 'This status change is not allowed.',
  not_available: 'An inactive or retired definition cannot be used here.',
  not_draft: 'Only a Draft curriculum can be changed.',
  not_published: 'Only a Published curriculum can be used for this.',
  curriculum_empty: 'Add at least one subject before publishing.',
  period_closed: 'Closed and Archived semesters cannot be changed.',
  period_not_draft: 'Offerings can be removed only while the semester is Draft.',
  reference_mismatch: 'The curriculum subject does not match the section or the semester.',
  offering_in_use: 'This offering has teaching assignment history and cannot be removed.',
  assignment_changed: 'The instructor assignment changed. Reload and try again.',
  no_change: 'Nothing changed.',
  instructor_ineligible: 'This account is not an eligible Instructor.',
  constraint_conflict: 'The change conflicts with existing records. Reload and try again.',
};
const FIELD_NAMES = ['code', 'name', 'title', 'classification', 'lecture_units', 'lab_units', 'label',
  'effective_start_year', 'year_level', 'term', 'status', 'expected_version', 'confirmed', 'reason_code', 'q', 'page',
  'course_id', 'subject_id', 'section_id', 'semester_id', 'curriculum_id', 'curriculum_subject_id', 'offering_id',
  'instructor_account_id', 'expected_assignment_id'];
const SAFE_FIELD_TEXT = new Set(['Use 1 to 20 letters, digits, spaces, dots, hyphens or slashes.',
  'Enter a name of up to 150 characters.', 'Enter a title of up to 200 characters.', 'Use up to 60 characters.',
  'Enter units from 0 to 30 in steps of 0.1, or leave blank.', 'Enter a label of up to 40 characters.',
  'Enter a year from 2000 to 2100, or leave blank.', 'Choose a year level from 1 to 6.',
  'Choose the First or Second semester.', 'Choose a valid status.', 'Reload and try again.',
  'Confirm the change to continue.', 'Choose a reason.', 'Use up to 50 plain characters.', 'Invalid page.',
  'Choose a valid item.', 'Enter a name.', 'Enter a title.', 'Enter a label.']);
const CODES: Record<number, string> = { 400: 'invalid_request', 401: 'authentication_required', 403: 'access_denied',
  404: 'not_found', 405: 'method_not_allowed', 409: 'configuration_conflict', 429: 'rate_limited',
  503: 'academic_configuration_unavailable' };
const isRecord = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);

/** Never renders server text: codes, reasons and field messages are allowlisted. */
export function parseConfigError(status: number, body: unknown): ConfigErrorDetail {
  const error = isRecord(body) && isRecord(body.error) ? body.error : {};
  let code = CODES[status] ?? 'request_failed';
  if (status === 403 && error.code === 'csrf_failed') code = 'csrf_failed';
  if (status === 503 && error.code === 'feature_disabled') code = 'feature_disabled';
  let reason = '';
  if (status === 409 && typeof error.reason === 'string' && REASONS.includes(error.reason)) reason = error.reason;
  if (status === 403 && error.reason === 'admin_context_required') reason = 'admin_context_required';
  const fields: Record<string, string> = {};
  if (status === 400 && isRecord(error.fields)) {
    for (const name of FIELD_NAMES) {
      const values = error.fields[name];
      if (Array.isArray(values) && values.length) {
        fields[name] = typeof values[0] === 'string' && SAFE_FIELD_TEXT.has(values[0]) ? values[0] : 'Check this value.';
      }
    }
  }
  return { status, code, reason, fields };
}

/** Fixed copy for any refusal. */
export function configErrorText(error: unknown): string {
  const detail = error instanceof ConfigApiError ? error.detail : null;
  if (!detail) return 'The request could not be completed. Reload and try again.';
  switch (detail.code) {
    case 'outcome_unknown': return 'We could not confirm the change. Reload to see the current state before trying again.';
    case 'authentication_required': return 'Your session has ended. Sign in again to continue.';
    case 'access_denied': return detail.reason === 'admin_context_required'
      ? 'Switch to your School Admin role, then try again.' : 'You do not have permission for this academic configuration.';
    case 'csrf_failed': return 'Security check failed. Refresh the page and try again.';
    case 'feature_disabled': return 'This change is not enabled on the server.';
    case 'academic_configuration_unavailable': return 'Academic configuration is not available right now.';
    case 'rate_limited': return 'Too many requests. Wait a minute, then try again.';
    case 'not_found': return 'This record is no longer available. Reload the list.';
    case 'configuration_conflict': return REASON_TEXT[detail.reason] ?? 'The change conflicts with existing records.';
    case 'invalid_request': return 'Check the highlighted details.';
    default: return 'The request could not be completed. Reload and try again.';
  }
}

// ---- Transport -----------------------------------------------------------------------------

const off = () => new ConfigApiError('Academic configuration is not available.',
  { status: 503, code: 'academic_configuration_unavailable', reason: '', fields: {} });
const unknown = () => new ConfigApiError('We could not confirm the change.',
  { status: 0, code: 'outcome_unknown', reason: '', fields: {} }, true);

async function read(response: Response, mutation: boolean): Promise<unknown> {
  let body: unknown;
  try { body = await response.json(); } catch {
    if (mutation && (response.ok || response.status >= 500)) throw unknown();
    throw new ConfigApiError('Unexpected response.', { status: response.status, code: 'invalid_response', reason: '', fields: {} });
  }
  if (!response.ok) {
    const detail = parseConfigError(response.status, body);
    if (response.status === 401) notifyAuthenticationRequired();
    if (mutation && response.status >= 500 && detail.code !== 'feature_disabled'
      && detail.code !== 'academic_configuration_unavailable') throw unknown();
    throw new ConfigApiError('The request could not be completed.', detail);
  }
  return body;
}

function path(suffix: string, query?: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query ?? {})) if (value !== undefined && value !== '') params.set(key, String(value));
  const text = params.toString();
  return `${ACADEMIC_CONFIGURATION_ROUTE_ROOT}${suffix}${text ? `?${text}` : ''}`;
}

export async function configGet(suffix: string, query?: Record<string, string | number | undefined>,
  enabled = ACADEMIC_CONFIGURATION_ENABLED): Promise<unknown> {
  if (!enabled) throw off(); // MUST stay first: no request while switched off
  let response: Response;
  try {
    response = await fetch(path(suffix, query), { method: 'GET', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json' }, signal: timeoutSignal() });
  } catch {
    throw new ConfigApiError('Unable to connect.', { status: 0, code: 'network_error', reason: '', fields: {} });
  }
  return read(response, false);
}

export async function configPost(suffix: string, body: unknown, enabled = ACADEMIC_CONFIGURATION_ENABLED): Promise<unknown> {
  if (!enabled) throw off();
  const csrfToken = await initializeCSRF();
  let response: Response;
  try {
    response = await fetch(path(suffix), { method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(body), signal: timeoutSignal() });
  } catch {
    throw unknown();
  }
  return read(response, true);
}

// ---- Strict parsing ------------------------------------------------------------------------

const invalid = () => new ConfigApiError('Unexpected response.', { status: 0, code: 'invalid_response', reason: '', fields: {} });
const id = (v: unknown): number => { if (typeof v !== 'number' || !Number.isInteger(v) || v < 1) throw invalid(); return v; };
const count = (v: unknown): number => { if (typeof v !== 'number' || !Number.isInteger(v) || v < 0) throw invalid(); return v; };
const text = (v: unknown, max = 200): string => { if (typeof v !== 'string' || !v || v.length > max) throw invalid(); return v; };
const optText = (v: unknown, max = 200): string | null => (v === null ? null : text(v, max));
const bool = (v: unknown): boolean => { if (typeof v !== 'boolean') throw invalid(); return v; };
const oneOf = <T extends string>(v: unknown, values: readonly T[]): T => {
  if (typeof v !== 'string' || !values.includes(v as T)) throw invalid();
  return v as T;
};
const rec = (v: unknown): Record<string, unknown> => { if (!isRecord(v)) throw invalid(); return v; };
const units = (v: unknown): string | null => {
  if (v === null) return null;
  if (typeof v !== 'string' || !/^\d{1,2}\.\d$/.test(v)) throw invalid();
  return v;
};
const STATUSES = ['Active', 'Inactive', 'Retired'] as const;
const TERMS = ['first', 'second'] as const;

export function parseCourse(value: unknown): Course {
  const v = rec(value); const r = rec(v.references);
  return { course_id: id(v.course_id), code: text(v.code, 20), name: text(v.name, 150), status: oneOf(v.status, STATUSES),
    version: id(v.version), in_use: bool(v.in_use),
    references: { curricula: count(r.curricula), sections: count(r.sections), offerings: count(r.offerings) } };
}

export function parseSubject(value: unknown): Subject {
  const v = rec(value); const r = rec(v.references);
  return { subject_id: id(v.subject_id), code: text(v.code, 20), title: text(v.title, 200),
    classification: optText(v.classification, 60), lecture_units: units(v.lecture_units), lab_units: units(v.lab_units),
    status: oneOf(v.status, STATUSES), version: id(v.version), in_use: bool(v.in_use),
    references: { curriculum_entries: count(r.curriculum_entries), offerings: count(r.offerings) } };
}

export function parseSection(value: unknown): Section {
  const v = rec(value); const c = rec(v.course);
  const level = id(v.year_level); if (level > 6) throw invalid();
  return { section_id: id(v.section_id), course: { course_id: id(c.course_id), code: text(c.code, 20) }, year_level: level,
    name: text(v.name, 20), status: oneOf(v.status, STATUSES), version: id(v.version), in_use: bool(v.in_use),
    references: { offerings: count(rec(v.references).offerings) } };
}

function parseEntry(value: unknown): CurriculumEntry {
  const v = rec(value); const s = rec(v.subject);
  return { curriculum_subject_id: id(v.curriculum_subject_id), year_level: id(v.year_level), term: oneOf(v.term, TERMS),
    subject: { subject_id: id(s.subject_id), code: text(s.code, 20), title: text(s.title), lecture_units: units(s.lecture_units),
      lab_units: units(s.lab_units), status: oneOf(s.status, STATUSES) } };
}

export function parseCurriculum(value: unknown): Curriculum {
  const v = rec(value); const c = rec(v.course);
  const start = v.effective_start_year === null ? null : id(v.effective_start_year);
  const result: Curriculum = { curriculum_id: id(v.curriculum_id),
    course: { course_id: id(c.course_id), code: text(c.code, 20), name: text(c.name, 150) }, label: text(v.label, 40),
    effective_start_year: start, status: oneOf(v.status, ['Draft', 'Published', 'Superseded'] as const),
    version: id(v.version), entry_count: count(v.entry_count), offering_count: count(v.offering_count),
    can_edit: bool(v.can_edit) };
  if (v.entries !== undefined) {
    if (!Array.isArray(v.entries)) throw invalid();
    result.entries = v.entries.map(parseEntry);
  }
  return result;
}

export function parseSemesterRef(value: unknown): SemesterRef {
  const v = rec(value);
  return { semester_id: id(v.semester_id), term: oneOf(v.term, TERMS), label: text(v.label, 40),
    status: oneOf(v.status, ['Draft', 'Active', 'Closed', 'Archived'] as const), school_year_id: id(v.school_year_id),
    school_year_label: text(v.school_year_label, 20) };
}

function parseInstructor(value: unknown): Instructor {
  const v = rec(value);
  return { account_id: id(v.account_id), ctug_id: text(v.ctug_id, 50), full_name: optText(v.full_name, 300) };
}

function parseAssignment(value: unknown): Assignment {
  const v = rec(value);
  return { assignment_id: id(v.assignment_id), status: oneOf(v.status, ['Active', 'Ended'] as const),
    instructor: parseInstructor(v.instructor), eligible: bool(v.eligible), assigned_at: optText(v.assigned_at, 40),
    ended_at: optText(v.ended_at, 40), end_reason: optText(v.end_reason, 40) };
}

export function parseOffering(value: unknown): Offering {
  const v = rec(value); const s = rec(v.section); const subj = rec(v.subject); const cur = rec(v.curriculum);
  return { offering_id: id(v.offering_id), semester: parseSemesterRef(v.semester),
    section: { section_id: id(s.section_id), name: text(s.name, 20), year_level: id(s.year_level), course_code: text(s.course_code, 20) },
    subject: { subject_id: id(subj.subject_id), code: text(subj.code, 20), title: text(subj.title) },
    curriculum: { curriculum_id: id(cur.curriculum_id), label: text(cur.label, 40) },
    assignment: v.assignment === null ? null : parseAssignment(v.assignment),
    ready_for_confirmation: bool(v.ready_for_confirmation), can_remove: bool(v.can_remove) };
}

export function parseFeatures(value: unknown): Features {
  const v = isRecord(value) ? value : {};
  // Fail closed: anything but an exact true is "not enabled".
  return { curriculum_writes: v.curriculum_writes === true, offering_writes: v.offering_writes === true,
    teaching_assignments: v.teaching_assignments === true };
}

function parsePage<T>(value: unknown, item: (v: unknown) => T): Page<T> {
  const v = rec(value);
  if (!Array.isArray(v.results) || v.results.length > 50 || typeof v.has_next !== 'boolean') throw invalid();
  return { results: v.results.map(item), page: id(v.page), has_next: v.has_next };
}

// ---- Operations ----------------------------------------------------------------------------

export const listCourses = async (query: { q?: string; status?: string; page?: number } = {}) =>
  parsePage(await configGet('courses/', query), parseCourse);
export const createCourse = async (body: { code: string; name: string }) => parseCourse(await configPost('courses/', body));
export const updateCourse = async (courseId: number, body: { code: string; name: string; expected_version: number }) =>
  parseCourse(await configPost(`courses/${courseId}/`, body));
export const setCourseStatus = async (courseId: number, status: DefinitionStatus, expectedVersion: number) =>
  parseCourse(await configPost(`courses/${courseId}/status/`, { status, expected_version: expectedVersion }));

export interface SubjectBody { code: string; title: string; classification: string | null; lecture_units: string | null;
  lab_units: string | null }
export const listSubjects = async (query: { q?: string; status?: string; page?: number } = {}) =>
  parsePage(await configGet('subjects/', query), parseSubject);
export const createSubject = async (body: SubjectBody) => parseSubject(await configPost('subjects/', body));
export const updateSubject = async (subjectId: number, body: SubjectBody & { expected_version: number }) =>
  parseSubject(await configPost(`subjects/${subjectId}/`, body));
export const setSubjectStatus = async (subjectId: number, status: DefinitionStatus, expectedVersion: number) =>
  parseSubject(await configPost(`subjects/${subjectId}/status/`, { status, expected_version: expectedVersion }));

export const listSections = async (query: { course_id?: number; year_level?: number; status?: string; page?: number } = {}) =>
  parsePage(await configGet('sections/', query), parseSection);
export const createSection = async (body: { course_id: number; year_level: number; name: string }) =>
  parseSection(await configPost('sections/', body));
export const updateSection = async (sectionId: number, body: { year_level: number; name: string; expected_version: number }) =>
  parseSection(await configPost(`sections/${sectionId}/`, body));
export const setSectionStatus = async (sectionId: number, status: DefinitionStatus, expectedVersion: number) =>
  parseSection(await configPost(`sections/${sectionId}/status/`, { status, expected_version: expectedVersion }));

export async function listCurricula(query: { course_id?: number; status?: string; page?: number } = {}) {
  const value = await configGet('curricula/', query);
  return { ...parsePage(value, parseCurriculum), features: parseFeatures(rec(value).features) };
}
export async function getCurriculum(curriculumId: number) {
  const value = await configGet(`curricula/${curriculumId}/`);
  return { curriculum: parseCurriculum(value), features: parseFeatures(rec(value).features) };
}
export const createCurriculum = async (body: { course_id: number; label: string; effective_start_year: number | null }) =>
  parseCurriculum(await configPost('curricula/', body));
export const addCurriculumEntry = async (curriculumId: number,
  body: { subject_id: number; year_level: number; term: Term; expected_version: number }) =>
  parseCurriculum(await configPost(`curricula/${curriculumId}/entries/`, body));
export const removeCurriculumEntry = async (curriculumId: number, entryId: number, expectedVersion: number) =>
  parseCurriculum(await configPost(`curricula/${curriculumId}/entries/${entryId}/remove/`, { expected_version: expectedVersion }));
export const publishCurriculum = async (curriculumId: number, expectedVersion: number) =>
  parseCurriculum(await configPost(`curricula/${curriculumId}/publish/`, { expected_version: expectedVersion, confirmed: true }));
export const supersedeCurriculum = async (curriculumId: number, expectedVersion: number) =>
  parseCurriculum(await configPost(`curricula/${curriculumId}/supersede/`, { expected_version: expectedVersion, confirmed: true }));
export async function deleteDraftCurriculum(curriculumId: number, expectedVersion: number): Promise<void> {
  const v = rec(await configPost(`curricula/${curriculumId}/delete/`, { expected_version: expectedVersion }));
  if (v.deleted !== true || v.curriculum_id !== curriculumId) throw invalid();
}

export async function listSemesters() {
  const value = rec(await configGet('semesters/'));
  if (!Array.isArray(value.results)) throw invalid();
  return { results: value.results.map(parseSemesterRef), features: parseFeatures(value.features) };
}
export async function listOfferings(semesterId: number) {
  const value = rec(await configGet('offerings/', { semester_id: semesterId }));
  if (!Array.isArray(value.results)) throw invalid();
  return { semester: parseSemesterRef(value.semester), results: value.results.map(parseOffering),
    valid_offering_count: count(value.valid_offering_count), has_next: bool(value.has_next),
    features: parseFeatures(value.features) };
}
export async function listCandidates(semesterId: number, sectionId: number): Promise<Candidate[]> {
  const value = rec(await configGet('offerings/candidates/', { semester_id: semesterId, section_id: sectionId }));
  if (!Array.isArray(value.results)) throw invalid();
  return value.results.map((item) => {
    const v = rec(item); const c = rec(v.curriculum); const s = rec(v.subject);
    return { curriculum_subject_id: id(v.curriculum_subject_id), curriculum: { curriculum_id: id(c.curriculum_id), label: text(c.label, 40) },
      subject: { subject_id: id(s.subject_id), code: text(s.code, 20), title: text(s.title) } };
  });
}
export const createOffering = async (body: { semester_id: number; section_id: number; curriculum_subject_id: number }) =>
  parseOffering(await configPost('offerings/', body));
export async function removeOffering(offeringId: number): Promise<void> {
  const v = rec(await configPost(`offerings/${offeringId}/remove/`, {}));
  if (v.deleted !== true || v.offering_id !== offeringId) throw invalid();
}

export async function searchInstructors(q: string): Promise<Instructor[]> {
  const value = rec(await configGet('instructors/', { q: q.trim() || undefined }));
  if (!Array.isArray(value.results) || value.results.length > 20) throw invalid();
  return value.results.map(parseInstructor);
}
export const assignInstructor = async (offeringId: number, instructorAccountId: number, expectedAssignmentId: number | null) =>
  parseOffering(await configPost(`offerings/${offeringId}/instructor/`,
    { instructor_account_id: instructorAccountId, expected_assignment_id: expectedAssignmentId }));
export const endAssignment = async (offeringId: number, expectedAssignmentId: number, reasonCode: string) =>
  parseOffering(await configPost(`offerings/${offeringId}/instructor/end/`,
    { expected_assignment_id: expectedAssignmentId, reason_code: reasonCode }));
export async function assignmentHistory(offeringId: number): Promise<Assignment[]> {
  const value = rec(await configGet(`offerings/${offeringId}/instructor/history/`));
  if (!Array.isArray(value.results)) throw invalid();
  return value.results.map(parseAssignment);
}
