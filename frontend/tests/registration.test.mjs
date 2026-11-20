import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, postJSON } from '../src/api/client.ts';
import { cancelRegistrationVerification, emptyRegistration, getRegistrationVerification, resendRegistrationCode, submitRegistration, validateRegistration, verifyRegistrationCode } from '../src/features/auth/registration.ts';

const valid = { ...emptyRegistration, school_id: ' 0012345 ', email: 'registrant@example.edu', first_name: ' Maria ', last_name: 'Santos', password: 'Copper!River7392', password_confirmation: 'Copper!River7392' };
const json = (body, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });
const verification = { status: 'verification_required', delivery_sent: true, expires_in: 1800, retry_after: 60, resends_remaining: 3, attempts_remaining: 5 };

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

test('email is required and CTU-G IDs have 1–7 ASCII digits', () => {
  assert.equal(validateRegistration(valid).email, undefined);
  assert.ok(validateRegistration({ ...valid, email: '' }).email);
  assert.ok(validateRegistration({ ...valid, email: 'bad' }).email);
  for (const school_id of ['12345678', 'CTU1234', '123-456', '１２３']) {
    assert.ok(validateRegistration({ ...valid, school_id }).school_id);
  }
  assert.deepEqual(validateRegistration({ ...valid, school_id: '0000001' }), {});
});

test('real registration client bootstraps CSRF, includes cookies and allowlists payload', async () => {
  const calls = [];
  await withFetch(async (path, options) => {
    calls.push({ path, options });
    return calls.length === 1 ? json({ csrfToken: 'masked-token' }) : json(verification, 202);
  }, () => submitRegistration({ ...valid, is_active: true, course: 'untrusted', year_level: 'untrusted', section: 'untrusted' }));
  assert.equal(calls[0].path, '/api/v1/auth/csrf/');
  assert.equal(calls[1].path, '/api/v1/auth/register/');
  assert.equal(calls[1].options.method, 'POST');
  assert.equal(calls[0].options.credentials, 'same-origin');
  assert.equal(calls[1].options.credentials, 'same-origin');
  assert.equal(calls[1].options.headers['X-CSRFToken'], 'masked-token');
  const payload = JSON.parse(calls[1].options.body);
  assert.equal(payload.school_id, '0012345');
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
      return json(role === 'Student' ? verification : { ...verification, requested_role: 'Instructor', email: valid.email, otp_expires_in: 600 }, 202);
    }, () => submitRegistration({ ...valid, requested_role: role, middle_name: ' Cruz ', suffix: ' Jr. ' }));
    assert.equal(posted.requested_role, role);
    assert.equal(posted.middle_name, 'Cruz');
    assert.equal(posted.suffix, 'Jr.');
    assert.deepEqual(Object.keys(posted).sort(), Object.keys(emptyRegistration).sort());
  }
});

test('required credentials and personal names remain required; optional fields remain optional', () => {
  for (const field of ['school_id', 'email', 'first_name', 'last_name', 'password', 'password_confirmation']) {
    assert.ok(validateRegistration({ ...valid, [field]: '' })[field], `${field} must be required`);
  }
  assert.deepEqual(validateRegistration({ ...valid, middle_name: '', suffix: '' }), {});
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
      assert.deepEqual(error.fields, { password: ['Choose a stronger password using the requirements shown.'] });
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

test('Student submission exposes verification-required result, without storing a browser token in application state', async () => {
  await withFetch(async (path) => path.endsWith('/csrf/') ? json({ csrfToken: 'token' }) : json(verification, 202), async () => {
    const result = await submitRegistration(valid);
    assert.equal(result.status, 'verification_required');
    assert.equal(result.browser_token, undefined);
  });
});

test('resume reads only cookie-bound verification status with no identity in URL or payload', async () => {
  await withFetch(async (path, options) => {
    assert.equal(path, '/api/v1/auth/register/verification/');
    assert.equal(options.credentials, 'same-origin');
    assert.equal(options.cache, 'no-store');
    assert.equal(options.body, undefined);
    return json(verification, 202);
  }, async () => assert.equal((await getRegistrationVerification()).attempts_remaining, 5));
});

test('OTP verify, resend and cancel use CSRF-protected POST and only their expected payload', async () => {
  for (const [action, expectedPath, expectedPayload] of [
    [() => verifyRegistrationCode('012345'), 'verify', { code: '012345' }],
    [resendRegistrationCode, 'resend', {}], [cancelRegistrationVerification, 'cancel', {}],
  ]) {
    const calls = [];
    await withFetch(async (path, options) => {
      calls.push({ path, options });
      return path.endsWith('/csrf/') ? json({ csrfToken: 'otp-csrf' }) : json(expectedPath === 'verify' ? { status: 'completed' } : expectedPath === 'cancel' ? { status: 'cancelled' } : verification);
    }, action);
    assert.equal(calls[1].path, `/api/v1/auth/register/${expectedPath}/`);
    assert.equal(calls[1].options.headers['X-CSRFToken'], 'otp-csrf');
    assert.equal(calls[1].options.credentials, 'same-origin');
    assert.deepEqual(JSON.parse(calls[1].options.body), expectedPayload);
  }
});

test('failed OTP and delivery responses remain errors rather than registration success', async () => {
  for (const code of ['otp_invalid', 'otp_expired', 'attempts_exhausted', 'delivery_failed', 'conflict']) {
    await withFetch(async (path) => path.endsWith('/csrf/') ? json({ csrfToken: 'token' }) : json({ error: { code, message: 'Could not complete verification.' } }, 400), async () => {
      await assert.rejects(() => verifyRegistrationCode('123456'), error => error instanceof ApiError && error.code === code);
    });
  }
});
