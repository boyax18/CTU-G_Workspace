import assert from 'node:assert/strict';
import { test } from 'node:test';
import { ApiError } from '../src/api/client.ts';
import {
  describeLoginFailure, LOGIN_NOT_COMPLETED, notCompletedMessage,
} from '../src/features/auth/loginFeedback.ts';

const reference = 'b'.repeat(32);

test('credentials failure shows the shared message, approval hint and keeps the reference', () => {
  const result = describeLoginFailure(new ApiError('server text', 401, 'invalid_credentials', {}, { requestId: reference }));
  assert.equal(result.error.message, 'Unable to sign in with these credentials.');
  assert.equal(result.error.requestId, reference);
  assert.equal(result.approvalHint, true);
  assert.equal(result.recovery, null);
});

test('rate limit waits for Retry-After, defaulting to 60 seconds', () => {
  assert.deepEqual(
    [describeLoginFailure(new ApiError('x', 429, 'too_many_attempts', {}, { retryAfter: 30 })).wait,
      describeLoginFailure(new ApiError('x', 429, 'too_many_attempts')).wait],
    [30, 60],
  );
  assert.equal(describeLoginFailure(new ApiError('x', 429, 'too_many_attempts')).recovery, 'wait');
});

test('CSRF failure offers an explicit security refresh, never an automatic retry', () => {
  const result = describeLoginFailure(new ApiError('x', 403, 'csrf_failed'));
  assert.equal(result.recovery, 'security');
  assert.equal(result.approvalHint, false);
});

test('unknown outcomes require a session read before claiming failure', () => {
  for (const problem of [
    new ApiError('x', 0, 'network_error', {}, { outcomeUnknown: true }),
    new ApiError('x', 503, 'auth_unavailable', {}, { outcomeUnknown: true }),
    new ApiError('x', 0, 'invalid_session'),
    new ApiError('x', 200, 'invalid_response'),
    new TypeError('unexpected'),
  ]) assert.equal(describeLoginFailure(problem).recovery, 'confirm', String(problem.code ?? problem));
});

test('a failure before any POST (CSRF bootstrap) is shown as-is without a session read', () => {
  const result = describeLoginFailure(new ApiError('We could not refresh the security check.', 0, 'network_error'));
  assert.equal(result.recovery, null);
  assert.equal(result.error.message, 'We could not refresh the security check.');
});

test('confirmed non-completion keeps the safe server outage message, otherwise a connection message', () => {
  assert.equal(notCompletedMessage(new ApiError('Authentication is temporarily unavailable.', 503, 'auth_unavailable')),
    'Authentication is temporarily unavailable.');
  assert.equal(notCompletedMessage(new ApiError('x', 0, 'network_error')), LOGIN_NOT_COMPLETED);
});
