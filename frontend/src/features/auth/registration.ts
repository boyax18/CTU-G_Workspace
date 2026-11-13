import { postJSON } from '../../api/client.ts';

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

export async function submitRegistration(data: RegistrationData): Promise<void> {
  // Explicitly select public fields; never serialize arbitrary form/account state.
  await postJSON('/api/v1/auth/register/', {
    school_id: data.school_id.trim(), email: data.email.trim(), first_name: data.first_name.trim(),
    middle_name: data.middle_name.trim(), last_name: data.last_name.trim(), suffix: data.suffix.trim(),
    requested_role: data.requested_role, password: data.password, password_confirmation: data.password_confirmation,
  });
}
