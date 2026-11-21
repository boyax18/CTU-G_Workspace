// WF-03.04 tests are deferred until consolidated WF-03 test phase.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
const read = p => readFileSync(new URL(p, import.meta.url), 'utf8');

test('account restrictions stay behind an explicit UI gate', () => {
  const conf = read('../src/features/access-control/accountRestrictionConfig.ts');
  assert.match(conf,/VITE_WORKSPACE_WF0304_ACCOUNT_RESTRICTIONS_ENABLED/);
  assert.match(conf,/=== '1'/);
});
test('revoke Grant, Deny, and Deny removal are separate confirmed commands', () => {
  const panel = read('../src/features/access-control/AccountRestrictionsPanel.tsx');
  for (const command of ['revoke_grant','remove_deny','deny']) assert.ok(panel.includes(command));
  assert.match(panel,/Warning:/);
  assert.match(panel,/Confirm/);
});
