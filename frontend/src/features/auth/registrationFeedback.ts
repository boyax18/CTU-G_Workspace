import { ApiError } from '../../api/client.ts';

export function asApiError(error: unknown): ApiError {
  return error instanceof ApiError ? error : new ApiError('We could not complete this request. Please try again later.', 0, 'request_failed');
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

export function clearRegistrationSecrets(error: ApiError): boolean {
  return error.outcomeUnknown || ['conflict', 'expired', 'csrf_failed', 'delivery_failed'].includes(error.code);
}
