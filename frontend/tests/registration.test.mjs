import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, postJSON } from '../src/api/client.ts';
import { emptyRegistration, submitRegistration, validateRegistration } from '../src/features/auth/registration.ts';

const valid = { ...emptyRegistration, school_id: ' 2026-001 ', first_name: ' Maria ', last_name: 'Santos', password: 'Copper!River7392', password_confirmation: 'Copper!River7392' };
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

async function withFetch(mock, action) {
  const original = globalThis.fetch;
  globalThis.fetch = mock;
  try { await action(); } finally { globalThis.fetch = original; }
}

test('required fields and mismatched passwords are identified before submission', () => {
  assert.ok(validateRegistration(emptyRegistration).school_id);
  assert.ok(validateRegistration({ ...valid, password_confirmation: 'different' }).password_confirmation);
  assert.deepEqual(validateRegistration(valid), {});
});

test('optional email is validated only when supplied', () => {
  assert.equal(validateRegistration(valid).email, undefined);
  assert.ok(validateRegistration({ ...valid, email: 'bad' }).email);
});

test('real registration client bootstraps CSRF, includes cookies and allowlists payload', async () => {
  const calls = [];
  await withFetch(async (path, options) => {
    calls.push({ path, options });
    return calls.length === 1 ? json({ csrfToken: 'masked-token' }) : json({ message: 'accepted' }, 202);
  }, () => submitRegistration({ ...valid, is_active: true, course: 'untrusted', year_level: 'untrusted', section: 'untrusted' }));
  assert.equal(calls[0].path, '/api/v1/auth/csrf/');
  assert.equal(calls[1].path, '/api/v1/auth/register/');
  assert.equal(calls[1].options.method, 'POST');
  assert.equal(calls[0].options.credentials, 'same-origin');
  assert.equal(calls[1].options.credentials, 'same-origin');
  assert.equal(calls[1].options.headers['X-CSRFToken'], 'masked-token');
  const payload = JSON.parse(calls[1].options.body);
  assert.equal(payload.school_id, '2026-001');
  assert.equal(payload.first_name, 'Maria');
  assert.equal(payload.password, valid.password);
  assert.equal(payload.is_active, undefined);
  assert.deepEqual(Object.keys(payload).sort(), Object.keys(emptyRegistration).sort());
  for (const field of ['course', 'year_level', 'section']) assert.equal(payload[field], undefined);
});

test('Student and Instructor selections preserve the same public payload contract', async () => {
  for (const role of ['Student', 'Instructor']) {
    let posted;
    await withFetch(async (path, options) => {
      if (path.endsWith('/csrf/')) return json({ csrfToken: 'token' });
      posted = JSON.parse(options.body);
      return json({ message: 'accepted' }, 202);
    }, () => submitRegistration({ ...valid, requested_role: role, middle_name: ' Cruz ', suffix: ' Jr. ' }));
    assert.equal(posted.requested_role, role);
    assert.equal(posted.middle_name, 'Cruz');
    assert.equal(posted.suffix, 'Jr.');
    assert.deepEqual(Object.keys(posted).sort(), Object.keys(emptyRegistration).sort());
  }
});

test('required credentials and personal names remain required; optional fields remain optional', () => {
  for (const field of ['school_id', 'first_name', 'last_name', 'password', 'password_confirmation']) {
    assert.ok(validateRegistration({ ...valid, [field]: '' })[field], `${field} must be required`);
  }
  assert.deepEqual(validateRegistration({ ...valid, email: '', middle_name: '', suffix: '' }), {});
});

test('failed CSRF bootstrap prevents the POST', async () => {
  let count = 0;
  await withFetch(async () => { count++; return json({ error: { message: 'Unavailable' } }, 503); }, async () => {
    await assert.rejects(() => submitRegistration(valid), (error) => error instanceof ApiError && error.status === 503);
  });
  assert.equal(count, 1);
});

test('missing bootstrap token prevents the POST', async () => {
  let count = 0;
  await withFetch(async () => { count++; return json({}); }, async () => {
    await assert.rejects(() => submitRegistration(valid), ApiError);
  });
  assert.equal(count, 1);
});

test('API validation messages are available for accessible field errors', async () => {
  let count = 0;
  await withFetch(async () => ++count === 1 ? json({ csrfToken: 'token' }) : json({ error: {
    code: 'validation_error', message: 'Check the details.', fields: { password: ['Too common.'], extra: 42 },
  } }, 400), async () => {
    await assert.rejects(() => submitRegistration(valid), (error) => {
      assert.equal(error.code, 'validation_error');
      assert.deepEqual(error.fields, { password: ['Too common.'] });
      return true;
    });
  });
});

test('network failure after POST is never automatically retried', async () => {
  let count = 0;
  await withFetch(async () => {
    if (++count === 1) return json({ csrfToken: 'token' });
    throw new TypeError('network failed');
  }, async () => { await assert.rejects(() => submitRegistration(valid), ApiError); });
  assert.equal(count, 2);
});

test('non-JSON server errors become safe client errors', async () => {
  await withFetch(async () => new Response('<html>technical detail</html>', { status: 502 }), async () => {
    await assert.rejects(() => submitRegistration(valid), (error) => !error.message.includes('technical detail'));
  });
});

test('cross-origin API paths are refused', async () => {
  await assert.rejects(() => postJSON('https://attacker.example/api/', valid), ApiError);
});
