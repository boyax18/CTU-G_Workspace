/** AR-6C7E.2: offline browser<->Django contract tests.
 * Every fetch is replaced with an in-memory fake. No live endpoint is contacted.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { registerHooks } from 'node:module';
import { test } from 'node:test';
import ts from 'typescript';

const hooks = registerHooks({
  load(url, _context, nextLoad) {
    if (url.endsWith('.ts')) {
      const { outputText } = ts.transpileModule(readFileSync(new URL(url), 'utf8'), {
        compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ESNext },
      });
      return { format: 'module', source: outputText, shortCircuit: true };
    }
    return nextLoad(url);
  },
});
const contract = await import('../src/features/admin/registrationReviewApiContract.ts');
const reviewAPI = await import('../src/features/admin/registrationReviewApi.ts');
const { postJSON } = await import('../src/api/client.ts');
const { REGISTRATION_REVIEW_LIVE_API_ENABLED } = await import('../src/features/admin/registrationReviewApiGate.ts');
const { REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT } = await import('../src/features/admin/registrationReviewLiveConfig.ts');
const view = await import('../src/features/admin/registrationReviewLiveViewModel.ts');
hooks.deregister();

// PROSPECTIVE route only. Not mounted or approved anywhere in current code.
const ROUTE = '/api/v1/registration-requests/';
const record = {
  account_id: 840001,
  school_id: 'P4-TEST-STUDENT',
  requested_role: 'Student',
  created_at: '2026-11-12T10:30:00+08:00',
};
function response(status, body) {
  return { status, ok: status >= 200 && status < 300, json: async () => body };
}

// Test helper always restores the original fetch, even on failure.
async function withFakeFetch(fake, body) {
  const original = globalThis.fetch;
  globalThis.fetch = fake;
  try { return await body(); } finally { globalThis.fetch = original; }
}

test('Django pending list envelope is accepted without exposing private account fields', () => {
  const result = contract.parsePendingRegistrationPage({ results: [record], page: 1, page_size: 20 });
  assert.deepEqual(result.results[0], record);
  assert.equal(result.page_size, 20);
  assert.throws(() => contract.parsePendingRegistrationPage({
    results: [{ ...record, email: 'private@example.invalid' }], page: 1, page_size: 20,
  }));
});

test('Django page 2 / empty page contract and approved Pending-only query match client', () => {
  assert.deepEqual(contract.buildPendingReviewRequest(ROUTE, 2), {
    method: 'GET', path: `${ROUTE}?page=2&status=Pending`,
  });
  assert.deepEqual(contract.parsePendingRegistrationPage({ results: [], page: 3, page_size: 20 }), {
    results: [], page: 3, page_size: 20,
  });
  assert.throws(() => contract.buildPendingReviewRequest(ROUTE, 0));
  assert.throws(() => contract.buildPendingReviewRequest(ROUTE, 10001));
});

test('Django approval POST uses only empty JSON and exact confirmation fields', () => {
  assert.deepEqual(contract.buildReviewDecisionRequest(ROUTE, 840001, 'approve'), {
    method: 'POST', path: `${ROUTE}840001/approve/`, body: {},
  });
  assert.deepEqual(contract.parseRegistrationReviewDecision(
    { account_id: 840001, status: 'Approved' }, 840001, 'Approved',
  ), { account_id: 840001, status: 'Approved' });
  assert.throws(() => contract.parseRegistrationReviewDecision({
    account_id: 840001, status: 'Approved', role: 'Admin',
  }, 840001, 'Approved'));
});

test('Django rejection POST uses one of four codes and exact confirmation', () => {
  assert.deepEqual([...contract.REGISTRATION_REJECTION_CODES].sort(), [
    'incomplete_submission', 'ineligible_registration', 'identity_mismatch', 'duplicate_request',
  ].sort());
  assert.deepEqual(contract.buildReviewDecisionRequest(ROUTE, 840001, 'reject', 'identity_mismatch'), {
    method: 'POST', path: `${ROUTE}840001/reject/`, body: { rejection_code: 'identity_mismatch' },
  });
  assert.deepEqual(contract.parseRegistrationReviewDecision(
    { account_id: 840001, status: 'Rejected' }, 840001, 'Rejected',
  ), { account_id: 840001, status: 'Rejected' });
  assert.throws(() => contract.buildReviewDecisionRequest(ROUTE, 840001, 'reject', 'arbitrary_reason'));
});

test('backend errors map to controlled UI messages, never raw private text', () => {
  for (const [status, code] of [
    [400, 'invalid_request'], [401, 'authentication_required'], [403, 'access_denied'],
    [404, 'request_unavailable'], [429, 'rate_limited'], [503, 'review_unavailable'],
  ]) {
    assert.equal(contract.parseRegistrationReviewError(status, { error: { code } }).code, code);
  }
  assert.doesNotMatch(view.safeReviewError({
    code: 'untrusted', message: 'password_hash=secret@example.invalid',
  }), /password_hash|secret@example/);
});

test('browser POST bootstraps CSRF then sends same-origin session credentials', async () => {
  const calls = [];
  const result = await withFakeFetch(async (path, opts) => {
    calls.push({ path, opts });
    if (calls.length === 1) return response(200, { csrfToken: 'fake-csrf-token' });
    return response(200, { account_id: 840001, status: 'Approved' });
  }, async () => postJSON(`${ROUTE}840001/approve/`, {}));
  assert.deepEqual(result, { account_id: 840001, status: 'Approved' });
  assert.equal(calls.length, 2);
  assert.equal(calls[0].path, '/api/v1/auth/csrf/');
  assert.equal(calls[0].opts.credentials, 'same-origin');
  assert.equal(calls[1].path, `${ROUTE}840001/approve/`);
  assert.equal(calls[1].opts.method, 'POST');
  assert.equal(calls[1].opts.credentials, 'same-origin');
  assert.equal(calls[1].opts.headers['X-CSRFToken'], 'fake-csrf-token');
  assert.equal(calls[1].opts.headers['Content-Type'], 'application/json');
  assert.equal(calls[1].opts.body, '{}');
});

test('CSRF bootstrap failure never reaches approval POST', async () => {
  const calls = [];
  await withFakeFetch(async (path) => {
    calls.push(path);
    return response(403, { error: { code: 'csrf_failed', message: 'Security check failed.' } });
  }, async () => assert.rejects(postJSON(`${ROUTE}840001/approve/`, {}), (error) =>
    error.status === 403 && error.code === 'csrf_failed'));
  assert.deepEqual(calls, ['/api/v1/auth/csrf/']);
});

test('ambiguous POST network failure is not retried automatically', async () => {
  const calls = [];
  await withFakeFetch(async (path) => {
    calls.push(path);
    if (calls.length === 1) return response(200, { csrfToken: 'fake-csrf-token' });
    throw new Error('Ambiguous connection drop after server may have committed');
  }, async () => assert.rejects(postJSON(`${ROUTE}840001/reject/`, { rejection_code: 'duplicate_request' }),
    (error) => error.code === 'network_error'));
  assert.equal(calls.length, 2, 'Must make exactly one decision POST');
});

test('disabled client refuses list/approve/reject without ANY browser network calls', async () => {
  assert.equal(REGISTRATION_REVIEW_LIVE_API_ENABLED, false);
  assert.equal(REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT, null);
  let calls = 0;
  await withFakeFetch(async () => { calls += 1; throw new Error('network must remain disabled'); }, async () => {
    await assert.rejects(reviewAPI.listPendingRegistrationRequests(ROUTE), (error) => error.code === 'review_unavailable');
    await assert.rejects(reviewAPI.approveRegistrationRequest(ROUTE, 840001), (error) => error.code === 'review_unavailable');
    await assert.rejects(reviewAPI.rejectRegistrationRequest(ROUTE, 840001, 'duplicate_request'),
      (error) => error.code === 'review_unavailable');
  });
  assert.equal(calls, 0);
});

test('backend URLconf is not mounted by the frontend integration', () => {
  const djangoUrls = readFileSync(new URL('../../backend/config/urls.py', import.meta.url), 'utf8');
  assert.doesNotMatch(djangoUrls, /registration_review_urls|registration-requests/);
  const dashboard = readFileSync(new URL('../src/features/dashboard/SessionDashboardPage.tsx', import.meta.url), 'utf8');
  assert.match(dashboard, /REGISTRATION_REVIEW_LIVE_API_ENABLED/);
  const candidate = readFileSync(new URL('../../backend/apps/accounts/registration_review_urls.py', import.meta.url), 'utf8');
  assert.match(candidate, /path\("", PendingRegistrationRequestsView\.as_view\(\)/);
  assert.match(candidate, /path\("<int:account_id>\/approve\/"/);
  assert.match(candidate, /path\("<int:account_id>\/reject\/"/);
});
