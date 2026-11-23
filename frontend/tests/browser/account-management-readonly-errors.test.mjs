// Normal dashboard read integration; isolated localhost Vite, synthetic APIs only.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';

process.env.VITE_WORKSPACE_ACCOUNT_DIRECTORY_ENABLED = '1';
process.env.VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED = '0';
process.env.VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED = '1';

const ROOT = '/api/v1/admin/school-accounts/';
const item = { account_id: 42, school_id: 'SYNTH-42', id_label: 'CTU-G ID',
  full_name: 'Synthetic Student', roles: ['Student'], is_active: true };
const detail = { ...item, name: { first: 'Synthetic', middle: null, last: 'Student', suffix: null },
  request_status: 'Approved', created_at: '2026-11-23T01:00:00+00:00', can_reactivate: true,
  approved_at: null, last_status_change: null };

function server(technical = false, permissions = ['accounts.school_accounts.read', 'accounts.registration_requests.read',
  'accounts.school_accounts.suspend', 'accounts.school_accounts.activate'], roles = technical ? ['Instructor', 'Admin', 'Technical Super Admin'] : ['Admin']) {
  const state = { reads: 0, mutations: 0 };
  return { state, handle: async ({ path, request, respond, route }) => {
    if (request.method() === 'POST') { state.mutations++; return route.abort(); }
    if (path.endsWith('/session/')) return respond({ authenticated: true,
      account: { school_id: 'SYNTH-ADMIN', roles },
      permissions });
    if (path === ROOT) { state.reads++; return respond({ results: [item], page: 1, page_size: 20, has_next: false }); }
    if (path === `${ROOT}42/`) return respond(detail, 200, { 'X-Workspace-Available-Actions': 'suspend,activate' });
    if (path === `${ROOT}42/history/`) return respond({ results: [], page: 1, page_size: 20, has_next: false });
    return route.abort();
  } };
}

for (const technical of [false, true]) {
  test(`${technical ? 'Technical Super Admin' : 'School Admin'} opens directory using only the read build switch`, async () => {
    const fake = server(technical);
    await scene(fake.handle, async (page) => {
      await page.getByText('Synthetic Student', { exact: true }).waitFor();
      await page.getByRole('link', { name: 'View account for CTU-G ID SYNTH-42' }).click();
      await page.getByRole('heading', { name: 'Account information', level: 3 }).waitFor();
      await page.getByRole('heading', { name: 'Status history', level: 3 }).waitFor();
      assert.equal(await page.getByRole('button', { name: 'Deactivate account', exact: true }).count(), 0);
      assert.equal(fake.state.mutations, 0);
      assert.ok(fake.state.reads > 0);
    }, '/dashboard?view=account-directory');
  });
}

test('a Student context cannot open Account Management or fetch directory records', async () => {
  const fake = server(false, [], ['Student']);
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Section unavailable' }).waitFor();
    assert.equal(fake.state.reads, 0);
    assert.equal(fake.state.mutations, 0);
  }, '/dashboard?view=account-directory');
});
