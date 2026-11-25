// Semester organizational fee client and contract. Every request is mocked.
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
const config = await import('../src/features/finance/semesterFeesConfig.ts');
const api = await import('../src/features/finance/semesterFeesApi.ts');
const navigation = await import('../src/features/dashboard/navigation.ts');
hooks.deregister();

const ROOT = '/api/v1/finance/semester-fees/';
const semester = { semester_id: 9, term: 'first', label: 'First semester', status: 'Draft', school_year_id: 2, school_year_label: '2026–2027' };
const revision = (overrides = {}) => ({ revision_id: 4, revision_number: 1, currency: 'PHP', amount: '1500.00', status: 'Draft', version: 1,
  change_reason: null, configured_by: 'You', configured_at: '2026-11-25T05:00:00+00:00', approved_by: null, approved_at: null,
  superseded_at: null, withdrawn_at: null, ...overrides });
const fee = (overrides = {}) => ({ semester, schedule_id: 1, schedule_version: 2, state: 'draft', current_approved: null, draft: revision(),
  revisions: [revision()], editable: true, reason_required: false,
  readiness: { key: 'approved_fee', status: 'missing', reason: 'fee_awaiting_approval' },
  features: { configuration: true, approval: true }, ...overrides });
const preview = (overrides = {}) => ({ semester, proposed: revision(), current_approved: null,
  impact: { status: 'not_applicable', count: null, reason: 'no_previous_rate' }, warnings: [], blockers: [], feature_enabled: true,
  can_confirm: true, ...overrides });
const reply = (status, body) => ({ ok: status >= 200 && status < 300, status, headers: new Headers(), json: async () => {
  if (body === undefined) throw new SyntaxError('not json');
  return body;
} });
async function withFetch(handler, run) {
  const calls = [];
  const before = globalThis.fetch;
  globalThis.fetch = async (path, init = {}) => {
    calls.push({ path, method: init.method ?? 'GET', body: init.body, headers: init.headers ?? {} });
    if (path === '/api/v1/auth/csrf/') return reply(200, { csrfToken: 'tok' });
    return handler(path, init);
  };
  try { return await run(calls); } finally { globalThis.fetch = before; }
}
const posts = (calls) => calls.filter((c) => c.method === 'POST');

test('switches are off by default and approval depends on configuration', () => {
  assert.equal(config.SEMESTER_FEE_CONFIGURATION_ENABLED, false);
  assert.equal(config.SEMESTER_FEE_APPROVAL_ENABLED, false);
  assert.match(readFileSync(new URL('../src/features/finance/semesterFeesConfig.ts', import.meta.url), 'utf8'),
    /SEMESTER_FEE_CONFIGURATION_ENABLED\s*&& import\.meta\.env\?\.VITE_WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED === '1'/);
  const item = navigation.getDashboardItem('semester-fees');
  assert.deepEqual([item.integration, item.group, item.requiredAny], ['planned', 'academic-configuration', ['finance.fee_schedule.manage']]);
  assert.equal(navigation.canOpenDashboardView('semester-fees', ['finance.fee_schedule.read']), false);
});

test('no request is sent while switched off, including approval', async () => {
  await withFetch(() => { throw new Error('must not fetch'); }, async (calls) => {
    await assert.rejects(api.listSemesterFees(), (e) => e.code === 'semester_fees_unavailable');
    await assert.rejects(api.saveDraft(9, { amount: '1500.00', expected_draft_version: null }), (e) => e.code === 'semester_fees_unavailable');
    await assert.rejects(api.approveFee(9, api.parsePreview(preview()), false), (e) => e.code === 'feature_disabled');
    assert.equal(calls.length, 0);
  });
});

test('amounts are exact strings: zero is a value and missing is never zero', () => {
  assert.equal(api.normalizeAmount('1500'), '1500.00');
  assert.equal(api.normalizeAmount(' 0 '), '0.00');
  assert.equal(api.normalizeAmount('99999.5'), '99999.50');
  assert.equal(api.normalizeAmount('100000.00'), '100000.00');
  for (const bad of ['', ' ', '-1', '1,500', '1500.001', '1e3', 'abc', '100000.01', '1000000']) assert.equal(api.normalizeAmount(bad), null, bad);
  assert.equal(api.peso('1500.00'), '₱1,500.00');
  assert.equal(api.peso('0.00'), '₱0.00');
  assert.equal(api.peso('100000.00'), '₱100,000.00');
});

test('strict parsing rejects malformed money and inconsistent states', () => {
  assert.equal(api.parseSemesterFee(fee()).draft.amount, '1500.00');
  for (const bad of [fee({ draft: revision({ amount: 1500 }) }), fee({ draft: revision({ amount: '1500.5' }) }),
    fee({ draft: revision({ currency: 'USD' }) }), fee({ draft: revision({ status: 'Approved' }) }), fee({ state: 'paid' })]) {
    assert.throws(() => api.parseSemesterFee(bad));
  }
  assert.throws(() => api.parsePreview(preview({ impact: { status: 'evaluated', count: null, reason: '' } })));
  assert.deepEqual(api.parseSemesterFee(fee({ features: { configuration: 'yes' } })).features, { configuration: false, approval: false });
});

test('refusals expose only allowlisted reasons and fixed field text', () => {
  const conflict = api.parseFeeError(409, { error: { code: 'fee_conflict', reason: 'impact_unavailable', message: '<b>x</b>' } });
  assert.equal(api.feeErrorText(new api.FeeApiError('x', conflict)),
    'The effect on existing student fee obligations cannot be checked yet, so this revision cannot be approved.');
  assert.equal(api.parseFeeError(409, { error: { reason: 'grant_admin' } }).reason, '');
  const denied = api.parseFeeError(403, { error: { code: 'access_denied' } });
  assert.match(api.feeErrorText(new api.FeeApiError('x', denied)), /School Admin responsibility/);
  assert.deepEqual(api.parseFeeError(400, { error: { fields: { amount: ['<img>'], password: ['x'] } } }).fields, { amount: 'Check this value.' });
});

test('approval sends exactly what was reviewed, once, with CSRF; ambiguous failures are outcome_unknown', async () => {
  await withFetch(() => reply(200, fee({ state: 'approved', draft: null, current_approved: revision({ status: 'Approved', version: 2,
    approved_by: 'You', approved_at: '2026-11-25T06:00:00+00:00' }) })), async (calls) => {
    await api.approveFee(9, api.parsePreview(preview({ warnings: ['zero_amount'], proposed: revision({ amount: '0.00' }) })), true, true);
    assert.deepEqual(posts(calls).map((c) => [c.path, JSON.parse(c.body), c.headers['X-CSRFToken']]), [[`${ROOT}9/approval/`,
      { revision_id: 4, expected_version: 1, expected_current_approved_revision_id: null, acknowledged_warnings: ['zero_amount'],
        confirmed: true, confirm_zero_amount: true }, 'tok']]);
  });
  await withFetch(() => { throw new TypeError('down'); }, async (calls) => {
    await assert.rejects(api.feePost('9/draft/', { amount: '1.00', expected_draft_version: null }, true), (e) => e.code === 'outcome_unknown');
    assert.equal(posts(calls).length, 1);
  });
  await withFetch(() => reply(503, { error: { code: 'feature_disabled' } }), async () => {
    await assert.rejects(api.feePost('9/approval/', {}, true), (e) => e.code === 'feature_disabled' && !e.outcomeUnknown);
  });
});
