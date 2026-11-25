/**
 * WF-01.05 CR-01 (owner-approved 16-17 Nov 2026): email → 6-digit code → new password.
 * The reset ticket travels only as an HttpOnly cookie; page scripts never see it.
 */
import { ApiError, postJSON } from '../../api/client.ts';

const record = (value: unknown): Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
const seconds = (value: unknown, fallback: number): number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 86400 ? value : fallback;

export interface RecoveryCodeRequest {
  resendAfter: number;
  codeValidSeconds: number;
}

/** Step 1. The response is the same whether or not the email belongs to an eligible account. */
export async function requestPasswordReset(email: string): Promise<RecoveryCodeRequest> {
  const body = record(await postJSON('/api/v1/auth/forgot-password/', { email: email.trim() }));
  return { resendAfter: seconds(body.resend_after, 60), codeValidSeconds: seconds(body.code_valid_seconds, 600) };
}

/** Step 2. Success sets the HttpOnly reset-ticket cookie; nothing is returned to scripts. */
export async function verifyPasswordResetCode(email: string, code: string): Promise<void> {
  const body = record(await postJSON('/api/v1/auth/forgot-password/verify/', { email: email.trim(), code }));
  if (body.status !== 'verified') {
    throw new ApiError(RECOVERY_VERIFY_UNCERTAIN, 0, 'invalid_response', {}, { outcomeUnknown: true });
  }
}

/** Assisted recovery (25 Nov 2026): an administrator-started code replaces steps 1-2. Success sets
 *  the same HttpOnly reset-ticket cookie; every failure looks the same (no enumeration). */
export async function verifyAssistedRecoveryCode(email: string, code: string): Promise<void> {
  const body = record(await postJSON('/api/v1/auth/account-recovery/verify/', { email: email.trim(), code }));
  if (body.status !== 'verified') {
    throw new ApiError(RECOVERY_VERIFY_UNCERTAIN, 0, 'invalid_response', {}, { outcomeUnknown: true });
  }
}

/** Step 3. The browser sends the ticket cookie automatically. */
export async function confirmPasswordReset(email: string, password: string, confirmation: string): Promise<void> {
  await postJSON('/api/v1/auth/reset-password/', { email: email.trim(), password, password_confirmation: confirmation });
}

export const RECOVERY_REQUEST_UNCERTAIN = 'We could not confirm that your code was sent. You can send it again.';
export const RECOVERY_VERIFY_UNCERTAIN = 'We could not confirm the code check. Enter the code again.';
export const RECOVERY_RESET_UNCERTAIN = 'We could not confirm whether your password was changed. Try signing in with your new password. If that does not work, start again.';
// 25 Nov 2026: an accepted request (HTTP 202) is not a delivered email, so the copy never says "sent".
export const RECOVERY_CODE_SENT = 'If an eligible account uses this email, a 6-digit code is on its way. It can take a few minutes; check Spam too.';
export const RECOVERY_ASSISTED_HINT = 'No email? If you never verified your email, sign in and verify it on My profile, or ask the campus administrator for an account recovery code.';
export const RECOVERY_ASSISTED_INTRO = 'Enter your registered email and the account recovery code the campus administrator arranged for you.';
export const RECOVERY_PASSWORD_HINT = 'Use at least 8 characters. Avoid common passwords, only numbers, and details similar to your CTU-G ID or email.';

// recovery_disabled and recovery_unavailable are definite refusals with nothing changed.
const KNOWN_REFUSALS = new Set(['recovery_disabled', 'recovery_unavailable']);

export type RecoveryStep = 'request' | 'verify' | 'reset';
export type RecoveryFailureKind = 'code_invalid' | 'session_invalid' | 'fields' | 'wait' | 'security' | 'uncertain' | 'other';

export interface RecoveryFailure {
  kind: RecoveryFailureKind;
  error: ApiError;
  /** Seconds to wait when kind is 'wait'. */
  wait: number;
}

const UNCERTAIN: Record<RecoveryStep, string> = {
  request: RECOVERY_REQUEST_UNCERTAIN, verify: RECOVERY_VERIFY_UNCERTAIN, reset: RECOVERY_RESET_UNCERTAIN,
};

export function describeRecoveryFailure(problem: unknown, step: RecoveryStep): RecoveryFailure {
  const error = problem instanceof ApiError ? problem : new ApiError('', 0, 'network_error', {}, { outcomeUnknown: true });
  if (error.code === 'recovery_code_invalid') return { kind: 'code_invalid', error, wait: 0 };
  if (error.code === 'reset_session_invalid') return { kind: 'session_invalid', error, wait: 0 };
  if (error.status === 429) return { kind: 'wait', error, wait: error.retryAfter ?? 60 };
  if (error.status === 403 || error.code === 'csrf_failed') return { kind: 'security', error, wait: 0 };
  if (error.status === 400 && Object.keys(error.fields).length) return { kind: 'fields', error, wait: 0 };
  // A POST was sent but its result is unknown. Never repeat it automatically.
  if (error.outcomeUnknown && !KNOWN_REFUSALS.has(error.code)) {
    return { kind: 'uncertain', error: new ApiError(UNCERTAIN[step], error.status, error.code, {}, { requestId: error.requestId }), wait: 0 };
  }
  return { kind: 'other', error, wait: 0 };
}
