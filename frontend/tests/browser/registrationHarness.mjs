// Repository UI tests: fresh headless browser profile, localhost-only, all API mocked.
// Uses the existing node:test runner and installed Edge; no real credentials/mail/DB.
import { before, after } from 'node:test';
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

async function fillRegistration(page, role = 'Student') {
  await page.getByLabel('Register as', { exact: true }).selectOption(role);
  await page.getByLabel(role === 'Instructor' ? 'Staff ID *' : 'School ID *', { exact: true }).fill('1234567');
  await page.getByLabel('Email *', { exact: true }).fill('fictional@example.edu');
  await page.getByLabel('First Name *', { exact: true }).fill('Test');
  await page.getByLabel('Last Name *', { exact: true }).fill('Applicant');
  await page.getByLabel('Password *', { exact: true }).fill('Copper!River7392');
  await page.getByLabel('Confirm Password *', { exact: true }).fill('Copper!River7392');
}


export { scene, summary, failure, reference, privateText, submitCode, fillRegistration };
