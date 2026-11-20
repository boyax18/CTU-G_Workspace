import assert from 'node:assert/strict';
import { test } from 'node:test';
import { getJSON } from '../src/api/client.ts';
import { signOutWorkspace, signOutMessage, SIGN_OUT_INCOMPLETE, SIGN_OUT_UNCONFIRMED } from '../src/features/auth/signOut.ts';

const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const signedIn = { authenticated: true, account: { school_id: '2026001', roles: ['Student'] }, permissions: [] };

async function run(responder) {
  const calls = [];
  const original = globalThis.fetch;
  globalThis.fetch = async (path, options = {}) => {
    calls.push({ path, method: options.method ?? 'GET' });
    return responder(path, options);
  };
  try { return { outcome: await signOutWorkspace(), calls }; } finally { globalThis.fetch = original; }
}
const posts = (calls) => calls.filter((c) => c.method === 'POST').length;

test('confirmed logout is signed out without an extra session read', async () => {
  const { outcome, calls } = await run((path) => path.endsWith('/csrf/') ? json({ csrfToken: 't' }) : json({ authenticated: false }));
  assert.equal(outcome, 'signed_out');
  assert.equal(posts(calls), 1);
  assert.ok(!calls.some((c) => c.path.endsWith('/session/')));
});

test('uncertain logout followed by an anonymous session read is signed out', async () => {
  const { outcome, calls } = await run((path) => {
    if (path.endsWith('/csrf/')) return json({ csrfToken: 't' });
    if (path.endsWith('/logout/')) throw new TypeError('network');
    return json({ authenticated: false });
  });
  assert.equal(outcome, 'signed_out');
  assert.equal(posts(calls), 1, 'the POST is never repeated');
});

test('uncertain logout with the session still active reports it did not complete', async () => {
  const { outcome, calls } = await run((path) => {
    if (path.endsWith('/csrf/')) return json({ csrfToken: 't' });
    if (path.endsWith('/logout/')) return json({ error: { code: 'auth_unavailable', message: 'x' } }, 503);
    return json(signedIn);
  });
  assert.equal(outcome, 'still_signed_in');
  assert.equal(signOutMessage(outcome), SIGN_OUT_INCOMPLETE);
  assert.equal(posts(calls), 1);
});

test('a failed session read is never treated as signed out', async () => {
  const { outcome, calls } = await run((path) => {
    if (path.endsWith('/csrf/')) return json({ csrfToken: 't' });
    throw new TypeError('network');
  });
  assert.equal(outcome, 'unconfirmed');
  assert.equal(signOutMessage(outcome), SIGN_OUT_UNCONFIRMED);
  assert.equal(posts(calls), 1);
});

test('only 401 authentication_required signals a session recheck; 403 and login 401 do not', async () => {
  const original = { fetch: globalThis.fetch, window: globalThis.window };
  const target = new EventTarget();
  let signals = 0;
  target.addEventListener('ctug:authentication-required', () => { signals++; });
  globalThis.window = target;
  try {
    for (const [status, code, expected] of [[401, 'authentication_required', 1], [403, 'access_denied', 1], [401, 'invalid_credentials', 1]]) {
      globalThis.fetch = async () => json({ error: { code, message: 'x' } }, status);
      await assert.rejects(getJSON('/api/v1/protected/'));
      assert.equal(signals, expected, `${status} ${code}`);
    }
  } finally {
    globalThis.fetch = original.fetch;
    if (original.window === undefined) delete globalThis.window; else globalThis.window = original.window;
  }
});
