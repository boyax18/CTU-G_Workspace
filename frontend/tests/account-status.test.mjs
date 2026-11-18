// WF-02.05 (P-08): school-account contract and client. Every request is mocked.
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
const contract = await import('../src/features/admin/accountStatusContract.ts');
const api = await import('../src/features/admin/accountStatusApi.ts');
const config = await import('../src/features/admin/accountStatusConfig.ts');
hooks.deregister();

const ROOT = '/api/v1/admin/school-accounts/';
const item = (id = 7, overrides = {}) => ({ account_id: id, school_id: '7240001', id_label: 'School ID', full_name: 'Ana Cruz',
  roles: ['Student'], is_active: true, ...overrides });
const detail = (id = 7, overrides = {}) => ({ ...item(id), name: { first: 'Ana', middle: null, last: 'Cruz', suffix: null },
  request_status: 'Approved', created_at: '2026-11-10T09:15:00+08:00', can_reactivate: true, ...overrides });
const reply = (status, body) => ({ ok: status >= 200 && status < 300, status, headers: new Headers(), json: async () => {
  if (body === undefined) throw new SyntaxError('not json');
  return body;
} });
async function withFetch(post, run, { csrf = () => reply(200, { csrfToken: 'tok' }) } = {}) {
  const calls = [];
  const before = globalThis.fetch;
  globalThis.fetch = async (path, init = {}) => {
    calls.push({ path, method: init.method ?? 'GET', body: init.body });
    if (path === '/api/v1/auth/csrf/') return csrf();
    return post(path, init);
  };
  try { return await run(calls); } finally { globalThis.fetch = before; }
}
const posts = (calls) => calls.filter((c) => c.method === 'POST');

test('the switch is off by default and the route is never config.urls-shaped review routes', () => {
  assert.equal(config.ACCOUNT_STATUS_ENABLED, false);
  assert.equal(config.ACCOUNT_STATUS_ROUTE_ROOT, ROOT);
  assert.match(readFileSync(new URL('../src/features/admin/accountStatusConfig.ts', import.meta.url), 'utf8'),
    /VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED === '1'/);
});

test('list plans send only page, search and status', () => {
  assert.equal(contract.buildAccountsRequest(ROOT), `${ROOT}?page=1`);
  assert.equal(contract.buildAccountsRequest(ROOT, 2, { q: '  ana cruz ', status: 'inactive' }), `${ROOT}?page=2&q=ana%20cruz&status=inactive`);
  for (const bad of [{ status: 'Active' }, { role: 'Admin' }, { q: 'é' }, { q: 'a'.repeat(51) }]) {
    assert.throws(() => contract.buildAccountsRequest(ROOT, 1, bad), JSON.stringify(bad));
  }
  assert.throws(() => contract.buildAccountsRequest(ROOT, 0));
});

test('status plans carry only the confirmed state, consistent with the action (D-68)', () => {
  assert.deepEqual(contract.buildStatusChangeRequest(ROOT, 7, 'suspend', true),
    { method: 'POST', path: `${ROOT}7/suspend/`, body: { expected_active: true } });
  assert.deepEqual(contract.buildStatusChangeRequest(ROOT, 7, 'activate', false),
    { method: 'POST', path: `${ROOT}7/activate/`, body: { expected_active: false } });
  assert.throws(() => contract.buildStatusChangeRequest(ROOT, 7, 'suspend', false));
  assert.throws(() => contract.buildStatusChangeRequest(ROOT, 7, 'activate', true));
  assert.throws(() => contract.buildStatusChangeRequest(ROOT, 7, 'delete', true));
  assert.throws(() => contract.buildStatusChangeRequest(ROOT, 0, 'suspend', true));
});

test('parsers accept exact minimized shapes and refuse extra or inconsistent fields', () => {
  assert.equal(contract.parseAccountPage({ results: [item()], page: 1, page_size: 20, has_next: false }).results[0].school_id, '7240001');
  assert.equal(contract.parseAccountDetail(detail(), 7).can_reactivate, true);
  for (const bad of [{ ...item(), email: 'a@example.edu' }, { ...item(), is_active: 'yes' }, { ...item(), id_label: 'ID' },
    { ...item(), roles: ['Student', 'Student'] }]) {
    assert.throws(() => contract.parseAccountPage({ results: [bad], page: 1, page_size: 20, has_next: false }), JSON.stringify(bad));
  }
  assert.throws(() => contract.parseAccountDetail(detail(8), 7));
  assert.throws(() => contract.parseAccountDetail({ ...detail(), request_status: 'Pending' }, 7));
  assert.throws(() => contract.parseAccountDetail({ ...detail(), password_hash: 'x' }, 7));
  assert.deepEqual(contract.parseStatusChange({ account_id: 7, is_active: false }, 7, false), { account_id: 7, is_active: false });
  assert.throws(() => contract.parseStatusChange({ account_id: 7, is_active: true }, 7, false));
  const conflict = (reason) => ({ error: { code: 'account_status_conflict', reason, message: 'x' } });
  for (const r of ['state_changed', 'protected_account', 'no_operational_role']) assert.equal(contract.parseStatusConflict(conflict(r)), r);
  assert.equal(contract.parseStatusConflict(conflict('other')), null);
  assert.equal(contract.parseAccountParam('12'), 12);
  for (const raw of ['0', 'abc', '1e3', '99999999999', null]) assert.equal(contract.parseAccountParam(raw), null);
});

test('switched off, nothing is requested', async () => {
  await withFetch(() => reply(200, {}), async (calls) => {
    for (const call of [() => api.listSchoolAccounts(), () => api.getSchoolAccount(7), () => api.changeAccountStatus(7, 'suspend', true)]) {
      await assert.rejects(call(), (e) => e.code === 'review_unavailable');
    }
    assert.equal(calls.length, 0);
  });
});

test('one CSRF-protected POST with the confirmed state; exact result required', async () => {
  await withFetch(() => reply(200, { account_id: 7, is_active: false }), async (calls) => {
    assert.deepEqual(await api.changeAccountStatus(7, 'suspend', true, true), { account_id: 7, is_active: false });
    assert.equal(posts(calls).length, 1);
    assert.deepEqual(JSON.parse(posts(calls)[0].body), { expected_active: true });
  });
});

test('definite refusals keep codes and are not retried; uncertain outcomes are never replayed', async () => {
  const definite = [
    [409, { error: { code: 'account_status_conflict', reason: 'state_changed', message: 'x' } }, 'state_changed'],
    [409, { error: { code: 'account_status_conflict', reason: 'protected_account', message: 'x' } }, 'protected_account'],
    [409, { error: { code: 'account_status_conflict', reason: 'no_operational_role', message: 'x' } }, 'no_operational_role'],
    [404, { error: { code: 'request_unavailable', message: 'x' } }, 'request_unavailable'],
    [400, { error: { code: 'invalid_request', message: 'x' } }, 'invalid_request'],
    [401, { error: { code: 'authentication_required', message: 'x' } }, 'authentication_required'],
    [403, { error: { code: 'access_denied', message: 'x' } }, 'access_denied'],
    [429, { error: { code: 'rate_limited', message: 'x' } }, 'rate_limited'],
    [503, { error: { code: 'review_unavailable', message: 'x' } }, 'review_unavailable'],
  ];
  for (const [status, body, code] of definite) {
    await withFetch(() => reply(status, body), async (calls) => {
      await assert.rejects(api.changeAccountStatus(7, 'suspend', true, true), (e) => e.code === code && !e.outcomeUnknown, `${status}`);
      assert.equal(posts(calls).length, 1);
    });
  }
  for (const post of [() => { throw new TypeError('down'); }, () => reply(500, {}), () => reply(502, undefined),
    () => reply(200, undefined), () => reply(200, { account_id: 7, is_active: true }), () => reply(200, { account_id: 8, is_active: false })]) {
    await withFetch(post, async (calls) => {
      await assert.rejects(api.changeAccountStatus(7, 'suspend', true, true), (e) => e.code === 'outcome_unknown' && e.outcomeUnknown);
      assert.equal(posts(calls).length, 1);
    });
  }
});

test('the UI never edits roles or permissions and has no history or bulk controls', () => {
  for (const file of ['AccountDirectoryPanel.tsx', 'AccountDetailPanel.tsx']) {
    const source = readFileSync(new URL(`../src/features/admin/${file}`, import.meta.url), 'utf8');
    assert.doesNotMatch(source, /role_assignments|account_permissions|role_permissions|postJSON|bulk|history\(\)/i, file);
  }
});
