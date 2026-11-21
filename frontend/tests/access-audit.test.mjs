// Deferred WF-03.06 frontend integration checks; keep in consolidated test run.
import { readFileSync } from 'node:fs';
import { test } from 'node:test';
import assert from 'node:assert/strict';
const read = name => readFileSync(new URL(`../src/${name}`,import.meta.url),'utf8');
test('audit page is a gated read-only dashboard module',()=>{
  const nav=read('features/dashboard/navigation.ts');
  const page=read('features/dashboard/SessionDashboardPage.tsx');
  const api=read('features/access-control/accessAuditApi.ts');
  const panel=read('features/access-control/AccessAuditPanel.tsx');
  assert.match(nav,/ACCESS_AUDIT_ENABLED \? 'shell' : planned/);
  assert.match(page,/view === 'access-audit' && ACCESS_AUDIT_ENABLED/);
  assert.match(api,/getAuditPage/);
  assert.match(api,/getAuditDetail/);
  assert.doesNotMatch(api,/postJSON|deleteJSON|putJSON/);
  assert.match(panel,/role="alert"/);
  assert.match(panel,/Audit entries/);
});
