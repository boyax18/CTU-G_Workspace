/** WF-03.05: read-only effective access explorer. Snapshot only, not authority. */
import { ApiError, getJSON } from '../../api/client.ts';
import { EFFECTIVE_ACCESS_INSPECT_ENABLED, EFFECTIVE_ACCESS_ROOT } from './effectiveAccessConfig.ts';
export type InspectAccount = {account_id: number; ctug_id: string; full_name: string};
export type InspectRole = {role_id: number; role_name: string};
export type ServiceStatus = {service_code: string; service_name: string; is_active: boolean};
export type AccessPermission = {permission_id: number; permission_code: string; permission_name: string;
  service_code: string; service_active: boolean; effective: boolean; explicit_deny: boolean;
  role_grant_recorded: boolean};
export type AccessSnapshot = {account_id: number; role: InspectRole; inherited_role_ids: number[];
  effective_count: number; services: ServiceStatus[]; permissions: AccessPermission[]};
const object = (v: unknown): v is Record<string,unknown> => v !== null && typeof v === 'object' && !Array.isArray(v);
const id = (v: unknown): v is number => typeof v === 'number' && Number.isInteger(v) && v > 0 && v <= 2147483647;
const string = (v: unknown, max: number): v is string => typeof v === 'string' && v.length > 0 && v.length <= max;
const invalid = (): never => { throw new ApiError('Invalid access inspection response.', 0, 'invalid_response'); };
const gate = () => { if (!EFFECTIVE_ACCESS_INSPECT_ENABLED) throw new ApiError('Access inspection is disabled.',503,'review_unavailable'); };

function parseAccount(value: unknown): InspectAccount {
  if (!object(value) || !id(value.account_id) || !string(value.ctug_id,100) || !string(value.full_name,250)) invalid();
  return value as unknown as InspectAccount;
}
function parseRole(value: unknown): InspectRole {
  if (!object(value) || !id(value.role_id) || !string(value.role_name,50)) invalid();
  return value as unknown as InspectRole;
}
export async function findAccessAccounts(q: string): Promise<InspectAccount[]> {
  gate(); if (q.length < 3 || q.length > 64 || q.trim() !== q) invalid();
  const response = await getJSON(`${EFFECTIVE_ACCESS_ROOT}accounts/?q=${encodeURIComponent(q)}`);
  if (!object(response) || !Array.isArray(response.accounts) || response.accounts.length > 20
      || typeof response.has_next !== 'boolean') invalid();
  const used = new Set<number>();
  return response.accounts.map((v: unknown) => { const a = parseAccount(v);
    if (used.has(a.account_id)) invalid(); used.add(a.account_id); return a; });
}
export async function getAccessRoles(accountId: number): Promise<{account: InspectAccount; roles: InspectRole[]}> {
  gate(); if (!id(accountId)) invalid();
  const response = await getJSON(`${EFFECTIVE_ACCESS_ROOT}accounts/${accountId}/roles/`);
  if (!object(response) || !object(response.account) || response.account.account_id !== accountId
      || !Array.isArray(response.roles) || response.roles.length > 32) invalid();
  const used = new Set<number>();
  const roles = response.roles.map((r: unknown) => { const role = parseRole(r);
    if (used.has(role.role_id)) invalid(); used.add(role.role_id); return role; });
  return {account: parseAccount(response.account),roles};
}
export async function getAccessSnapshot(accountId: number, roleId: number): Promise<AccessSnapshot> {
  gate(); if (!id(accountId) || !id(roleId)) invalid();
  const response = await getJSON(`${EFFECTIVE_ACCESS_ROOT}accounts/${accountId}/roles/${roleId}/`);
  if (!object(response) || response.account_id !== accountId || !object(response.role)
      || response.role.role_id !== roleId || !Array.isArray(response.inherited_role_ids)
      || response.inherited_role_ids.length > 32 || response.inherited_role_ids.some(v=>!id(v))
      || !Array.isArray(response.services) || response.services.length > 128
      || !Array.isArray(response.permissions) || response.permissions.length > 1024
      || typeof response.effective_count !== 'number' || !Number.isInteger(response.effective_count)
      || response.effective_count < 0 || response.effective_count > 1024) invalid();
  const role = parseRole(response.role);
  const services = response.services.map((v: unknown): ServiceStatus => {
    if (!object(v) || !string(v.service_code,100) || !string(v.service_name,100)
        || typeof v.is_active !== 'boolean') invalid();
    return v as unknown as ServiceStatus;
  });
  const used = new Set<number>();
  const permissions = response.permissions.map((v: unknown): AccessPermission => {
    if (!object(v) || !id(v.permission_id) || !string(v.permission_code,150)
        || !string(v.permission_name,100) || !string(v.service_code,100)
        || typeof v.service_active !== 'boolean' || typeof v.effective !== 'boolean'
        || typeof v.explicit_deny !== 'boolean' || typeof v.role_grant_recorded !== 'boolean'
        || used.has(v.permission_id) || (v.effective && (!v.service_active || v.explicit_deny))) invalid();
    used.add(v.permission_id);
    return v as unknown as AccessPermission;
  });
  if (permissions.filter(v=>v.effective).length !== response.effective_count) invalid();
  return {account_id:accountId,role,inherited_role_ids:response.inherited_role_ids as number[],
          effective_count:response.effective_count,services,permissions};
}
