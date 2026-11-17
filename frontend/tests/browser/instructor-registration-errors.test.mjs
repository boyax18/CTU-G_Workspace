import assert from 'node:assert/strict';
import { test } from 'node:test';
import { API_MESSAGES } from '../../src/api/client.ts';
import { scene, summary, failure, privateText, fillRegistration, submitCode } from './registrationHarness.mjs';

const saved = { ...summary, requested_role: 'Instructor' };
const verifyPath = '/register/verify?requested_role=Instructor';
const problem = (code, extra = {}) => failure(code, { ...saved, ...extra, status: code });

test('Instructor OTP status uses the shared Student conflict message for an untrusted HTML 409', async () => {
  await scene(({ route }) => route.fulfill({ status: 409, contentType: 'text/html', body: '<pre>' + privateText + '</pre>' }), async page => {
    const alert = page.getByRole('alert').first();
    await alert.waitFor();
    assert.ok((await alert.innerText()).includes(API_MESSAGES.conflict));
    assert.ok(!(await alert.innerText()).includes(privateText));
    assert.equal(await page.getByRole('link', { name: 'Start new registration' }).getAttribute('href'), '/register?requested_role=Instructor');
  }, verifyPath);
});

test('Instructor Staff ID form has no school section and requires OTP before School Admin confirmation', async () => {
  await scene(({ path, respond }) => path.endsWith('/verify/') ? respond({ status: 'completed', requested_role: 'Instructor' }) : respond(saved, 202), async (page, seen) => {
    await fillRegistration(page, 'Instructor');
    assert.equal(await page.getByText('03 — School Information', { exact: true }).count(), 0);
    await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
    await page.waitForURL('**/register/verify?requested_role=Instructor');
    await page.getByLabel('Verification code', { exact: true }).waitFor();
    assert.match(await page.locator('body').innerText(), /email address in your saved Instructor registration/);
    assert.match(await page.locator('body').innerText(), /No account has been created yet/);
    assert.equal(seen.mutations.length, 1);
    assert.equal(seen.mutations[0].body.requested_role, 'Instructor');
    assert.equal(seen.mutations[0].body.course, undefined);
    await submitCode(page);
    await page.getByRole('status').filter({ hasText: 'Registration submitted' }).waitFor();
    await page.waitForFunction(() => document.activeElement?.getAttribute('role') === 'status');
    assert.match(await page.locator('body').innerText(), /Your account is pending administrative review/);
    assert.equal(seen.mutations.length, 2);
  }, '/register');
});

for (const options of [
  { password_reset_enabled: false, support_contact: '' },
  { password_reset_enabled: true, support_contact: 'https://support.example.edu/help' },
  { password_reset_enabled: false, support_contact: 'javascript:alert(1)' },
]) {
  test('Instructor adopts Student conflict feedback regardless of retired action metadata: ' + JSON.stringify(options), async () => {
    await scene(({ respond }) => respond(problem('conflict', { ...options, can_continue: true }), 409), async (page, seen) => {
      await fillRegistration(page, 'Instructor');
      await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
      const alert = page.getByRole('alert').first();
      await alert.waitFor();
      assert.ok((await alert.innerText()).includes(API_MESSAGES.conflict));
      assert.match(await alert.innerText(), /Check both your Staff ID and email, then try again/);
      assert.match(await alert.innerText(), /wait for its review/);
      assert.doesNotMatch(await alert.innerText(), /PRIVATE|We did not send|Password reset is not available|School Admin office/);
      assert.equal(await page.getByLabel('Staff ID *', { exact: true }).inputValue(), '1234567');
      assert.equal(await page.getByLabel('Email *', { exact: true }).inputValue(), 'fictional@example.edu');
      assert.equal(await page.getByLabel('Password *', { exact: true }).inputValue(), '');
      assert.equal(await page.getByLabel('Confirm Password *', { exact: true }).inputValue(), '');
      assert.equal(await page.getByRole('link', { name: 'Sign in', exact: true }).getAttribute('href'), '/');
      for (const label of ['Log in', 'Reset your password', 'Contact support']) assert.equal(await page.getByRole('link', { name: label, exact: true }).count(), 0);
      assert.equal(await page.getByRole('button', { name: 'Continue your registration', exact: true }).count(), 0);
      await page.waitForFunction(() => document.activeElement?.getAttribute('role') === 'alert');
      await page.keyboard.press('Tab');
      assert.equal(await page.evaluate(() => document.activeElement?.textContent), 'Sign in');
      assert.equal(new URL(page.url()).pathname, '/register');
      assert.equal(seen.mutations.length, 1);
      assert.equal(seen.statusReads, 0);
    }, '/register');
  });
}

test('same-browser Instructor resume continues original recipient without a conflict or a second registration write', async () => {
  await scene(({ path, respond }) => respond({ ...saved, email: 'original@example.edu', status: path.endsWith('/register/') ? 'existing_verification' : 'verification_required' }, 202), async (page, seen) => {
    await fillRegistration(page, 'Instructor');
    await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
    await page.getByLabel('Verification code', { exact: true }).waitFor();
    assert.match(await page.locator('body').innerText(), /saved Instructor registration/);
    assert.doesNotMatch(await page.locator('body').innerText(), /original@example.edu/);
    assert.doesNotMatch(await page.locator('body').innerText(), /We did not send a verification code for this attempt/);
    assert.equal(seen.mutations.length, 1);
  }, '/register');
});

for (const outcome of ['network', 'malformed', 'HTML', 'structured 503', '200 error']) {
  test(`uncertain Instructor ${outcome} clears secrets and checks owned OTP status without repeating POST`, async () => {
    await scene(({ path, route, respond }) => {
      if (path.endsWith('/verification/')) return respond(saved, 202);
      if (outcome === 'network') return route.abort('failed');
      if (outcome === 'HTML') return route.fulfill({ status: 502, contentType: 'text/html', body: '<pre>' + privateText + '</pre>' });
      if (outcome === 'structured 503') return respond(problem('registration_unavailable'), 503);
      if (outcome === '200 error') return respond(problem('server_error'));
      return respond({ message: 'legacy direct acknowledgement' }, 202);
    }, async (page, seen) => {
      await fillRegistration(page, 'Instructor');
      await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
      const check = page.getByRole('button', { name: 'Check registration status', exact: true });
      await check.waitFor();
      assert.equal(await page.getByLabel('Password *', { exact: true }).inputValue(), '');
      assert.equal(await page.getByLabel('Register as', { exact: true }).isDisabled(), true);
      assert.equal(seen.mutations.length, 1);
      assert.equal(seen.statusReads, 0);
      assert.ok(!(await page.locator('body').innerText()).includes(privateText));
      await check.press('Enter');
      await page.getByLabel('Verification code', { exact: true }).waitFor();
      assert.equal(seen.mutations.length, 1);
      assert.ok(seen.statusReads >= 1);
    }, '/register');
  });
}

test('Instructor wrong OTP announces remaining attempts, clears the code and preserves field accessibility', async () => {
  await scene(({ path, respond }) => path.endsWith('/verification/') ? respond(saved, 202) : respond(problem('otp_invalid', { attempts_remaining: 4 }), 400), async (page, seen) => {
    await submitCode(page);
    await page.getByRole('alert').first().waitFor();
    assert.match(await page.locator('body').innerText(), /4 attempts remaining/);
    assert.equal(await page.getByLabel('Verification code', { exact: true }).inputValue(), '');
    assert.equal(await page.getByLabel('Verification code', { exact: true }).getAttribute('aria-invalid'), 'true');
    assert.equal(await page.getByRole('alert').first().getAttribute('aria-live'), 'assertive');
    assert.equal(seen.mutations.length, 1);
  }, verifyPath);
});

test('Instructor expired OTP uses the Student error and Resend code action', async () => {
  await scene(({ path, respond }) => path.endsWith('/verify/') ? respond(problem('otp_expired'), 400) : respond(saved, 202), async (page, seen) => {
    await submitCode(page);
    await page.getByRole('alert').first().waitFor();
    assert.match(await page.getByRole('alert').first().innerText(), /The code has expired or is unavailable. Request a new code./);
    assert.equal(await page.getByRole('button', { name: 'Send a new code', exact: true }).count(), 0);
    await page.getByRole('button', { name: 'Resend code', exact: true }).press('Enter');
    await page.getByRole('status').filter({ hasText: 'A new code was sent' }).waitFor();
    assert.equal(seen.mutations.length, 2);
    assert.equal(seen.mutations[1].path, '/api/v1/auth/register/resend/');
  }, verifyPath);
});

test('Instructor exhausted attempts use shared cancellation and expiry guidance', async () => {
  await scene(({ path, respond }) => path.endsWith('/verification/') ? respond(saved, 202) : respond(problem('attempts_exhausted', { attempts_remaining: 0, expires_in: 120, delivery_sent: false }), 400), async (page) => {
    await submitCode(page);
    await page.getByRole('alert').first().waitFor();
    assert.match(await page.locator('body').innerText(), /The attempt limit was reached. Cancel this attempt to start again/);
    assert.doesNotMatch(await page.locator('body').innerText(), /expires in \d+ seconds/);
    assert.equal(await page.getByRole('button', { name: 'Resend code', exact: true }).isDisabled(), true);
    assert.equal(await page.getByRole('button', { name: 'Cancel registration', exact: true }).isEnabled(), true);
  }, verifyPath);
});

test('Instructor delivery failure uses shared bounded resend recovery and countdown without claiming success', async () => {
  await scene(({ path, respond }) => path.endsWith('/register/') ? respond(problem('delivery_failed', { delivery_sent: false, retry_after: 2, otp_expires_in: 0 }), 503)
    : respond({ ...saved, delivery_sent: false, retry_after: 2, otp_expires_in: 0 }, 202), async (page, seen) => {
    await fillRegistration(page, 'Instructor');
    await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
    await page.getByRole('alert').first().waitFor();
    assert.match(await page.locator('body').innerText(), /could not send the verification email/);
    await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
    await page.getByRole('button', { name: 'Cancel registration', exact: true }).waitFor();
    assert.match(await page.locator('body').innerText(), /we could not send a code. Use Resend code after the waiting period/);
    const resend = page.getByRole('button', { name: 'Resend code', exact: true });
    assert.equal(await resend.isDisabled(), true);
    assert.match(await page.locator('#registration-resend-wait').innerText(), /Resend available in [12]s/);
    assert.equal(seen.mutations.length, 1);
  }, '/register');
});

test('Student-style cancellation returns Instructor to the Staff ID form', async () => {
  await scene(({ path, respond }) => path.endsWith('/cancel/') ? respond({ status: 'cancelled', requested_role: 'Instructor' }) : respond(saved, 202), async (page, seen) => {
    await page.getByRole('button', { name: 'Cancel registration', exact: true }).press('Enter');
    await page.waitForURL('**/register?requested_role=Instructor');
    await page.getByLabel('Staff ID *', { exact: true }).waitFor();
    assert.equal(await page.getByLabel('Register as', { exact: true }).inputValue(), 'Instructor');
    assert.equal(seen.mutations.length, 1);
    assert.equal(seen.mutations[0].path, '/api/v1/auth/register/cancel/');
  }, verifyPath);
});

test('Instructor overlapping submits send one registration POST', async () => {
  let release, entered;
  const pending = new Promise(resolve => { release = resolve; });
  const arrived = new Promise(resolve => { entered = resolve; });
  try {
    await scene(async ({ path, respond }) => {
      if (path.endsWith('/register/')) { entered(); await pending; }
      return respond(saved, 202);
    }, async (page, seen) => {
      await fillRegistration(page, 'Instructor');
      await page.evaluate(() => { const form = document.querySelector('form'); form.requestSubmit(); form.requestSubmit(); });
      await arrived;
      assert.equal(seen.mutations.length, 1);
      assert.equal(await page.getByRole('button', { name: 'Requesting verification…' }).isDisabled(), true);
      release();
      await page.getByLabel('Verification code', { exact: true }).waitFor();
      assert.equal(seen.mutations.length, 1);
    }, '/register');
  } finally { release(); }
});

test('Instructor CSRF failure refreshes security without a POST retry', async () => {
  await scene(({ respond }) => respond(problem('csrf_failed'), 403), async (page, seen) => {
    await fillRegistration(page, 'Instructor');
    await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
    await page.getByRole('button', { name: 'Refresh security check' }).waitFor();
    assert.equal(await page.getByLabel('Password *', { exact: true }).inputValue(), '');
    await page.getByRole('button', { name: 'Refresh security check' }).press('Enter');
    await page.getByRole('status').filter({ hasText: 'Security check refreshed' }).waitFor();
    assert.equal(seen.csrfReads, 2);
    assert.equal(seen.mutations.length, 1);
  }, '/register');
});

test('Instructor registration throttling waits without automatically resubmitting', async () => {
  await scene(({ respond }) => respond(problem('throttled', { error: { code: 'throttled', retry_after: 1 } }), 429, { 'Retry-After': '1' }), async (page, seen) => {
    await fillRegistration(page, 'Instructor');
    await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
    await page.getByRole('alert').first().waitFor();
    assert.equal(await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).isDisabled(), true);
    await page.waitForFunction(() => !document.querySelector('button[type="submit"]')?.disabled);
    assert.equal(seen.mutations.length, 1);
  }, '/register');
});
