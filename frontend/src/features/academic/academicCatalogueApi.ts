/** Read-only current academic period (FR-ACA-07) for every session holding academic.catalogue.read.
 *
 * Off unless the build sets VITE_WORKSPACE_ACADEMIC_CATALOGUE_ENABLED=1; Django's own default-off
 * WORKSPACE_ACADEMIC_CATALOGUE_ENABLED and the exact effective permission decide every request.
 * This never shows management data and never decides anything about activation.
 */
import { ApiError, timeoutSignal } from '../../api/client.ts';

export const ACADEMIC_CATALOGUE_ENABLED: boolean = import.meta.env?.VITE_WORKSPACE_ACADEMIC_CATALOGUE_ENABLED === '1';
export const CATALOGUE_CODE = 'academic.catalogue.read';
export const CURRENT_PERIOD_ROUTE = '/api/v1/academic/catalogue/current-period/';

export interface CurrentPeriod {
  semester_id: number;
  term: 'first' | 'second';
  label: string;
  school_year_id: number;
  school_year_label: string;
  start_date: string | null;
  end_date: string | null;
}

const invalid = () => new ApiError('Unexpected response.', 0, 'invalid_response');
const isRecord = (v: unknown): v is Record<string, unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);
const date = (v: unknown) => (v === null || (typeof v === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(v)) ? v as string | null : (() => { throw invalid(); })());
const text = (v: unknown, max: number) => (typeof v === 'string' && v && v.length <= max ? v : (() => { throw invalid(); })());
const id = (v: unknown) => (typeof v === 'number' && Number.isInteger(v) && v > 0 ? v : (() => { throw invalid(); })());

export function parseCurrentPeriod(value: unknown): CurrentPeriod | null {
  if (!isRecord(value) || !('active' in value)) throw invalid();
  if (value.active === null) return null;
  const v = value.active;
  if (!isRecord(v) || (v.term !== 'first' && v.term !== 'second')) throw invalid();
  return { semester_id: id(v.semester_id), term: v.term, label: text(v.label, 40), school_year_id: id(v.school_year_id),
    school_year_label: text(v.school_year_label, 20), start_date: date(v.start_date), end_date: date(v.end_date) };
}

/** One GET, never retried; any failure is reported as "unknown" by the caller, never as "no period". */
export async function getCurrentPeriod(enabled = ACADEMIC_CATALOGUE_ENABLED): Promise<CurrentPeriod | null> {
  if (!enabled) throw new ApiError('The academic catalogue is not available.', 503, 'academic_catalogue_unavailable');
  let response: Response;
  try {
    response = await fetch(CURRENT_PERIOD_ROUTE, { method: 'GET', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json' }, signal: timeoutSignal() });
  } catch {
    throw new ApiError('Unable to connect.', 0, 'network_error');
  }
  if (!response.ok) throw new ApiError('The current period is unavailable.', response.status, 'request_failed');
  let body: unknown;
  try { body = await response.json(); } catch { throw invalid(); }
  return parseCurrentPeriod(body);
}
