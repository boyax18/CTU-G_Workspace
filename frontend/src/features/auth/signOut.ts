/**
 * WF-01.04 P-01 (owner-approved 16 Nov 2026): sign out, and when the result is
 * not confirmed, read the session (GET) instead of guessing. The POST is never
 * repeated automatically, and a failed status read is never treated as signed out.
 */
import { getWorkspaceSession, logoutWorkspace } from './session.ts';
import { announceSignedOut } from '../../utils/sessionSignals.ts';

export type SignOutOutcome = 'signed_out' | 'still_signed_in' | 'unconfirmed';

export const SIGN_OUT_INCOMPLETE = 'Sign-out did not complete. Please try again.';
export const SIGN_OUT_UNCONFIRMED = 'Sign-out could not be confirmed. Check your connection and try again.';

export async function signOutWorkspace(): Promise<SignOutOutcome> {
  try {
    await logoutWorkspace();
  } catch {
    let session;
    try {
      session = await getWorkspaceSession();
    } catch {
      return 'unconfirmed';
    }
    if (session.authenticated) return 'still_signed_in';
  }
  announceSignedOut();
  return 'signed_out';
}

export function signOutMessage(outcome: Exclude<SignOutOutcome, 'signed_out'>): string {
  return outcome === 'still_signed_in' ? SIGN_OUT_INCOMPLETE : SIGN_OUT_UNCONFIRMED;
}
