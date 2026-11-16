/**
 * WF-01.04 P-02/P-03/P-04 (owner-approved 16 Nov 2026): browser signals that a
 * page should re-read GET /api/v1/auth/session/. A signal never changes state
 * by itself; only the server's session answer does. Nothing is stored.
 */

const CHANNEL_NAME = 'ctug-session';
const SIGNED_OUT = 'signed-out';
const AUTHENTICATION_REQUIRED_EVENT = 'ctug:authentication-required';

/** Tell other tabs of this browser that a sign-out was confirmed. Data-free. */
export function announceSignedOut(): void {
  if (typeof BroadcastChannel === 'undefined') return;
  try {
    const channel = new BroadcastChannel(CHANNEL_NAME);
    channel.postMessage(SIGNED_OUT);
    channel.close();
  } catch {
    /* Unsupported or blocked: other tabs still recheck when they become visible. */
  }
}

/** A protected API answered 401 (not signed in). 403 (permission denied) must never call this. */
export function notifyAuthenticationRequired(): void {
  if (typeof window === 'undefined') return;
  window.dispatchEvent(new Event(AUTHENTICATION_REQUIRED_EVENT));
}

/**
 * Call `recheck` whenever the session may have changed: another tab signed out,
 * this tab became visible again, the page was restored from the back/forward
 * cache, or a protected API reported 401. Returns an unsubscribe function.
 */
export function subscribeSessionSignals(recheck: () => void): () => void {
  if (typeof window === 'undefined') return () => {};
  const onVisibility = () => { if (document.visibilityState === 'visible') recheck(); };
  const onPageShow = (event: PageTransitionEvent) => { if (event.persisted) recheck(); };
  document.addEventListener('visibilitychange', onVisibility);
  window.addEventListener('pageshow', onPageShow);
  window.addEventListener(AUTHENTICATION_REQUIRED_EVENT, recheck);
  let channel: BroadcastChannel | null = null;
  if (typeof BroadcastChannel !== 'undefined') {
    try {
      channel = new BroadcastChannel(CHANNEL_NAME);
      // The message content is ignored beyond triggering a server check.
      channel.onmessage = () => recheck();
    } catch {
      channel = null;
    }
  }
  return () => {
    document.removeEventListener('visibilitychange', onVisibility);
    window.removeEventListener('pageshow', onPageShow);
    window.removeEventListener(AUTHENTICATION_REQUIRED_EVENT, recheck);
    channel?.close();
  };
}
