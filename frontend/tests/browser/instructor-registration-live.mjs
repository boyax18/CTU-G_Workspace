// Invoked by the guarded backend acceptance script, never a development server.
// Real browser -> Vite -> Django -> disposable MySQL. No API response mocking.
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { chromium } from 'playwright-core';
import { API_MESSAGES } from '../../src/api/client.ts';

const backend = process.env.CTUG_WF0102_TEST_BACKEND || '';
const database = process.env.CTUG_WF0102_TEST_DATABASE || '';
const run = process.env.CTUG_WF0102_TEST_RUN || '';
assert.match(backend, /^http:\/\/127\.0\.0\.1:[0-9]+$/);
assert.match(database, /^test_ctug_registration_[0-9a-f]{16}$/);
assert.match(run, /^[0-9a-f]{32}$/);
const probe = await fetch(backend + '/__wf0102__/probe/');
assert.equal(probe.status, 200);
const initial = await probe.json();
assert.equal(initial.database, database);
assert.equal(initial.run_id, run);
assert.equal(initial.permanent_records, 0);

const listener = createServer();
await new Promise(resolve => listener.listen(0, '127.0.0.1', resolve));
const port = listener.address().port;
await new Promise(resolve => listener.close(resolve));
const origin = `http://127.0.0.1:${port}`;
const server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', String(port), '--strictPort'], {
  env: { ...process.env, CTUG_API_TARGET: backend }, windowsHide: true, stdio: 'ignore',
});
let browser;
try {
  const deadline = Date.now() + 30000;
  while (true) {
    try { if ((await fetch(origin)).ok) break; } catch { /* Startup observation only. */ }
    if (Date.now() >= deadline || server.exitCode !== null) throw new Error('Isolated Vite server did not start.');
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  browser = await chromium.launch({ headless: true,
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH }
      : { channel: process.env.CTUG_TEST_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : 'chromium') }),
  });
  const results = { registration_posts: 0, successful_verifications: 0, conflicts: 0, same_browser_resumes: 0, pre_otp_permanent_records: 0, confirmation_focused: true };
  const fixtureCode = process.env.CTUG_WF0102_TEST_CODE;
  assert.match(fixtureCode || '', /^[0-9]{6}$/);
  for (const attempt of [
    { school: '0054321', email: ' Instructor.Integration@EXAMPLE.EDU ', name: 'Test' },
    { school: '0054321', email: 'different@example.edu', name: 'Changed' },
    { school: '0054322', email: 'INSTRUCTOR.INTEGRATION@example.edu', name: 'Changed' },
  ]) {
    const context = await browser.newContext();
    try {
      const page = await context.newPage();
      let otpRequests = 0;
      const registrationBodies = [];
      page.setDefaultTimeout(10000);
      page.setDefaultNavigationTimeout(15000);
      await page.route('**/*', async route => {
        const request = route.request();
        const url = new URL(request.url());
        if (url.origin !== origin) return route.abort();
        if (request.method() === 'POST' && url.pathname === '/api/v1/auth/register/') {
          // Buffer the real response before React navigates; forward it unchanged.
          const upstream = await route.fetch();
          registrationBodies.push(await upstream.json());
          return route.fulfill({ response: upstream });
        }
        return route.continue();
      });
      page.on('request', request => {
        const url = new URL(request.url());
        if (request.method() === 'POST' && url.pathname === '/api/v1/auth/register/') results.registration_posts++;
        if (/\/api\/v1\/auth\/register\/.+/.test(url.pathname)) otpRequests++;
      });
      await page.goto(origin + '/register');
      await page.getByLabel('Register as', { exact: true }).selectOption('Instructor');
      await page.getByLabel('Staff ID *', { exact: true }).fill(attempt.school);
      await page.getByLabel('Email *', { exact: true }).fill(attempt.email);
      await page.getByLabel('First Name *', { exact: true }).fill(attempt.name);
      await page.getByLabel('Middle Name (optional)', { exact: true }).fill('Q.');
      await page.getByLabel('Last Name *', { exact: true }).fill('Instructor');
      await page.getByLabel('Suffix (optional)', { exact: true }).fill('Jr.');
      await page.getByLabel('Password *', { exact: true }).fill('Copper!River7392');
      await page.getByLabel('Confirm Password *', { exact: true }).fill('Copper!River7392');
      const received = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/auth/register/' && response.request().method() === 'POST');
      assert.equal(await page.getByText('03 — School Information', { exact: true }).count(), 0);
      await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
      const response = await received;
      assert.match(response.headers()['x-request-id'], /^[a-f0-9]{32}$/);
      assert.match(response.headers()['cache-control'], /no-store/);
      if (results.registration_posts > 1) {
        assert.equal(response.status(), 409);
        assert.equal(registrationBodies.at(-1).error.message, API_MESSAGES.conflict);
        await page.getByRole('alert').first().waitFor();
        assert.equal(new URL(page.url()).pathname, '/register');
        assert.equal(await page.getByLabel('Staff ID *', { exact: true }).inputValue(), attempt.school);
        assert.equal(await page.getByLabel('Password *', { exact: true }).inputValue(), '');
        assert.match(await page.locator('body').innerText(), /Check both your Staff ID and email/);
        assert.equal(await page.getByRole('link', { name: 'Sign in', exact: true }).getAttribute('href'), '/');
        assert.equal(await page.getByRole('button', { name: 'Continue your registration' }).count(), 0);
        assert.equal(otpRequests, 0);
        results.conflicts++;
        continue;
      }
      assert.equal(response.status(), 202);
      assert.equal(registrationBodies.at(-1).status, 'verification_required');
      await page.getByLabel('Verification code', { exact: true }).waitFor();
      const staged = await (await fetch(backend + '/__wf0102__/probe/')).json();
      assert.equal(staged.permanent_records, 0);
      assert.equal(staged.stages, 1);
      assert.equal(staged.mail_messages, 1);
      results.pre_otp_permanent_records = staged.permanent_records;
      assert.match(await page.locator('body').innerText(), /saved Instructor registration/);
      const ownedCookies = await context.cookies();
      const owned = ownedCookies.find(cookie => cookie.name === 'ctug_student_registration');
      assert.ok(owned?.httpOnly);
      assert.equal(owned.sameSite, 'Strict');

      // Same-browser submission continues the original encrypted attempt.
      await page.goto(origin + '/register?requested_role=Instructor');
      for (const [label, value] of [
        ['Staff ID *', attempt.school], ['Email *', 'changed@example.edu'],
        ['First Name *', 'Changed'], ['Last Name *', 'Instructor'],
        ['Password *', 'Copper!River7392'], ['Confirm Password *', 'Copper!River7392'],
      ]) await page.getByLabel(label, { exact: true }).fill(value);
      const resumed = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/auth/register/' && response.request().method() === 'POST');
      await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
      const resumedResponse = await resumed;
      assert.equal(resumedResponse.status(), 202);
      assert.equal(registrationBodies.at(-1).status, 'existing_verification');
      results.same_browser_resumes++;
      await page.getByLabel('Verification code', { exact: true }).waitFor();
      assert.match(await page.locator('body').innerText(), /saved Instructor registration/);
      assert.doesNotMatch(await page.locator('body').innerText(), /We did not send a verification code for this attempt/);
      const verified = page.waitForResponse(response => new URL(response.url()).pathname === '/api/v1/auth/register/verify/' && response.request().method() === 'POST');
      await page.getByLabel('Verification code', { exact: true }).fill(fixtureCode);
      await page.getByRole('button', { name: 'Verify and submit registration' }).press('Enter');
      assert.equal((await verified).status(), 200);
      results.successful_verifications++;
      const confirmation = page.getByRole('status').filter({ hasText: 'Registration submitted' });
      await confirmation.waitFor();
      await page.waitForFunction(() => document.activeElement?.getAttribute('role') === 'status');
      assert.match(await confirmation.innerText(), /Your account is pending administrative review/);
      assert.equal(await page.getByLabel('Password *', { exact: true }).count(), 0);
      assert.equal(await page.getByLabel('Verification code', { exact: true }).count(), 0);
      const cookies = await context.cookies();
      assert.ok(cookies.some(cookie => cookie.name === 'csrftoken'));
      assert.ok(cookies.every(cookie => !['sessionid', 'ctug_student_registration'].includes(cookie.name)));
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement?.textContent), 'Return to home');
    } finally { await context.close(); }
  }
  assert.equal(results.registration_posts, 4);
  const completed = await (await fetch(backend + '/__wf0102__/probe/')).json();
  assert.equal(completed.permanent_records, 2);
  assert.equal(completed.stages, 0);
  assert.equal(completed.mail_messages, 1);
  console.log(JSON.stringify(results));
} finally {
  await browser?.close();
  server.kill();
}
