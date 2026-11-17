import assert from 'node:assert/strict';
import { test } from 'node:test';
import { confirmPasswordReset, requestPasswordReset, verifyPasswordResetCode } from '../src/features/auth/passwordReset.ts';

const json = (body, status = 200) => new Response(JSON.stringify(body), { status });
async function mockCalls(reply, action) {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (path, options) => {
    calls.push({ path, options });
    return path.endsWith('/csrf/') ? json({ csrfToken: 'csrf-token' }) : reply(path);
  };
  try { await action(calls); } finally { globalThis.fetch = original; }
}

test('request sends only the trimmed email with CSRF and reads the resend timing', async () => {
  await mockCalls(() => json({ status: 'code_requested', resend_after: 60, code_valid_seconds: 600 }, 202), async (calls) => {
    assert.deepEqual(await requestPasswordReset(' user@example.edu '), { resendAfter: 60, codeValidSeconds: 600 });
    assert.equal(calls[1].path, '/api/v1/auth/forgot-password/');
    assert.equal(calls[1].options.headers['X-CSRFToken'], 'csrf-token');
    assert.deepEqual(JSON.parse(calls[1].options.body), { email: 'user@example.edu' });
  });
});

test('verify posts email and code, and never reads a ticket from the body', async () => {
  await mockCalls(() => json({ status: 'verified', ticket: 'must-be-ignored' }), async (calls) => {
    assert.equal(await verifyPasswordResetCode('user@example.edu', '123456'), undefined);
    assert.equal(calls[1].path, '/api/v1/auth/forgot-password/verify/');
    assert.deepEqual(JSON.parse(calls[1].options.body), { email: 'user@example.edu', code: '123456' });
    assert.equal(calls[1].options.credentials, 'same-origin');
  });
});

test('a verify reply without the verified status is treated as unconfirmed', async () => {
  await mockCalls(() => json({ status: 'something-else' }), async () => {
    await assert.rejects(verifyPasswordResetCode('user@example.edu', '123456'), (error) => error.outcomeUnknown === true);
  });
});

test('reset posts email and passwords only; the ticket rides in the cookie', async () => {
  await mockCalls(() => json({ message: 'ok' }), async (calls) => {
    await confirmPasswordReset('user@example.edu', 'New!StrongPass543', 'New!StrongPass543');
    assert.equal(calls[1].path, '/api/v1/auth/reset-password/');
    assert.deepEqual(JSON.parse(calls[1].options.body), { email: 'user@example.edu', password: 'New!StrongPass543', password_confirmation: 'New!StrongPass543' });
  });
});
