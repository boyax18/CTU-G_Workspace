import assert from 'node:assert/strict';
import { test } from 'node:test';
import { confirmPasswordReset, readResetLink, requestPasswordReset } from '../src/features/auth/passwordReset.ts';

const json = (body, status=200) => new Response(JSON.stringify(body), {status});
async function mockCalls(action) {
  const original = globalThis.fetch;
  const calls = [];
  globalThis.fetch = async (path, options) => {
    calls.push({path, options});
    return path.endsWith('/csrf/') ? json({csrfToken:'csrf-token'}) : json({message:'ok'},202);
  };
  try { await action(calls); } finally { globalThis.fetch = original; }
}

test('forgot-password includes School ID, registered email and CSRF', async () => {
  await mockCalls(async (calls) => {
    await requestPasswordReset(' 0012345 ', ' user@example.edu ');
    assert.equal(calls[1].path, '/api/v1/auth/forgot-password/');
    assert.equal(calls[1].options.headers['X-CSRFToken'], 'csrf-token');
    assert.deepEqual(JSON.parse(calls[1].options.body), {school_id:'0012345', email:'user@example.edu'});
  });
});
test('reset link is read from fragment and never constructed from a remote URL', () => {
  assert.deepEqual(readResetLink('#uid=MQ&token=abc-123'), {uid:'MQ',token:'abc-123'});
  assert.equal(readResetLink('#uid=bad%3Fvalue&token=x'), null);
  assert.equal(readResetLink('?uid=MQ&token=xyz'), null);
});
test('reset confirmation transmits token in CSRF-protected POST body', async () => {
  await mockCalls(async (calls) => {
    await confirmPasswordReset('MQ', 'abc-123', 'New!StrongPass543', 'New!StrongPass543');
    assert.equal(calls[1].path, '/api/v1/auth/reset-password/');
    assert.deepEqual(JSON.parse(calls[1].options.body), {uid:'MQ',token:'abc-123',password:'New!StrongPass543',password_confirmation:'New!StrongPass543'});
  });
});
