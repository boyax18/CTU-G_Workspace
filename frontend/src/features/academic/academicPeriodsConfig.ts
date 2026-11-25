/** WF-11.01 School years & semesters (Draft management only).
 *
 * Off unless the build sets VITE_WORKSPACE_ACADEMIC_PERIODS_ENABLED=1. This switch only decides
 * whether the dashboard calls the API. Django's own default-off WORKSPACE_ACADEMIC_PERIODS_ENABLED
 * gate, the exact effective academic.periods.manage permission, the Admin assignment and role
 * context, and every business rule are enforced by the server on each request.
 *
 * There is no activation, closure, archiving or fee-setting client: those operations are not
 * available in this release, and the backend exposes no route for them.
 */
export const ACADEMIC_PERIODS_ENABLED: boolean =
  import.meta.env?.VITE_WORKSPACE_ACADEMIC_PERIODS_ENABLED === '1';

/** Mounted in config/urls.py; every view answers 503 while the server gate is off. */
export const ACADEMIC_PERIODS_ROUTE_ROOT = '/api/v1/academic/';
