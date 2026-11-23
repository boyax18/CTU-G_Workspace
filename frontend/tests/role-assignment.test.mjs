// WF-03.01: Role assignments contract and client (Technical Super Admin). Every request is mocked.
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
const contract = await import('../src/features/access-control/roleAssignmentContract.ts');
const api = await import('../src/features/access-control/roleAssignmentApi.ts');
const config = await import('../src/features/access-control/roleAssignmentConfig.ts');
const navigation = await import('../src/features/dashboard/navigation.ts');
hooks.deregister();

const ROOT = '/api/v1/admin/role-assignments/';
const TSA = 'access_control.admin_assignments.manage';
const item = (id = 7, overrides = {}) => ({ account_id: id, school_id: '0030202', full_name: 'Ana Cruz', roles: ['Instructor'],
  school_admin_action: 'assign', restriction: null, ...overrides });
const page = (results, overrides = {}) => ({ results, page: 1, page_size: 20, has_next: false, ...overrides });
const reply = (status, body) => ({ ok: status >= 200 && status < 300, status, headers: new Headers(), json: async () => {
  if (body === undefined) throw new SyntaxError('not json');
  return body;
} });
async function withFetch(handler, run) {
  const calls = [];
  const before = globalThis.fetch;
  globalThis.fetch = async (path, init = {}) => {
    calls.push({ path, method: init.method ?? 'GET', body: init.body });
    if (path === '/api/v1/auth/csrf/') return reply(200, { csrfToken: 'tok' });
    return handler(path, init);
  };
  try { return await run(calls); } finally { globalThis.fetch = before; }
}

test('the switch is off by default and the route is the isolated role-assignments root', () => {
  assert.equal(config.ROLE_ASSIGNMENT_ENABLED, false);
  assert.equal(config.ROLE_ASSIGNMENT_ROUTE_ROOT, ROOT);
  assert.match(readFileSync(new URL('../src/features/access-control/roleAssignmentConfig.ts', import.meta.url), 'utf8'),
    /VITE_WORKSPACE_ROLE_ASSIGNMENT_ENABLED === '1'/);
});

test('plans send only the page, the search and the confirmed expected state', () => {
  assert.equal(contract.buildRoleListRequest(ROOT), `${ROOT}?page=1`);
  assert.equal(contract.buildRoleListRequest(ROOT, 2, '  ana cruz '), `${ROOT}?page=2&q=ana%20cruz`);
  assert.throws(() => contract.buildRoleListRequest(ROOT, 0));
  assert.throws(() => contract.buildRoleListRequest(ROOT, 1, 'é'));
  assert.deepEqual(contract.buildSchoolAdminChange(ROOT, 7, 'assign', false),
    { method: 'POST', path: `${ROOT}7/school-admin/assign/`, body: { expected_present: false } });
  assert.deepEqual(contract.buildSchoolAdminChange(ROOT, 7, 'revoke', true),
    { method: 'POST', path: `${ROOT}7/school-admin/revoke/`, body: { expected_present: true } });
  for (const [action, expected] of [['assign', true], ['revoke', false], ['grant-technical-super-admin', false]]) {
    assert.throws(() => contract.buildSchoolAdminChange(ROOT, 7, action, expected), action);
  }
});

test('parsers accept exact minimized shapes and refuse extra, inconsistent or unknown values', () => {
  assert.equal(contract.parseRolePage(page([item(), item(8, { school_admin_action: null, restriction: 'legacy_admin', roles: ['Admin'] })])).results.length, 2);
  for (const bad of [{ ...item(), email: 'a@example.edu' }, { ...item(), school_admin_action: 'grant' },
    { ...item(), restriction: 'last_school_admin' }, { ...item(), restriction: 'superuser' }, { ...item(), roles: ['Admin', 'Admin'] },
    { ...item(), account_id: 0 }]) {
    assert.throws(() => contract.parseRolePage(page([bad])), JSON.stringify(bad));
  }
  assert.throws(() => contract.parseRolePage(page([], { has_next: true })));
  assert.deepEqual(contract.parseRoleChange({ account_id: 7, role: 'Admin', assigned: true }, 7, true), { account_id: 7, role: 'Admin', assigned: true });
  assert.throws(() => contract.parseRoleChange({ account_id: 7, role: 'Technical Super Admin', assigned: true }, 7, true));
  const conflict = (reason) => ({ error: { code: 'role_assignment_conflict', reason, message: 'x' } });
  for (const r of ['state_changed', 'not_eligible', 'protected_account', 'last_school_admin']) assert.equal(contract.parseRoleConflict(conflict(r)), r);
  assert.equal(contract.parseRoleConflict(conflict('other')), null);
});

test('switched off, nothing is requested', async () => {
  await withFetch(() => reply(200, {}), async (calls) => {
    await assert.rejects(api.listRoleAssignments(), (e) => e.code === 'review_unavailable');
    await assert.rejects(api.changeSchoolAdmin(7, 'assign', false), (e) => e.code === 'review_unavailable');
    assert.equal(calls.length, 0);
  });
});

test('one CSRF-protected POST; refusals keep codes; uncertain outcomes are never replayed', async () => {
  await withFetch(() => reply(200, { account_id: 7, role: 'Admin', assigned: true }), async (calls) => {
    assert.deepEqual(await api.changeSchoolAdmin(7, 'assign', false, true), { account_id: 7, role: 'Admin', assigned: true });
    const posts = calls.filter((c) => c.method === 'POST');
    assert.equal(posts.length, 1);
    assert.deepEqual(JSON.parse(posts[0].body), { expected_present: false });
  });
  for (const [status, body, code] of [
    [409, { error: { code: 'role_assignment_conflict', reason: 'protected_account', message: 'x' } }, 'protected_account'],
    [403, { error: { code: 'access_denied', message: 'x' } }, 'access_denied'],
    [503, { error: { code: 'review_unavailable', message: 'x' } }, 'review_unavailable'],
    [500, undefined, 'outcome_unknown'], [200, { account_id: 8, role: 'Admin', assigned: true }, 'outcome_unknown']]) {
    await withFetch(() => reply(status, body), async (calls) => {
      await assert.rejects(api.changeSchoolAdmin(7, 'assign', false, true), (e) => e.code === code);
      assert.equal(calls.filter((c) => c.method === 'POST').length, 1);
    });
  }
});

test('navigation: Role assignments needs the exact governance code and is never a School Admin link', () => {
  const entry = navigation.DASHBOARD_NAV_ITEMS.find((i) => i.id === 'role-assignments');
  assert.deepEqual([entry.group, [...entry.requiredAny], entry.integration], ['access-control', [TSA], 'planned']); // switch off
  const SCHOOL_ADMIN = ['accounts.registration_requests.read', 'accounts.registration_requests.approve',
    'accounts.registration_requests.reject', 'accounts.school_accounts.read', 'accounts.school_accounts.suspend',
    'accounts.school_accounts.activate'];
  const visible = (perms) => navigation.getVisibleDashboardItems(perms).map((i) => i.id);
  const accessControl = navigation.DASHBOARD_NAV_ITEMS.filter((i) => i.group === 'access-control').map((i) => i.id);
  assert.ok(accessControl.includes('role-assignments'));
  assert.deepEqual(visible(SCHOOL_ADMIN).filter((id) => accessControl.includes(id)), []); // School Admin sees none
  assert.ok(visible([...SCHOOL_ADMIN, TSA]).includes('role-assignments'));
  assert.ok(visible([...SCHOOL_ADMIN, TSA]).includes('account-directory')); // inherited School Admin items stay
  assert.ok(!visible([TSA, 'accounts.school_accounts.read']).includes('registration-review'));
  const panel = readFileSync(new URL('../src/features/access-control/RoleAssignmentsPanel.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(panel, /technical-super-admin\/(assign|revoke)|role_permissions|account_permissions|bulk/i);
});
