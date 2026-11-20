import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError } from '../src/api/client.ts';
import { getWorkspaceSession, loginWorkspace, logoutWorkspace } from '../src/features/auth/session.ts';

const json = (body, status = 200) => new Response(JSON.stringify(body), {
  status, headers: { 'Content-Type': 'application/json' },
});
const signedIn = {
  authenticated: true,
  account: { school_id: '2026-001', roles: ['Student'] },
  permissions: [],
};

async function withFetch(mock, action) {
  const original = globalThis.fetch;
  globalThis.fetch = mock;
  try { await action(); } finally { globalThis.fetch = original; }
}

test('login uses existing CSRF-protected POST, cookies, and expected credentials only', async () => {
  const calls = [];
  await withFetch(async (path, options) => {
    calls.push({ path, options });
    return calls.length === 1 ? json({ csrfToken: 'csrf' }) : json(signedIn);
  }, async () => {
    const session = await loginWorkspace(' 2026-001 ', 'my-secret');
    assert.equal(session.account.school_id, '2026-001');
  });
  assert.deepEqual(calls.map((c) => c.path), ['/api/v1/auth/csrf/', '/api/v1/auth/login/']);
  assert.equal(calls[1].options.credentials, 'same-origin');
  assert.equal(calls[1].options.headers['X-CSRFToken'], 'csrf');
  assert.deepEqual(JSON.parse(calls[1].options.body), { school_id: '2026-001', password: 'my-secret' });
});

test('login never assumes success from an invalid or negative payload', async () => {
  await withFetch(async (path) => path.endsWith('/csrf/') ? json({ csrfToken: 'csrf' }) : json({ authenticated: false }),
    async () => assert.rejects(() => loginWorkspace('2026-001', 'pw'), ApiError));
});

test('bad credentials propagate a safe server error', async () => {
  await withFetch(async (path) => path.endsWith('/csrf/') ? json({ csrfToken: 'csrf' }) : json({ error: {
    code: 'invalid_credentials', message: 'Unable to sign in with these credentials.',
  } }, 401), async () => assert.rejects(() => loginWorkspace('2026-001', 'wrong'), (err) => {
    assert.equal(err.status, 401);
    assert.equal(err.code, 'invalid_credentials');
    return true;
  }));
});

test('session GET uses same-origin cookie and does not grant authority from a local value', async () => {
  let sent;
  await withFetch(async (url, options) => {
    sent = { url, options };
    return json(signedIn);
  }, async () => assert.deepEqual(await getWorkspaceSession(), signedIn));
  assert.equal(sent.url, '/api/v1/auth/session/');
  assert.equal(sent.options.credentials, 'same-origin');
  assert.equal(sent.options.cache, 'no-store');
});

test('anonymous session remains anonymous', async () => {
  await withFetch(async () => json({ authenticated: false }), async () => {
    assert.deepEqual(await getWorkspaceSession(), { authenticated: false });
  });
});

test('malformed session response fails closed', async () => {
  await withFetch(async () => json({ authenticated: true, account: { school_id: 'fake', roles: 'Admin' }, permissions: [] }),
    async () => assert.rejects(() => getWorkspaceSession(), ApiError));
});

test('network failures must not be interpreted as anonymous sessions', async () => {
  await withFetch(async () => { throw new TypeError('offline'); },
    async () => assert.rejects(() => getWorkspaceSession(), ApiError));
});

test('logout is a CSRF-protected POST and requires server confirmation', async () => {
  const calls = [];
  await withFetch(async (path, options) => {
    calls.push({ path, options });
    return calls.length === 1 ? json({ csrfToken: 'csrf' }) : json({ authenticated: false });
  }, logoutWorkspace);
  assert.equal(calls[1].path, '/api/v1/auth/logout/');
  assert.equal(calls[1].options.method, 'POST');
  assert.equal(calls[1].options.headers['X-CSRFToken'], 'csrf');
});

test('unconfirmed logout fails closed rather than claiming success', async () => {
  await withFetch(async (path) => path.endsWith('/csrf/') ? json({ csrfToken: 'csrf' }) : json({ authenticated: true }),
    async () => assert.rejects(logoutWorkspace, ApiError));
});
