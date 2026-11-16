import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError, API_MESSAGES } from '../src/api/client.ts';
import {
  describeRecoveryFailure, RECOVERY_REQUEST_UNCERTAIN, RECOVERY_RESET_UNCERTAIN,
} from '../src/features/auth/passwordReset.ts';

test('invalid or expired link is its own outcome with the shared message', () => {
  assert.equal(API_MESSAGES.reset_link_invalid, 'This reset link is invalid or expired. Request a new reset link.');
  assert.equal(describeRecoveryFailure(new ApiError(API_MESSAGES.reset_link_invalid, 400, 'reset_link_invalid'), 'reset').kind, 'link_invalid');
});

test('field errors, rate limits and CSRF failures get specific outcomes', () => {
  assert.equal(describeRecoveryFailure(new ApiError('x', 400, 'invalid_request', { password: ['p'] }), 'reset').kind, 'fields');
  const wait = describeRecoveryFailure(new ApiError('x', 429, 'too_many_attempts', {}, { retryAfter: 42 }), 'request');
  assert.deepEqual([wait.kind, wait.wait], ['wait', 42]);
  assert.equal(describeRecoveryFailure(new ApiError('x', 403, 'csrf_failed'), 'request').kind, 'security');
});

test('an unknown reset outcome never claims the link is invalid', () => {
  const reset = describeRecoveryFailure(new ApiError('x', 0, 'network_error', {}, { outcomeUnknown: true, requestId: 'c'.repeat(32) }), 'reset');
  assert.equal(reset.kind, 'uncertain');
  assert.equal(reset.error.message, RECOVERY_RESET_UNCERTAIN);
  assert.equal(reset.error.requestId, 'c'.repeat(32));
  assert.equal(describeRecoveryFailure(new TypeError('x'), 'request').error.message, RECOVERY_REQUEST_UNCERTAIN);
});

test('disabled and unavailable recovery are definite refusals, not uncertain outcomes', () => {
  for (const code of ['recovery_disabled', 'recovery_unavailable']) {
    const result = describeRecoveryFailure(new ApiError(API_MESSAGES[code], 503, code, {}, { outcomeUnknown: true }), 'reset');
    assert.equal(result.kind, 'other', code);
    assert.equal(result.error.message, API_MESSAGES[code]);
  }
});
