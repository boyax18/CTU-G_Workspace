import { postJSON } from '../../api/client.ts';

export async function requestPasswordReset(schoolId: string, email: string): Promise<void> {
  await postJSON('/api/v1/auth/forgot-password/', {
    school_id: schoolId.trim(), email: email.trim(),
  });
}

export async function confirmPasswordReset(uid: string, token: string, password: string, confirmation: string): Promise<void> {
  await postJSON('/api/v1/auth/reset-password/', {
    uid, token, password, password_confirmation: confirmation,
  });
}

export function readResetLink(hash: string): { uid: string; token: string } | null {
  if (!hash.startsWith('#')) return null;
  const fields = new URLSearchParams(hash.slice(1));
  const uid = fields.get('uid');
  const token = fields.get('token');
  if (!uid || !token || !/^[a-zA-Z0-9_-]{1,40}$/.test(uid) || !/^[a-zA-Z0-9-]{1,150}$/.test(token)) return null;
  return { uid, token };
}
