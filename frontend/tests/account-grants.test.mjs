// WF-03.03 deferred frontend smoke assertions (consolidated WF-03 test phase).
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

const ui = readFileSync(new URL('../src/features/access-control/AccountGrantsPanel.tsx', import.meta.url), 'utf8');
const nav = readFileSync(new URL('../src/features/dashboard/navigation.ts', import.meta.url), 'utf8');
const api = readFileSync(new URL('../src/features/access-control/accountGrantApi.ts', import.meta.url), 'utf8');

test('account grants are role-bound with confirmation and exact CTU-G ID search', () => {
  assert.match(ui, /Individual permission Grants/);
  assert.match(ui, /Grant individual permission/);
  assert.match(ui, /CTU-G ID/);
  assert.match(api, /expected_active: false/);
  assert.match(nav, /ACCOUNT_GRANTS_ENABLED \? 'shell' : planned/);
});
