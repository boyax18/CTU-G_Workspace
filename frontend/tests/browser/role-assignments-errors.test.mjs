// WF-03.01: Access control → Role assignments (TC-020, TC-023, TC-036). Every API call is mocked;
// no real database, session or role change. The role-assignment switch is on for this Vite only.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport, DASHBOARD_TEXT } from './contrastProbe.mjs';

process.env.VITE_WORKSPACE_ROLE_ASSIGNMENT_ENABLED = '1';

const TSA = 'access_control.admin_assignments.manage';
const SCHOOL = ['accounts.registration_requests.read', 'accounts.school_accounts.read'];
const API = '/api/v1/admin/role-assignments/';
const VIEW = '/dashboard?view=role-assignments';
const session = (permissions) => ({ authenticated: true, account: { school_id: 'TSA-001', roles: ['Instructor', 'Admin', 'Technical Super Admin'] }, permissions });
const row = (id, overrides = {}) => ({ account_id: id, school_id: `00302${String(id % 100).padStart(2, '0')}`, full_name: `Teacher ${id} Reyes`,
  roles: ['Instructor'], school_admin_action: 'assign', restriction: null, ...overrides });
const ROWS = [row(9101), row(9102, { roles: ['Admin', 'Instructor'], school_admin_action: 'revoke' }),
  row(9103, { roles: ['Admin', 'Instructor', 'Technical Super Admin'], school_admin_action: null, restriction: 'technical_super_admin' }),
  row(9104, { roles: ['Admin'], school_admin_action: null, restriction: 'legacy_admin' })];

function server({ permissions = [...SCHOOL, TSA], rows = ROWS, change = (id, action) => [{ account_id: id, role: 'Admin', assigned: action === 'assign' }] } = {}) {
  const state = { lists: [], posts: [] };
  const handle = async ({ path, request, respond, route }) => {
    if (path.endsWith('/session/')) return respond(session(permissions));
    if (request.method() === 'POST') {
      const m = path.match(/^\/api\/v1\/admin\/role-assignments\/(\d+)\/school-admin\/(assign|revoke)\/$/);
      if (!m) return route.abort('failed');
      state.posts.push({ id: Number(m[1]), action: m[2], body: request.postDataJSON(), csrf: request.headers()['x-csrftoken'] });
      const result = await change(Number(m[1]), m[2]);
      if (result === 'abort') return route.abort('failed');
      return respond(result[0], result[1] ?? 200);
    }
    if (path === API) {
      state.lists.push(new URL(request.url()).search);
      return respond({ results: rows, page: 1, page_size: 20, has_next: false });
    }
    return route.abort('failed');
  };
  return { state, handle };
}

const focused = (page) => page.evaluate(() => document.activeElement?.textContent?.trim() ?? '');
async function until(check, label) {
  for (let i = 0; i < 100; i++) { if (await check()) return; await new Promise((r) => setTimeout(r, 50)); }
  throw new Error('Timed out waiting for ' + label);
}

test('the Technical Super Admin sees Access control → Role assignments with roles and restrictions in words', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Role assignments', level: 2 }).waitFor();
    // Group labels are CSS-uppercased, so compare case-insensitively.
    const nav = (await page.locator('#workspace-sidebar').innerText()).toLowerCase();
    assert.ok(nav.includes('access control') && nav.includes('role assignments') && nav.includes('applicant reviews'), nav);
    const list = await page.getByRole('list', { name: 'Accounts and roles' }).innerText();
    for (const text of ['Teacher 9101 Reyes', 'Roles: Instructor', 'Roles: Admin, Instructor',
      'Only the Django Superuser manages this account’s administrator roles', 'Protected School Admin account']) assert.ok(list.includes(text), text);
    assert.equal(await page.getByRole('button', { name: /Technical Super Admin|grant|elevate/i }).count(), 0);
    assert.equal(await page.getByRole('button', { name: 'Make School Admin for Teacher 9101 Reyes' }).count(), 1);
    assert.equal(await page.getByRole('button', { name: 'Remove School Admin for Teacher 9102 Reyes' }).count(), 1);
    assert.equal(await page.getByRole('button', { name: /School Admin for Teacher 910[34]/ }).count(), 0);
    await page.getByLabel('Search CTU-G ID or name').fill('reyes');
    await page.getByRole('button', { name: 'Search accounts' }).click();
    await until(() => fake.state.lists.some((q) => q.includes('q=reyes')), 'search');
  }, VIEW);
});

test('assigning School Admin is a primary confirmation and sends one confirmed POST', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    const trigger = page.getByRole('button', { name: 'Make School Admin for Teacher 9101 Reyes' });
    await trigger.click();
    const dialog = page.getByRole('dialog', { name: 'Make this account a School Admin?' });
    await dialog.waitFor();
    assert.equal(await focused(page), 'Cancel');
    assert.ok((await dialog.innerText()).includes('keep the Instructor role') && (await dialog.innerText()).includes('signed out on every device'));
    await page.keyboard.press('Escape');
    await until(async () => (await page.getByRole('dialog').count()) === 0, 'closed');
    assert.ok((await focused(page)).startsWith('Make School Admin'));
    assert.equal(fake.state.posts.length, 0);
    await trigger.click();
    await dialog.getByRole('button', { name: 'Confirm School Admin' }).click();
    const notice = page.getByRole('status').filter({ hasText: 'is now a School Admin and keeps the Instructor role' });
    await notice.waitFor();
    assert.ok(await notice.evaluate((el) => el === document.activeElement));
    assert.deepEqual(fake.state.posts.map((p) => [p.id, p.action, p.body]), [[9101, 'assign', { expected_present: false }]]);
    assert.ok(fake.state.posts[0].csrf);
    await until(() => fake.state.lists.length >= 2, 'list reloaded');
  }, VIEW);
});

test('removing School Admin is a destructive confirmation', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('button', { name: 'Remove School Admin for Teacher 9102 Reyes' }).click();
    const dialog = page.getByRole('dialog', { name: 'Remove School Admin?' });
    const confirm = dialog.getByRole('button', { name: 'Confirm removal' });
    assert.equal(await confirm.evaluate((el) => getComputedStyle(el).backgroundColor), 'rgb(185, 28, 28)');
    assert.ok((await dialog.innerText()).includes('keep the Instructor role'));
    await confirm.click();
    await page.getByRole('status').filter({ hasText: 'School Admin was removed from Teacher 9102 Reyes' }).waitFor();
    assert.deepEqual(fake.state.posts.map((p) => [p.action, p.body]), [['revoke', { expected_present: true }]]);
  }, VIEW);
});

test('refusals show fixed messages, change nothing and are sent once; an uncertain result pauses changes', async () => {
  const replies = {
    state_changed: [[{ error: { code: 'role_assignment_conflict', reason: 'state_changed', message: 'x' } }, 409], 'roles changed since the list was loaded', true],
    protected_account: [[{ error: { code: 'role_assignment_conflict', reason: 'protected_account', message: 'x' } }, 409], 'This account is protected.', false],
    last_school_admin: [[{ error: { code: 'role_assignment_conflict', reason: 'last_school_admin', message: 'x' } }, 409], 'The last School Admin cannot be removed.', false],
    access_denied: [[{ error: { code: 'access_denied', message: 'x' } }, 403], 'You do not have permission to change role assignments.', false],
    review_unavailable: [[{ error: { code: 'review_unavailable', message: 'x' } }, 503], 'Role changes are not available right now.', false],
  };
  for (const [key, [reply, title, reload]] of Object.entries(replies)) {
    const fake = server({ change: () => reply });
    await scene(fake.handle, async (page) => {
      await page.getByRole('button', { name: 'Remove School Admin for Teacher 9102 Reyes' }).click();
      await page.getByRole('dialog').getByRole('button', { name: 'Confirm removal' }).click();
      const alert = page.getByRole('alert').filter({ hasText: title });
      await alert.waitFor();
      assert.ok(await alert.evaluate((el) => el === document.activeElement), key);
      assert.equal(await page.getByRole('button', { name: 'Reload list' }).count(), reload ? 1 : 0, key);
      assert.equal(fake.state.posts.length, 1, key);
    }, VIEW);
  }
  const unsure = server({ change: () => 'abort' });
  await scene(unsure.handle, async (page) => {
    await page.getByRole('button', { name: 'Make School Admin for Teacher 9101 Reyes' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Confirm School Admin' }).click();
    await page.getByRole('alert').filter({ hasText: 'We could not confirm the change.' }).waitFor();
    assert.ok(await page.getByRole('button', { name: 'Make School Admin for Teacher 9101 Reyes' }).isDisabled());
    await new Promise((r) => setTimeout(r, 300));
    assert.equal(unsure.state.posts.length, 1);
    await page.getByRole('button', { name: 'Reload list' }).click();
    await until(async () => !(await page.getByRole('button', { name: 'Make School Admin for Teacher 9101 Reyes' }).isDisabled()), 'unlocked');
    assert.equal(unsure.state.posts.length, 1);
  }, VIEW);
});

test('a School Admin never sees Access control and the page is not reachable for them (TC-020)', async () => {
  const fake = server({ permissions: SCHOOL });
  await scene(fake.handle, async (page) => {
    await page.locator('#workspace-sidebar').waitFor();
    await page.waitForLoadState('networkidle');
    const nav = (await page.locator('#workspace-sidebar').innerText()).toLowerCase();  // case-insensitive: labels are uppercased
    assert.ok(nav.includes('applicant reviews'), nav);  // the School Admin's own items are there
    assert.ok(!nav.includes('access control') && !nav.includes('role assignments'), nav);
    assert.equal(await page.getByRole('heading', { name: 'Role assignments', level: 2 }).count(), 0);
    assert.equal(fake.state.lists.length, 0);  // no role-assignment request at all
    assert.equal(await page.getByRole('button', { name: /School Admin/ }).count(), 0);
  }, VIEW);
});

test('responsive 360–1440px in Light, System-dark and Dark with composited AA contrast, dialog included (TC-036)', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    for (const [preference, scheme] of [['light', 'light'], ['system', 'dark'], ['dark', 'dark']]) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate((v) => localStorage.setItem('ctug-theme', v), preference);
      for (const width of [360, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await page.goto(new URL(page.url()).origin + VIEW);
        await page.getByRole('list', { name: 'Accounts and roles' }).waitFor();
        await page.waitForLoadState('networkidle');
        const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
        assert.ok(layout.scroll <= layout.width, `${preference} ${width}px overflow ${layout.scroll}`);
        const selector = `${DASHBOARD_TEXT}, main li p, dialog h3, dialog p, dialog button`;
        for (const { text, ratio } of await contrastReport(page, selector)) {
          assert.ok(ratio >= 4.5, `${preference} ${width}px "${text}" ${ratio.toFixed(2)}`);
        }
        await page.getByRole('button', { name: 'Remove School Admin for Teacher 9102 Reyes' }).click();
        await page.getByRole('dialog').waitFor();
        await page.mouse.move(1, 1);
        await new Promise((r) => setTimeout(r, 250));  // settle the trigger's hover transition before measuring
        for (const { text, ratio } of await contrastReport(page, selector)) {
          assert.ok(ratio >= 4.5, `${preference} ${width}px dialog "${text}" ${ratio.toFixed(2)}`);
        }
        const box = await page.getByRole('dialog').boundingBox();
        assert.ok(box && box.x >= 0 && box.x + box.width <= width);
        await page.keyboard.press('Escape');
      }
    }
    assert.equal(fake.state.posts.length, 0);
  }, VIEW);
});
