/** WF-03.01 Role assignments: typed contract (School Admin assign/revoke by a Technical Super Admin).
 *
 * The page never offers Technical Super Admin changes (Django Superuser only) or ordinary roles (not
 * yet approved in the catalogue). Every parser refuses extra or inconsistent fields; plans send only
 * the confirmed `expected_present` state.
 */
export type SchoolAdminAction = 'assign' | 'revoke';
export type RoleRestriction = 'not_instructor' | 'technical_super_admin' | 'legacy_admin' | 'last_school_admin';
export type RoleConflictReason = 'state_changed' | 'not_eligible' | 'protected_account' | 'last_school_admin'
  | 'last_technical_super_admin';

export interface RoleAssignmentItem {
  account_id: number;
  school_id: string;
  full_name: string | null;
  roles: string[];
  school_admin_action: SchoolAdminAction | null;
  restriction: RoleRestriction | null;
}

export interface RoleAssignmentPage { results: RoleAssignmentItem[]; page: number; page_size: 20; has_next: boolean }
export interface RoleChangeResult { account_id: number; role: 'Admin'; assigned: boolean }

const MAX_ID = 2_147_483_647;
const INVALID = 'The role assignment service returned an unexpected response.';
const ACTIONS: readonly string[] = ['assign', 'revoke'];
const RESTRICTIONS: readonly string[] = ['not_instructor', 'technical_super_admin', 'legacy_admin', 'last_school_admin'];
const REASONS: readonly string[] = ['state_changed', 'not_eligible', 'protected_account', 'last_school_admin', 'last_technical_super_admin'];

const isRecord = (v: unknown): v is Record<string, unknown> => typeof v === 'object' && v !== null && !Array.isArray(v);
const exactKeys = (v: Record<string, unknown>, keys: readonly string[]) =>
  Object.keys(v).length === keys.length && keys.every((k) => Object.prototype.hasOwnProperty.call(v, k));
export const isAccountId = (v: unknown): v is number => typeof v === 'number' && Number.isInteger(v) && v >= 1 && v <= MAX_ID;
const fail = (): never => { throw new Error(INVALID); };

function validateRoot(root: string): string {
  if (typeof root !== 'string' || !/^\/api\/(?:[A-Za-z0-9_-]+\/)+$/.test(root)) throw new Error('An approved, same-origin API route prefix is required.');
  return root;
}

export const ROLE_SEARCH_MAX = 50;

export function normalizeRoleSearch(value: string): string {
  const term = typeof value === 'string' ? value.trim() : '';
  if (!term) return '';
  if (term.length > ROLE_SEARCH_MAX || !/^[\x20-\x7E]+$/.test(term) || term.split(/\s+/).length > 5) {
    throw new Error(`Use up to ${ROLE_SEARCH_MAX} letters, digits or punctuation (no accents), in at most 5 words.`);
  }
  return term;
}

export function buildRoleListRequest(root: string, page = 1, q = ''): string {
  const base = validateRoot(root);
  if (!Number.isInteger(page) || page < 1 || page > 10_000) throw new Error('Invalid page.');
  const params = new URLSearchParams({ page: String(page) });
  const term = normalizeRoleSearch(q);
  if (term) params.set('q', term);
  return `${base}?${params.toString().replace(/\+/g, '%20')}`;
}

export function buildSchoolAdminChange(root: string, accountId: number, action: SchoolAdminAction, expectedPresent: boolean) {
  if (!isAccountId(accountId)) throw new Error('Invalid account ID.');
  if (!ACTIONS.includes(action)) throw new Error('Unsupported action.');
  // Assigning confirms the role is absent; revoking confirms it is present.
  if (typeof expectedPresent !== 'boolean' || expectedPresent !== (action === 'revoke')) throw new Error('Inconsistent confirmation.');
  return { method: 'POST' as const, path: `${validateRoot(root)}${accountId}/school-admin/${action}/`, body: { expected_present: expectedPresent } };
}

function parseItem(value: unknown): RoleAssignmentItem {
  if (!isRecord(value) || !exactKeys(value, ['account_id', 'school_id', 'full_name', 'roles', 'school_admin_action', 'restriction'])) fail();
  const v = value as Record<string, unknown>;
  if (!isAccountId(v.account_id) || typeof v.school_id !== 'string' || v.school_id.length < 1 || v.school_id.length > 50
    || !(v.full_name === null || (typeof v.full_name === 'string' && v.full_name.length >= 1 && v.full_name.length <= 400))
    || !Array.isArray(v.roles) || v.roles.length > 20 || v.roles.some((r) => typeof r !== 'string' || r.length < 1 || r.length > 50)
    || new Set(v.roles).size !== v.roles.length
    || !(v.school_admin_action === null || ACTIONS.includes(v.school_admin_action as string))
    || !(v.restriction === null || RESTRICTIONS.includes(v.restriction as string))
    || (v.school_admin_action !== null && v.restriction !== null)) fail();
  return {
    account_id: v.account_id as number, school_id: v.school_id as string, full_name: v.full_name as string | null,
    roles: [...(v.roles as string[])], school_admin_action: v.school_admin_action as SchoolAdminAction | null,
    restriction: v.restriction as RoleRestriction | null,
  };
}

export function parseRolePage(value: unknown): RoleAssignmentPage {
  if (!isRecord(value) || !exactKeys(value, ['results', 'page', 'page_size', 'has_next'])) fail();
  const v = value as Record<string, unknown>;
  if (!Array.isArray(v.results) || v.results.length > 20 || v.page_size !== 20 || typeof v.has_next !== 'boolean'
    || !Number.isInteger(v.page) || (v.page as number) < 1 || (v.has_next && v.results.length !== 20)) fail();
  const results = (v.results as unknown[]).map(parseItem);
  if (new Set(results.map((r) => r.account_id)).size !== results.length) fail();
  return { results, page: v.page as number, page_size: 20, has_next: v.has_next as boolean };
}

/** The server must confirm exactly this account and the new state. */
export function parseRoleChange(value: unknown, expectedId: number, assigned: boolean): RoleChangeResult {
  if (!isRecord(value) || !exactKeys(value, ['account_id', 'role', 'assigned'])
    || value.account_id !== expectedId || value.role !== 'Admin' || value.assigned !== assigned) fail();
  return { account_id: expectedId, role: 'Admin', assigned };
}

export function parseRoleConflict(value: unknown): RoleConflictReason | null {
  if (!isRecord(value) || !exactKeys(value, ['error']) || !isRecord(value.error)) return null;
  const { code, reason } = value.error;
  return code === 'role_assignment_conflict' && REASONS.includes(reason as string) ? reason as RoleConflictReason : null;
}
