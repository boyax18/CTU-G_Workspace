import { ApiError, postJSON } from '../../api/client.ts';

export async function requestPasswordReset(schoolId: string, email: string): Promise<void> {
  await postJSON('/api/v1/auth/forgot-password/', {
    school_id: schoolId.trim(), email: email.trim(),
  });
}

export async function confirmPasswordReset(uid: string, token: string, password: string, confirmation: string): Promise<void> {
  await postJSON('/api/v1/auth/reset-password/', {
    uid, token, password, password_confirmation: confirmation,
  });
}

export function readResetLink(hash: string): { uid: string; token: string } | null {
  if (!hash.startsWith('#')) return null;
  const fields = new URLSearchParams(hash.slice(1));
  const uid = fields.get('uid');
  const token = fields.get('token');
  if (!uid || !token || !/^[a-zA-Z0-9_-]{1,40}$/.test(uid) || !/^[a-zA-Z0-9-]{1,150}$/.test(token)) return null;
  return { uid, token };
}

// WF-01.05 P-01/P-02 (owner-approved 16 Nov 2026): specific, safe recovery feedback.
export const RECOVERY_REQUEST_UNCERTAIN = 'We could not confirm that your request was received. You can send it again.';
export const RECOVERY_RESET_UNCERTAIN = 'We could not confirm whether your password was changed. Try signing in with your new password. If that does not work, request a new reset link.';
export const RECOVERY_ASSISTED_HINT = 'If no email arrives, your account may need assisted recovery. Contact support.';
export const RECOVERY_PASSWORD_HINT = 'Use at least 8 characters. Avoid common passwords, only numbers, and details similar to your School ID, Staff ID or email.';

const KNOWN_REFUSALS = new Set(['recovery_disabled', 'recovery_unavailable']);

export type RecoveryFailureKind = 'link_invalid' | 'fields' | 'wait' | 'security' | 'uncertain' | 'other';

export interface RecoveryFailure {
  kind: RecoveryFailureKind;
  error: ApiError;
  /** Seconds to wait when kind is 'wait'. */
  wait: number;
}

export function describeRecoveryFailure(problem: unknown, step: 'request' | 'reset'): RecoveryFailure {
  const error = problem instanceof ApiError ? problem : new ApiError('', 0, 'network_error', {}, { outcomeUnknown: true });
  if (error.code === 'reset_link_invalid') return { kind: 'link_invalid', error, wait: 0 };
  if (error.status === 429) return { kind: 'wait', error, wait: error.retryAfter ?? 60 };
  if (error.status === 403 || error.code === 'csrf_failed') return { kind: 'security', error, wait: 0 };
  if (error.status === 400 && Object.keys(error.fields).length) return { kind: 'fields', error, wait: 0 };
  // A POST was sent but its result is unknown. Never repeat it automatically.
  // recovery_disabled and recovery_unavailable are definite refusals with nothing changed.
  if (error.outcomeUnknown && !KNOWN_REFUSALS.has(error.code)) {
    const message = step === 'reset' ? RECOVERY_RESET_UNCERTAIN : RECOVERY_REQUEST_UNCERTAIN;
    return { kind: 'uncertain', error: new ApiError(message, error.status, error.code, {}, { requestId: error.requestId }), wait: 0 };
  }
  return { kind: 'other', error, wait: 0 };
}
