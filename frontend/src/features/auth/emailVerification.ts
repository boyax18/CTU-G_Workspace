/** Signed-in email verification (24-25 Nov 2026). Django decides everything; nothing is stored here.
 *  POSTs go through postJSON (CSRF, never retried automatically). */
import { ApiError, getJSON, postJSON } from '../../api/client.ts';

export interface EmailVerificationStatus {
  email: string | null;
  email_verified: boolean;
  /** A code for THIS account is outstanding (the code itself is never returned). */
  codePending: boolean;
  resendAfter: number;
  codeExpiresIn: number;
}

const ROOT = '/api/v1/auth/email-verification/';

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === 'object' && value !== null && !Array.isArray(value);
}

const seconds = (value: unknown, fallback = 0): number =>
  typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 86400 ? value : fallback;

export async function getEmailVerificationStatus(): Promise<EmailVerificationStatus> {
  const value = await getJSON(ROOT);
  if (!isRecord(value) || typeof value.email_verified !== 'boolean'
    || !(value.email === null || typeof value.email === 'string')) {
    throw new ApiError('Email verification status could not be read.', 0, 'invalid_response');
  }
  return {
    email: value.email as string | null,
    email_verified: value.email_verified,
    codePending: value.code_pending === true,
    resendAfter: seconds(value.resend_after),
    codeExpiresIn: seconds(value.code_expires_in),
  };
}

export async function requestEmailVerificationCode(): Promise<{ resendAfter: number; validSeconds: number }> {
  const value = await postJSON(`${ROOT}request/`, {});
  return {
    resendAfter: isRecord(value) ? seconds(value.resend_after, 60) : 60,
    validSeconds: isRecord(value) ? seconds(value.code_valid_seconds, 600) : 600,
  };
}

export async function confirmEmailVerificationCode(code: string): Promise<void> {
  if (!/^[0-9]{6}$/.test(code)) throw new ApiError('Enter the 6-digit code.', 400, 'verification_code_invalid');
  await postJSON(`${ROOT}confirm/`, { code });
}
