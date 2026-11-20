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
    full_name: 'Fictional Applicant',
    requested_role: 'Student',
    created_at: '2026-11-10T09:15:00+08:00',
    email_verified: false,
  }],
  page: 1,
  page_size: 20,
  has_next: false,
});

// Response payloads are supplied by fake data, not by HTTP.
test('parses the exact minimal pending-list envelope', () => {
  const payload = example();
  assert.deepEqual(parsePendingRegistrationPage(payload), payload);
});

test('allows empty pages without inventing a total count', () => {
  assert.deepEqual(parsePendingRegistrationPage({ results: [], page: 100, page_size: 20, has_next: false }), {
    results: [], page: 100, page_size: 20, has_next: false,
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
  // AR-6C7E.1 deliberately lets the dashboard read the activation gate (a boolean
  // constant) to decide whether the live panel may appear. The dashboard must still
  // never import the review API client or its contract directly.
  const reviewModules = dashboard.match(/registrationReviewApi\w*/g) ?? [];
  assert.deepEqual([...new Set(reviewModules)], ['registrationReviewApiGate']);
  assert.doesNotMatch(dashboard, /registrationReviewApi(?:Contract)?['".]/);
  const gate = readFileSync(new URL('../src/features/admin/registrationReviewPreviewGate.ts', import.meta.url), 'utf8');
  assert.match(gate, /= false;/);
});

// ---- WF-02.01 View pending applications (P-07) ----
const { PENDING_APPLICATIONS_LIST_ENABLED, PENDING_APPLICATIONS_ROUTE_ROOT } = await import('../src/features/admin/pendingApplicationsConfig.ts');
const LIST_ROOT = '/api/v1/admin/registration-requests/';

test('WF-02.01 list switch is off by default and targets the one mounted route', () => {
  assert.equal(PENDING_APPLICATIONS_LIST_ENABLED, false);
  assert.equal(PENDING_APPLICATIONS_ROUTE_ROOT, LIST_ROOT);
});

test('WF-02.01 query builder sends only validated server-side search, filters and sort', () => {
  assert.deepEqual(buildPendingReviewRequest(LIST_ROOT, 1, {}), { method: 'GET', path: `${LIST_ROOT}?page=1&status=Pending` });
  assert.deepEqual(
    buildPendingReviewRequest(LIST_ROOT, 3, { q: '  maria santos ', role: 'Instructor', proof: 'legacy', sort: '-submitted' }),
    { method: 'GET', path: `${LIST_ROOT}?page=3&status=Pending&q=maria%20santos&role=Instructor&proof=legacy&sort=-submitted` },
  );
  assert.equal(buildPendingReviewRequest(LIST_ROOT, 1, { q: '   ' }).path, `${LIST_ROOT}?page=1&status=Pending`);
  assert.match(buildPendingReviewRequest(LIST_ROOT, 1, { q: '50%_&x=1' }).path, /q=50%25_%26x%3D1$/);
});

test('WF-02.01 query builder refuses malformed or unsupported values before any request', () => {
  for (const query of [
    { q: '1'.repeat(51) }, { q: 'Ñame' }, { q: 'a\nb' }, { q: 'a b c d e f' },
    { role: 'Admin' }, { role: 'student' }, { proof: 'yes' }, { sort: 'created_at' },
    { status: 'Approved' }, { page: 2 }, null, [],
  ]) {
    assert.throws(() => buildPendingReviewRequest(LIST_ROOT, 1, query), undefined, JSON.stringify(query));
  }
  assert.equal(contract.normalizePendingSearch('  7240  '), '7240');
  assert.equal(contract.normalizePendingSearch(''), '');
});

test('WF-02.01 parser requires an accurate has_next and typed name/proof fields', () => {
  const full = (overrides = {}) => ({
    ...example(),
    results: Array.from({ length: 20 }, (_, i) => ({ ...example().results[0], account_id: 1000 + i })),
    has_next: true,
    ...overrides,
  });
  assert.equal(parsePendingRegistrationPage(full()).has_next, true);
  assert.throws(() => parsePendingRegistrationPage({ ...example(), has_next: true }), undefined, 'has_next with a short page');
  for (const hasNext of [undefined, 'false', 0, null]) {
    const payload = { ...example(), has_next: hasNext };
    if (hasNext === undefined) delete payload.has_next;
    assert.throws(() => parsePendingRegistrationPage(payload));
  }
  for (const patch of [
    { email_verified: 'true' }, { email_verified: 1 }, { email_verified: undefined },
    { full_name: '' }, { full_name: 42 }, { full_name: 'x'.repeat(401) },
  ]) {
    const payload = example();
    Object.assign(payload.results[0], patch);
    if ('email_verified' in patch && patch.email_verified === undefined) delete payload.results[0].email_verified;
    assert.throws(() => parsePendingRegistrationPage(payload), undefined, JSON.stringify(patch));
  }
  const nameless = example();
  nameless.results[0].full_name = null;
  assert.equal(parsePendingRegistrationPage(nameless).results[0].full_name, null);
});

test('WF-02.01 list client refuses without ANY request while switched off', async () => {
  let called = 0;
  const before = globalThis.fetch;
  globalThis.fetch = async () => { called += 1; throw new Error('Should never be called'); };
  try {
    await assert.rejects(api.listPendingApplications(1, { q: 'x' }), (error) => error.code === 'review_unavailable' && error.status === 503);
    assert.equal(called, 0);
  } finally {
    globalThis.fetch = before;
  }
});

test('WF-02.01 list client, when enabled, issues exactly one GET and never a write', async () => {
  const calls = [];
  const before = globalThis.fetch;
  globalThis.fetch = async (path, init) => {
    calls.push({ path, method: init.method, credentials: init.credentials, cache: init.cache });
    return { ok: true, status: 200, json: async () => example() };
  };
  try {
    const page = await api.listPendingApplications(2, { role: 'Student' }, true);
    assert.equal(page.results[0].school_id, '9900001');
  } finally {
    globalThis.fetch = before;
  }
  assert.deepEqual(calls, [{
    path: `${LIST_ROOT}?page=2&status=Pending&role=Student`, method: 'GET', credentials: 'same-origin', cache: 'no-store',
  }]);
});

// ---- WF-02.02 Verify and review applicant information (P-07) ----
const detailExample = (overrides = {}) => ({
  account_id: 910001, school_id: '7240001', id_label: 'School ID',
  name: { first: 'Maria', middle: null, last: 'Santos', suffix: null }, full_name: 'Maria Santos',
  email: 'maria@example.edu', requested_role: 'Student', request_status: 'Pending',
  created_at: '2026-11-10T09:15:00+08:00',
  email_evidence: { state: 'verified', verified_at: '2026-11-10T09:20:00+08:00' },
  institutional_check: { subject: 'enrollment', verified_by_workspace: false },
  data_notes: [],
  ...overrides,
});

test('WF-02.02 applicant query value is validated before any request', () => {
  assert.equal(contract.parseApplicantId('910001'), 910001);
  for (const raw of [null, '', '0', '-1', '01', '1.5', 'abc', '1e3', ' 1', '2147483648', '99999999999']) {
    assert.equal(contract.parseApplicantId(raw), null, String(raw));
  }
  assert.deepEqual(contract.buildApplicantDetailRequest(LIST_ROOT, 12), { method: 'GET', path: `${LIST_ROOT}12/` });
  assert.throws(() => contract.buildApplicantDetailRequest(LIST_ROOT, 0));
  assert.throws(() => contract.buildApplicantDetailRequest('//evil.invalid/api/', 12));
});

test('WF-02.02 parser accepts the four evidence states and both roles', () => {
  assert.equal(contract.parseApplicantDetail(detailExample(), 910001).email_evidence.state, 'verified');
  for (const state of ['no_proof', 'address_changed']) {
    assert.equal(contract.parseApplicantDetail(detailExample({ email_evidence: { state, verified_at: null } }), 910001).email_evidence.state, state);
  }
  const noEmail = detailExample({ email: null, email_evidence: { state: 'no_email', verified_at: null } });
  assert.equal(contract.parseApplicantDetail(noEmail, 910001).email, null);
  const instructor = detailExample({
    school_id: '0012345', id_label: 'Staff ID', requested_role: 'Instructor',
    institutional_check: { subject: 'employment', verified_by_workspace: false }, data_notes: ['missing_profile'],
  });
  assert.equal(contract.parseApplicantDetail(instructor, 910001).id_label, 'Staff ID');
});

test('WF-02.02 parser refuses extra, inconsistent or sensitive fields', () => {
  const bad = [
    detailExample({ password_hash: 'x' }),
    detailExample({ token: 'x' }),
    detailExample({ account_id: 910002 }),
    detailExample({ id_label: 'Staff ID' }),
    detailExample({ request_status: 'Approved' }),
    detailExample({ requested_role: 'Admin' }),
    detailExample({ email_evidence: { state: 'verified', verified_at: null } }),
    detailExample({ email_evidence: { state: 'no_proof', verified_at: '2026-11-10T09:20:00+08:00' } }),
    detailExample({ email_evidence: { state: 'confirmed', verified_at: null } }),
    detailExample({ email: null }),
    detailExample({ email_evidence: { state: 'no_email', verified_at: null } }),
    detailExample({ institutional_check: { subject: 'enrollment', verified_by_workspace: true } }),
    detailExample({ institutional_check: { subject: 'employment', verified_by_workspace: false } }),
    detailExample({ name: { first: 'A', middle: null, last: 'B' } }),
    detailExample({ data_notes: ['unknown'] }),
    detailExample({ data_notes: ['missing_profile', 'missing_profile'] }),
    detailExample({ email: 'not-an-email' }),
  ];
  for (const payload of bad) assert.throws(() => contract.parseApplicantDetail(payload, 910001), undefined, JSON.stringify(payload).slice(0, 80));
});

test('WF-02.02 client refuses without any request while the read switch is off, and only GETs when on', async () => {
  const calls = [];
  const before = globalThis.fetch;
  globalThis.fetch = async (path, init) => {
    calls.push({ path, method: init.method });
    return { ok: true, status: 200, json: async () => detailExample({ account_id: 12 }) };
  };
  try {
    await assert.rejects(api.getPendingApplication(12), (error) => error.code === 'review_unavailable');
    assert.equal(calls.length, 0);
    const detail = await api.getPendingApplication(12, true);
    assert.equal(detail.account_id, 12);
  } finally {
    globalThis.fetch = before;
  }
  assert.deepEqual(calls, [{ path: `${LIST_ROOT}12/`, method: 'GET' }]);
});
