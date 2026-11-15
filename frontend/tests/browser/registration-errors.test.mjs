// Repository UI tests: fresh headless browser profile, localhost-only, all API mocked.
// Uses the existing node:test runner and installed Edge; no real credentials/mail/DB.
import assert from 'node:assert/strict';
import { before, after, test } from 'node:test';
import { spawn } from 'node:child_process';
import { createServer } from 'node:net';
import { fileURLToPath } from 'node:url';
import { chromium } from 'playwright-core';

const frontend = fileURLToPath(new URL('../../', import.meta.url));
const reference = 'a'.repeat(32);
const privateText = 'PRIVATE-SMTP-OTP-654321-ENCRYPTION-KEY';
const summary = { status: 'verification_required', delivery_sent: true, expires_in: 1800, retry_after: 0, resends_remaining: 3, attempts_remaining: 5 };
const failure = (code, extra = {}) => ({ status: code, ...extra, error: { code, message: privateText, request_id: reference, ...(code === 'resend_cooldown' ? { retry_after: 30 } : {}) } });
let browser, server, origin;

before(async () => {
  const probe = createServer();
  await new Promise(resolve => probe.listen(0, '127.0.0.1', resolve));
  const port = probe.address().port;
  await new Promise(resolve => probe.close(resolve));
  origin = `http://127.0.0.1:${port}`;
  server = spawn(process.execPath, ['node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', String(port), '--strictPort'], {
    cwd: frontend, windowsHide: true, stdio: 'ignore',
  });
  const deadline = Date.now() + 30000;
  while (true) {
    try { if ((await fetch(origin)).ok) break; } catch { /* Startup observation only. */ }
    if (Date.now() >= deadline || server.exitCode !== null) throw new Error('Isolated UI test server did not start.');
    await new Promise(resolve => setTimeout(resolve, 100));
  }
  browser = await chromium.launch({ headless: true,
    ...(process.env.PLAYWRIGHT_EXECUTABLE_PATH ? { executablePath: process.env.PLAYWRIGHT_EXECUTABLE_PATH }
      : { channel: process.env.CTUG_TEST_BROWSER_CHANNEL || (process.platform === 'win32' ? 'msedge' : 'chromium') }),
  });
}, { timeout: 45000 });

after(async () => { await browser?.close(); server?.kill(); });

async function scene(handler, check, pathname = '/register/verify') {
  const context = await browser.newContext();
  const page = await context.newPage();
  const seen = { mutations: [], statusReads: 0, csrfReads: 0 };
  await page.route('**/*', async route => {
    const request = route.request();
    const url = new URL(request.url());
    if (url.origin !== origin) return route.abort();
    if (!url.pathname.startsWith('/api/')) return route.continue();
    const respond = (body, status = 200, headers = {}) => route.fulfill({ status, contentType: 'application/json',
      headers: { 'X-Request-ID': reference, ...headers }, body: JSON.stringify(body) });
    if (url.pathname.endsWith('/csrf/')) {
      seen.csrfReads++;
      return respond({ csrfToken: 'test-csrf-' + seen.csrfReads });
    }
    if (request.method() === 'POST') seen.mutations.push({ path: url.pathname, body: request.postDataJSON(), csrf: request.headers()['x-csrftoken'] });
    if (url.pathname.endsWith('/verification/')) seen.statusReads++;
    return handler({ path: url.pathname, request, route, respond, seen });
  });
  try { await page.goto(origin + pathname); await check(page, seen); }
  finally { await context.close(); }
}

async function submitCode(page) {
  await page.getByLabel('Verification code', { exact: true }).fill('123456');
  await page.getByLabel('Verification code', { exact: true }).press('Enter');
}

test('incorrect OTP announces one safe summary, clears code and supports keyboard correction', async () => {
  await scene(({ path, respond }) => path.endsWith('/verification/') ? respond(summary, 202)
    : respond(failure('otp_invalid', { ...summary, status: 'otp_invalid', attempts_remaining: 4 }), 400), async (page, seen) => {
    await submitCode(page);
    const alert = page.getByRole('alert').first();
    await alert.waitFor();
    assert.match(await alert.innerText(), /verification code is incorrect/);
    assert.equal(await alert.getAttribute('aria-live'), 'assertive');
    assert.equal(await alert.getAttribute('aria-atomic'), 'true');
    await page.waitForFunction(() => document.activeElement?.getAttribute('role') === 'alert');
    assert.match(await alert.innerText(), new RegExp(reference));
    assert.ok(!(await page.locator('body').innerText()).includes(privateText));
    const input = page.getByLabel('Verification code', { exact: true });
    assert.equal(await input.inputValue(), '');
    assert.equal(await input.getAttribute('aria-invalid'), 'true');
    assert.equal(await input.getAttribute('aria-describedby'), 'registration-otp-error');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement?.textContent), 'Enter verification code');
    await page.keyboard.press('Enter');
    assert.equal(await page.evaluate(() => document.activeElement?.id), 'registration-otp');
    assert.equal(seen.mutations.length, 1);
  });
});

test('missing or expired session shows restart with no code input or automatic write', async () => {
  await scene(({ respond }) => respond(failure('expired'), 410), async (page, seen) => {
    await page.getByRole('link', { name: 'Start new registration' }).waitFor();
    assert.equal(await page.getByLabel('Verification code', { exact: true }).count(), 0);
    assert.equal(seen.mutations.length, 0);
    assert.match(await page.getByRole('alert').first().innerText(), /registration has expired/);
    await page.waitForFunction(() => document.activeElement?.getAttribute('role') === 'alert');
    await page.keyboard.press('Tab');
    assert.equal(await page.evaluate(() => document.activeElement?.textContent), 'Start new registration');
  });
});

test('generic registration conflict retains safe inputs, clears passwords and never identifies a field', async () => {
  await scene(({ respond }) => respond(failure('conflict'), 409), async (page, seen) => {
    await page.getByLabel('School ID *', { exact: true }).fill('1234567');
    await page.getByLabel('Email *', { exact: true }).fill('fictional@example.edu');
    await page.getByLabel('First Name *', { exact: true }).fill('Test');
    await page.getByLabel('Last Name *', { exact: true }).fill('Applicant');
    await page.getByLabel('Password *', { exact: true }).fill('Copper!River7392');
    await page.getByLabel('Confirm Password *', { exact: true }).fill('Copper!River7392');
    await page.getByRole('button', { name: 'Proceed Email Verification' }).press('Enter');
    await page.getByRole('alert').first().waitFor();
    const alert = await page.getByRole('alert').first().innerText();
    assert.match(alert, /We could not complete this registration\. Please check your information or contact support\./);
    assert.match(alert, /Check both your School ID and email/);
    assert.doesNotMatch(alert, /School ID (?:is |has been )?already|email (?:is |has been )?already|PRIVATE/i);
    assert.equal(await page.getByRole('button', { name: 'Review registration details' }).count(), 0);
    assert.equal(await page.getByRole('link', { name: 'Sign in', exact: true }).getAttribute('href'), '/');
    assert.equal(await page.getByLabel('Email *', { exact: true }).inputValue(), 'fictional@example.edu');
    assert.equal(await page.getByLabel('First Name *', { exact: true }).inputValue(), 'Test');
    assert.equal(await page.getByLabel('Password *', { exact: true }).inputValue(), '');
    assert.equal(await page.getByLabel('Confirm Password *', { exact: true }).inputValue(), '');
    assert.equal(await page.getByLabel('Email *', { exact: true }).getAttribute('aria-invalid'), null);
    assert.equal(seen.mutations.length, 1);
    assert.equal(await page.getByText('Resume email verification', { exact: true }).count(), 0);
  }, '/register');
});

test('CSRF recovery refreshes security explicitly without retrying the failed POST', async () => {
  await scene(({ path, respond }) => path.endsWith('/verification/') ? respond(summary, 202) : respond(failure('csrf_failed'), 403), async (page, seen) => {
    await submitCode(page);
    await page.getByRole('button', { name: 'Refresh security check' }).press('Enter');
    await page.getByRole('status').filter({ hasText: 'Security check refreshed' }).waitFor();
    assert.equal(seen.mutations.length, 1);
    assert.equal(seen.csrfReads, 2);
    assert.equal(await page.getByLabel('Verification code', { exact: true }).inputValue(), '');
  });
});

test('resend cooldown uses a disabled native button and keeps countdown outside the alert', async () => {
  await scene(({ path, respond }) => path.endsWith('/verification/') ? respond(summary, 202)
    : respond(failure('resend_cooldown', { ...summary, status: 'resend_cooldown', retry_after: 30 }), 429, { 'Retry-After': '30' }), async (page, seen) => {
    await page.getByRole('button', { name: 'Resend code', exact: true }).press('Enter');
    await page.getByRole('alert').first().waitFor();
    assert.equal(await page.getByRole('button', { name: 'Resend code', exact: true }).isDisabled(), true);
    assert.match(await page.getByRole('button', { name: 'Resend code', exact: true }).innerText(), /Resend in [0-9]+s/);
    assert.doesNotMatch(await page.getByRole('alert').first().innerText(), /[0-9]+s/);
    assert.equal(seen.mutations.length, 1);
  });
});

test('attempt exhaustion clears/disables code and keeps explicit cancellation available', async () => {
  await scene(({ path, respond }) => path.endsWith('/verification/') ? respond(summary, 202)
    : respond(failure('attempts_exhausted', { ...summary, status: 'attempts_exhausted', attempts_remaining: 0, delivery_sent: false }), 400), async (page, seen) => {
    await submitCode(page);
    await page.getByRole('alert').first().waitFor();
    assert.equal(await page.getByLabel('Verification code', { exact: true }).inputValue(), '');
    assert.equal(await page.getByRole('button', { name: 'Verify and submit registration' }).isDisabled(), true);
    assert.equal(await page.getByRole('button', { name: 'Resend code', exact: true }).isDisabled(), true);
    assert.equal(await page.getByRole('button', { name: 'Cancel registration' }).isEnabled(), true);
    assert.equal(seen.mutations.length, 1);
  });
});

test('mail failure never claims delivery or exposes transport details', async () => {
  await scene(({ path, respond }) => path.endsWith('/verification/') ? respond({ ...summary, delivery_sent: false }, 202)
    : respond(failure('delivery_failed', { ...summary, status: 'delivery_failed', delivery_sent: false, retry_after: 60 }), 503), async (page, seen) => {
    await page.getByRole('button', { name: 'Resend code', exact: true }).press('Enter');
    await page.getByRole('alert').first().waitFor();
    assert.match(await page.getByRole('alert').first().innerText(), /could not send the verification email/);
    assert.equal(await page.getByRole('button', { name: 'Verify and submit registration' }).isDisabled(), true);
    assert.ok(!(await page.locator('body').innerText()).includes(privateText));
    assert.equal(seen.mutations.length, 1);
  });
});

test('lost POST response requires an explicit GET and does not equate 410 with failed account creation', async () => {
  await scene(({ path, respond, route, seen }) => path.endsWith('/verification/')
    ? respond(seen.mutations.length ? failure('expired') : summary, seen.mutations.length ? 410 : 202)
    : route.abort('failed'), async (page, seen) => {
    await submitCode(page);
    await page.getByRole('button', { name: 'Check registration status' }).waitFor();
    assert.equal(seen.mutations.length, 1);
    assert.equal(await page.getByLabel('Verification code', { exact: true }).count(), 0);
    const reads = seen.statusReads;
    await page.getByRole('button', { name: 'Check registration status' }).press('Enter');
    await page.getByRole('link', { name: 'Start new registration' }).waitFor();
    assert.ok(seen.statusReads > reads);
    assert.equal(seen.mutations.length, 1);
    assert.match(await page.locator('body').innerText(), /could not confirm whether the earlier registration completed/);
    assert.doesNotMatch(await page.locator('body').innerText(), /Registration submitted|No account has been created yet/);
  });
});

test('HTML server failure is safe and offers status checking without repeating verification', async () => {
  await scene(({ path, respond, route }) => path.endsWith('/verification/') ? respond(summary, 202)
    : route.fulfill({ status: 502, contentType: 'text/html', body: '<pre>' + privateText + '</pre>' }), async (page, seen) => {
    await submitCode(page);
    await page.getByRole('button', { name: 'Check registration status' }).waitFor();
    assert.equal(seen.mutations.length, 1);
    assert.ok(!(await page.locator('body').innerText()).includes(privateText));
  });
});
