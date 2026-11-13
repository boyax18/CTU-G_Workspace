export class ApiError extends Error {
  status: number;
  code: string;
  fields: Record<string, string[]>;

  constructor(message: string, status = 0, code = 'network_error', fields: Record<string, string[]> = {}) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.code = code;
    this.fields = fields;
  }
}

async function readResponse(response: Response): Promise<unknown> {
  let body: unknown;
  try {
    body = await response.json();
  } catch {
    throw new ApiError('The server returned an unexpected response. Please try again later.', response.status);
  }
  if (!response.ok) {
    const error = (body as { error?: { message?: unknown; code?: unknown; fields?: unknown } })?.error;
    const fields: Record<string, string[]> = {};
    if (error?.fields && typeof error.fields === 'object') {
      for (const [key, value] of Object.entries(error.fields)) {
        if (Array.isArray(value) && value.every((item) => typeof item === 'string')) fields[key] = value;
      }
    }
    throw new ApiError(
      typeof error?.message === 'string' ? error.message : 'The request could not be completed.',
      response.status, typeof error?.code === 'string' ? error.code : 'request_failed', fields,
    );
  }
  return body;
}

export async function postJSON(path: string, body: unknown): Promise<unknown> {
  if (!path.startsWith('/api/') || path.includes('\\')) throw new ApiError('Invalid API path.');
  try {
    const bootstrap = await fetch('/api/v1/auth/csrf/', {
      credentials: 'same-origin', cache: 'no-store', headers: { Accept: 'application/json' },
      signal: AbortSignal.timeout(15_000),
    });
    const tokenBody = await readResponse(bootstrap) as { csrfToken?: unknown };
    if (typeof tokenBody?.csrfToken !== 'string' || !tokenBody.csrfToken) {
      throw new ApiError('The security check could not be initialized. Refresh the page and try again.');
    }
    // Never automatically retry a state-changing request after an ambiguous failure.
    return await readResponse(await fetch(path, {
      method: 'POST', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': tokenBody.csrfToken },
      body: JSON.stringify(body), signal: AbortSignal.timeout(15_000),
    }));
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('We could not confirm your submission. Check your connection and try again.');
  }
}
