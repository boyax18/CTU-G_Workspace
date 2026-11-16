// WF-01.04 sign-out behavior on the real dashboard; every API call is mocked.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';

const anonymous = { authenticated: false };
const signedIn = { authenticated: true, account: { school_id: '2026001', roles: ['Student'] }, permissions: [] };

/** Shared fake server: one browser session that logout ends. */
function fakeServer({ logout = 'ok', sessionAfterFailure = 'anonymous' } = {}) {
  const state = { active: true, sessionReads: 0, readsFail: false };
  const handle = ({ path, route, respond, request }) => {
    if (path.endsWith('/session/')) {
      state.sessionReads++;
      if (state.readsFail) return route.abort('failed');
      return respond(state.active ? signedIn : anonymous);
    }
    if (path.endsWith('/logout/') && request.method() === 'POST') {
      if (logout === 'ok') { state.active = false; return respond(anonymous); }
      if (sessionAfterFailure === 'anonymous') state.active = false;
      if (sessionAfterFailure === 'unreadable') state.readsFail = true;
      return route.abort('failed');
    }
    if (path.endsWith('/protected-401/')) { state.active = false; return respond({ error: { code: 'authentication_required', message: 'x' } }, 401); }
    if (path.endsWith('/protected-403/')) return respond({ error: { code: 'access_denied', message: 'x' } }, 403);
    return route.abort('failed');
  };
  return { state, handle };
}

/** A second tab in the same browser context, served by the same fake server. */
async function secondTab(page, server, { withoutBroadcastChannel = false } = {}) {
  const tab = await page.context().newPage();
  if (withoutBroadcastChannel) await tab.addInitScript(() => { delete window.BroadcastChannel; });
  const origin = new URL(page.url()).origin;
  await tab.route('**/*', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== origin) return route.abort();
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const respond = (body, status = 200) => route.fulfill({ status, contentType: 'application/json', body: JSON.stringify(body) });
    if (url.pathname.endsWith('/csrf/')) return respond({ csrfToken: 'tab-csrf' });
    return server.handle({ path: url.pathname, route, respond, request });
  });
  await tab.goto(origin + '/dashboard');
  await tab.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
  return tab;
}

const signOutButton = (page) => page.getByRole('button', { name: 'Sign out', exact: true });

test('dashboard sign-out ends the session, opens / and Back does not return to the dashboard', async () => {
  const server = fakeServer();
  await scene(server.handle, async (page, seen) => {
    await page.goto(new URL(page.url()).origin + '/dashboard');
    await signOutButton(page).press('Enter');
    await page.waitForURL((url) => url.pathname === '/');
    assert.deepEqual(seen.mutations.map((m) => m.path), ['/api/v1/auth/logout/']);
    await page.goBack();
    assert.equal(new URL(page.url()).pathname, '/');
    await page.getByLabel('School ID or Staff ID', { exact: true }).waitFor();
  }, '/');
});

test('uncertain sign-out followed by an anonymous session continues as signed out', async () => {
  const server = fakeServer({ logout: 'fail', sessionAfterFailure: 'anonymous' });
  await scene(server.handle, async (page, seen) => {
    await signOutButton(page).press('Enter');
    await page.waitForURL((url) => url.pathname === '/');
    assert.equal(seen.mutations.length, 1);
  }, '/dashboard');
});

test('uncertain sign-out with the session still active says it did not complete', async () => {
  const server = fakeServer({ logout: 'fail', sessionAfterFailure: 'active' });
  await scene(server.handle, async (page, seen) => {
    await signOutButton(page).press('Enter');
    await page.getByRole('alert').getByText('Sign-out did not complete. Please try again.').waitFor();
    assert.equal(new URL(page.url()).pathname, '/dashboard');
    assert.equal(await signOutButton(page).isEnabled(), true);
    assert.equal(seen.mutations.length, 1);
  }, '/dashboard');
});

test('a failed status check keeps the outcome uncertain with an explicit retry', async () => {
  const server = fakeServer({ logout: 'fail', sessionAfterFailure: 'unreadable' });
  await scene(server.handle, async (page, seen) => {
    await signOutButton(page).press('Enter');
    await page.getByRole('alert').getByText('Sign-out could not be confirmed. Check your connection and try again.').waitFor();
    assert.equal(new URL(page.url()).pathname, '/dashboard');
    assert.equal(await signOutButton(page).isEnabled(), true);
    assert.equal(seen.mutations.length, 1);
  }, '/dashboard');
});

test('another tab switches to Sign in required after a sign-out (BroadcastChannel)', async () => {
  const server = fakeServer();
  await scene(server.handle, async (page) => {
    const tab = await secondTab(page, server);
    await signOutButton(page).press('Enter');
    await tab.getByRole('heading', { name: 'Sign in required' }).waitFor();
    assert.ok(!(await tab.locator('body').innerText()).includes('2026001'));
  }, '/dashboard');
});

test('without BroadcastChannel another tab rechecks when it becomes visible', async () => {
  const server = fakeServer();
  await scene(server.handle, async (page) => {
    const tab = await secondTab(page, server, { withoutBroadcastChannel: true });
    await signOutButton(page).press('Enter');
    await page.waitForURL((url) => url.pathname === '/');
    assert.equal(await tab.getByRole('heading', { name: 'Sign in required' }).count(), 0);
    await tab.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
    await tab.getByRole('heading', { name: 'Sign in required' }).waitFor();
  }, '/dashboard');
});

test('a dashboard restored from the back/forward cache rechecks the session', async () => {
  const server = fakeServer();
  await scene(server.handle, async (page) => {
    server.state.active = false; // the session ended elsewhere
    await page.evaluate(() => window.dispatchEvent(new PageTransitionEvent('pageshow', { persisted: true })));
    await page.getByRole('heading', { name: 'Sign in required' }).waitFor();
  }, '/dashboard');
});

test('a protected 401 shows Sign in required, while a 403 never signs the user out', async () => {
  const server = fakeServer();
  await scene(server.handle, async (page) => {
    const call = (path) => page.evaluate(async (target) => {
      const client = await import('/src/api/client.ts');
      try { await client.getJSON(target); } catch { /* expected */ }
    }, path);
    // Let the dashboard's own initial session reads (doubled by StrictMode) finish first.
    await signOutButton(page).waitFor();
    await page.waitForTimeout(300);
    const readsBefore = server.state.sessionReads;
    await call('/api/v1/test/protected-403/');
    await page.waitForTimeout(300);
    assert.equal(server.state.sessionReads, readsBefore, '403 must not trigger a session recheck');
    await signOutButton(page).waitFor();
    await call('/api/v1/test/protected-401/');
    await page.getByRole('heading', { name: 'Sign in required' }).waitFor();
  }, '/dashboard');
});
