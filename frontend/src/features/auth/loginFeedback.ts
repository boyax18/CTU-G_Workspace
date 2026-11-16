/**
 * WF-01.03 P-01 (owner-approved 16 Nov 2026): turn a failed sign-in into safe,
 * specific feedback. Messages come from the shared API_MESSAGES map; nothing
 * here reveals whether an ID exists or what state an account is in.
 */
import { API_MESSAGES, ApiError } from '../../api/client.ts';

/** What the form offers after a failure. */
export type LoginRecovery =
  | 'security' // 403: explicit "Refresh security check"
  | 'wait' // 429: countdown, then sign in again
  | 'confirm' // outcome unknown: re-read the session before claiming failure
  | null;

export interface LoginFailure {
  error: ApiError;
  /** Show the non-revealing "awaiting approval" hint (every credentials failure). */
  approvalHint: boolean;
  recovery: LoginRecovery;
  /** Seconds to wait when recovery is 'wait'. */
  wait: number;
}

export const LOGIN_APPROVAL_HINT = 'If you registered recently, your account may still be awaiting School Admin approval.';
export const LOGIN_NOT_COMPLETED = 'Sign-in did not complete. Check your connection and try again.';
export const LOGIN_UNCONFIRMED = 'Sign-in could not be confirmed. Check your connection, then reload the page to see whether you are signed in.';

const UNCERTAIN_CODES = new Set(['invalid_session', 'invalid_response']);

export function describeLoginFailure(problem: unknown): LoginFailure {
  const error = problem instanceof ApiError
    ? problem
    : new ApiError(LOGIN_UNCONFIRMED, 0, 'network_error', {}, { outcomeUnknown: true });
  if (error.status === 401 || error.code === 'invalid_credentials') {
    return { error: new ApiError(API_MESSAGES.invalid_credentials, 401, 'invalid_credentials', {}, { requestId: error.requestId }),
      approvalHint: true, recovery: null, wait: 0 };
  }
  if (error.status === 429) {
    return { error, approvalHint: false, recovery: 'wait', wait: error.retryAfter ?? 60 };
  }
  if (error.status === 403 || error.code === 'csrf_failed') {
    return { error, approvalHint: false, recovery: 'security', wait: 0 };
  }
  // A POST was sent but its result is unknown: a session may exist.
  if (error.outcomeUnknown || UNCERTAIN_CODES.has(error.code)) {
    return { error, approvalHint: false, recovery: 'confirm', wait: 0 };
  }
  return { error, approvalHint: false, recovery: null, wait: 0 };
}

/** Message to show when the follow-up session read confirmed no session exists. */
export function notCompletedMessage(error: ApiError): string {
  return error.status >= 500 && error.code === 'auth_unavailable' ? error.message : LOGIN_NOT_COMPLETED;
}
