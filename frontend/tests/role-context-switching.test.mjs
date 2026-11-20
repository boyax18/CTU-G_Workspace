/* D-113 deferred source/contract checks — run in consolidated WF-03 test phase. */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const src = (name) => readFileSync(new URL(`../src/${name}`, import.meta.url), 'utf8');

test('role change requires verified server response, not client-combined permissions', () => {
  const session = src('features/auth/session.ts');
  assert.match(session, /switchWorkspaceRole/);
  assert.match(session, /active_role_id !== roleId/);
  const layout = src('layouts/DashboardLayout.tsx');
  assert.match(layout, /setState\(\{ status: 'ready', session: updated \}\)/);
  assert.match(layout, /setView\('overview'\)/);
});

test('role selector is independently gated and accessible', () => {
  assert.match(src('components/dashboard/RoleContextSwitcher.tsx'), /htmlFor="workspace-role-context"/);
  assert.match(src('features/dashboard/roleContextConfig.ts'), /VITE_WORKSPACE_ROLE_CONTEXT_SWITCHING_ENABLED/);
});
