// WF-02.03/02.04: bulk requests are bounded, explicit, CSRF protected and never automatically retried.
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
const IDs = [7, 8];
const reply = (status, body) => ({
  ok: status >= 200 && status < 300,
  status,
  headers: new Headers(),
  json: async () => {
    if (body === undefined) throw new SyntaxError('not json');
    return body;
  },
});
async function withFetch(post, run) {
  const calls = [];
  const before = globalThis.fetch;
  globalThis.fetch = async (path, init = {}) => {
    calls.push({ path, method: init.method ?? 'GET', body: init.body, csrf: init.headers?.['X-CSRFToken'] });
    if (path === '/api/v1/auth/csrf/') return reply(200, { csrfToken: 'tok' });
    return post();
  };
  try { return await run(calls); } finally { globalThis.fetch = before; }
}

const report = {
  action: 'approve', requested: 2, processed: 2, remaining: 0, interrupted: false,
  counts: { Approved: 1, Rejected: 0, Skipped: 1, Failed: 0, Unconfirmed: 0 },
  results: [
    { account_id: 7, outcome: 'Approved', notification: 'queued' },
    { account_id: 8, outcome: 'Skipped' },
  ],
};

test('bulk feature flag remains off by default', () => {
  assert.equal(config.BULK_APPLICANT_DECISIONS_ENABLED, false);
  assert.match(readFileSync(new URL('../src/features/admin/pendingApplicationsConfig.ts', import.meta.url), 'utf8'),
    /VITE_WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED === '1'/);
});

test('bulk plans send only explicit unique IDs and one fixed action payload', () => {
  assert.deepEqual(contract.buildBulkRegistrationDecisionRequest(ROOT, IDs, 'approve'), {
    method: 'POST', path: `${ROOT}bulk/`,
    body: { action: 'approve', account_ids: IDs, eligibility_confirmed: true },
  });
  assert.deepEqual(contract.buildBulkRegistrationDecisionRequest(ROOT, IDs, 'reject', 'duplicate_request'), {
    method: 'POST', path: `${ROOT}bulk/`,
    body: { action: 'reject', account_ids: IDs, rejection_code: 'duplicate_request' },
  });
  for (const invalid of [[], Array.from({ length: 21 }, (_, index) => index + 1), [7, 7], [true], ['7']]) {
    assert.throws(() => contract.buildBulkRegistrationDecisionRequest(ROOT, invalid, 'approve'));
  }
  assert.throws(() => contract.buildBulkRegistrationDecisionRequest(ROOT, IDs, 'reject', 'free text'));
  assert.throws(() => contract.buildBulkRegistrationDecisionRequest('https://evil.example/', IDs, 'approve'));
});

test('bulk result parser requires individual outcomes and queued notifications only for successes', () => {
  assert.deepEqual(contract.parseBulkRegistrationDecision(report, IDs, 'approve'), report);
  for (const malformed of [
    { ...report, results: [{ ...report.results[0], notification: 'sent' }, report.results[1]] },
    { ...report, results: [report.results[0], { ...report.results[1], notification: 'queued' }] },
    { ...report, results: [report.results[0], report.results[0]] },
    { ...report, counts: { ...report.counts, Approved: 2 } },
    { ...report, remaining: 1 },
  ]) {
    assert.throws(() => contract.parseBulkRegistrationDecision(malformed, IDs, 'approve'));
  }
});

test('disabled bulk API sends no CSRF request or decision POST', async () => {
  await withFetch(() => reply(200, report), async (calls) => {
    await assert.rejects(api.decideBulkApplications(IDs, 'approve'), (error) => error.code === 'review_unavailable');
    assert.deepEqual(calls, []);
  });
});

test('bulk API sends one same-origin CSRF POST and accepts a truthful partial report', async () => {
  await withFetch(() => reply(200, report), async (calls) => {
    assert.deepEqual(await api.decideBulkApplications(IDs, 'approve', undefined, true), report);
    assert.equal(calls.length, 2);
    assert.equal(calls[0].path, '/api/v1/auth/csrf/');
    assert.equal(calls[1].path, `${ROOT}bulk/`);
    assert.equal(calls[1].method, 'POST');
    assert.equal(calls[1].csrf, 'tok');
    assert.deepEqual(JSON.parse(calls[1].body), {
      action: 'approve', account_ids: IDs, eligibility_confirmed: true,
    });
  });
});

test('uncertain bulk POST is sent once and never replayed', async () => {
  await withFetch(() => { throw new TypeError('connection lost'); }, async (calls) => {
    await assert.rejects(api.decideBulkApplications(IDs, 'approve', undefined, true),
      (error) => error.code === 'outcome_unknown' && error.outcomeUnknown === true);
    assert.equal(calls.filter((call) => call.method === 'POST').length, 1);
  });
});
