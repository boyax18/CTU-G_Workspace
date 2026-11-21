/** Task 4: frontend ↔ isolated Django URL route contract for all six WF-03 panels.
 * Static integration guard, not a browser or permission-granting test.
 * Uses only Node built-ins; does not require external test packages.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';

const src = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8');
const backend = (path) => readFileSync(new URL(`../../backend/${path}`, import.meta.url), 'utf8');
const nav = src('features/dashboard/navigation.ts');
const page = src('features/dashboard/SessionDashboardPage.tsx');
const layout = src('layouts/DashboardLayout.tsx');
const reviewUrls = backend('config/review_local_urls.py');
const normalUrls = backend('config/urls.py');

const flows = [
  ['WF-03.01', 'role-assignments', 'RoleAssignmentsPanel', 'ROLE_ASSIGNMENT_ENABLED',
    'roleAssignmentConfig.ts', 'ROLE_ASSIGNMENT_ROUTE_ROOT', 'role-assignments', 'role_assignment_urls', 'access_control.admin_assignments.manage'],
  ['WF-03.02', 'role-permissions', 'RolePermissionsPanel', 'ROLE_PERMISSION_MANAGEMENT_ENABLED',
    'rolePermissionConfig.ts', 'ROLE_PERMISSION_API_ROOT', 'role-permissions', 'role_permission_urls', 'access_control.role_permissions.manage'],
  ['WF-03.03', 'account-overrides', 'AccountGrantsPanel', 'ACCOUNT_GRANTS_ENABLED',
    'accountGrantConfig.ts', 'ACCOUNT_GRANTS_ROOT', 'account-grants', 'account_grant_urls', 'access_control.account_permissions.manage'],
  ['WF-03.04', 'account-restrictions', 'AccountRestrictionsPanel', 'ACCOUNT_RESTRICTIONS_ENABLED',
    'accountRestrictionConfig.ts', 'ACCOUNT_RESTRICTIONS_ROOT', 'account-restrictions', 'account_restriction_urls', 'access_control.account_permissions.manage'],
  ['WF-03.05', 'access-reviews', 'EffectiveAccessPanel', 'EFFECTIVE_ACCESS_INSPECT_ENABLED',
    'effectiveAccessConfig.ts', 'EFFECTIVE_ACCESS_ROOT', 'effective-access', 'effective_access_urls', 'access_control.effective_permissions.inspect'],
  ['WF-03.06', 'access-audit', 'AccessAuditPanel', 'ACCESS_AUDIT_ENABLED',
    'accessAuditConfig.ts', 'ACCESS_AUDIT_ROOT', 'access-audit', 'access_audit_urls', 'access_control.audit.read'],
];

const escapeRx = (value) => value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
const rx = (literal) => new RegExp(escapeRx(literal));

test('all six sidebar items have exact permission hints and only gated screen components', () => {
  for (const [id, view, panel, gate, configFile, , , , code] of flows) {
    assert.match(nav, rx(`id: '${view}'`), `${id} sidebar route missing`);
    assert.match(nav, rx(`requiredAny: ['${code}']`), `${id} exact hint missing`);
    assert.match(nav, rx(`integration: ${gate} ? 'shell' : planned`), `${id} view gate missing`);
    assert.match(page, rx(`view === '${view}' && ${gate}`), `${id} page gate missing`);
    assert.match(page, rx(`<${panel} permissions={permissions} />`), `${id} panel not mounted`);
    assert.match(page, rx(`from '../access-control/${panel}'`), `${id} component import absent`);
    assert.match(src(`features/access-control/${configFile}`), /import\.meta\.env\?\./,
      `${id} feature switch must be an explicit Vite value`);
  }
});

test('all frontend API roots correspond exactly to reviewed backend routes', () => {
  for (const [id, , , , configFile, rootKey, urlSegment, urlModule] of flows) {
    const config = src(`features/access-control/${configFile}`);
    const m = config.match(new RegExp(`\\b${rootKey}\\s*=\\s*['\"]([^'\"]+)['\"]`));
    assert.ok(m, `${id} missing literal API root ${rootKey}`);
    assert.equal(m[1], `/api/v1/admin/${urlSegment}/`, `${id} frontend root mismatch`);
    assert.ok(reviewUrls.includes(`path("api/v1/admin/${urlSegment}/", include("apps.access_control.${urlModule}"))`),
      `${id} reviewed Django URL mount missing`);
    assert.ok(!normalUrls.includes(`api/v1/admin/${urlSegment}/`), `${id} exposed in normal URLconf`);
  }
});

test('role switch waits for confirmed session and leaves protected pages', () => {
  assert.match(layout, /const updated = await switchWorkspaceRole\(roleId\)/);
  assert.match(layout, /setState\(\{ status: 'ready', session: updated \}\)/);
  assert.match(layout, /getDashboardHref\('overview'\)/);
  assert.match(layout, /setSubpage\(null\)/);
  assert.match(page, /if \(!canOpenDashboardView\(view, permissions\)\) return <AccessDenied/);
  const session = src('features/auth/session.ts');
  assert.match(session, /active_role_id !== roleId/);
  assert.match(src('components/dashboard/RoleContextSwitcher.tsx'), /if \(error\) setSelection\(context\.active_role_id/);
});

test('all six API clients use expected roots and have server-backed reads', () => {
  const clients = [
    ['roleAssignmentApi.ts', 'ROLE_ASSIGNMENT_ROUTE_ROOT'],
    ['rolePermissionApi.ts', 'ROLE_PERMISSION_API_ROOT'],
    ['accountGrantApi.ts', 'ACCOUNT_GRANTS_ROOT'],
    ['accountRestrictionApi.ts', 'ACCOUNT_RESTRICTIONS_ROOT'],
    ['effectiveAccessApi.ts', 'EFFECTIVE_ACCESS_ROOT'],
    ['accessAuditApi.ts', 'ACCESS_AUDIT_ROOT'],
  ];
  for (const [name, root] of clients) {
    const client = src(`features/access-control/${name}`);
    assert.ok(client.includes(root), `${name} does not use ${root}`);
    assert.ok(/getJSON\(|fetch\(/.test(client), `${name} missing server-backed reads`);
  }
});
