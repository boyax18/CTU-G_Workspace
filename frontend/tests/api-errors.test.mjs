import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, API_MESSAGES, getJSON, postJSON } from '../src/api/client.ts';
import { asApiError, clearRegistrationSecrets, registrationRecovery } from '../src/features/auth/registrationFeedback.ts';
import { submitRegistration, emptyRegistration, verifyRegistrationCode } from '../src/features/auth/registration.ts';

const ref = 'a'.repeat(32);
const secret = 'private-password-654321-cookie-key-recipient@example.edu';
const json = (value, status = 200, headers = {}) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json', ...headers } });
async function withFetch(mock, action) {
  const before = globalThis.fetch;
  globalThis.fetch = mock;
  try { return await action(); } finally { globalThis.fetch = before; }
}

test('Student and Instructor conflicts share one safe message before and after OTP', async () => {
  for (const role of ['Student', 'Instructor']) {
    for (const path of ['/api/v1/auth/register/', '/api/v1/auth/register/verify/']) {
      await withFetch(async () => json({ requested_role: role, error: { code: 'email_already_used', message: secret, fields: { email: [secret] } } }, 409), async () => {
        await assert.rejects(() => getJSON(path), error => {
          assert.equal(error.message, API_MESSAGES.conflict);
          assert.deepEqual(error.fields, {});
          assert.ok(!error.message.includes(secret));
          return true;
        });
      });
    }
  }
});

test('deprecated Instructor action metadata cannot change shared error feedback or leak into ApiError', async () => {
  await withFetch(async () => json({ requested_role: 'Instructor', support_contact: secret, password_reset_enabled: true, can_continue: true,
    error: { code: 'conflict', message: secret } }, 409), async () => {
    await assert.rejects(() => getJSON('/api/v1/auth/register/'), error => {
      assert.equal(error.message, API_MESSAGES.conflict);
      assert.equal(error.instructor, undefined);
      assert.deepEqual(error.context, {});
      assert.ok(!JSON.stringify(error).includes(secret));
      return true;
    });
  });
});

test('both role feedback paths strip field details from conflict errors', () => {
  for (const role of ['Student', 'Instructor']) {
    const error = asApiError(new ApiError(secret, 409, 'conflict', { email: [secret] }, { requestId: ref }), role);
    assert.equal(error.message, API_MESSAGES.conflict);
    assert.deepEqual(error.fields, {});
    assert.equal(error.requestId, ref);
  }
});

test('Staff ID validation retains its label in the shared error response path', async () => {
  await withFetch(async () => json({ error: { code: 'validation_error', fields: { school_id: [secret] } } }, 400), async () => {
    await assert.rejects(() => getJSON('/api/v1/auth/register/'), error => {
      assert.equal(asApiError(error, 'Instructor').fields.school_id[0], 'Staff ID must contain 1 to 7 digits only.');
      assert.equal(asApiError(error, 'Student').fields.school_id[0], 'School ID must contain 1 to 7 digits only.');
      return true;
    });
  });
});

for (const [status, code, recovery] of [
  [400, 'validation_error', 'correct'], [400, 'otp_invalid', 'correct'], [400, 'otp_expired', 'resend'],
  [400, 'attempts_exhausted', 'cancel'], [403, 'csrf_failed', 'security'], [409, 'conflict', 'restart'],
  [410, 'expired', 'restart'], [429, 'resend_cooldown', 'wait'], [429, 'resends_exhausted', 'cancel'],
  [429, 'throttled', 'wait'], [503, 'delivery_failed', 'resend'], [503, 'registration_unavailable', 'retry'],
  [500, 'server_error', 'retry'], [405, 'method_not_allowed', 'retry'], [406, 'not_acceptable', 'retry'], [415, 'unsupported_media_type', 'retry'],
]) {
  test(`${status} ${code}: safe message, request reference and ${recovery} recovery`, async () => {
    await withFetch(async () => json({ error: { code, message: secret, request_id: ref } }, status), async () => {
      await assert.rejects(() => getJSON('/api/v1/auth/register/verification/'), error => {
        assert.equal(error.status, status);
        assert.equal(error.code, code);
        assert.equal(error.message, API_MESSAGES[code]);
        assert.equal(error.requestId, ref);
        assert.equal(registrationRecovery(error, 'verification'), recovery);
        assert.ok(!error.message.includes(secret));
        return true;
      });
    });
  });
}

test('generic 409 never exposes field-specific detail, including a malformed server code', async () => {
  await withFetch(async () => json({ error: { code: 'email_exists', message: secret, fields: { email: [secret] } } }, 409), async () => {
    await assert.rejects(() => getJSON('/api/v1/auth/register/verification/'), error => {
      assert.equal(error.code, 'conflict');
      assert.equal(error.message, API_MESSAGES.conflict);
      assert.deepEqual(error.fields, {});
      assert.equal(registrationRecovery(error, 'registration'), 'correct');
      assert.equal(clearRegistrationSecrets(error), true);
      return true;
    });
  });
});

test('validation fields and references cannot echo arbitrary secret text or prototype keys', async () => {
  await withFetch(async () => json({ error: { code: 'validation_error', message: secret, request_id: secret,
    fields: { password: [secret], email: ['Enter a valid email address.'], token: [secret], constructor: [secret] } } }, 400), async () => {
    await assert.rejects(() => getJSON('/api/v1/auth/register/verification/'), error => {
      assert.deepEqual(error.fields, { password: ['Choose a stronger password using the requirements shown.'], email: ['Enter a valid email address.'] });
      assert.equal(error.requestId, '');
      assert.ok(!JSON.stringify(error).includes(secret));
      return true;
    });
  });
});

test('retry and stage metadata are bounded and the header reference is preserved', async () => {
  await withFetch(async () => json({ retry_after: 23, expires_in: 1200, delivery_sent: true, attempts_remaining: 4,
    encrypted_payload: secret, error: { code: 'resend_cooldown', request_id: 'b'.repeat(32), retry_after: 23 } }, 429,
  { 'X-Request-ID': ref, 'Retry-After': '23' }), async () => {
    await assert.rejects(() => getJSON('/api/v1/auth/register/verification/'), error => {
      assert.equal(error.retryAfter, 23);
      assert.equal(error.requestId, ref);
      assert.deepEqual(error.context, { expires_in: 1200, retry_after: 23, attempts_remaining: 4, delivery_sent: true });
      return true;
    });
  });
});

test('network failure after POST is uncertain, issued once, and requires a read before another write', async () => {
  let writes = 0;
  await withFetch(async (path) => {
    if (path.endsWith('/csrf/')) return json({ csrfToken: 'csrf' });
    writes++;
    throw new TypeError(secret);
  }, async () => {
    await assert.rejects(() => verifyRegistrationCode('123456'), error => {
      assert.equal(error.outcomeUnknown, true);
      assert.equal(registrationRecovery(error, 'verification'), 'check_status');
      assert.equal(clearRegistrationSecrets(error), true);
      assert.ok(!error.message.includes(secret));
      return true;
    });
    assert.equal(writes, 1);
  });
});

test('a bootstrap failure performs no POST and has no uncertain mutation', async () => {
  let calls = 0;
  await withFetch(async () => { calls++; throw new TypeError(secret); }, async () => {
    await assert.rejects(() => postJSON('/api/v1/auth/register/verify/', { code: '123456' }), error => !error.outcomeUnknown);
    assert.equal(calls, 1);
  });
});

test('HTML 5xx and HTTP 200 error envelopes cannot become successful verification', async () => {
  for (const response of [() => new Response('<pre>' + secret + '</pre>', { status: 502 }), () => json({ error: { code: 'server_error', message: secret } })]) {
    let writes = 0;
    await withFetch(async path => {
      if (path.endsWith('/csrf/')) return json({ csrfToken: 'csrf' });
      writes++;
      return response();
    }, async () => {
      await assert.rejects(() => verifyRegistrationCode('123456'), error => error.outcomeUnknown && !error.message.includes(secret));
      assert.equal(writes, 1);
    });
  }
});

test('a malformed positive Student acknowledgement is uncertain, not a created account', async () => {
  const data = { ...emptyRegistration, school_id: '1234567', email: 'fictional@example.edu', first_name: 'Test', last_name: 'Applicant', password: 'Copper!River7392', password_confirmation: 'Copper!River7392' };
  await withFetch(async path => path.endsWith('/csrf/') ? json({ csrfToken: 'csrf' }) : json({ message: secret }, 202), async () => {
    await assert.rejects(() => submitRegistration(data), error => error.code === 'invalid_response' && error.outcomeUnknown && !error.message.includes(secret));
  });
});

test('unknown error codes cannot smuggle secrets through ApiError properties', async () => {
  await withFetch(async () => json({ error: { code: 'otp654321', message: secret } }, 500), async () => {
    await assert.rejects(() => getJSON('/api/v1/auth/register/verification/'), error => {
      assert.equal(error.code, 'server_error');
      assert.ok(!JSON.stringify(error).includes('654321'));
      return true;
    });
  });
});

test('absent optional response headers do not hide a legacy CSRF refusal', async () => {
  await withFetch(async () => ({ status: 403, ok: false, json: async () => ({ error: { code: 'csrf_failed', message: secret } }) }), async () => {
    await assert.rejects(() => postJSON('/api/v1/auth/register/verify/', { code: '123456' }), error => {
      assert.equal(error.status, 403);
      assert.equal(error.code, 'csrf_failed');
      assert.equal(error.requestId, '');
      assert.equal(error.outcomeUnknown, false);
      return true;
    });
  });
});
