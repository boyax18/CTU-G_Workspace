import assert from 'node:assert/strict';
import { test } from 'node:test';
import { emptyRegistration, requestReapplicationLink, submitRegistration } from '../src/features/auth/registration.ts';

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
    return posts.length % 2 ? json({ csrfToken: 'csrf-token' }) : json({ message: 'accepted' }, 202);
  };
  try { await run(posts); } finally { globalThis.fetch = original; }
};

test('reapplication request has only School ID and old email', async () => {
  await withFetch(async (posts) => {
    await requestReapplicationLink(' 1000001 ', ' old@example.edu ');
    assert.equal(posts[1].url, '/api/v1/auth/reapply/link/');
    assert.deepEqual(JSON.parse(posts[1].options.body), {
      school_id: '1000001', email: 'old@example.edu',
    });
  });
});

test('verified reapplication resubmits every full form field and token', async () => {
  await withFetch(async (posts) => {
    await submitRegistration(valid, 'signed-token-example');
    assert.equal(posts[1].url, '/api/v1/auth/reapply/complete/');
    const body = JSON.parse(posts[1].options.body);
    assert.equal(body.reapplication_token, 'signed-token-example');
    assert.equal(body.password, valid.password);
    assert.deepEqual(Object.keys(body).sort(), [...Object.keys(emptyRegistration), 'reapplication_token'].sort());
  });
});

test('normal new registration does not carry a reapplication token', async () => {
  await withFetch(async (posts) => {
    await submitRegistration(valid);
    assert.equal(posts[1].url, '/api/v1/auth/register/');
    assert.equal(JSON.parse(posts[1].options.body).reapplication_token, undefined);
  });
});
