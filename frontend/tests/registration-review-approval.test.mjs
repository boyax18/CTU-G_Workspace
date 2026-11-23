// WF-02.03 Approve applicant account (P-08): approval contract and client. Every request is mocked.
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
const api = await import('../src/features/admin/registrationReviewApi.ts');
const config = await import('../src/features/admin/pendingApplicationsConfig.ts');
hooks.deregister();

const ROOT = '/api/v1/admin/registration-requests/';
const STUDENT = 'ctu_main_system_records';
const INSTRUCTOR = 'institutional_employment_records';

const reply = (status, body) => ({ ok: status >= 200 && status < 300, status, headers: new Headers(), json: async () => {
  if (body === undefined) throw new SyntaxError('not json');
  return body;
} });

/** Mock fetch: the CSRF bootstrap answers normally; `post` decides the approval POST. */
async function withFetch(post, run, { csrf = () => reply(200, { csrfToken: 'tok' }) } = {}) {
  const calls = [];
  const before = globalThis.fetch;
  globalThis.fetch = async (path, init = {}) => {
    calls.push({ path, method: init.method ?? 'GET', body: init.body, csrf: init.headers?.['X-CSRFToken'] });
    if (path === '/api/v1/auth/csrf/') return csrf();
    return post();
  };
  try { return await run(calls); } finally { globalThis.fetch = before; }
}
const posts = (calls) => calls.filter((call) => call.method === 'POST');

test('the approval switch is off by default and separate from the read switch', () => {
  assert.equal(config.APPLICANT_APPROVAL_ENABLED, false);
  const source = readFileSync(new URL('../src/features/admin/pendingApplicationsConfig.ts', import.meta.url), 'utf8');
  assert.match(source, /VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED === '1'/);
});

test('each role has exactly one fixed eligibility source (D-45)', () => {
  assert.deepEqual(contract.ELIGIBILITY_SOURCE_FOR_ROLE, { Student: STUDENT, Instructor: INSTRUCTOR });
  assert.deepEqual(Object.keys(contract.ELIGIBILITY_SOURCE_LABELS).sort(), [INSTRUCTOR, STUDENT].sort());
});

test('the approval plan carries only the attestation, never a role or status', () => {
  assert.deepEqual(contract.buildApprovalRequest(ROOT, 7, STUDENT), {
    method: 'POST', path: `${ROOT}7/approve/`, body: { eligibility_confirmed: true, eligibility_source: STUDENT },
  });
  assert.deepEqual(Object.keys(contract.buildApprovalRequest(ROOT, 7, INSTRUCTOR).body), ['eligibility_confirmed', 'eligibility_source']);
  for (const bad of ['', 'applicant_upload', 'CTU_MAIN_SYSTEM_RECORDS', null, undefined, ['ctu_main_system_records']]) {
    assert.throws(() => contract.buildApprovalRequest(ROOT, 7, bad), String(bad));
  }
  for (const id of [0, -1, 1.5, '7', 2_147_483_648]) assert.throws(() => contract.buildApprovalRequest(ROOT, id, STUDENT));
  assert.throws(() => contract.buildApprovalRequest('https://evil.example/api/', 7, STUDENT));
});

test('only the two fixed refusal reasons are recognised (D-47)', () => {
  const refusal = (reason, extra = {}) => ({ error: { code: 'approval_not_allowed', reason, message: 'x', ...extra } });
  assert.equal(contract.parseApprovalRefusal(refusal('email_unverified')), 'email_unverified');
  assert.equal(contract.parseApprovalRefusal(refusal('eligibility_unconfirmed')), 'eligibility_unconfirmed');
  assert.equal(contract.parseApprovalRefusal(refusal('student@example.edu')), null);
  assert.equal(contract.parseApprovalRefusal({ error: { code: 'conflict', reason: 'email_unverified' } }), null);
  assert.equal(contract.parseApprovalRefusal({ ...refusal('email_unverified'), email: 'x@example.edu' }), null);
  assert.equal(contract.parseApprovalRefusal(null), null);
});

test('switched off, approval refuses before any CSRF request or POST', async () => {
  await withFetch(() => reply(200, {}), async (calls) => {
    await assert.rejects(api.approveApplication(7, STUDENT), (error) => error.code === 'review_unavailable');
    await assert.rejects(api.approveApplication(7, STUDENT, false), (error) => error.code === 'review_unavailable');
    assert.equal(calls.length, 0);
  });
});

test('success sends one CSRF-protected POST and requires the queued-notification result', async () => {
  await withFetch(() => reply(200, { account_id: 7, status: 'Approved', notification: 'queued' }), async (calls) => {
    assert.deepEqual(await api.approveApplication(7, STUDENT, true), {
      account_id: 7, status: 'Approved', notification: 'queued',
    });
    assert.equal(posts(calls).length, 1);
    assert.equal(posts(calls)[0].path, `${ROOT}7/approve/`);
    assert.equal(posts(calls)[0].csrf, 'tok');
    assert.deepEqual(JSON.parse(posts(calls)[0].body), { eligibility_confirmed: true, eligibility_source: STUDENT });
  });
});

test('definite refusals keep fixed codes and are never retried', async () => {
  const cases = [
    [409, { error: { code: 'approval_not_allowed', reason: 'email_unverified', message: 'x' } }, 'email_unverified'],
    [409, { error: { code: 'approval_not_allowed', reason: 'eligibility_unconfirmed', message: 'x' } }, 'eligibility_unconfirmed'],
    [409, { error: { code: 'approval_not_allowed', reason: 'other', message: 'x' } }, 'approval_not_allowed'],
    [404, { error: { code: 'request_unavailable', message: 'x' } }, 'request_unavailable'],
    [400, { error: { code: 'invalid_request', message: 'x' } }, 'invalid_request'],
    [401, { error: { code: 'authentication_required', message: 'x' } }, 'authentication_required'],
    [403, { error: { code: 'access_denied', message: 'x' } }, 'access_denied'],
    [403, undefined, 'access_denied'],
    [429, { error: { code: 'rate_limited', message: 'x' } }, 'rate_limited'],
    [503, { error: { code: 'review_unavailable', message: 'x' } }, 'review_unavailable'],
  ];
  for (const [status, body, code] of cases) {
    await withFetch(() => reply(status, body), async (calls) => {
      await assert.rejects(api.approveApplication(7, STUDENT, true), (error) => {
        assert.equal(error.code, code, `${status}`);
        assert.equal(error.outcomeUnknown, false, `${status}`);
        assert.ok(!String(error.message).includes('x@'), 'no server text');
        return true;
      });
      assert.equal(posts(calls).length, 1, `${status} must not be retried`);
    });
  }
});

test('anything that may have been applied is outcome_unknown, sent once and never replayed (D-48)', async () => {
  const unsure = [
    () => { throw new TypeError('network down after send'); },
    () => reply(500, { error: { code: 'server_error' } }),
    () => reply(502, undefined),
    () => reply(503, undefined),
    () => reply(504, { error: { code: 'review_unavailable' } }),
    () => reply(200, undefined),
    () => reply(200, { account_id: 8, status: 'Approved' }),
    () => reply(200, { account_id: 7, status: 'Rejected' }),
    () => reply(200, { account_id: 7, status: 'Approved', role: 'Admin' }),
  ];
  for (const [index, post] of unsure.entries()) {
    await withFetch(post, async (calls) => {
      await assert.rejects(api.approveApplication(7, STUDENT, true),
        (error) => error.code === 'outcome_unknown' && error.outcomeUnknown === true, `case ${index}`);
      assert.equal(posts(calls).length, 1, `case ${index} must not be retried`);
    });
  }
});

test('a failed security-check bootstrap sends nothing and is a definite non-approval', async () => {
  await withFetch(() => reply(200, { account_id: 7, status: 'Approved', notification: 'queued' }), async (calls) => {
    await assert.rejects(api.approveApplication(7, STUDENT, true), (error) => error.code !== 'outcome_unknown' && !error.outcomeUnknown);
    assert.equal(posts(calls).length, 0);
  }, { csrf: () => { throw new TypeError('offline'); } });
});

test('the legacy live-panel approval plan is unchanged and now refused by the server (documented)', () => {
  assert.deepEqual(contract.buildReviewDecisionRequest(ROOT, 7, 'approve'), { method: 'POST', path: `${ROOT}7/approve/`, body: {} });
});

test('the approval UI never sends a role, never uses postJSON and has no reject control', () => {
  const panel = readFileSync(new URL('../src/features/admin/ApplicantApprovalPanel.tsx', import.meta.url), 'utf8');
  const client = readFileSync(new URL('../src/features/admin/registrationReviewApi.ts', import.meta.url), 'utf8');
  assert.doesNotMatch(panel, /rejectRegistration|rejection_code|\/reject\/|>\s*Reject/);
  assert.doesNotMatch(panel, /postJSON|fetch\(/);
  const approve = client.slice(client.indexOf('export async function approveApplication'));
  assert.doesNotMatch(approve, /postJSON|requested_role|role_id/);
});
