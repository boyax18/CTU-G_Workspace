/* D-117 deferred source contract checks; run during consolidated WF-03 testing. */
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const src = (name) => readFileSync(new URL(`../src/${name}`, import.meta.url), 'utf8');

test('role dropdown invokes server switch without needing an extra button', () => {
  const selector = src('components/dashboard/RoleContextSwitcher.tsx');
  assert.match(selector, /onSwitch\(nextId\)/);
  assert.match(selector, /Currently using:/);
  assert.match(selector, /aria-live="polite"/);
});
test('dashboard follows confirmed server role and explains rejected switches', () => {
  const layout = src('layouts/DashboardLayout.tsx');
  assert.match(layout, /setState\(\{ status: 'ready', session: updated \}\)/);
  assert.match(layout, /Role switching is unavailable in the current server configuration/);
  const page = src('features/dashboard/SessionDashboardPage.tsx');
  assert.match(page, /session\.role_context\?\.choices\.find/);
  assert.match(page, /displayRole \? `\$\{displayRole\} workspace`/);
});
