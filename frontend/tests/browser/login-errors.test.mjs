// WF-01.03 sign-in feedback on the real home page; every API call is mocked.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene, reference, privateText } from './registrationHarness.mjs';

const anonymous = { authenticated: false };
const signedIn = { authenticated: true, account: { school_id: '2026001', roles: ['Student'] }, permissions: [] };
const loginError = (code) => ({ error: { code, message: privateText } });

async function signIn(page, id = '2026001', password = 'Copper!River7392') {
  await page.getByLabel('School ID or Staff ID', { exact: true }).fill(id);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign In', exact: true }).last().press('Enter');
}

test('wrong credentials show the shared message, approval hint and reference, and clear only the password', async () => {
  await scene(({ path, respond }) => path.endsWith('/session/') ? respond(anonymous)
    : respond(loginError('invalid_credentials'), 401), async (page, seen) => {
    await signIn(page);
    const alert = page.getByRole('alert').first();
    await alert.waitFor();
    const text = await alert.innerText();
    assert.match(text, /Unable to sign in with these credentials\./);
    assert.match(text, /may still be awaiting School Admin approval/);
    assert.match(text, new RegExp(reference));
    assert.ok(!(await page.locator('body').innerText()).includes(privateText));
    assert.equal(await page.getByLabel('Password', { exact: true }).inputValue(), '');
    assert.equal(await page.getByLabel('School ID or Staff ID', { exact: true }).inputValue(), '2026001');
    assert.equal(seen.mutations.length, 1);
    assert.deepEqual(Object.keys(seen.mutations[0].body).sort(), ['password', 'school_id']);
  }, '/');
});

test('rate limit shows a countdown and disables Sign In without retrying', async () => {
  await scene(({ path, respond }) => path.endsWith('/session/') ? respond(anonymous)
    : respond(loginError('too_many_attempts'), 429, { 'Retry-After': '30' }), async (page, seen) => {
    await signIn(page);
    await page.getByText(/Try again in (30|29|28) seconds\./).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Sign In', exact: true }).last().isDisabled(), true);
    assert.match(await page.getByRole('alert').first().innerText(), /Too many attempts/);
    assert.equal(seen.mutations.length, 1);
  }, '/');
});

test('CSRF failure offers an explicit security refresh that sends no POST', async () => {
  await scene(({ path, respond }) => path.endsWith('/session/') ? respond(anonymous)
    : respond(loginError('csrf_failed'), 403), async (page, seen) => {
    await signIn(page);
    const refresh = page.getByRole('button', { name: 'Refresh security check' });
    await refresh.waitFor();
    const csrfBefore = seen.csrfReads;
    await refresh.press('Enter');
    await page.getByText('Security check refreshed. Enter your password and sign in again.').waitFor();
    assert.equal(seen.csrfReads, csrfBefore + 1);
    assert.equal(seen.mutations.length, 1);
  }, '/');
});

test('an unknown outcome reads the session and continues when a session exists', async () => {
  let readsAfterPost = 0;
  await scene(({ path, route, respond, seen }) => {
    // The session exists only once the (aborted) login POST has reached the server.
    if (path.endsWith('/session/')) {
      if (!seen.mutations.length) return respond(anonymous);
      readsAfterPost++;
      return respond(signedIn);
    }
    return route.abort('failed');
  }, async (page, seen) => {
    await signIn(page);
    await page.waitForURL('**/dashboard');
    assert.equal(seen.mutations.length, 1);
    assert.ok(readsAfterPost >= 1);
  }, '/');
});

test('an unknown outcome with no session reports that sign-in did not complete', async () => {
  await scene(({ path, route, respond }) => path.endsWith('/session/') ? respond(anonymous) : route.abort('failed'),
    async (page, seen) => {
      await signIn(page);
      const alert = page.getByRole('alert').first();
      await alert.waitFor();
      assert.match(await alert.innerText(), /Sign-in did not complete\. Check your connection and try again\./);
      assert.equal(seen.mutations.length, 1);
    }, '/');
});

test('an existing session is offered the dashboard, and Sign Out returns to the form', async () => {
  let signedOut = false;
  await scene(({ path, respond }) => {
    if (path.endsWith('/logout/')) { signedOut = true; return respond(anonymous); }
    if (path.endsWith('/session/')) return respond(signedOut ? anonymous : signedIn);
    return respond(loginError('invalid_credentials'), 401);
  }, async (page, seen) => {
    await page.getByText('You’re signed in as').waitFor();
    assert.match(await page.locator('#login').innerText(), /2026001/);
    await page.getByRole('button', { name: 'Continue to Dashboard' }).waitFor();
    await page.getByRole('button', { name: 'Sign Out', exact: true }).last().press('Enter');
    await page.getByLabel('School ID or Staff ID', { exact: true }).waitFor();
    assert.deepEqual(seen.mutations.map((m) => m.path), ['/api/v1/auth/logout/']);
  }, '/');
});

test('successful sign-in opens the dashboard', async () => {
  await scene(({ path, respond }) => respond(path.endsWith('/login/') ? signedIn : anonymous), async (page, seen) => {
    await signIn(page);
    await page.waitForURL('**/dashboard');
    assert.deepEqual(seen.mutations.map((m) => m.path), ['/api/v1/auth/login/']);
  }, '/');
});
