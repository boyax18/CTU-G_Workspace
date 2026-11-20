/* D-116 deferred source contract checks — do not run before WF-03 test phase. */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const src = (name) => readFileSync(new URL(`../src/${name}`, import.meta.url), 'utf8');

test('the selector follows server context even without a Vite opt-in', () => {
  const gate = src('features/dashboard/roleContextConfig.ts');
  assert.match(gate, /!== '0'/);
  const shell = src('components/dashboard/DashboardShell.tsx');
  assert.match(shell, /session\.role_context\?\.enabled/);
  assert.match(shell, /role_context\.choices\.length > 1/);
});

test('the role switch only accepts a confirmed server session', () => {
  const session = src('features/auth/session.ts');
  assert.match(session, /active_role_id !== roleId/);
  const layout = src('layouts/DashboardLayout.tsx');
  assert.match(layout, /setState\(\{ status: 'ready', session: updated \}\)/);
});
