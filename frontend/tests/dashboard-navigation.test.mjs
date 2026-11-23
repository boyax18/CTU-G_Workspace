import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { registerHooks } from 'node:module';
import { test } from 'node:test';
import ts from 'typescript';

const hooks = registerHooks({
  load(url, context, nextLoad) {
    if (url.endsWith('.ts')) {
      const { outputText } = ts.transpileModule(readFileSync(new URL(url), 'utf8'), {
        compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ESNext },
      });
      return { format: 'module', source: outputText, shortCircuit: true };
    }
    return nextLoad(url, context);
  },
});
const nav = await import('../src/features/dashboard/navigation.ts');
hooks.deregister();
const {
  DASHBOARD_NAV_ITEMS, DASHBOARD_NAV_GROUPS, getVisibleDashboardItems, getVisibleNavGroups,
  canOpenDashboardView, getDashboardView, getDashboardHref, getDashboardItem, getDashboardGroup,
} = nav;

const catalogue = JSON.parse(readFileSync(new URL('../../backend/apps/access_control/catalogue/v2_0.json', import.meta.url), 'utf8'));
const catalogueCodes = new Set(catalogue.permissions.map((permission) => permission.permission_code));
const bindings = (role) => catalogue.default_bindings.filter((binding) => binding.role_name === role).map((binding) => binding.permission_code);

const ids = (permissions) => getVisibleDashboardItems(permissions).map((item) => item.id);
const groups = (permissions, placement) => getVisibleNavGroups(permissions, placement).map((group) => group.id);
const READ = 'accounts.registration_requests.read';

test('every permission code in the registry exists in the implemented catalogue (none invented)', () => {
  for (const item of DASHBOARD_NAV_ITEMS) {
    for (const code of item.requiredAny ?? []) assert.ok(catalogueCodes.has(code), `${item.id}: ${code}`);
  }
});

test('ids are unique and every item belongs to a known group', () => {
  const seen = new Set(DASHBOARD_NAV_ITEMS.map((item) => item.id));
  assert.equal(seen.size, DASHBOARD_NAV_ITEMS.length);
  const groupIds = new Set(DASHBOARD_NAV_GROUPS.map((group) => group.id));
  for (const item of DASHBOARD_NAV_ITEMS) assert.ok(groupIds.has(item.group), item.id);
});

test('no grants shows only the dashboard and the profile', () => {
  assert.deepEqual(ids([]), ['overview', 'account']);
  assert.deepEqual(groups([], 'main'), ['overview']);
  assert.deepEqual(groups([], 'utility'), ['account']);
});

test('role names do not authorize any module', () => {
  assert.deepEqual(ids(['Admin', 'Student', 'Treasurer', 'Technical Super Admin']), ['overview', 'account']);
});

test('the exact registration read grant reveals Applicant reviews under Account management', () => {
  assert.deepEqual(ids([READ]), ['overview', 'registration-review', 'account']);
  assert.deepEqual(groups([READ], 'main'), ['overview', 'account-operations']);
  assert.equal(getDashboardItem('registration-review').label, 'Applicant reviews');
  assert.equal(getDashboardGroup('registration-review').label, 'Account management');
  assert.equal(canOpenDashboardView('registration-review', []), false);
  assert.equal(canOpenDashboardView('registration-review', ['accounts.registration_requests.approve']), false);
});

test('explicit deny text is not transformed into a grant by the frontend', () => {
  assert.deepEqual(ids([`Deny:${READ}`]), ['overview', 'account']);
});

test('School Admin catalogue defaults show no Access control, Security or System links (v0.1 §8)', () => {
  const admin = bindings('Admin');
  assert.ok(admin.includes(READ));
  const visible = groups(admin, 'main');
  for (const forbidden of ['access-control', 'security-audit', 'system-operations']) assert.ok(!visible.includes(forbidden), forbidden);
  assert.ok(visible.includes('account-operations'));
});

test('Super Admin (Admin + Technical Super Admin grants) inherits School Admin operations and adds governance', () => {
  const both = [...bindings('Admin'), ...bindings('Technical Super Admin')];
  const visible = groups(both, 'main');
  for (const expected of ['account-operations', 'access-control', 'security-audit', 'system-operations']) {
    assert.ok(visible.includes(expected), expected);
  }
  // The governance role alone does not carry the School Admin operations.
  assert.ok(!groups(bindings('Technical Super Admin'), 'main').includes('account-operations'));
});

test('multi-role permissions produce one deduplicated tree', () => {
  const merged = [...bindings('Student'), ...bindings('Treasurer'), ...bindings('Student')];
  const visible = ids(merged);
  assert.equal(new Set(visible).size, visible.length);
  const tree = getVisibleNavGroups(merged, 'main').flatMap((group) => group.items.map((item) => item.id));
  assert.equal(new Set(tree).size, tree.length);
  assert.ok(visible.includes('my-payments') && visible.includes('payments'));
});

test('groups with no permitted links are hidden', () => {
  for (const group of getVisibleNavGroups(['finance.payments.read'], 'main')) assert.ok(group.items.length > 0, group.id);
  assert.deepEqual(groups(['finance.payments.read'], 'main'), ['overview', 'financial-management']);
});

test('unfinished modules are marked planned; only working views are shell', () => {
  const working = DASHBOARD_NAV_ITEMS.filter((item) => item.integration === 'shell').map((item) => item.id);
  assert.deepEqual(working, ['overview', 'account']); // list switch is off in unit tests
});

test('querystring view is parsed only from known route keys', () => {
  assert.equal(getDashboardView('?view=account'), 'account');
  assert.equal(getDashboardView('?view=registration-review'), 'registration-review');
  assert.equal(getDashboardView('?view=unknown'), 'overview');
  assert.equal(getDashboardView(''), 'overview');
});

test('links stay within the single shared dashboard route', () => {
  assert.equal(getDashboardHref('overview'), '/dashboard');
  assert.equal(getDashboardHref('account'), '/dashboard?view=account');
  assert.equal(getDashboardHref('role-permissions'), '/dashboard?view=role-permissions');
});
