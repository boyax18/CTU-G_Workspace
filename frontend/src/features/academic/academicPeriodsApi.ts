/** WF-11.01 academic-period client. Every call returns early while ACADEMIC_PERIODS_ENABLED is off.
 *
 * GETs are never retried automatically. Each mutation is sent once; a failure after the request
 * may have reached Django is reported as `outcome_unknown` so the page reloads the list instead of
 * resubmitting. The server re-authorizes every request; nothing here decides access.
 */
import { ApiError, initializeCSRF, timeoutSignal } from '../../api/client.ts';
import { notifyAuthenticationRequired } from '../../utils/sessionSignals.ts';
import { ACADEMIC_PERIODS_ENABLED, ACADEMIC_PERIODS_ROUTE_ROOT } from './academicPeriodsConfig.ts';
import {
  buildCreateRequest, buildDatesRequest, buildDeleteRequest, buildListRequest, parseAcademicError, parseDeletion,
  parseSchoolYear, parseSchoolYearPage,
} from './academicPeriodsContract.ts';
import type { AcademicError, DatesRequest, SchoolYear, SchoolYearPage } from './academicPeriodsContract.ts';

/** An ApiError carrying the parsed academic refusal (reason and safe field messages). */
export class AcademicApiError extends ApiError {
  detail: AcademicError;

  constructor(message: string, detail: AcademicError, outcomeUnknown = false) {
    super(message, detail.status, detail.code, {}, { outcomeUnknown });
    this.name = 'AcademicApiError';
    this.detail = detail;
  }
}

const off = () => new AcademicApiError('School years and semesters are not available.',
  { status: 503, code: 'academic_periods_unavailable', reason: '', fields: {} });
const unknown = () => new AcademicApiError('We could not confirm the change. Reload the list before trying again.',
  { status: 0, code: 'outcome_unknown', reason: '', fields: {} }, true);

async function read(response: Response, mutation: boolean): Promise<unknown> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    if (mutation && (response.ok || response.status >= 500)) throw unknown();
    throw new AcademicApiError('The server returned an unexpected response.',
      { status: response.status, code: 'invalid_response', reason: '', fields: {} });
  }
  if (!response.ok) {
    const detail = parseAcademicError(response.status, body);
    if (response.status === 401) notifyAuthenticationRequired();
    if (mutation && response.status >= 500 && detail.code !== 'academic_periods_unavailable') throw unknown();
    throw new AcademicApiError('The request could not be completed.', detail);
  }
  return body;
}

async function get(path: string): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(path, { method: 'GET', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json' }, signal: timeoutSignal() });
  } catch {
    throw new AcademicApiError('Unable to connect to the academic service.',
      { status: 0, code: 'network_error', reason: '', fields: {} });
  }
  return read(response, false);
}

async function send(path: string, body: unknown): Promise<unknown> {
  const csrfToken = await initializeCSRF(); // fails before anything is sent
  let response: Response;
  try {
    response = await fetch(path, {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(body), signal: timeoutSignal(),
    });
  } catch {
    throw unknown();
  }
  return read(response, true);
}

export async function listSchoolYears(page = 1, enabled = ACADEMIC_PERIODS_ENABLED): Promise<SchoolYearPage> {
  if (!enabled) throw off(); // MUST stay first: no request while switched off
  return parseSchoolYearPage(await get(buildListRequest(ACADEMIC_PERIODS_ROUTE_ROOT, page)), page);
}

export async function createSchoolYear(startYear: number, enabled = ACADEMIC_PERIODS_ENABLED): Promise<SchoolYear> {
  if (!enabled) throw off();
  const plan = buildCreateRequest(ACADEMIC_PERIODS_ROUTE_ROOT, startYear);
  return parseSchoolYear(await send(plan.path, plan.body));
}

export async function updateSemesterDates(semesterId: number, request: DatesRequest,
  enabled = ACADEMIC_PERIODS_ENABLED): Promise<SchoolYear> {
  if (!enabled) throw off();
  const plan = buildDatesRequest(ACADEMIC_PERIODS_ROUTE_ROOT, semesterId, request);
  return parseSchoolYear(await send(plan.path, plan.body));
}

export async function deleteSchoolYear(schoolYearId: number, expectedStartYear: number,
  enabled = ACADEMIC_PERIODS_ENABLED): Promise<void> {
  if (!enabled) throw off();
  const plan = buildDeleteRequest(ACADEMIC_PERIODS_ROUTE_ROOT, schoolYearId, expectedStartYear);
  parseDeletion(await send(plan.path, plan.body), schoolYearId);
}
