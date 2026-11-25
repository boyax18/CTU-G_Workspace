// WF-01.05 CR-01 three-step recovery in a real browser; every API call is mocked.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene, reference, privateText } from './registrationHarness.mjs';

// The assisted-recovery UI is build-gated (default off); this isolated test server turns it on.
process.env.VITE_WORKSPACE_ASSISTED_RECOVERY_ENABLED = '1';

const fail = (code, fields) => ({ error: { code, message: privateText, ...(fields ? { fields } : {}) } });
const sent = { status: 'code_requested', message: 'x', resend_after: 60, code_valid_seconds: 600 };

/** A fake server for the three steps; `overrides[path]` replaces a step's reply. */
function server(overrides = {}) {
  return ({ path, respond, route }) => {
    for (const [suffix, reply] of Object.entries(overrides)) if (path.endsWith(suffix)) return reply({ respond, route });
    if (path.endsWith('/forgot-password/verify/')) return respond({ status: 'verified' }, 200, { 'Set-Cookie': 'ctug_password_reset_ticket=t; Path=/api/v1/auth/reset-password/; HttpOnly; SameSite=Strict' });
    if (path.endsWith('/account-recovery/verify/')) return respond({ status: 'verified' }, 200, { 'Set-Cookie': 'ctug_password_reset_ticket=t; Path=/api/v1/auth/reset-password/; HttpOnly; SameSite=Strict' });
    if (path.endsWith('/forgot-password/')) return respond(sent, 202);
    if (path.endsWith('/reset-password/')) return respond({ message: 'Password changed. You can now sign in.' });
    return route.abort('failed');
  };
}

async function sendEmail(page) {
  await page.getByLabel('Registered email', { exact: true }).fill('student@example.edu');
  await page.getByRole('button', { name: 'Send code' }).press('Enter');
  await page.getByLabel('Verification code', { exact: true }).waitFor();
}
async function enterCode(page, code = '123456') {
  await page.getByLabel('Verification code', { exact: true }).fill(code);
  await page.getByRole('button', { name: 'Verify code' }).press('Enter');
}
async function enterPassword(page, password = 'New!Password643') {
  await page.getByLabel('New password', { exact: true }).fill(password);
  await page.getByLabel('Confirm new password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Update password' }).press('Enter');
}

test('full flow: email, code, new password, with neutral copy and no ticket in the page', async () => {
  await scene(server(), async (page, seen) => {
    assert.equal(await page.getByLabel('CTU-G ID', { exact: true }).count(), 0);
    await sendEmail(page);
    await page.getByText('If an eligible account uses this email, a 6-digit code is on its way. It can take a few minutes; check Spam too.').waitFor();
    await page.getByText(/The code is valid for 10 minutes/).waitFor();
    await page.getByText('No email? If you never verified your email, sign in and verify it on My profile, or ask the campus administrator for an account recovery code.').waitFor();
    await enterCode(page, '123 456');
    await enterPassword(page);
    await page.getByText('Password changed. You can now sign in.').waitFor();
    assert.deepEqual(seen.mutations.map((m) => [m.path, Object.keys(m.body).sort()]), [
      ['/api/v1/auth/forgot-password/', ['email']],
      ['/api/v1/auth/forgot-password/verify/', ['code', 'email']],
      ['/api/v1/auth/reset-password/', ['email', 'password', 'password_confirmation']],
    ]);
    assert.equal(seen.mutations[1].body.code, '123456');
    assert.equal(await page.evaluate(() => document.cookie.includes('ctug_password_reset_ticket')), false);
  }, '/forgot-password');
});

test('a wrong code shows the shared message, clears the field and keeps the code step', async () => {
  await scene(server({ '/forgot-password/verify/': ({ respond }) => respond(fail('recovery_code_invalid'), 400) }), async (page, seen) => {
    await sendEmail(page);
    await enterCode(page);
    const alert = page.getByRole('alert').first();
    await alert.waitFor();
    assert.match(await alert.innerText(), /The code is incorrect or has expired\./);
    assert.match(await alert.innerText(), new RegExp(reference));
    assert.ok(!(await page.locator('body').innerText()).includes(privateText));
    assert.equal(await page.getByLabel('Verification code', { exact: true }).inputValue(), '');
    assert.equal(seen.mutations.length, 2);
  }, '/forgot-password');
});

test('resend waits for the countdown, and Start over returns to the email step', async () => {
  await scene(server(), async (page, seen) => {
    await sendEmail(page);
    assert.equal(await page.getByRole('button', { name: 'Resend code' }).isDisabled(), true);
    await page.getByText(/Resend available in (60|59|58)s/).waitFor();
    await page.getByRole('button', { name: 'Start over' }).press('Enter');
    await page.getByLabel('Registered email', { exact: true }).waitFor();
    assert.equal(seen.mutations.length, 1);
  }, '/forgot-password');
});

test('an expired verification returns to the email step with its message', async () => {
  await scene(server({ '/reset-password/': ({ respond }) => respond(fail('reset_session_invalid'), 400) }), async (page) => {
    await sendEmail(page);
    await enterCode(page);
    await enterPassword(page);
    await page.getByRole('alert').getByText('Your verification has expired. Request a new code.').waitFor();
    await page.getByLabel('Registered email', { exact: true }).waitFor();
  }, '/forgot-password');
});

test('a rejected password shows the field error and requirements and clears both fields', async () => {
  await scene(server({ '/reset-password/': ({ respond }) => respond(fail('invalid_request', { password: ['Choose a stronger password using the requirements shown.'] }), 400) }), async (page) => {
    await sendEmail(page);
    await enterCode(page);
    await page.getByText(/Use at least 8 characters/).waitFor();
    await enterPassword(page, 'password1234');
    await page.locator('#reset-password-error').getByText('Choose a stronger password using the requirements shown.').waitFor();
    assert.equal(await page.getByLabel('New password', { exact: true }).inputValue(), '');
    assert.equal(await page.getByLabel('Confirm new password', { exact: true }).inputValue(), '');
  }, '/forgot-password');
});

test('an unknown reset outcome says it could not be confirmed and does not repeat the POST', async () => {
  await scene(server({ '/reset-password/': ({ route }) => route.abort('failed') }), async (page, seen) => {
    await sendEmail(page);
    await enterCode(page);
    await enterPassword(page);
    await page.getByRole('alert').getByText(/We could not confirm whether your password was changed/).waitFor();
    assert.equal(seen.mutations.filter((m) => m.path.endsWith('/reset-password/')).length, 1);
  }, '/forgot-password');
});

test('disabled recovery and rate limits show their own messages', async () => {
  await scene(server({ '/forgot-password/': ({ respond }) => respond(fail('recovery_disabled'), 503) }), async (page) => {
    await page.getByLabel('Registered email', { exact: true }).fill('student@example.edu');
    await page.getByRole('button', { name: 'Send code' }).press('Enter');
    const alert = page.getByRole('alert').first();
    await alert.waitFor();
    assert.match(await alert.innerText(), /Password recovery is unavailable\./);
  }, '/forgot-password');
  await scene(server({ '/forgot-password/': ({ respond }) => respond(fail('too_many_attempts'), 429, { 'Retry-After': '20' }) }), async (page) => {
    await page.getByLabel('Registered email', { exact: true }).fill('student@example.edu');
    await page.getByRole('button', { name: 'Send code' }).press('Enter');
    await page.getByText(/Try again in (20|19|18) seconds\./).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Send code' }).isDisabled(), true);
  }, '/forgot-password');
});

test('old reset links land on a pointer to Forgot Password and lose their fragment', async () => {
  await scene(server(), async (page, seen) => {
    await page.getByRole('link', { name: 'Go to Forgot Password' }).waitFor();
    await page.waitForFunction(() => window.location.hash === '');
    assert.equal(seen.mutations.length, 0);
  }, '/reset-password#uid=MQ&token=abc-123');
});

test('assisted recovery: recovery code link, email + code, then the normal new-password step', async () => {
  await scene(server(), async (page, seen) => {
    await page.getByRole('button', { name: 'I have an account recovery code' }).click();
    await page.getByText(/account recovery code the campus administrator arranged/).waitFor();
    await page.getByLabel('Registered email', { exact: true }).fill('legacy@example.edu');
    await page.getByLabel('Account recovery code', { exact: true }).fill('654-321');
    await page.getByRole('button', { name: 'Verify recovery code' }).press('Enter');
    await enterPassword(page);
    await page.getByText('Password changed. You can now sign in.').waitFor();
    assert.deepEqual(seen.mutations.map((m) => [m.path, Object.keys(m.body).sort()]), [
      ['/api/v1/auth/account-recovery/verify/', ['code', 'email']],
      ['/api/v1/auth/reset-password/', ['email', 'password', 'password_confirmation']],
    ]);
    assert.equal(seen.mutations[0].body.code, '654321');
    assert.equal(await page.evaluate(() => document.cookie.includes('ctug_password_reset_ticket')), false);
  }, '/forgot-password');
});

test('assisted recovery deep link: a wrong code shows the shared neutral message and keeps the step', async () => {
  await scene(server({ '/account-recovery/verify/': ({ respond }) => respond(fail('recovery_code_invalid'), 400) }), async (page, seen) => {
    await page.getByLabel('Account recovery code', { exact: true }).waitFor();
    await page.getByLabel('Registered email', { exact: true }).fill('legacy@example.edu');
    await page.getByLabel('Account recovery code', { exact: true }).fill('111111');
    await page.getByRole('button', { name: 'Verify recovery code' }).press('Enter');
    const alert = page.getByRole('alert').first();
    await alert.waitFor();
    assert.match(await alert.innerText(), /The code is incorrect or has expired\./);
    assert.equal(await page.getByLabel('Account recovery code', { exact: true }).inputValue(), '');
    assert.equal(seen.mutations.length, 1);
    await page.getByRole('button', { name: 'Use Forgot Password with a code sent to my email instead' }).click();
    await page.getByRole('button', { name: 'Send code' }).waitFor();
  }, '/forgot-password?recovery=code');
});
