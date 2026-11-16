import { notifyAuthenticationRequired } from '../utils/sessionSignals.ts';

export const API_MESSAGES: Record<string, string> = {
  validation_error: 'Check the submitted registration details.',
  otp_invalid: 'The verification code is incorrect. Please try again.',
  otp_expired: 'The code has expired or is unavailable. Request a new code.',
  attempts_exhausted: 'Too many incorrect codes. Cancel this attempt or wait for it to expire before starting again.',
  csrf_failed: 'Security check failed. Refresh the page and try again.',
  conflict: 'We could not complete this registration. Please check your information or contact support.',
  expired: 'This registration has expired. Start a new registration.',
  throttled: 'Too many requests. Please wait before trying again.',
  resend_cooldown: 'Please wait before requesting another code.',
  resends_exhausted: 'The resend limit has been reached. Cancel this attempt or wait for it to expire.',
  delivery_failed: 'We could not send the verification email. Your details are saved temporarily; try resending after the waiting period.',
  registration_unavailable: 'Registration is temporarily unavailable. Please try again later.',
  server_error: 'We could not complete this request. Please try again later.',
  method_not_allowed: 'This request method is not supported.',
  not_acceptable: 'Request an application/json response.',
  unsupported_media_type: 'Send an application/json request.',
  invalid_credentials: 'Unable to sign in with these credentials.',
  auth_unavailable: 'Authentication is temporarily unavailable.',
  too_many_attempts: 'Too many attempts. Please try again later.',
  invalid_request: 'Check the submitted data.',
  access_denied: 'You cannot perform this action.',
  authentication_required: 'Sign in to continue.',
  not_found: 'The requested resource is unavailable.',
  request_failed: 'The request could not be completed.',
  request_unavailable: 'Registration request is unavailable.',
  review_unavailable: 'Registration review is unavailable.',
  recovery_disabled: 'Password recovery is unavailable.',
};
const STAFF_ID_ERROR = 'Staff ID must contain 1 to 7 digits only.';
const INSTRUCTOR_FIELDS_ERROR = 'Student-only school information is not accepted for Instructor registration.';
const FIELD_MESSAGES: Record<string, string> = {
  school_id: 'School ID must contain 1 to 7 digits only.', email: 'Enter a valid email address.',
  first_name: 'Enter a valid first name.', middle_name: 'Enter a valid middle name.',
  last_name: 'Enter a valid last name.', suffix: 'Enter a valid suffix.',
  requested_role: 'Select Student or Instructor.', password: 'Choose a stronger password using the requirements shown.',
  password_confirmation: 'Passwords do not match.', code: 'Enter a six-digit verification code.',
  non_field_errors: 'Check the submitted registration details.',
};
const SAFE_FIELDS = new Set([...Object.values(FIELD_MESSAGES), STAFF_ID_ERROR, INSTRUCTOR_FIELDS_ERROR, 'This field is required.', 'This value is too long.']);
const STATUS_CODES: Record<number, string> = { 400: 'validation_error', 401: 'authentication_required', 403: 'csrf_failed', 409: 'conflict', 410: 'expired', 429: 'throttled', 500: 'server_error', 503: 'registration_unavailable' };
const own = (object: object, key: string) => Object.prototype.hasOwnProperty.call(object, key);
const record = (value: unknown): Record<string, unknown> => value !== null && typeof value === 'object' && !Array.isArray(value) ? value as Record<string, unknown> : {};
const identifier = (value: unknown): string => typeof value === 'string' && /^[a-f0-9]{32}$/.test(value) ? value : '';
const bounded = (value: unknown): number | undefined => typeof value === 'number' && Number.isInteger(value) && value >= 0 && value <= 86400 ? value : undefined;
const responseHeader = (response: Response, name: string): string | null => response.headers?.get?.(name) ?? null;
const REQUEST_TIMEOUT_MS = 15_000;

/** AbortSignal.timeout is missing on Safari < 16 and older WebViews; fall back safely. */
export function timeoutSignal(ms: number = REQUEST_TIMEOUT_MS): AbortSignal {
  if (typeof AbortSignal !== 'undefined' && typeof AbortSignal.timeout === 'function') return AbortSignal.timeout(ms);
  const controller = new AbortController();
  setTimeout(() => controller.abort(), ms);
  return controller.signal;
}

interface ErrorOptions {
  requestId?: string;
  retryAfter?: number;
  outcomeUnknown?: boolean;
  context?: Record<string, number | boolean>;
}

export class ApiError extends Error {
  status: number;
  code: string;
  fields: Record<string, string[]>;
  requestId: string;
  retryAfter?: number;
  outcomeUnknown: boolean;
  context: Record<string, number | boolean>;

  constructor(message: string, status = 0, code = 'network_error', fields: Record<string, string[]> = {}, options: ErrorOptions = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.fields = fields;
    this.requestId = identifier(options.requestId);
    this.retryAfter = bounded(options.retryAfter);
    this.outcomeUnknown = options.outcomeUnknown ?? false;
    this.context = options.context ?? {};
  }
}

async function readResponse(response: Response, mutation = false): Promise<unknown> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    const code = STATUS_CODES[response.status] ?? 'invalid_response';
    throw new ApiError(API_MESSAGES[code] ?? 'The server returned an unexpected response. Please try again later.', response.status, code, {}, {
      requestId: identifier(responseHeader(response, 'X-Request-ID')), outcomeUnknown: mutation && (response.ok || response.status >= 500),
    });
  }
  if (!response.ok) {
    const data = record(body);
    const error = record(data.error);
    const code = response.status === 409 ? 'conflict' : response.status === 410 ? 'expired'
      : typeof error.code === 'string' && own(API_MESSAGES, error.code) ? error.code : STATUS_CODES[response.status] ?? 'request_failed';
    // WF-01.04 P-04: only "not signed in" asks pages to re-read the session.
    // 403 access_denied and the login's own 401 invalid_credentials never do.
    if (response.status === 401 && code === 'authentication_required') notifyAuthenticationRequired();
    const fields: Record<string, string[]> = {};
    if (response.status === 400) {
      for (const [key, value] of Object.entries(record(error.fields))) {
        if (own(FIELD_MESSAGES, key) && Array.isArray(value) && value.length) {
          fields[key] = value.slice(0, 1).map(item => {
            return typeof item === 'string' && SAFE_FIELDS.has(item) ? item : FIELD_MESSAGES[key];
          });
        }
      }
    }
    const context: Record<string, number | boolean> = {};
    for (const key of ['expires_in', 'retry_after', 'resends_remaining', 'attempts_remaining']) {
      const value = bounded(data[key]);
      if (value !== undefined) context[key] = value;
    }
    if (typeof data.delivery_sent === 'boolean') context.delivery_sent = data.delivery_sent;
    const headerWait = responseHeader(response, 'Retry-After');
    const retryAfter = bounded(error.retry_after) ?? (headerWait !== null && /^\d+$/.test(headerWait) ? bounded(Number(headerWait)) : undefined);
    throw new ApiError(
      own(API_MESSAGES, code) ? API_MESSAGES[code] : API_MESSAGES[STATUS_CODES[response.status]] ?? 'The request could not be completed.',
      response.status, code, fields, {
        requestId: identifier(responseHeader(response, 'X-Request-ID')) || identifier(error.request_id), retryAfter,
        outcomeUnknown: mutation && response.status >= 500 && code !== 'delivery_failed', context,
      },
    );
  }
  if (own(record(body), 'error')) {
    throw new ApiError('We could not confirm the result. Check the current status before trying again.', response.status, 'invalid_response', {}, {
      requestId: identifier(responseHeader(response, 'X-Request-ID')), outcomeUnknown: mutation,
    });
  }
  return body;
}

export async function initializeCSRF(): Promise<string> {
  try {
    const bootstrap = await fetch('/api/v1/auth/csrf/', {
      credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' }, signal: timeoutSignal(),
    });
    const tokenBody = record(await readResponse(bootstrap));
    if (typeof tokenBody.csrfToken !== 'string' || !tokenBody.csrfToken) {
      throw new ApiError('The security check could not be initialized. Refresh the security check and try again.', 0, 'csrf_failed');
    }
    return tokenBody.csrfToken;
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('We could not refresh the security check. Check your connection and try again.');
  }
}

export async function postJSON(path: string, body: unknown): Promise<unknown> {
  if (!path.startsWith('/api/') || path.includes('\\')) throw new ApiError('Invalid API path.');
  let mutationAttempted = false;
  try {
    const csrfToken = await initializeCSRF();
    // Never automatically retry a state-changing request after an ambiguous failure.
    mutationAttempted = true;
    return await readResponse(await fetch(path, {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': csrfToken },
      body: JSON.stringify(body), signal: timeoutSignal(),
    }), true);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('We could not confirm your submission. Check the current status before trying again.', 0, 'network_error', {}, { outcomeUnknown: mutationAttempted });
  }
}

export async function getJSON(path: string): Promise<unknown> {
  if (!path.startsWith('/api/') || path.includes('\\')) throw new ApiError('Invalid API path.');
  try {
    return await readResponse(await fetch(path, {
      credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' },
      signal: timeoutSignal(),
    }));
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('We could not check your registration. Check your connection and try again.');
  }
}
