// WF-02.04 (P-09): rejection contract and client. Every request is mocked.
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
const OK = { account_id: 7, status: 'Rejected', notification: 'queued' };
const reply = (status, body) => ({ ok: status >= 200 && status < 300, status, headers: new Headers(), json: async () => {
  if (body === undefined) throw new SyntaxError('not json');
  return body;
} });

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

test('the rejection switch is off by default and separate from the read and approval switches', () => {
  assert.equal(config.APPLICANT_REJECTION_ENABLED, false);
  const source = readFileSync(new URL('../src/features/admin/pendingApplicationsConfig.ts', import.meta.url), 'utf8');
  assert.match(source, /VITE_WORKSPACE_REGISTRATION_REJECTION_ENABLED === '1'/);
});

test('public reason labels match the backend email labels exactly, one per fixed code (D-56)', () => {
  const backend = readFileSync(new URL('../../backend/apps/accounts/registration_email_templates.py', import.meta.url), 'utf8');
  assert.deepEqual(Object.keys(contract.REJECTION_PUBLIC_LABELS), [...contract.REGISTRATION_REJECTION_CODES]);
  for (const [code, label] of Object.entries(contract.REJECTION_PUBLIC_LABELS)) {
    assert.ok(backend.includes(`"${code}": "${label}"`), code);
  }
});

test('the rejection plan carries only one fixed code', () => {
  assert.deepEqual(contract.buildRejectionRequest(ROOT, 7, 'identity_mismatch'), {
    method: 'POST', path: `${ROOT}7/reject/`, body: { rejection_code: 'identity_mismatch' },
  });
  for (const bad of ['', 'other', 'Identity_Mismatch', null, undefined, ['identity_mismatch']]) {
    assert.throws(() => contract.buildRejectionRequest(ROOT, 7, bad), String(bad));
  }
  for (const id of [0, -1, 1.5, '7', 2_147_483_648]) assert.throws(() => contract.buildRejectionRequest(ROOT, id, 'duplicate_request'));
});

test('success needs the exact decision with notification "queued"; nothing else is success', () => {
  assert.deepEqual(contract.parseRejectionDecision(OK, 7), OK);
  for (const bad of [{ ...OK, notification: 'delivered' }, { ...OK, notification: 'sent' }, { account_id: 7, status: 'Rejected' },
    { ...OK, account_id: 8 }, { ...OK, status: 'Approved' }, { ...OK, email: 'x@example.edu' }, null]) {
    assert.throws(() => contract.parseRejectionDecision(bad, 7), JSON.stringify(bad));
  }
});

test('only the three fixed conflict reasons are recognised (D-58)', () => {
  const refusal = (reason, extra = {}) => ({ error: { code: 'rejection_not_allowed', reason, message: 'x', ...extra } });
  for (const reason of ['recipient_unverified', 'direct_permissions', 'protected_history']) {
    assert.equal(contract.parseRejectionRefusal(refusal(reason)), reason);
  }
  assert.equal(contract.parseRejectionRefusal(refusal('a@example.edu')), null);
  assert.equal(contract.parseRejectionRefusal({ error: { code: 'approval_not_allowed', reason: 'recipient_unverified' } }), null);
  assert.equal(contract.parseRejectionRefusal({ ...refusal('protected_history'), extra: 1 }), null);
});

test('switched off, rejection refuses before any CSRF request or POST', async () => {
  await withFetch(() => reply(200, OK), async (calls) => {
    await assert.rejects(api.rejectApplication(7, 'duplicate_request'), (error) => error.code === 'review_unavailable');
    await assert.rejects(api.rejectApplication(7, 'duplicate_request', false), (error) => error.code === 'review_unavailable');
    assert.equal(calls.length, 0);
  });
});

test('success sends one CSRF-protected POST with only the reason', async () => {
  await withFetch(() => reply(200, OK), async (calls) => {
    assert.deepEqual(await api.rejectApplication(7, 'incomplete_submission', true), OK);
    assert.equal(posts(calls).length, 1);
    assert.equal(posts(calls)[0].path, `${ROOT}7/reject/`);
    assert.equal(posts(calls)[0].csrf, 'tok');
    assert.deepEqual(JSON.parse(posts(calls)[0].body), { rejection_code: 'incomplete_submission' });
  });
});

test('definite refusals keep fixed codes and are never retried', async () => {
  const cases = [
    [409, { error: { code: 'rejection_not_allowed', reason: 'recipient_unverified', message: 'x' } }, 'recipient_unverified'],
    [409, { error: { code: 'rejection_not_allowed', reason: 'direct_permissions', message: 'x' } }, 'direct_permissions'],
    [409, { error: { code: 'rejection_not_allowed', reason: 'protected_history', message: 'x' } }, 'protected_history'],
    [409, { error: { code: 'rejection_not_allowed', reason: 'other', message: 'x' } }, 'rejection_not_allowed'],
    [404, { error: { code: 'request_unavailable', message: 'x' } }, 'request_unavailable'],
    [400, { error: { code: 'invalid_request', message: 'x' } }, 'invalid_request'],
    [401, { error: { code: 'authentication_required', message: 'x' } }, 'authentication_required'],
    [403, { error: { code: 'access_denied', message: 'x' } }, 'access_denied'],
    [429, { error: { code: 'rate_limited', message: 'x' } }, 'rate_limited'],
    [503, { error: { code: 'review_unavailable', message: 'x' } }, 'review_unavailable'],
  ];
  for (const [status, body, code] of cases) {
    await withFetch(() => reply(status, body), async (calls) => {
      await assert.rejects(api.rejectApplication(7, 'duplicate_request', true), (error) => {
        assert.equal(error.code, code, `${status}`);
        assert.equal(error.outcomeUnknown, false);
        return true;
      });
      assert.equal(posts(calls).length, 1, `${status} must not be retried`);
    });
  }
});

test('anything possibly applied is outcome_unknown, sent once and never replayed', async () => {
  const unsure = [
    () => { throw new TypeError('network down after send'); },
    () => reply(500, { error: { code: 'server_error' } }),
    () => reply(502, undefined),
    () => reply(503, undefined),
    () => reply(200, undefined),
    () => reply(200, { account_id: 7, status: 'Rejected' }),
    () => reply(200, { ...OK, notification: 'delivered' }),
    () => reply(200, { ...OK, account_id: 8 }),
  ];
  for (const [index, post] of unsure.entries()) {
    await withFetch(post, async (calls) => {
      await assert.rejects(api.rejectApplication(7, 'duplicate_request', true),
        (error) => error.code === 'outcome_unknown' && error.outcomeUnknown === true, `case ${index}`);
      assert.equal(posts(calls).length, 1, `case ${index}`);
    });
  }
});

test('a failed security-check bootstrap sends nothing', async () => {
  await withFetch(() => reply(200, OK), async (calls) => {
    await assert.rejects(api.rejectApplication(7, 'duplicate_request', true), (error) => !error.outcomeUnknown);
    assert.equal(posts(calls).length, 0);
  }, { csrf: () => { throw new TypeError('offline'); } });
});

test('the rejection UI has no free text, bulk control or delivery claim', () => {
  const panel = readFileSync(new URL('../src/features/admin/ApplicantRejectionPanel.tsx', import.meta.url), 'utf8');
  const detail = readFileSync(new URL('../src/features/admin/ApplicantDetailPanel.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(panel, /<textarea|type="text"|postJSON|fetch\(|bulk/i);
  assert.doesNotMatch(panel + detail, /email (was|has been) (sent|delivered)/i);
  assert.match(detail, /has been queued for delivery/);
});
