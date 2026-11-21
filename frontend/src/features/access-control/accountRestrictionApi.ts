/** WF-03.04 typed, fail-closed client for account restrictions. */
import { ApiError, getJSON, postJSON } from '../../api/client.ts';
import { ACCOUNT_RESTRICTIONS_ENABLED, ACCOUNT_RESTRICTIONS_ROOT } from './accountRestrictionConfig.ts';

export type AccountMatch = { account_id: number; ctug_id: string; full_name: string };
export type RestrictionAction = 'deny' | 'revoke_grant' | 'remove_deny';
export type RestrictionPermission = {
  permission_id: number; permission_code: string; permission_name: string;
  service_code: string; effect: 'Grant' | 'Deny' | null;
  scope_role_id: number | null; can_deny: boolean;
  can_revoke_grant: boolean; can_remove_deny: boolean;
};
export type RestrictionDirectory = { account: AccountMatch; permissions: RestrictionPermission[] };
const obj = (v: unknown): v is Record<string, unknown> => Boolean(v) && typeof v === 'object' && !Array.isArray(v);
const id = (v: unknown): v is number => typeof v === 'number' && Number.isInteger(v) && v > 0 && v <= 2147483647;
const str = (v: unknown, n: number): v is string => typeof v === 'string' && v.length > 0 && v.length <= n;
const error = (): ApiError => new ApiError('Invalid permission restriction response.', 0, 'invalid_response');
const gate = () => { if (!ACCOUNT_RESTRICTIONS_ENABLED) throw new ApiError('Account restrictions disabled.', 503, 'review_unavailable'); };

export async function findRestrictionAccounts(q: string): Promise<AccountMatch[]> {
  gate(); if (q.length < 3 || q.length > 64 || q.trim() !== q) throw error();
  const data = await getJSON(`${ACCOUNT_RESTRICTIONS_ROOT}accounts/?q=${encodeURIComponent(q)}`);
  if (!obj(data) || !Array.isArray(data.accounts) || data.accounts.length > 20 || typeof data.has_next !== 'boolean') throw error();
  const ids = new Set<number>();
  return data.accounts.map((v: unknown) => {
    if (!obj(v) || !id(v.account_id) || !str(v.ctug_id, 100) || typeof v.full_name !== 'string'
        || v.full_name.length > 250 || ids.has(v.account_id)) throw error();
    ids.add(v.account_id); return v as unknown as AccountMatch;
  });
}

export async function getRestrictionDirectory(accountId: number): Promise<RestrictionDirectory> {
  gate(); if (!id(accountId)) throw error();
  const data = await getJSON(`${ACCOUNT_RESTRICTIONS_ROOT}accounts/${accountId}/overrides/`);
  if (!obj(data) || !obj(data.account) || data.account.account_id !== accountId
      || !str(data.account.ctug_id, 100) || typeof data.account.full_name !== 'string'
      || data.account.full_name.length > 250 || !Array.isArray(data.permissions) || data.permissions.length > 1024) throw error();
  const used = new Set<number>();
  const permissions = data.permissions.map((r: unknown) => {
    if (!obj(r) || !id(r.permission_id) || !str(r.permission_code, 150)
        || !str(r.permission_name, 100) || !str(r.service_code, 100)
        || ![null, 'Grant', 'Deny'].includes(r.effect as string | null)
        || (r.scope_role_id !== null && !id(r.scope_role_id))
        || typeof r.can_deny !== 'boolean' || typeof r.can_revoke_grant !== 'boolean'
        || typeof r.can_remove_deny !== 'boolean' || used.has(r.permission_id)) throw error();
    used.add(r.permission_id); return r as unknown as RestrictionPermission;
  });
  return {account: data.account as unknown as AccountMatch, permissions};
}

export async function changeRestriction(
    accountId: number, permission: RestrictionPermission, action: RestrictionAction,
): Promise<void> {
  gate(); if (!id(accountId) || !id(permission.permission_id)
      || !['deny', 'revoke_grant', 'remove_deny'].includes(action)) throw error();
  const result = await postJSON(`${ACCOUNT_RESTRICTIONS_ROOT}accounts/${accountId}/overrides/${permission.permission_id}/`, {
    action, expected_effect: permission.effect, expected_scope_role_id: permission.scope_role_id,
  });
  if (!obj(result) || result.account_id !== accountId || result.permission_id !== permission.permission_id
      || result.action !== action || result.changed !== true) {
    throw new ApiError('Restriction outcome uncertain. Reload before any further action.', 0, 'outcome_unknown');
  }
}
