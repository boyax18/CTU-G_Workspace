import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { registerHooks } from 'node:module';
import { test } from 'node:test';
import ts from 'typescript';

// Matches the project's existing Node test loader, without changing the build config.
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
const api = await import('../src/features/admin/registrationReviewApi.ts');
const { REGISTRATION_REVIEW_LIVE_API_ENABLED } = await import('../src/features/admin/registrationReviewApiGate.ts');
hooks.deregister();

const {
  buildPendingReviewRequest,
  buildReviewDecisionRequest,
  parsePendingRegistrationPage,
  parseRegistrationReviewDecision,
  parseRegistrationReviewError,
  REGISTRATION_REJECTION_CODES,
} = contract;

// Deliberately fictional path. There is no approved route mount in Django yet.
const TEST_ROOT = '/api/v1/fictional-contract-only/';
const example = () => ({
  results: [{
    account_id: 910001,
    school_id: '9900001',
    requested_role: 'Student',
    created_at: '2026-11-10T09:15:00+08:00',
  }],
  page: 1,
  page_size: 20,
});

// Response payloads are supplied by fake data, not by HTTP.
test('parses the exact minimal pending-list envelope', () => {
  const payload = example();
  assert.deepEqual(parsePendingRegistrationPage(payload), payload);
});

test('allows empty pages without inventing a total count', () => {
  assert.deepEqual(parsePendingRegistrationPage({ results: [], page: 100, page_size: 20 }), {
    results: [], page: 100, page_size: 20,
  });
});

test('rejects unexpected or sensitive fields instead of forwarding them to the UI', () => {
  assert.throws(() => parsePendingRegistrationPage({ ...example(), total: 5 }));
  const payload = example();
  payload.results[0].email = 'must-not-display@example.invalid';
  assert.throws(() => parsePendingRegistrationPage(payload));
});

test('rejects invalid role, school ID and missing required fields', () => {
  for (const entry of [
    { ...example().results[0], requested_role: 'Admin' },
    { ...example().results[0], school_id: '' },
    { ...example().results[0], requested_role: undefined },
  ]) {
    assert.throws(() => parsePendingRegistrationPage({ ...example(), results: [entry] }));
  }
});

test('rejects invalid or duplicate account IDs', () => {
  for (const id of [0, -1, 2_147_483_648, 1.5, '910001']) {
    assert.throws(() => parsePendingRegistrationPage({ ...example(), results: [{ ...example().results[0], account_id: id }] }));
  }
  const item = example().results[0];
  assert.throws(() => parsePendingRegistrationPage({ ...example(), results: [item, item] }));
});

test('rejects malformed server timestamps without time zones', () => {
  for (const when of ['2026-11-10', '2026-11-10T09:15:00', 'invalid']) {
    assert.throws(() => parsePendingRegistrationPage({ ...example(), results: [{ ...example().results[0], created_at: when }] }));
  }
});

test('enforces the backend page size of exactly twenty', () => {
  assert.throws(() => parsePendingRegistrationPage({ ...example(), page_size: 50 }));
  assert.throws(() => parsePendingRegistrationPage({ ...example(), results: Array.from({ length: 21 }, (_, i) => ({
    ...example().results[0], account_id: 100 + i,
  })) }));
});

test('rejects invalid response pages and non-object bodies', () => {
  for (const page of [0, '1', 10001, -3, 2.5]) {
    assert.throws(() => parsePendingRegistrationPage({ ...example(), page }));
  }
  for (const value of [null, [], 'invalid', {}]) {
    assert.throws(() => parsePendingRegistrationPage(value));
  }
});

test('builds only GET Pending list with page and status', () => {
  assert.deepEqual(buildPendingReviewRequest(TEST_ROOT, 2), {
    method: 'GET', path: `${TEST_ROOT}?page=2&status=Pending`,
  });
});

test('rejects root URL attacks and unapproved path shapes', () => {
  for (const root of [
    'https://example.invalid/api/v1/review/',
    '//evil.invalid/api/',
    '/api/v1/review/?other=1',
    '/api/v1/../review/',
    '/api/v1/%2F/',
    '/api//review/',
    '/auth/review/',
  ]) {
    assert.throws(() => buildPendingReviewRequest(root));
  }
});

test('rejects page-number and account ID abuse at planning time', () => {
  for (const page of [0, -1, 10001, 1.1, '2']) {
    assert.throws(() => buildPendingReviewRequest(TEST_ROOT, page));
  }
  for (const accountId of [0, 2_147_483_648, 3.14, '1']) {
    assert.throws(() => buildReviewDecisionRequest(TEST_ROOT, accountId, 'approve'));
  }
});

test('approval request is POST with no body fields', () => {
  assert.deepEqual(buildReviewDecisionRequest(TEST_ROOT, 910001, 'approve'), {
    method: 'POST', path: `${TEST_ROOT}910001/approve/`, body: {},
  });
  assert.throws(() => buildReviewDecisionRequest(TEST_ROOT, 910001, 'approve', 'identity_mismatch'));
});

test('rejection request requires exactly one of the backend four reason codes', () => {
  assert.deepEqual([...REGISTRATION_REJECTION_CODES].sort(), [
    'incomplete_submission', 'ineligible_registration', 'identity_mismatch', 'duplicate_request',
  ].sort());
  for (const rejectionCode of REGISTRATION_REJECTION_CODES) {
    assert.deepEqual(buildReviewDecisionRequest(TEST_ROOT, 910002, 'reject', rejectionCode), {
      method: 'POST', path: `${TEST_ROOT}910002/reject/`, body: { rejection_code: rejectionCode },
    });
  }
  assert.throws(() => buildReviewDecisionRequest(TEST_ROOT, 910001, 'reject'));
  assert.throws(() => buildReviewDecisionRequest(TEST_ROOT, 910001, 'reject', 'arbitrary'));
});

test('rejects unsupported actions, never defaults to a decision', () => {
  assert.throws(() => buildReviewDecisionRequest(TEST_ROOT, 910001, 'bulk'));
});

test('accepts only the expected account and decision response', () => {
  assert.deepEqual(parseRegistrationReviewDecision({ account_id: 910001, status: 'Approved' }, 910001, 'Approved'), {
    account_id: 910001, status: 'Approved',
  });
  assert.deepEqual(parseRegistrationReviewDecision({ account_id: 910001, status: 'Rejected' }, 910001, 'Rejected'), {
    account_id: 910001, status: 'Rejected',
  });
});

test('rejects wrong target ID, wrong status, extra server fields and malformed response', () => {
  for (const data of [
    { account_id: 910002, status: 'Approved' },
    { account_id: 910001, status: 'Rejected' },
    { account_id: 910001, status: 'Approved', email: 'private' },
    { account_id: '910001', status: 'Approved' },
    null,
  ]) {
    assert.throws(() => parseRegistrationReviewDecision(data, 910001, 'Approved'));
  }
});

test('error interpreter uses fixed, non-sensitive backend status mapping', () => {
  for (const [status, code] of [
    [400, 'invalid_request'], [401, 'authentication_required'], [403, 'access_denied'],
    [404, 'request_unavailable'], [405, 'method_not_allowed'], [406, 'not_acceptable'],
    [415, 'unsupported_media_type'], [429, 'rate_limited'], [503, 'review_unavailable'],
  ]) {
    assert.equal(parseRegistrationReviewError(status, { error: { code, message: 'DO NOT DISPLAY THIS' } }).code, code);
    assert.doesNotMatch(parseRegistrationReviewError(status, { error: { code } }).message, /DO NOT/);
  }
  assert.equal(parseRegistrationReviewError(500, null).code, 'request_failed');
  assert.equal(parseRegistrationReviewError(403, { error: { code: 'unexpected' } }).code, 'request_failed');
});

test('API client remains independently hard-disabled', () => {
  assert.equal(REGISTRATION_REVIEW_LIVE_API_ENABLED, false);
});

test('all live client operations refuse before ANY HTTP request', async () => {
  let called = 0;
  const before = globalThis.fetch;
  globalThis.fetch = async () => { called += 1; throw new Error('Should never be called'); };
  try {
    await assert.rejects(api.listPendingRegistrationRequests(TEST_ROOT), (error) => error.code === 'review_unavailable' && error.status === 503);
    await assert.rejects(api.approveRegistrationRequest(TEST_ROOT, 910001), (error) => error.code === 'review_unavailable');
    await assert.rejects(api.rejectRegistrationRequest(TEST_ROOT, 910001, 'identity_mismatch'), (error) => error.code === 'review_unavailable');
    assert.equal(called, 0);
  } finally {
    globalThis.fetch = before;
  }
});

test('mock UI and dashboard are not modified or coupled to real client', () => {
  const preview = readFileSync(new URL('../src/features/admin/RegistrationReviewPreview.tsx', import.meta.url), 'utf8');
  const dashboard = readFileSync(new URL('../src/features/dashboard/SessionDashboardPage.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(preview, /registrationReviewApi(?:Contract|Gate)?/);
  assert.doesNotMatch(dashboard, /registrationReviewApi(?:Contract|Gate)?/);
  const gate = readFileSync(new URL('../src/features/admin/registrationReviewPreviewGate.ts', import.meta.url), 'utf8');
  assert.match(gate, /= false;/);
});
