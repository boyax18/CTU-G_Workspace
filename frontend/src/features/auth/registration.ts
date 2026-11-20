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
  if (data.school_id.trim() && !/^[0-9]{1,7}$/.test(data.school_id.trim())) errors.school_id = 'CTU-G ID must contain 1 to 7 digits only.';
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
  /** Configured code lifetime (D-01), shown as guidance; optional for older servers. */
  code_valid_seconds?: number;
  requested_role?: 'Student' | 'Instructor';
}

function verificationResult(value: unknown, statuses: string[], mutation: boolean): RegistrationVerification {
  const body = value !== null && typeof value === 'object' ? value as Record<string, unknown> : {};
  if (typeof body.status !== 'string' || !statuses.includes(body.status)) {
    throw new ApiError('We could not confirm the result. Check the current status before trying again.', 0, 'invalid_response', {}, { outcomeUnknown: mutation });
  }
  const role = body.requested_role === 'Instructor' ? 'Instructor' : body.requested_role === 'Student' ? 'Student' : undefined;
  if (['completed', 'cancelled'].includes(body.status)) return { status: body.status, ...(role ? { requested_role: role } : {}) };
  const names = ['expires_in', 'retry_after', 'resends_remaining', 'attempts_remaining'] as const;
  if (typeof body.delivery_sent !== 'boolean' || names.some(key => typeof body[key] !== 'number' || !Number.isInteger(body[key]) || (body[key] as number) < 0 || (body[key] as number) > 86400)) {
    throw new ApiError('We could not confirm the verification status. Check its status before trying again.', 0, 'invalid_response', {}, { outcomeUnknown: mutation });
  }
  const lifetime = body.code_valid_seconds;
  const validLifetime = typeof lifetime === 'number' && Number.isInteger(lifetime) && lifetime >= 1 && lifetime <= 86400;
  return {
    status: body.status, delivery_sent: body.delivery_sent, expires_in: body.expires_in as number,
    retry_after: body.retry_after as number, attempts_remaining: body.attempts_remaining as number,
    resends_remaining: body.resends_remaining as number,
    ...(validLifetime ? { code_valid_seconds: lifetime } : {}),
    ...(role ? { requested_role: role } : {}),
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
  return verificationResult(result, ['verification_required', 'existing_verification'], true);
}

const roleQuery = (role?: 'Student' | 'Instructor') => role === 'Instructor' ? '?requested_role=Instructor' : '';

export const verificationPath = (role?: 'Student' | 'Instructor') => '/register/verify' + roleQuery(role);

// One-tab, non-identifying flag: the last submission resumed an existing saved
// attempt, so the newly entered details were not applied (WF-01 R-05).
const RESUMED_KEY = 'ctug.registration.resumed';

export function markRegistrationResumed(): void {
  try { window.sessionStorage.setItem(RESUMED_KEY, '1'); } catch { /* storage unavailable: notice is optional */ }
}

export function takeRegistrationResumed(): boolean {
  try {
    const resumed = window.sessionStorage.getItem(RESUMED_KEY) === '1';
    window.sessionStorage.removeItem(RESUMED_KEY);
    return resumed;
  } catch {
    return false;
  }
}

export async function getRegistrationVerification(role?: 'Student' | 'Instructor'): Promise<RegistrationVerification> {
  return verificationResult(await getJSON('/api/v1/auth/register/verification/' + roleQuery(role)), ['verification_required', 'existing_verification'], false);
}

export async function verifyRegistrationCode(code: string, role?: 'Student' | 'Instructor'): Promise<RegistrationVerification> {
  return verificationResult(await postJSON('/api/v1/auth/register/verify/' + roleQuery(role), { code }), ['completed'], true);
}

export async function resendRegistrationCode(role?: 'Student' | 'Instructor'): Promise<RegistrationVerification> {
  return verificationResult(await postJSON('/api/v1/auth/register/resend/' + roleQuery(role), {}), ['verification_required'], true);
}

export async function cancelRegistrationVerification(role?: 'Student' | 'Instructor'): Promise<void> {
  verificationResult(await postJSON('/api/v1/auth/register/cancel/' + roleQuery(role), {}), ['cancelled'], true);
}
