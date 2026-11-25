/** Assisted email recovery, operator step (25 Nov 2026). One POST per confirmation, never retried.
 *  Django re-checks the exact permission, the account rules and the privileged-account boundary. */
import { ApiError, initializeCSRF, timeoutSignal } from '../../api/client.ts';

export const ASSIST_RECOVERY_PERMISSION = 'accounts.school_accounts.assist_recovery';

export type AssistedRecoveryReason =
  | 'own_account' | 'privileged_account' | 'inactive_account' | 'no_operational_role'
  | 'email_missing' | 'already_verified' | 'recovery_wait';
const REASONS = new Set<string>(['own_account', 'privileged_account', 'inactive_account', 'no_operational_role',
  'email_missing', 'already_verified', 'recovery_wait']);

const record = (value: unknown): Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};

export class AssistedRecoveryError extends ApiError {
  reason: AssistedRecoveryReason | null;
  constructor(message: string, status: number, code: string, reason: AssistedRecoveryReason | null = null,
    options: { retryAfter?: number; outcomeUnknown?: boolean } = {}) {
    super(message, status, code, {}, options);
    this.name = 'AssistedRecoveryError';
    this.reason = reason;
  }
}

/** Returns the code lifetime in seconds. The code itself is never returned to the operator. */
export async function startAssistedRecovery(accountId: number): Promise<{ codeValidSeconds: number }> {
  if (!Number.isInteger(accountId) || accountId < 1) throw new AssistedRecoveryError('Invalid account.', 0, 'invalid_request');
  const csrfToken = await initializeCSRF(); // fails before anything is sent
  let response: Response;
  try {
    response = await fetch(`/api/v1/admin/school-accounts/${accountId}/assisted-recovery/`, {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify({ identity_confirmed: true }), signal: timeoutSignal(),
    });
  } catch {
    throw new AssistedRecoveryError('We could not confirm whether recovery started.', 0, 'outcome_unknown', null, { outcomeUnknown: true });
  }
  let value: unknown = null;
  try { value = await response.json(); } catch { /* handled below */ }
  const body = record(value);
  if (response.status === 202 && body.status === 'code_queued') {
    const seconds = typeof body.code_valid_seconds === 'number' ? body.code_valid_seconds : 600;
    return { codeValidSeconds: seconds };
  }
  const error = record(body.error);
  const code = typeof error.code === 'string' ? error.code : 'request_failed';
  if (response.status === 409) {
    const reason = typeof error.reason === 'string' && REASONS.has(error.reason) ? error.reason as AssistedRecoveryReason : null;
    const retryAfter = typeof error.retry_after === 'number' ? error.retry_after : undefined;
    throw new AssistedRecoveryError('Assisted recovery could not be started.', 409, code, reason, { retryAfter });
  }
  if (response.ok || response.status >= 500 && !(response.status === 503 && code === 'review_unavailable')) {
    throw new AssistedRecoveryError('We could not confirm whether recovery started.', response.status, 'outcome_unknown', null, { outcomeUnknown: true });
  }
  throw new AssistedRecoveryError('Assisted recovery could not be started.', response.status, code);
}
