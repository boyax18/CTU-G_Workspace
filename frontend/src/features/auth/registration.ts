import { ApiError, getJSON, postJSON } from '../../api/client.ts';

export interface RegistrationData {
  school_id: string;
  email: string;
  first_name: string;
  middle_name: string;
  last_name: string;
  suffix: string;
  requested_role: 'Student' | 'Instructor';
  password: string;
  password_confirmation: string;
}

export const emptyRegistration: RegistrationData = {
  school_id: '', email: '', first_name: '', middle_name: '', last_name: '', suffix: '',
  requested_role: 'Student', password: '', password_confirmation: '',
};

export function validateRegistration(data: RegistrationData): Partial<Record<keyof RegistrationData, string>> {
  const errors: Partial<Record<keyof RegistrationData, string>> = {};
  for (const field of ['school_id', 'email', 'first_name', 'last_name', 'password', 'password_confirmation'] as const) {
    if (!data[field].trim()) errors[field] = 'This field is required.';
  }
  if (data.school_id.trim() && !/^[0-9]{1,7}$/.test(data.school_id.trim())) errors.school_id = 'Use 1 to 7 digits only.';
  if (data.email.trim() && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email.trim())) errors.email = 'Enter a valid email address.';
  if (data.password && data.password.length < 8) errors.password = 'Use at least 8 characters.';
  if (data.password !== data.password_confirmation) errors.password_confirmation = 'Passwords do not match.';
  return errors;
}

export interface RegistrationVerification {
  status: string;
  delivery_sent?: boolean;
  expires_in?: number;
  retry_after?: number;
  resends_remaining?: number;
  attempts_remaining?: number;
}

function verificationResult(value: unknown, statuses: string[], mutation: boolean): RegistrationVerification {
  const body = value !== null && typeof value === 'object' ? value as Record<string, unknown> : {};
  if (typeof body.status !== 'string' || !statuses.includes(body.status)) {
    throw new ApiError('We could not confirm the result. Check the current status before trying again.', 0, 'invalid_response', {}, { outcomeUnknown: mutation });
  }
  if (['completed', 'cancelled'].includes(body.status)) return { status: body.status };
  const names = ['expires_in', 'retry_after', 'resends_remaining', 'attempts_remaining'] as const;
  if (typeof body.delivery_sent !== 'boolean' || names.some(key => typeof body[key] !== 'number' || !Number.isInteger(body[key]) || (body[key] as number) < 0 || (body[key] as number) > 86400)) {
    throw new ApiError('We could not confirm the verification status. Check its status before trying again.', 0, 'invalid_response', {}, { outcomeUnknown: mutation });
  }
  return {
    status: body.status, delivery_sent: body.delivery_sent, expires_in: body.expires_in as number,
    retry_after: body.retry_after as number, attempts_remaining: body.attempts_remaining as number,
    resends_remaining: body.resends_remaining as number,
  };
}

export async function submitRegistration(data: RegistrationData): Promise<RegistrationVerification> {
  // Explicitly select public fields; never serialize arbitrary form/account state.
  const payload = {
    school_id: data.school_id.trim(), email: data.email.trim(), first_name: data.first_name.trim(),
    middle_name: data.middle_name.trim(), last_name: data.last_name.trim(), suffix: data.suffix.trim(),
    requested_role: data.requested_role, password: data.password, password_confirmation: data.password_confirmation,
  };
  const result = await postJSON('/api/v1/auth/register/', payload);
  if (data.requested_role === 'Student') return verificationResult(result, ['verification_required', 'existing_verification'], true);
  if (!result || typeof result !== 'object' || typeof (result as Record<string, unknown>).message !== 'string') {
    throw new ApiError('We could not confirm the result. Check its status before trying again.', 0, 'invalid_response', {}, { outcomeUnknown: true });
  }
  return { status: 'submitted' };
}

export async function getRegistrationVerification(): Promise<RegistrationVerification> {
  return verificationResult(await getJSON('/api/v1/auth/register/verification/'), ['verification_required', 'existing_verification'], false);
}

export async function verifyRegistrationCode(code: string): Promise<RegistrationVerification> {
  return verificationResult(await postJSON('/api/v1/auth/register/verify/', { code }), ['completed'], true);
}

export async function resendRegistrationCode(): Promise<RegistrationVerification> {
  return verificationResult(await postJSON('/api/v1/auth/register/resend/', {}), ['verification_required'], true);
}

export async function cancelRegistrationVerification(): Promise<void> {
  verificationResult(await postJSON('/api/v1/auth/register/cancel/', {}), ['cancelled'], true);
}
