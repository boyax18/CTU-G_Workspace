import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene, summary, failure, reference, privateText, submitCode, fillRegistration } from './registrationHarness.mjs';

test('uncertain Student submission retains explicit cookie-bound status recovery', async () => {
  await scene(({ path, route, respond }) => path.endsWith('/verification/') ? respond(summary, 202) : route.abort('failed'), async (page, seen) => {
    await fillRegistration(page, 'Student');
    await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
    const check = page.getByRole('button', { name: 'Check registration status' });
    await check.waitFor();
    assert.equal(await page.getByLabel('Register as', { exact: true }).isDisabled(), true);
    assert.equal(seen.mutations.length, 1);
    assert.equal(seen.statusReads, 0);
    await check.press('Enter');
    await page.waitForURL('**/register/verify');
    await page.getByLabel('Verification code', { exact: true }).waitFor();
    assert.ok(seen.statusReads >= 1);
    assert.equal(seen.mutations.length, 1);
  }, '/register');
});

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
    // R-06: a missing session on first load is described neutrally, not as expiry.
    assert.match(await page.getByRole('alert').first().innerText(), /No registration is waiting for email verification in this browser/);
    assert.doesNotMatch(await page.getByRole('alert').first().innerText(), /has expired/);
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
    assert.equal(new URL(page.url()).pathname, '/register');
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
    // R-08: visible text equals the accessible name; the countdown is a linked description.
    const resend = page.getByRole('button', { name: 'Resend code', exact: true });
    assert.equal((await resend.innerText()).trim(), 'Resend code');
    assert.equal(await resend.getAttribute('aria-describedby'), 'registration-resend-wait');
    assert.match(await page.locator('#registration-resend-wait').innerText(), /Resend available in [0-9]+s/);
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

// ---- WF-01 audit corrections (owner-approved 16 Nov 2026) ----

const resumedNotice = /details you just submitted were not used/;

for (const role of ['Student', 'Instructor']) {
  test(`R-05: ${role} resubmission that resumes a saved attempt explains the new details were not applied`, async () => {
    await scene(({ path, respond }) => respond({ ...summary, ...(role === 'Instructor' ? { requested_role: 'Instructor' } : {}),
      status: path.endsWith('/register/') ? 'existing_verification' : 'verification_required' }, 202), async (page, seen) => {
      await fillRegistration(page, role);
      await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
      await page.waitForURL('**/register/verify**');
      await page.getByLabel('Verification code', { exact: true }).waitFor();
      const body = await page.locator('body').innerText();
      assert.match(body, resumedNotice);
      assert.match(body, /choose Cancel registration and register again/);
      assert.ok(!body.includes('fictional@example.edu'), 'no identity is displayed');
      assert.equal(seen.mutations.length, 1);
      // One-shot: a refresh does not repeat the notice.
      await page.reload();
      await page.getByLabel('Verification code', { exact: true }).waitFor();
      assert.doesNotMatch(await page.locator('body').innerText(), resumedNotice);
    }, '/register');
  });
}

test('R-05: a fresh submission shows no resumed notice', async () => {
  await scene(({ respond }) => respond(summary, 202), async (page) => {
    await fillRegistration(page, 'Student');
    await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
    await page.getByLabel('Verification code', { exact: true }).waitFor();
    assert.doesNotMatch(await page.locator('body').innerText(), resumedNotice);
  }, '/register');
});

test('OD-3: code screen shows the configured lifetime and spam-folder hint', async () => {
  await scene(({ respond }) => respond({ ...summary, code_valid_seconds: 600 }, 202), async (page) => {
    await page.getByLabel('Verification code', { exact: true }).waitFor();
    assert.match(await page.locator('body').innerText(), /The code is valid for 10 minutes\. If you don't see the email, check your spam or junk folder\./);
  });
});

test('OD-3: guidance is hidden when no code was delivered', async () => {
  await scene(({ respond }) => respond({ ...summary, delivery_sent: false, code_valid_seconds: 600 }, 202), async (page) => {
    await page.getByLabel('Verification code', { exact: true }).waitFor();
    assert.doesNotMatch(await page.locator('body').innerText(), /check your spam or junk folder/);
  });
});

test('R-09: pasting a formatted code keeps all six digits and submits them', async () => {
  await scene(({ path, respond }) => path.endsWith('/verification/') ? respond(summary, 202) : respond({ status: 'completed' }), async (page, seen) => {
    const input = page.getByLabel('Verification code', { exact: true });
    await input.waitFor();
    // fill() inserts the whole string as one edit, like a paste; a maxlength=6
    // input would have cut "123-456" to "123-45" before digits were kept.
    await input.fill('123-456');
    assert.equal(await input.inputValue(), '123456');
    await input.press('Enter');
    await page.getByRole('status').filter({ hasText: 'Registration submitted' }).waitFor();
    assert.deepEqual(seen.mutations.at(-1).body, { code: '123456' });
  });
});

test('R-08: registration validation is announced once by the summary, with field errors still linked', async () => {
  await scene(() => { throw new Error('no request expected'); }, async (page, seen) => {
    await page.getByRole('button', { name: 'Proceed Email Verification', exact: true }).press('Enter');
    await page.getByRole('alert').first().waitFor();
    assert.equal(await page.getByRole('alert').count(), 1);
    const id = page.getByLabel('School ID *', { exact: true });
    assert.equal(await id.getAttribute('aria-invalid'), 'true');
    assert.equal(await id.getAttribute('aria-describedby'), 'register-credentials-hint register-school_id-error');
    assert.equal(seen.mutations.length, 0);
  }, '/register');
});
