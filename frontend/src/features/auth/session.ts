/** Browser-session client for CTU-G Workspace. No tokens or passwords are stored. */
import { ApiError, postJSON } from '../../api/client.ts';

export interface AuthenticatedWorkspaceSession {
  authenticated: true;
  account: {
    school_id: string;
    roles: string[];
  };
  /** UI hints only. The backend must authorize every protected operation. */
  permissions: string[];
}

export type WorkspaceSession = AuthenticatedWorkspaceSession | { authenticated: false };

function parseSession(value: unknown): WorkspaceSession {
  if (!value || typeof value !== 'object') {
    throw new ApiError('The server returned an unexpected session response.', 0, 'invalid_session');
  }
  const body = value as Record<string, unknown>;
  if (body.authenticated === false) return { authenticated: false };
  if (body.authenticated !== true || !body.account || typeof body.account !== 'object') {
    throw new ApiError('The server returned an unexpected session response.', 0, 'invalid_session');
  }
  const account = body.account as Record<string, unknown>;
  if (
    typeof account.school_id !== 'string' ||
    !Array.isArray(account.roles) ||
    !account.roles.every((role) => typeof role === 'string') ||
    !Array.isArray(body.permissions) ||
    !body.permissions.every((code) => typeof code === 'string')
  ) {
    throw new ApiError('The server returned an unexpected session response.', 0, 'invalid_session');
  }
  return {
    authenticated: true,
    account: { school_id: account.school_id, roles: account.roles },
    permissions: body.permissions as string[],
  };
}

export async function loginWorkspace(schoolId: string, password: string): Promise<AuthenticatedWorkspaceSession> {
  const result = parseSession(await postJSON('/api/v1/auth/login/', {
    school_id: schoolId.trim(),
    password,
  }));
  if (!result.authenticated) {
    throw new ApiError('Unable to sign in with these credentials.', 401, 'invalid_credentials');
  }
  return result;
}

export async function getWorkspaceSession(): Promise<WorkspaceSession> {
  try {
    const response = await fetch('/api/v1/auth/session/', {
      method: 'GET', credentials: 'same-origin', cache: 'no-store',
      headers: { Accept: 'application/json' }, signal: AbortSignal.timeout(15_000),
    });
    if (!response.ok) {
      throw new ApiError('Unable to verify your session. Please try again.', response.status, 'session_unavailable');
    }
    return parseSession(await response.json());
  } catch (error) {
    if (error instanceof ApiError) throw error;
    throw new ApiError('Unable to verify your session. Check your connection and try again.', 0, 'session_unavailable');
  }
}

export async function logoutWorkspace(): Promise<void> {
  const result = await postJSON('/api/v1/auth/logout/', {});
  if (!result || typeof result !== 'object' || (result as Record<string, unknown>).authenticated !== false) {
    throw new ApiError('Could not confirm sign-out. Please try again.', 0, 'logout_unconfirmed');
  }
}
