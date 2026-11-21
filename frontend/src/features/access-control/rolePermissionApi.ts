/** WF-03.02 isolated role-permission directory & confirmed single-change requests. */
import { ApiError, getJSON, postJSON } from '../../api/client.ts';
import { ROLE_PERMISSION_API_ROOT, ROLE_PERMISSION_MANAGEMENT_ENABLED } from './rolePermissionConfig.ts';

export interface RoleChoice { role_id: number; role_name: string; is_active: boolean; protected: boolean }
export interface PermissionChoice {
  permission_id: number;
  permission_code: string;
  permission_name: string;
  service_code: string;
  assigned: boolean;
  change_allowed: boolean;
}
export interface PermissionDirectory { role_id: number; role_name: string; permissions: PermissionChoice[] }

const record = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value);
const id = (x: unknown): x is number => typeof x === 'number' && Number.isInteger(x) && x > 0 && x <= 2_147_483_647;
const str = (x: unknown, max: number): x is string => typeof x === 'string' && x.length > 0 && x.length <= max;
const fail = (): ApiError => new ApiError('Unexpected role permission response.', 0, 'invalid_response');
const off = (): never => { throw new ApiError('Role-permission management is not active.', 503, 'review_unavailable'); };

export async function getRoleChoices(): Promise<RoleChoice[]> {
  if (!ROLE_PERMISSION_MANAGEMENT_ENABLED) off();
  const payload = await getJSON(`${ROLE_PERMISSION_API_ROOT}roles/`);
  if (!record(payload) || !Array.isArray(payload.roles) || payload.roles.length > 128) throw fail();
  const seen = new Set<number>();
  const result: RoleChoice[] = [];
  for (const value of payload.roles) {
    if (!record(value) || !id(value.role_id) || !str(value.role_name, 50)
      || typeof value.is_active !== 'boolean' || typeof value.protected !== 'boolean'
      || seen.has(value.role_id)) throw fail();
    seen.add(value.role_id);
    result.push(value as unknown as RoleChoice);
  }
  return result;
}

export async function getRolePermissions(roleId: number): Promise<PermissionDirectory> {
  if (!ROLE_PERMISSION_MANAGEMENT_ENABLED) off();
  if (!id(roleId)) throw fail();
  const payload = await getJSON(`${ROLE_PERMISSION_API_ROOT}roles/${roleId}/permissions/`);
  if (!record(payload) || payload.role_id !== roleId || !str(payload.role_name, 50)
    || !Array.isArray(payload.permissions) || payload.permissions.length > 1024) throw fail();
  const seen = new Set<number>();
  const permissions: PermissionChoice[] = [];
  for (const value of payload.permissions) {
    if (!record(value) || !id(value.permission_id) || !str(value.permission_code, 150)
      || !str(value.permission_name, 100) || !str(value.service_code, 100)
      || typeof value.assigned !== 'boolean' || typeof value.change_allowed !== 'boolean'
      || seen.has(value.permission_id)) throw fail();
    seen.add(value.permission_id);
    permissions.push(value as unknown as PermissionChoice);
  }
  return { role_id: roleId, role_name: payload.role_name as string, permissions };
}

export async function setRolePermission(
  roleId: number, permissionId: number, action: 'grant' | 'revoke', expectedActive: boolean,
): Promise<void> {
  if (!ROLE_PERMISSION_MANAGEMENT_ENABLED) off();
  if (!id(roleId) || !id(permissionId) || typeof expectedActive !== 'boolean'
    || !['grant', 'revoke'].includes(action) || expectedActive !== (action === 'revoke')) throw fail();
  // postJSON enforces CSRF and does not retry uncertain writes.
  const data = await postJSON(`${ROLE_PERMISSION_API_ROOT}roles/${roleId}/permissions/${permissionId}/${action}/`,
    { expected_active: expectedActive });
  if (!record(data) || data.role_id !== roleId || data.permission_id !== permissionId
    || data.active !== (action === 'grant') || typeof data.changed !== 'boolean') {
    throw new ApiError('Change outcome unknown; reload before trying again.', 0, 'outcome_unknown');
  }
}
