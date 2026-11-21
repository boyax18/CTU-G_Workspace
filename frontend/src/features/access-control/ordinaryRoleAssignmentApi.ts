/** WF-03.01 D-100. Separate opt-in ordinary-role API; never accepts client appointment proof. */
import { ApiError, initializeCSRF, timeoutSignal } from '../../api/client.ts';
import { notifyAuthenticationRequired } from '../../utils/sessionSignals.ts';
import { parseRegistrationReviewError } from '../admin/registrationReviewApiContract.ts';
import { ROLE_ASSIGNMENT_ROUTE_ROOT } from './roleAssignmentConfig.ts';
import { normalizeRoleSearch } from './roleAssignmentContract.ts';

export const ORDINARY_ROLE_ENABLED = import.meta.env?.VITE_WORKSPACE_ORDINARY_ROLE_ASSIGNMENT_ENABLED === '1';
export type OrdinaryRole = 'Treasurer' | 'SSG Advisor';
export type OrdinaryAction = 'assign' | 'revoke';
export interface OrdinaryRoleRow {
  account_id: number;
  school_id: string;
  full_name: string | null;
  roles: string[];
  treasurer_action: OrdinaryAction | null;
  advisor_action: OrdinaryAction | null;
}
export interface OrdinaryPage { results: OrdinaryRoleRow[]; page: number; page_size: 20; has_next: boolean }

const fail = (): ApiError => new ApiError('Unexpected response from the role service.', 0, 'invalid_response');
const record = (x: unknown): x is Record<string, unknown> => !!x && typeof x === 'object' && !Array.isArray(x);
const exact = (x: Record<string, unknown>, keys: string[]) => Object.keys(x).length === keys.length && keys.every(k => Object.prototype.hasOwnProperty.call(x, k));
const validId = (n: unknown): n is number => typeof n === 'number' && Number.isInteger(n) && n > 0 && n <= 2_147_483_647;
const validAction = (x: unknown): x is OrdinaryAction | null => x === null || x === 'assign' || x === 'revoke';
const offline = () => new ApiError('Ordinary role changes are not activated.', 503, 'review_unavailable');
const uncertain = () => new ApiError('Change outcome unknown. Reload before trying again.', 0, 'outcome_unknown');

function parsePage(data: unknown): OrdinaryPage {
  if (!record(data) || !exact(data, ['results', 'page', 'page_size', 'has_next'])
    || !Array.isArray(data.results) || data.results.length > 20 || !Number.isInteger(data.page) || (data.page as number) < 1
    || data.page_size !== 20 || typeof data.has_next !== 'boolean'
    || (data.has_next && data.results.length !== 20)) throw fail();
  const results: OrdinaryRoleRow[] = [];
  for (const row of data.results as unknown[]) {
    if (!record(row) || !exact(row, ['account_id', 'school_id', 'full_name', 'roles', 'treasurer_action', 'advisor_action'])
      || !validId(row.account_id) || typeof row.school_id !== 'string' || !row.school_id || row.school_id.length > 50
      || !(row.full_name === null || (typeof row.full_name === 'string' && !!row.full_name && row.full_name.length <= 400))
      || !Array.isArray(row.roles) || row.roles.length > 20 || row.roles.some(r => typeof r !== 'string' || !r || r.length > 50)
      || new Set(row.roles).size !== row.roles.length || !validAction(row.treasurer_action) || !validAction(row.advisor_action)) throw fail();
    results.push(row as unknown as OrdinaryRoleRow);
  }
  if (new Set(results.map(r => r.account_id)).size !== results.length) throw fail();
  return { results, page: data.page as number, page_size: 20, has_next: data.has_next as boolean };
}

async function decode(response: Response): Promise<unknown> {
  let data: unknown;
  try { data = await response.json(); } catch { throw new ApiError('Invalid server response.', response.status, 'invalid_response'); }
  if (response.ok) return data;
  if (response.status === 409 && record(data) && record(data.error) && data.error.code === 'role_assignment_conflict') {
    const reason = data.error.reason;
    if (typeof reason === 'string' && ['state_changed', 'not_eligible', 'protected_account', 'last_role'].includes(reason)) {
      throw new ApiError('Role assignment could not be changed.', 409, reason);
    }
  }
  const { code, message } = parseRegistrationReviewError(response.status, data);
  if (response.status === 401) notifyAuthenticationRequired();
  throw new ApiError(message, response.status, code);
}

export async function listOrdinaryRoles(page: number, q: string): Promise<OrdinaryPage> {
  if (!ORDINARY_ROLE_ENABLED) throw offline();
  if (!Number.isInteger(page) || page < 1 || page > 10000) throw new Error('Invalid page.');
  const term = normalizeRoleSearch(q);
  const qs = new URLSearchParams({ page: String(page) });
  if (term) qs.set('q', term);
  let response: Response;
  try { response = await fetch(`${ROLE_ASSIGNMENT_ROUTE_ROOT}ordinary/?${qs.toString()}`, {
    method: 'GET', credentials: 'same-origin', cache: 'no-store',
    headers: { Accept: 'application/json' }, signal: timeoutSignal(),
  }); } catch { throw new ApiError('Cannot connect to the role service.', 0, 'network_error'); }
  return parsePage(await decode(response));
}

export async function changeOrdinaryRole(id: number, role: OrdinaryRole, action: OrdinaryAction): Promise<void> {
  if (!ORDINARY_ROLE_ENABLED) throw offline();
  if (!validId(id) || !(['Treasurer', 'SSG Advisor'] as string[]).includes(role) || !(['assign', 'revoke'] as string[]).includes(action)) {
    throw new ApiError('Unsupported role change.', 400, 'invalid_request');
  }
  const slug = role === 'Treasurer' ? 'treasurer' : 'ssg-advisor';
  const csrf = await initializeCSRF();
  let response: Response;
  try { response = await fetch(`${ROLE_ASSIGNMENT_ROUTE_ROOT}${id}/ordinary/${slug}/${action}/`, {
    method: 'POST', credentials: 'same-origin', cache: 'no-store',
    headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrf },
    body: JSON.stringify({ expected_present: action === 'revoke' }), signal: timeoutSignal(),
  }); } catch { throw uncertain(); }
  let data: unknown;
  try { data = await decode(response); } catch (err: unknown) {
    if (err instanceof ApiError && (err.code === 'invalid_response' || (err.status >= 500 && err.code !== 'review_unavailable'))) throw uncertain();
    throw err;
  }
  if (!record(data) || !exact(data, ['account_id', 'role', 'assigned'])
    || data.account_id !== id || data.role !== role || data.assigned !== (action === 'assign')) throw uncertain();
}
