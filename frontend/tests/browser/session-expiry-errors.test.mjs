// WF-01.06 P-05/P-06: session-ended messaging on the real dashboard; every API call is mocked.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';

const ENDED = 'Your session has ended. Sign in again to continue.';
const anonymous = { authenticated: false };
const signedIn = { authenticated: true, account: { school_id: '2026001', roles: ['Student'] }, permissions: [] };

function server() {
  const state = { active: true, sessionReads: 0 };
  const handle = ({ path, route, respond }) => {
    if (path.endsWith('/session/')) { state.sessionReads++; return respond(state.active ? signedIn : anonymous); }
    if (path.endsWith('/protected-401/')) return respond({ error: { code: 'authentication_required', message: 'x' } }, 401);
    if (path.endsWith('/protected-403/')) return respond({ error: { code: 'access_denied', message: 'x' } }, 403);
    return route.abort('failed');
  };
  return { state, handle };
}

const callProtected = (page, path) => page.evaluate(async (target) => {
  const client = await import('/src/api/client.ts');
  try { await client.getJSON(target); } catch { /* expected */ }
}, path);

test('a server-side expiry found by a protected 401 shows the session-ended message and drops account data', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
    fake.state.active = false; // the server ended the session (idle or absolute limit)
    await callProtected(page, '/api/v1/test/protected-401/');
    const message = page.getByRole('status').filter({ hasText: ENDED });
    await message.waitFor();
    await page.getByRole('heading', { name: 'Sign in required' }).waitFor();
    assert.equal(await page.getByRole('link', { name: 'Return to sign-in' }).getAttribute('href'), '/#login');
    assert.ok(!(await page.locator('body').innerText()).includes('2026001'));
    assert.equal(await page.getByRole('button', { name: 'Sign out', exact: true }).count(), 0);
  }, '/dashboard');
});

test('an expiry noticed when the tab becomes visible shows the same message, with no polling', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
    await page.waitForTimeout(300);
    const reads = fake.state.sessionReads;
    await page.waitForTimeout(1500);
    assert.equal(fake.state.sessionReads, reads, 'no background polling');
    fake.state.active = false;
    await page.evaluate(() => document.dispatchEvent(new Event('visibilitychange')));
    await page.getByText(ENDED).waitFor();
  }, '/dashboard');
});

test('a first visit without a session keeps the ordinary sign-in text', async () => {
  const fake = server();
  fake.state.active = false;
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Sign in required' }).waitFor();
    await page.getByText('Sign in using an approved, active Workspace account.').waitFor();
    assert.equal(await page.getByText(ENDED).count(), 0);
  }, '/dashboard');
});

test('a permission denial (403) never shows the session-ended message', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
    await callProtected(page, '/api/v1/test/protected-403/');
    await page.waitForTimeout(300);
    assert.equal(await page.getByText(ENDED).count(), 0);
    await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
  }, '/dashboard');
});
