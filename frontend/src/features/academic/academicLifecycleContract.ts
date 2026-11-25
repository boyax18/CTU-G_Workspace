/** WF-11.01 lifecycle, correction and history contract: strict parsing of the server's previews.
 * Previews are presentation only; every confirmation is re-validated by Django under lock. */
import { ApiError } from '../../api/client.ts';
import { isIsoDate } from './academicPeriodsContract.ts';
import type { SemesterStatus, SemesterTerm } from './academicPeriodsContract.ts';

export type PrerequisiteKey = 'valid_dates' | 'approved_fee' | 'academic_offerings';
export type ObligationKey = 'outstanding_clearance_signatures' | 'unpaid_fee_obligations' | 'incomplete_onboarding';
export type ImpactKey = 'student_participation' | 'fee_obligations' | 'clearance_records';
export type ReasonCode = 'calendar_change' | 'data_entry_correction' | 'institutional_directive';

export interface SemesterRef {
  semester_id: number;
  term: SemesterTerm;
  label: string;
  status: SemesterStatus;
  start_date: string | null;
  end_date: string | null;
  version: number;
  school_year_id: number;
  school_year_label: string;
}

export interface PrerequisiteCheck { key: PrerequisiteKey; status: 'ready' | 'missing' | 'unavailable'; reason: string }
export interface CountCheck<K extends string> { key: K; status: 'evaluated' | 'unavailable'; count: number | null; reason: string }

interface PreviewBase {
  semester: SemesterRef;
  warnings: string[];
  blockers: string[];
  feature_enabled: boolean;
  can_confirm: boolean;
}
export interface ActivationPreview extends PreviewBase {
  current_active: SemesterRef | null;
  prerequisites: PrerequisiteCheck[];
}
export interface ObligationPreview extends PreviewBase {
  obligations: CountCheck<ObligationKey>[];
}
export interface CorrectionPreview {
  semester: SemesterRef;
  kind: 'active_edit' | 'historical_correction';
  impact: CountCheck<ImpactKey>[];
  affected: ImpactKey[];
  reason_codes: ReasonCode[];
  blockers: string[];
  feature_enabled: boolean;
  can_confirm: boolean;
}

export type HistoryField = 'start_date' | 'end_date' | 'status';
export interface HistoryEntry {
  event: string;
  description: string;
  occurred_at: string;
  actor: 'You' | 'An administrator';
  semester: SemesterTerm | null;
  changes: Partial<Record<HistoryField, { before: string | null; after: string | null }>>;
  reason: string | null;
  note: string | null;
}
export interface HistoryPage { results: HistoryEntry[]; page: number; page_size: number; has_next: boolean }

const PREREQUISITES: readonly string[] = ['valid_dates', 'approved_fee', 'academic_offerings'];
const OBLIGATIONS: readonly string[] = ['outstanding_clearance_signatures', 'unpaid_fee_obligations', 'incomplete_onboarding'];
const IMPACTS: readonly string[] = ['student_participation', 'fee_obligations', 'clearance_records'];
const REASONS: readonly string[] = ['calendar_change', 'data_entry_correction', 'institutional_directive'];
const STATUSES: readonly string[] = ['Draft', 'Active', 'Closed', 'Archived'];
const CODE = /^[a-z][a-z_]{0,59}$/;
const MAX_ID = 2_147_483_647;

const invalid = () => new ApiError('The server returned an unexpected response.', 0, 'invalid_response');
const isRecord = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);
const isId = (v: unknown): v is number => typeof v === 'number' && Number.isInteger(v) && v >= 1 && v <= MAX_ID;
const isText = (v: unknown, max = 100): v is string => typeof v === 'string' && v.length > 0 && v.length <= max;
const optionalDate = (v: unknown): v is string | null => v === null || isIsoDate(v);
const codes = (v: unknown, max = 20): string[] => {
  if (!Array.isArray(v) || v.length > max || !v.every((item) => typeof item === 'string' && CODE.test(item))) throw invalid();
  return [...v] as string[];
};

export function parseSemesterRef(value: unknown): SemesterRef {
  if (!isRecord(value) || !isId(value.semester_id) || (value.term !== 'first' && value.term !== 'second')
    || !isText(value.label) || typeof value.status !== 'string' || !STATUSES.includes(value.status)
    || !optionalDate(value.start_date) || !optionalDate(value.end_date) || !isId(value.version)
    || !isId(value.school_year_id) || !isText(value.school_year_label, 20)) {
    throw invalid();
  }
  return { semester_id: value.semester_id, term: value.term, label: value.label, status: value.status as SemesterStatus,
    start_date: value.start_date, end_date: value.end_date, version: value.version,
    school_year_id: value.school_year_id, school_year_label: value.school_year_label };
}

function parseCounts<K extends string>(value: unknown, keys: readonly string[]): CountCheck<K>[] {
  if (!Array.isArray(value) || value.length !== keys.length) throw invalid();
  return value.map((item, index) => {
    if (!isRecord(item) || item.key !== keys[index] || (item.status !== 'evaluated' && item.status !== 'unavailable')
      || typeof item.reason !== 'string' || item.reason.length > 60) throw invalid();
    const count = item.status === 'evaluated'
      ? (typeof item.count === 'number' && Number.isInteger(item.count) && item.count >= 0 ? item.count : null) : null;
    // "Unavailable" is never shown as zero; an evaluated row must carry a real count.
    if (item.status === 'evaluated' && count === null) throw invalid();
    if (item.status === 'unavailable' && item.count !== null) throw invalid();
    return { key: item.key as K, status: item.status, count, reason: item.reason };
  });
}

function parseBase(value: Record<string, unknown>): PreviewBase {
  if (typeof value.feature_enabled !== 'boolean' || typeof value.can_confirm !== 'boolean') throw invalid();
  return { semester: parseSemesterRef(value.semester), warnings: codes(value.warnings), blockers: codes(value.blockers),
    feature_enabled: value.feature_enabled, can_confirm: value.can_confirm };
}

export function parseActivationPreview(value: unknown): ActivationPreview {
  if (!isRecord(value) || !Array.isArray(value.prerequisites) || value.prerequisites.length !== 3) throw invalid();
  const prerequisites = value.prerequisites.map((item, index) => {
    if (!isRecord(item) || item.key !== PREREQUISITES[index] || typeof item.reason !== 'string' || item.reason.length > 60
      || (item.status !== 'ready' && item.status !== 'missing' && item.status !== 'unavailable')) throw invalid();
    return { key: item.key as PrerequisiteKey, status: item.status, reason: item.reason } as PrerequisiteCheck;
  });
  return { ...parseBase(value), prerequisites,
    current_active: value.current_active === null ? null : parseSemesterRef(value.current_active) };
}

export function parseObligationPreview(value: unknown): ObligationPreview {
  if (!isRecord(value)) throw invalid();
  return { ...parseBase(value), obligations: parseCounts<ObligationKey>(value.obligations, OBLIGATIONS) };
}

export function parseCorrectionPreview(value: unknown): CorrectionPreview {
  if (!isRecord(value) || (value.kind !== 'active_edit' && value.kind !== 'historical_correction')
    || typeof value.feature_enabled !== 'boolean' || typeof value.can_confirm !== 'boolean') throw invalid();
  const affected = codes(value.affected, 3);
  const reasons = codes(value.reason_codes, 3);
  if (!affected.every((k) => IMPACTS.includes(k)) || !reasons.every((k) => REASONS.includes(k))) throw invalid();
  return { semester: parseSemesterRef(value.semester), kind: value.kind,
    impact: parseCounts<ImpactKey>(value.impact, IMPACTS), affected: affected as ImpactKey[],
    reason_codes: reasons as ReasonCode[], blockers: codes(value.blockers), feature_enabled: value.feature_enabled,
    can_confirm: value.can_confirm };
}

function parseHistoryEntry(value: unknown): HistoryEntry {
  if (!isRecord(value) || !isText(value.event, 60) || !isText(value.description) || !isText(value.occurred_at, 40)
    || (value.actor !== 'You' && value.actor !== 'An administrator')
    || (value.semester !== null && value.semester !== 'first' && value.semester !== 'second')
    || !isRecord(value.changes) || (value.reason !== null && !(typeof value.reason === 'string' && CODE.test(value.reason)))
    || (value.note !== null && !isText(value.note, 500))) throw invalid();
  const changes: HistoryEntry['changes'] = {};
  for (const [field, change] of Object.entries(value.changes)) {
    if (field !== 'start_date' && field !== 'end_date' && field !== 'status') throw invalid();
    if (!isRecord(change)) throw invalid();
    const ok = (v: unknown) => v === null || (typeof v === 'string' && v.length <= 20);
    if (!ok(change.before) || !ok(change.after)) throw invalid();
    changes[field] = { before: change.before as string | null, after: change.after as string | null };
  }
  return { event: value.event, description: value.description, occurred_at: value.occurred_at, actor: value.actor,
    semester: value.semester, changes, reason: value.reason, note: value.note };
}

export function parseHistoryPage(value: unknown, page: number): HistoryPage {
  if (!isRecord(value) || !Array.isArray(value.results) || value.page !== page || value.page_size !== 20
    || typeof value.has_next !== 'boolean' || value.results.length > 20) throw invalid();
  return { results: value.results.map(parseHistoryEntry), page, page_size: 20, has_next: value.has_next };
}

// ---- Fixed presentation copy (never server text) -------------------------------------------

export const PREREQUISITE_LABELS: Record<PrerequisiteKey, string> = {
  valid_dates: 'Valid start and end dates',
  approved_fee: 'Approved semester organization fee',
  academic_offerings: 'Curriculum and subject offerings',
};
export const OBLIGATION_LABELS: Record<ObligationKey, string> = {
  outstanding_clearance_signatures: 'Outstanding clearance signatures',
  unpaid_fee_obligations: 'Unpaid organization fee obligations',
  incomplete_onboarding: 'Students with incomplete onboarding',
};
export const IMPACT_LABELS: Record<ImpactKey, string> = {
  student_participation: 'Student semester records',
  fee_obligations: 'Organization fee obligations',
  clearance_records: 'Clearance records',
};
export const REASON_LABELS: Record<ReasonCode, string> = {
  calendar_change: 'Campus calendar change',
  data_entry_correction: 'Data entry correction',
  institutional_directive: 'Institutional directive',
};
const WARNING_LABELS: Record<string, string> = {
  previous_active_will_close: 'The current Active semester will be closed in the same step.',
  earlier_than_current_active: 'This semester starts before the current Active semester.',
  outside_semester_dates: 'Today is outside this semester’s configured dates.',
  before_end_date: 'The semester’s end date has not been reached yet.',
};

export function warningLabel(code: string): string {
  if (WARNING_LABELS[code]) return WARNING_LABELS[code];
  const match = /^(.+)_(unavailable|outstanding)$/.exec(code);
  const key = match?.[1] as ObligationKey | undefined;
  if (match && key && OBLIGATION_LABELS[key]) {
    return match[2] === 'unavailable'
      ? `${OBLIGATION_LABELS[key]} cannot be checked yet; outstanding items may exist.`
      : `${OBLIGATION_LABELS[key]} are still outstanding. They stay on record after this step.`;
  }
  return 'Another condition needs your review.';
}

export function dependencyNote(status: string, count: number | null): string {
  if (status === 'unavailable') return 'Cannot be checked yet';
  return count === 0 ? 'None' : `${count}`;
}
