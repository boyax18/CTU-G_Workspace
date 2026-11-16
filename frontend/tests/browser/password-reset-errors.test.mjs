// WF-01.05 recovery pages in a real browser; every API call is mocked.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene, reference, privateText } from './registrationHarness.mjs';

const fail = (code, fields) => ({ error: { code, message: privateText, ...(fields ? { fields } : {}) } });
const LINK = '/reset-password#uid=MQ&token=abc-123';

async function requestReset(page) {
  await page.getByLabel('School ID or Staff ID', { exact: true }).fill('0012345');
  await page.getByLabel('Registered email', { exact: true }).fill('student@example.edu');
  await page.getByRole('button', { name: 'Send reset link' }).press('Enter');
}

async function submitPassword(page, password = 'New!Password643', confirmation = password) {
  await page.getByLabel('New password', { exact: true }).fill(password);
  await page.getByLabel('Confirm new password', { exact: true }).fill(confirmation);
  await page.getByRole('button', { name: 'Update password' }).press('Enter');
}

test('request shows the neutral message, the Staff ID label and the assisted-recovery hint', async () => {
  await scene(({ respond }) => respond({ message: 'If the account details match an eligible account, a password reset email will be sent.' }, 202),
    async (page, seen) => {
      await requestReset(page);
      await page.getByText('If the account details match an eligible account, a password reset email will be sent.').waitFor();
      await page.getByText('If no email arrives, your account may need assisted recovery. Contact support.').waitFor();
      assert.deepEqual(seen.mutations[0].body, { school_id: '0012345', email: 'student@example.edu' });
    }, '/forgot-password');
});

test('disabled recovery shows its own message, not the registration outage text', async () => {
  await scene(({ respond }) => respond(fail('recovery_disabled'), 503), async (page) => {
    await requestReset(page);
    const alert = page.getByRole('alert').first();
    await alert.waitFor();
    assert.match(await alert.innerText(), /Password recovery is unavailable\./);
    assert.doesNotMatch(await alert.innerText(), /Registration/);
    assert.ok(!(await page.locator('body').innerText()).includes(privateText));
  }, '/forgot-password');
});

test('request rate limit shows a countdown; CSRF failure offers a refresh without a POST', async () => {
  await scene(({ respond }) => respond(fail('too_many_attempts'), 429, { 'Retry-After': '20' }), async (page, seen) => {
    await requestReset(page);
    await page.getByText(/Try again in (20|19|18) seconds\./).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Send reset link' }).isDisabled(), true);
    assert.equal(seen.mutations.length, 1);
  }, '/forgot-password');
  await scene(({ respond }) => respond(fail('csrf_failed'), 403), async (page, seen) => {
    await requestReset(page);
    const before = seen.csrfReads;
    await page.getByRole('button', { name: 'Refresh security check' }).press('Enter');
    await page.getByText('Security check refreshed. Send the request again.').waitFor();
    assert.equal(seen.csrfReads, before + 1);
    assert.equal(seen.mutations.length, 1);
  }, '/forgot-password');
});

test('reset page removes the token from the address bar and an invalid link offers a new request', async () => {
  await scene(({ respond }) => respond(fail('reset_link_invalid'), 400), async (page, seen) => {
    await page.getByLabel('New password', { exact: true }).waitFor();
    await page.waitForFunction(() => window.location.hash === '' && window.location.pathname === '/reset-password');
    await submitPassword(page);
    const alert = page.getByRole('alert').first();
    await alert.waitFor();
    assert.match(await alert.innerText(), /This reset link is invalid or expired\. Request a new reset link\./);
    assert.match(await alert.innerText(), new RegExp(reference));
    await page.getByRole('link', { name: 'Request a new reset link' }).waitFor();
    assert.equal(await page.getByLabel('New password', { exact: true }).count(), 0);
    assert.equal(seen.mutations.length, 1);
  }, LINK);
});

test('a rejected password shows the field error and requirements and clears both fields', async () => {
  await scene(({ respond }) => respond(fail('invalid_request', { password: ['Choose a stronger password using the requirements shown.'] }), 400),
    async (page) => {
      await page.getByText(/Use at least 8 characters/).waitFor();
      await submitPassword(page, 'password1234');
      await page.locator('#reset-password-error').getByText('Choose a stronger password using the requirements shown.').waitFor();
      assert.equal(await page.getByLabel('New password', { exact: true }).inputValue(), '');
      assert.equal(await page.getByLabel('Confirm new password', { exact: true }).inputValue(), '');
      assert.equal(await page.getByLabel('New password', { exact: true }).getAttribute('aria-invalid'), 'true');
    }, LINK);
});

test('an unknown reset outcome says it could not be confirmed and does not repeat the POST', async () => {
  await scene(({ route }) => route.abort('failed'), async (page, seen) => {
    await submitPassword(page);
    const alert = page.getByRole('alert').first();
    await alert.waitFor();
    assert.match(await alert.innerText(), /We could not confirm whether your password was changed/);
    assert.doesNotMatch(await alert.innerText(), /invalid or expired/);
    assert.equal(seen.mutations.length, 1);
    await page.getByRole('button', { name: 'Update password' }).waitFor();
  }, LINK);
});

test('a successful reset confirms and offers sign-in', async () => {
  await scene(({ respond }) => respond({ message: 'Password changed. You can now sign in.' }), async (page, seen) => {
    await submitPassword(page);
    await page.getByText('Password changed. You can now sign in.').waitFor();
    assert.deepEqual(Object.keys(seen.mutations[0].body).sort(), ['password', 'password_confirmation', 'token', 'uid']);
  }, LINK);
});
