import { ApiError, API_MESSAGES } from '../../api/client.ts';

export function asApiError(error: unknown, role?: 'Student' | 'Instructor'): ApiError {
  const problem = error instanceof ApiError ? error : new ApiError('We could not complete this request. Please try again later.', 0, 'request_failed');
  if (problem.code === 'conflict') {
    return new ApiError(API_MESSAGES.conflict, 409, 'conflict', {}, { requestId: problem.requestId });
  }
  if (role === 'Instructor' && problem.fields.school_id) {
    return new ApiError(problem.message, problem.status, problem.code, {
      ...problem.fields, school_id: problem.fields.school_id.map(text => text.replace(/School ID/g, 'Staff ID')),
    }, { requestId: problem.requestId, retryAfter: problem.retryAfter, outcomeUnknown: problem.outcomeUnknown, context: problem.context });
  }
  return problem;
}

export function registrationRecovery(error: ApiError, screen: 'registration' | 'verification') {
  if (error.outcomeUnknown) return 'check_status';
  if (error.code === 'csrf_failed') return 'security';
  if (error.code === 'expired' || (error.code === 'conflict' && screen === 'verification')) return 'restart';
  if (error.code === 'otp_expired' || error.code === 'delivery_failed') return 'resend';
  if (error.code === 'attempts_exhausted' || error.code === 'resends_exhausted') return 'cancel';
  if (error.code === 'resend_cooldown' || error.code === 'throttled') return 'wait';
  if (error.code === 'otp_invalid' || error.code === 'validation_error' || error.code === 'conflict') return 'correct';
  return 'retry';
}

// Shown when this browser holds no saved attempt on first load: it may have
// expired, been cancelled, or already been verified and submitted (WF-01 R-06).
export const NO_SAVED_ATTEMPT = 'No registration is waiting for email verification in this browser. It may have expired, been cancelled, or already been submitted for review. Start a new registration if you still need an account.';

/** OD-3 guidance (owner-approved 16 Nov 2026); the lifetime comes from D-01 configuration. */
export function codeGuidance(seconds?: number): string {
  const spam = "If you don't see the email, check your spam or junk folder.";
  if (!seconds) return spam;
  const minutes = Math.max(1, Math.round(seconds / 60));
  return `The code is valid for ${minutes} minute${minutes === 1 ? '' : 's'}. ${spam}`;
}

/** Keep digits only, so a pasted "123 456" or "123-456" becomes "123456" (WF-01 R-09). */
export const normalizeCode = (value: string): string => value.replace(/[^0-9]/g, '').slice(0, 6);

export function clearRegistrationSecrets(error: ApiError): boolean {
  return error.outcomeUnknown || ['conflict', 'expired', 'csrf_failed', 'delivery_failed'].includes(error.code);
}
