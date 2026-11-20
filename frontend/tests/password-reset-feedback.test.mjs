import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, API_MESSAGES } from '../src/api/client.ts';
import {
  describeRecoveryFailure, RECOVERY_REQUEST_UNCERTAIN, RECOVERY_RESET_UNCERTAIN, RECOVERY_VERIFY_UNCERTAIN,
} from '../src/features/auth/passwordReset.ts';

test('wrong or expired code and expired verification are their own outcomes', () => {
  assert.equal(API_MESSAGES.recovery_code_invalid, 'The code is incorrect or has expired.');
  assert.equal(API_MESSAGES.reset_session_invalid, 'Your verification has expired. Request a new code.');
  assert.equal(describeRecoveryFailure(new ApiError('x', 400, 'recovery_code_invalid'), 'verify').kind, 'code_invalid');
  assert.equal(describeRecoveryFailure(new ApiError('x', 400, 'reset_session_invalid'), 'reset').kind, 'session_invalid');
});

test('field errors, rate limits and CSRF failures get specific outcomes', () => {
  assert.equal(describeRecoveryFailure(new ApiError('x', 400, 'invalid_request', { password: ['p'] }), 'reset').kind, 'fields');
  const wait = describeRecoveryFailure(new ApiError('x', 429, 'too_many_attempts', {}, { retryAfter: 42 }), 'request');
  assert.deepEqual([wait.kind, wait.wait], ['wait', 42]);
  assert.equal(describeRecoveryFailure(new ApiError('x', 403, 'csrf_failed'), 'verify').kind, 'security');
});

test('unknown outcomes say which step could not be confirmed, keeping the reference', () => {
  const unknown = (step) => describeRecoveryFailure(new ApiError('x', 0, 'network_error', {}, { outcomeUnknown: true, requestId: 'c'.repeat(32) }), step);
  assert.equal(unknown('request').error.message, RECOVERY_REQUEST_UNCERTAIN);
  assert.equal(unknown('verify').error.message, RECOVERY_VERIFY_UNCERTAIN);
  assert.equal(unknown('reset').error.message, RECOVERY_RESET_UNCERTAIN);
  assert.equal(unknown('reset').error.requestId, 'c'.repeat(32));
  assert.equal(describeRecoveryFailure(new TypeError('x'), 'request').kind, 'uncertain');
});

test('disabled and unavailable recovery are definite refusals, not uncertain outcomes', () => {
  for (const code of ['recovery_disabled', 'recovery_unavailable']) {
    const result = describeRecoveryFailure(new ApiError(API_MESSAGES[code], 503, code, {}, { outcomeUnknown: true }), 'reset');
    assert.equal(result.kind, 'other', code);
    assert.equal(result.error.message, API_MESSAGES[code]);
  }
});
