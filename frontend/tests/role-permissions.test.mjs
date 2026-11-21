// WF-03.02 deferred dashboard/API contract checks.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const source = (path) => readFileSync(new URL(`../src/${path}`, import.meta.url), 'utf8');

test('role permission page is separately gated and requires exact server permission', () => {
  const nav = source('features/dashboard/navigation.ts');
  const page = source('features/dashboard/SessionDashboardPage.tsx');
  const config = source('features/access-control/rolePermissionConfig.ts');
  assert.match(nav, /requiredAny: \['access_control\.role_permissions\.manage'\]/);
  assert.match(nav, /ROLE_PERMISSION_MANAGEMENT_ENABLED \? 'shell' : planned/);
  assert.match(page, /<RolePermissionsPanel permissions=\{permissions\}/);
  assert.match(config, /VITE_WORKSPACE_WF0302_ROLE_PERMISSIONS_ENABLED/);
});

test('UI confirms each change and uses server results without assuming success', () => {
  const panel = source('features/access-control/RolePermissionsPanel.tsx');
  const api = source('features/access-control/rolePermissionApi.ts');
  assert.match(panel, /<Modal open=\{pending !== null\}/);
  assert.match(panel, /permission\.change_allowed/);
  assert.match(panel, /await reload\(\)/);
  assert.match(api, /expected_active: expectedActive/);
  assert.match(api, /postJSON\(/);
});
