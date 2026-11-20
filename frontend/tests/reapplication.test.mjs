import assert from 'node:assert/strict';
import { test } from 'node:test';
import { emptyRegistration, submitRegistration } from '../src/features/auth/registration.ts';
import * as registration from '../src/features/auth/registration.ts';

const valid = {
  ...emptyRegistration, school_id: '1000001', email: 'new@example.edu',
  first_name: 'A', last_name: 'B', password: 'NewStrongPassword!72',
  password_confirmation: 'NewStrongPassword!72',
};
const json = (body, status = 200) => new Response(JSON.stringify(body), { status });
const withFetch = async (run) => {
  const original = globalThis.fetch;
  const posts = [];
  globalThis.fetch = async (url, options) => {
    posts.push({ url, options });
    return posts.length % 2 ? json({ csrfToken: 'csrf-token' }) : json({ status: 'verification_required', delivery_sent: true, expires_in: 1800, retry_after: 60, resends_remaining: 3, attempts_remaining: 5 }, 202);
  };
  try { await run(posts); } finally { globalThis.fetch = original; }
};

test('registration client no longer exposes a reapplication link request', () => {
  assert.equal(registration.requestReapplicationLink, undefined);
});

test('a stale reapplication argument cannot redirect a standard registration', async () => {
  await withFetch(async (posts) => {
    await submitRegistration(valid, 'signed-token-example');
    assert.equal(posts[1].url, '/api/v1/auth/register/');
    const body = JSON.parse(posts[1].options.body);
    assert.equal(body.reapplication_token, undefined);
    assert.equal(body.password, valid.password);
    assert.deepEqual(Object.keys(body).sort(), Object.keys(emptyRegistration).sort());
  });
});

test('normal new registration does not carry a reapplication token', async () => {
  await withFetch(async (posts) => {
    await submitRegistration(valid);
    assert.equal(posts[1].url, '/api/v1/auth/register/');
    assert.equal(JSON.parse(posts[1].options.body).reapplication_token, undefined);
  });
});
