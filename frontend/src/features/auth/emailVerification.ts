/** Signed-in email verification (24 Nov 2026). Django decides everything; nothing is stored here.
 *  POSTs go through postJSON (CSRF, never retried automatically). */
import { ApiError, getJSON, postJSON } from '../../api/client.ts';

export interface EmailVerificationStatus {
  email: string | null;
  email_verified: boolean;
}

const ROOT = '/api/v1/auth/email-verification/';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

export async function getEmailVerificationStatus(): Promise<EmailVerificationStatus> {
  const value = await getJSON(ROOT);
  if (!isRecord(value) || typeof value.email_verified !== 'boolean'
    || !(value.email === null || typeof value.email === 'string')) {
    throw new ApiError('Email verification status could not be read.', 0, 'invalid_response');
  }
  return { email: value.email as string | null, email_verified: value.email_verified };
}

export async function requestEmailVerificationCode(): Promise<{ resendAfter: number; validSeconds: number }> {
  const value = await postJSON(`${ROOT}request/`, {});
  const resendAfter = isRecord(value) && typeof value.resend_after === 'number' ? value.resend_after : 60;
  const validSeconds = isRecord(value) && typeof value.code_valid_seconds === 'number' ? value.code_valid_seconds : 600;
  return { resendAfter, validSeconds };
}

export async function confirmEmailVerificationCode(code: string): Promise<void> {
  if (!/^[0-9]{6}$/.test(code)) throw new ApiError('Enter the 6-digit code.', 400, 'verification_code_invalid');
  await postJSON(`${ROOT}confirm/`, { code });
}
