// WF-03.01 D-112 contract checks, deferred until consolidated WF-03 test pass.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
const source = (path) => readFileSync(new URL(`../src/features/${path}`, import.meta.url), 'utf8');
test('appointment UI is gated and does not expose role mutation controls', () => {
  const panel = source('access-control/AppointmentManagementPanel.tsx');
  const api = source('access-control/appointmentManagementApi.ts');
  const nav = source('dashboard/navigation.ts');
  assert.match(nav, /requiredAny: \['access_control\.appointments\.record', 'access_control\.appointments\.verify'\]/);
  assert.match(nav, /group: 'account-operations'/);
  assert.match(api, /await initializeCSRF\(\)/);
  assert.match(api, /crypto\.subtle\.digest\('SHA-256'/);
  assert.match(panel, /independent institutional source/i);
  assert.doesNotMatch(panel, /changeOrdinaryRole|assignSchoolAdmin/);
});
