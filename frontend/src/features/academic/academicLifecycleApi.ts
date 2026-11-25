/** WF-11.01 lifecycle, correction and history client.
 *
 * Previews and history need only the Draft-management switch; each confirmation also needs its
 * own switch (no request is sent while it is off). Confirmations are sent once and never retried;
 * an ambiguous failure is `outcome_unknown`. Django decides access and re-validates everything.
 */
import { ACADEMIC_PERIODS_ENABLED, ACADEMIC_PERIOD_CORRECTIONS_ENABLED, ACADEMIC_PERIOD_TRANSITIONS_ENABLED,
  ACADEMIC_PERIODS_ROUTE_ROOT } from './academicPeriodsConfig.ts';
import { AcademicApiError, getAcademic, sendAcademic } from './academicPeriodsApi.ts';
import { parseSchoolYear } from './academicPeriodsContract.ts';
import type { SchoolYear } from './academicPeriodsContract.ts';
import {
  parseActivationPreview, parseCorrectionPreview, parseHistoryPage, parseObligationPreview, parseSemesterRef,
} from './academicLifecycleContract.ts';
import type {
  ActivationPreview, CorrectionPreview, HistoryPage, ImpactKey, ObligationPreview, ReasonCode, SemesterRef,
} from './academicLifecycleContract.ts';

export type Transition = 'activation' | 'closure' | 'archive';

const off = (code = 'academic_periods_unavailable', status = 503) =>
  new AcademicApiError('This academic-period action is not available.', { status, code, reason: '', fields: {}, details: [] });

function semesterPath(semesterId: number, action: Transition | 'corrections'): string {
  if (!Number.isInteger(semesterId) || semesterId < 1 || semesterId > 2_147_483_647) throw off('invalid_request', 0);
  return `${ACADEMIC_PERIODS_ROUTE_ROOT}semesters/${semesterId}/${action}/`;
}

export async function getActivationPreview(semesterId: number, enabled = ACADEMIC_PERIODS_ENABLED): Promise<ActivationPreview> {
  if (!enabled) throw off();
  return parseActivationPreview(await getAcademic(semesterPath(semesterId, 'activation')));
}

export async function getObligationPreview(semesterId: number, transition: 'closure' | 'archive',
  enabled = ACADEMIC_PERIODS_ENABLED): Promise<ObligationPreview> {
  if (!enabled) throw off();
  return parseObligationPreview(await getAcademic(semesterPath(semesterId, transition)));
}

export interface TransitionRequest {
  expected_version: number;
  acknowledged_warnings: string[];
  /** Activation only: the Active semester the preview showed (null when none). */
  expected_active_semester_id?: number | null;
}

export async function confirmTransition(semesterId: number, transition: Transition, request: TransitionRequest,
  enabled = ACADEMIC_PERIOD_TRANSITIONS_ENABLED): Promise<SemesterRef> {
  if (!enabled) throw off('feature_disabled');
  const body: Record<string, unknown> = { confirmed: true, expected_version: request.expected_version,
    acknowledged_warnings: [...request.acknowledged_warnings] };
  if (transition === 'activation') body.expected_active_semester_id = request.expected_active_semester_id ?? null;
  return parseSemesterRef(await sendAcademic(semesterPath(semesterId, transition), body));
}

export async function getCorrectionPreview(semesterId: number, enabled = ACADEMIC_PERIODS_ENABLED): Promise<CorrectionPreview> {
  if (!enabled) throw off();
  return parseCorrectionPreview(await getAcademic(semesterPath(semesterId, 'corrections')));
}

export interface CorrectionRequest {
  start_date: string;
  end_date: string;
  expected_version: number;
  reason_code: ReasonCode;
  reason_note: string;
  acknowledged_impacts: ImpactKey[];
  acknowledge_cross_year_overlap: boolean;
}

export async function correctSemester(semesterId: number, request: CorrectionRequest,
  enabled = ACADEMIC_PERIOD_CORRECTIONS_ENABLED): Promise<SchoolYear> {
  if (!enabled) throw off('feature_disabled');
  const body: Record<string, unknown> = { start_date: request.start_date, end_date: request.end_date,
    expected_version: request.expected_version, reason_code: request.reason_code, reason_note: request.reason_note };
  if (request.acknowledged_impacts.length) body.acknowledged_impacts = [...request.acknowledged_impacts];
  if (request.acknowledge_cross_year_overlap) body.acknowledge_cross_year_overlap = true;
  return parseSchoolYear(await sendAcademic(semesterPath(semesterId, 'corrections'), body));
}

export async function getSchoolYearHistory(schoolYearId: number, page = 1, enabled = ACADEMIC_PERIODS_ENABLED): Promise<HistoryPage> {
  if (!enabled) throw off();
  if (!Number.isInteger(schoolYearId) || schoolYearId < 1 || !Number.isInteger(page) || page < 1 || page > 500) {
    throw off('invalid_request', 0);
  }
  const path = `${ACADEMIC_PERIODS_ROUTE_ROOT}school-years/${schoolYearId}/history/${page === 1 ? '' : `?page=${page}`}`;
  return parseHistoryPage(await getAcademic(path), page);
}
