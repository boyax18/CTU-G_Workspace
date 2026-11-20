/** WF-03.01 Role assignments client. Off unless VITE_WORKSPACE_ROLE_ASSIGNMENT_ENABLED=1 (D-87).
 *
 * The switch only decides whether the dashboard calls the API; Django's gate, the composite Technical
 * Super Admin profile and the exact effective permission decide everything. GETs are never retried
 * automatically; the change POST is sent once, and anything that might have been applied is
 * `outcome_unknown` until the list is reloaded.
 */
import { ApiError, initializeCSRF, timeoutSignal } from '../../api/client.ts';
import { notifyAuthenticationRequired } from '../../utils/sessionSignals.ts';
import { parseRegistrationReviewError } from '../admin/registrationReviewApiContract.ts';
import { buildRoleListRequest, buildSchoolAdminChange, parseRoleChange, parseRoleConflict, parseRolePage } from './roleAssignmentContract.ts';
import { ROLE_ASSIGNMENT_ENABLED, ROLE_ASSIGNMENT_ROUTE_ROOT } from './roleAssignmentConfig.ts';
import type { RoleAssignmentPage, RoleChangeResult, SchoolAdminAction } from './roleAssignmentContract.ts';

const off = () => new ApiError('Role assignments are not activated.', 503, 'review_unavailable');
const uncertain = () => new ApiError(
  'We could not confirm the change. Reload the list before trying again.', 0, 'outcome_unknown', {}, { outcomeUnknown: true },
);

export async function listRoleAssignments(page = 1, q = '', enabled = ROLE_ASSIGNMENT_ENABLED): Promise<RoleAssignmentPage> {
  if (!enabled) throw off(); // MUST stay first: no request while switched off
  const path = buildRoleListRequest(ROLE_ASSIGNMENT_ROUTE_ROOT, page, q);
  let response: Response;
  try {
    response = await fetch(path, { method: 'GET', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json' }, signal: timeoutSignal() });
  } catch {
    throw new ApiError('Unable to connect to the role assignment service.', 0, 'network_error');
  }
  let value: unknown;
  try {
    value = await response.json();
  } catch {
    throw new ApiError('The server returned an unexpected response.', response.status, 'invalid_response');
  }
  if (!response.ok) {
    const { code, message } = parseRegistrationReviewError(response.status, value);
    if (response.status === 401) notifyAuthenticationRequired();
    throw new ApiError(message, response.status, code);
  }
  return parseRolePage(value);
}

/** One confirmed-state POST; never retried. Definite refusals keep their codes. */
export async function changeSchoolAdmin(
  accountId: number, action: SchoolAdminAction, expectedPresent: boolean, enabled = ROLE_ASSIGNMENT_ENABLED,
): Promise<RoleChangeResult> {
  if (!enabled) throw off();
  const plan = buildSchoolAdminChange(ROLE_ASSIGNMENT_ROUTE_ROOT, accountId, action, expectedPresent);
  const csrfToken = await initializeCSRF(); // fails before anything is sent
  let response: Response;
  try {
    response = await fetch(plan.path, {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(plan.body), signal: timeoutSignal(),
    });
  } catch {
    throw uncertain();
  }
  let value: unknown = null;
  try {
    value = await response.json();
  } catch {
    if (response.ok || response.status >= 500) throw uncertain();
  }
  if (response.ok) {
    try {
      return parseRoleChange(value, accountId, action === 'assign');
    } catch {
      throw uncertain();
    }
  }
  if (response.status === 409) {
    throw new ApiError('The role assignment could not be changed.', 409, parseRoleConflict(value) ?? 'role_assignment_conflict');
  }
  const { code, message } = parseRegistrationReviewError(response.status, value);
  if (response.status >= 500 && !(response.status === 503 && code === 'review_unavailable')) throw uncertain();
  if (response.status === 401) notifyAuthenticationRequired();
  throw new ApiError(message, response.status, code);
}
