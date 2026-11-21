/** WF-03.03 strictly parsed lookup and role-scoped individual grant API. */
import { ApiError, getJSON, postJSON } from '../../api/client.ts';
import { ACCOUNT_GRANTS_ENABLED, ACCOUNT_GRANTS_ROOT } from './accountGrantConfig.ts';

export type AccountMatch = { account_id: number; ctug_id: string; full_name: string };
export type AccountRoleOption = { role_id: number; role_name: string };
export type AccountPermissionRow = {
  permission_id: number; permission_code: string; permission_name: string;
  service_code: string; effect: 'Grant' | 'Deny' | null;
  scope_role_id: number | null; grant_role_ids: number[];
};
export type AccountGrantDirectory = {
  account: AccountMatch & { roles: AccountRoleOption[] }; permissions: AccountPermissionRow[];
};

const rec = (v: unknown): v is Record<string, unknown> => Boolean(v) && typeof v === 'object' && !Array.isArray(v);
const id = (v: unknown): v is number => typeof v === 'number' && Number.isInteger(v) && v > 0 && v <= 2_147_483_647;
const str = (v: unknown, limit: number): v is string => typeof v === 'string' && v.length > 0 && v.length <= limit;
const fail = (): never => { throw new ApiError('Invalid account grant response.', 0, 'invalid_response'); };
const check = () => { if (!ACCOUNT_GRANTS_ENABLED) throw new ApiError('Account grants not enabled.', 503, 'review_unavailable'); };

export async function searchGrantAccounts(q: string): Promise<AccountMatch[]> {
  check();
  if (q.trim() !== q || q.length < 3 || q.length > 64) fail();
  const data = await getJSON(`${ACCOUNT_GRANTS_ROOT}accounts/?q=${encodeURIComponent(q)}`);
  if (!rec(data) || !Array.isArray(data.accounts) || data.accounts.length > 20 || typeof data.has_next !== 'boolean') fail();
  const seen = new Set<number>();
  return data.accounts.map((x: unknown) => {
    if (!rec(x) || !id(x.account_id) || !str(x.ctug_id, 100) || typeof x.full_name !== 'string'
      || x.full_name.length > 250 || seen.has(x.account_id)) fail();
    seen.add(x.account_id);
    return x as unknown as AccountMatch;
  });
}

export async function getAccountGrantDirectory(accountId: number): Promise<AccountGrantDirectory> {
  check(); if (!id(accountId)) fail();
  const data = await getJSON(`${ACCOUNT_GRANTS_ROOT}accounts/${accountId}/grants/`);
  if (!rec(data) || !rec(data.account) || data.account.account_id !== accountId
    || !str(data.account.ctug_id, 100) || typeof data.account.full_name !== 'string'
    || !Array.isArray(data.account.roles) || data.account.roles.length > 100
    || !Array.isArray(data.permissions) || data.permissions.length > 1024) fail();
  const roleIds = new Set<number>();
  const roles = data.account.roles.map((r: unknown) => {
    if (!rec(r) || !id(r.role_id) || !str(r.role_name, 50) || roleIds.has(r.role_id)) fail();
    roleIds.add(r.role_id); return r as unknown as AccountRoleOption;
  });
  const permissionIds = new Set<number>();
  const permissions = data.permissions.map((p: unknown) => {
    if (!rec(p) || !id(p.permission_id) || !str(p.permission_code, 150) || !str(p.permission_name, 100)
      || !str(p.service_code, 100) || ![null, 'Grant', 'Deny'].includes(p.effect as string | null)
      || (p.scope_role_id !== null && !id(p.scope_role_id))
      || !Array.isArray(p.grant_role_ids) || p.grant_role_ids.length > 100
      || p.grant_role_ids.some((r: unknown) => !id(r) || !roleIds.has(r))
      || permissionIds.has(p.permission_id)) fail();
    permissionIds.add(p.permission_id); return p as unknown as AccountPermissionRow;
  });
  return {account: {...(data.account as unknown as AccountMatch), roles}, permissions};
}

export async function grantIndividualPermission(accountId: number, permissionId: number, roleId: number): Promise<void> {
  check(); if (![accountId, permissionId, roleId].every(id)) fail();
  const data = await postJSON(`${ACCOUNT_GRANTS_ROOT}accounts/${accountId}/grants/${permissionId}/`, {
    role_id: roleId, expected_active: false,
  });
  if (!rec(data) || data.account_id !== accountId || data.permission_id !== permissionId
    || data.role_id !== roleId || data.effect !== 'Grant' || data.changed !== true) {
    throw new ApiError('Grant outcome uncertain. Reload before continuing.', 0, 'outcome_unknown');
  }
}
