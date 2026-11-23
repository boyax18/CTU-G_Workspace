// WF-02.05 P-08: Account directory, read-only detail and status controls. Every API call is mocked;
// no real database, session or account change. The account-status switch is on for this Vite only.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport, DASHBOARD_TEXT } from './contrastProbe.mjs';

process.env.VITE_WORKSPACE_ACCOUNT_STATUS_ENABLED = '1';

const READ = 'accounts.school_accounts.read';
const SUSPEND = 'accounts.school_accounts.suspend';
const ACTIVATE = 'accounts.school_accounts.activate';
const API = '/api/v1/admin/school-accounts/';
const VIEW = '/dashboard?view=account-directory';
const session = (permissions) => ({ authenticated: true, account: { school_id: 'ADMIN-001', roles: ['Admin'] }, permissions });
const item = (id, overrides = {}) => ({ account_id: id, school_id: `72430${String(id % 100).padStart(2, '0')}`, id_label: 'CTU-G ID',
  full_name: `Person ${id} Reyes`, roles: ['Student'], is_active: true, ...overrides });
const detail = (id, overrides = {}) => ({ ...item(id), name: { first: 'Person', middle: null, last: 'Reyes', suffix: null },
  request_status: 'Approved', created_at: '2026-11-10T09:15:00+08:00', can_reactivate: true,
  approved_at: null, last_status_change: null, ...overrides });
// WF-02.06 history entries, exactly as Django returns them (D-73/D-74).
const deactivated = (at, actor = 'You') => ({ event: 'account_deactivated', description: 'Account deactivated', occurred_at: at,
  actor, previous_is_active: true, new_is_active: false });
const reactivated = (at, actor = 'An administrator') => ({ event: 'account_reactivated', description: 'Account reactivated',
  occurred_at: at, actor, previous_is_active: false, new_is_active: true });
const approval = (at) => ({ event: 'registration_approved', description: 'Registration approved', occurred_at: at, actor: 'An administrator' });
const historyPage = (results, page = 1, has_next = false) => ({ results, page, page_size: 20, has_next });
const HISTORY = '/history/';

function server({ permissions = [READ, SUSPEND, ACTIVATE], actions = 'suspend,activate', detailFor = (id) => detail(id),
  change = (id, action) => [{ account_id: id, is_active: action === 'activate' }],
  historyFor = (id, page) => historyPage([], page) } = {}) {
  // `active` remembers confirmed changes so a re-read detail reflects them, as Django would.
  const state = { session: session(permissions), lists: [], details: [], posts: [], histories: [], active: {} };
  const handle = async ({ path, request, respond, route }) => {
    if (path.endsWith('/session/')) return respond(state.session);
    const post = path.match(/^\/api\/v1\/admin\/school-accounts\/(\d+)\/(suspend|activate)\/$/);
    if (request.method() === 'POST') {
      if (!post) return route.abort('failed');
      state.posts.push({ id: Number(post[1]), action: post[2], body: request.postDataJSON(), csrf: request.headers()['x-csrftoken'] });
      const result = await change(Number(post[1]), post[2], state);
      if (result === 'abort') return route.abort('failed');
      if ((result[1] ?? 200) === 200) state.active[Number(post[1])] = result[0].is_active;
      return respond(result[0], result[1] ?? 200);
    }
    const history = path.match(/^\/api\/v1\/admin\/school-accounts\/(\d+)\/history\/$/);
    if (history) {
      const page = Number(new URL(request.url()).searchParams.get('page'));
      state.histories.push([Number(history[1]), page]);
      const value = await historyFor(Number(history[1]), page, state);
      if (value === 'abort') return route.abort('failed');
      return Array.isArray(value) ? respond(value[0], value[1]) : respond(value);
    }
    if (path === API) {
      state.lists.push(new URL(request.url()).search);
      return respond({ results: [item(8101), item(8102, { is_active: false, roles: ['Treasurer'] }),
        item(8103, { id_label: 'CTU-G ID', school_id: '0012345', roles: ['Instructor'] })], page: 1, page_size: 20, has_next: false });
    }
    const one = path.match(/^\/api\/v1\/admin\/school-accounts\/(\d+)\/$/);
    if (one) {
      state.details.push(Number(one[1]));
      const value = detailFor(Number(one[1]), state);
      if (Array.isArray(value)) return respond(value[0], value[1]);
      const id = Number(one[1]);
      return respond(id in state.active ? { ...value, is_active: state.active[id] } : value, 200, { 'X-Workspace-Available-Actions': actions });
    }
    return route.abort('failed');
  };
  return { state, handle };
}

const at = (id) => `${VIEW}&account=${id}`;

test('read-only server hides status actions despite mutation build flag and permission hints', async () => {
  const fake = server({ actions: '' });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Account information', level: 3 }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Deactivate account', exact: true }).count(), 0);
    assert.equal(await page.getByRole('button', { name: 'Reactivate account', exact: true }).count(), 0);
    assert.equal(fake.state.posts.length, 0);
  }, at(8101));
});
const focused = (page) => page.evaluate(() => document.activeElement?.textContent?.trim() ?? '');
async function until(check, label) {
  for (let i = 0; i < 100; i++) { if (await check()) return; await new Promise((r) => setTimeout(r, 50)); }
  throw new Error('Timed out waiting for ' + label);
}

test('directory lists eligible accounts with status in words, filters on the server and opens a detail', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'School accounts', level: 2 }).waitFor();
    const list = await page.getByRole('list', { name: 'School accounts' }).innerText();
    for (const text of ['Person 8101 Reyes', 'Active', 'Inactive', 'Treasurer', 'CTU-G ID 0012345']) assert.ok(list.includes(text), text);
    await page.getByLabel('Search CTU-G ID or name').fill('reyes');
    await page.getByLabel('Status').selectOption('inactive');
    await page.getByRole('button', { name: 'Apply filters' }).click();
    await until(() => fake.state.lists.some((q) => q.includes('q=reyes') && q.includes('status=inactive')), 'filtered list');
    await page.getByRole('link', { name: 'View account for CTU-G ID 7243001' }).click();
    await page.getByRole('heading', { name: 'Person 8101 Reyes', level: 2 }).waitFor();
    const main = await page.locator('main').innerText();
    assert.ok(main.includes('Active: can sign in') && main.includes('Roles') && main.includes('managed separately'));
    assert.equal(await page.getByRole('button', { name: /edit|assign|grant|history/i }).count(), 0);
    await page.getByRole('button', { name: 'Back to school accounts' }).click();
    await page.getByRole('list', { name: 'School accounts' }).waitFor();
  }, VIEW);
});

test('deactivation uses a destructive dialog, sends one confirmed POST and reports the result', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Deactivate account', level: 3 }).waitFor();
    const trigger = page.getByRole('button', { name: 'Deactivate account' });
    await trigger.click();
    const dialog = page.getByRole('dialog', { name: 'Deactivate this account?' });
    await dialog.waitFor();
    assert.equal(await focused(page), 'Cancel');
    assert.ok((await dialog.innerText()).includes('signed out on every device and cannot sign in until the account is reactivated'));
    const confirm = dialog.getByRole('button', { name: 'Confirm deactivation' });
    assert.equal(await confirm.evaluate((el) => getComputedStyle(el).backgroundColor), 'rgb(185, 28, 28)');
    await page.keyboard.press('Escape');
    await until(async () => (await page.getByRole('dialog').count()) === 0, 'closed');
    assert.equal(await focused(page), 'Deactivate account');
    assert.equal(fake.state.posts.length, 0);
    await trigger.click();
    await dialog.getByRole('button', { name: 'Confirm deactivation' }).click();
    const notice = page.getByRole('status').filter({ hasText: 'Account deactivated.' });
    await notice.waitFor();
    assert.ok(await notice.evaluate((el) => el === document.activeElement));
    assert.deepEqual(fake.state.posts.map((p) => [p.action, p.body]), [['suspend', { expected_active: true }]]);
    assert.ok(fake.state.posts[0].csrf);
    assert.ok((await page.locator('main').innerText()).includes('Inactive: cannot sign in'));
    await page.getByRole('heading', { name: 'Reactivate account', level: 3 }).waitFor();
  }, at(8101));
});

test('reactivation is a primary confirmation and never promises old sign-ins back', async () => {
  const fake = server({ detailFor: (id) => detail(id, { is_active: false }) });
  await scene(fake.handle, async (page) => {
    await page.getByRole('button', { name: 'Reactivate account' }).click();
    const dialog = page.getByRole('dialog', { name: 'Reactivate this account?' });
    assert.ok((await dialog.innerText()).includes('earlier sign-ins are not restored'));
    await dialog.getByRole('button', { name: 'Confirm reactivation' }).click();
    await page.getByRole('status').filter({ hasText: 'Account reactivated.' }).waitFor();
    assert.deepEqual(fake.state.posts.map((p) => [p.action, p.body]), [['activate', { expected_active: false }]]);
  }, at(8102));
});

test('controls appear only with the exact permission; an account without an active role cannot be reactivated', async () => {
  const readOnly = server({ permissions: [READ] });
  await scene(readOnly.handle, async (page) => {
    await page.getByRole('heading', { name: 'Account information' }).waitFor();
    assert.equal(await page.getByRole('button', { name: /deactivate|reactivate/i }).count(), 0);
  }, at(8101));
  const suspendOnly = server({ permissions: [READ, SUSPEND], detailFor: (id) => detail(id, { is_active: false }) });
  await scene(suspendOnly.handle, async (page) => {
    await page.getByRole('heading', { name: 'Account information' }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Reactivate account' }).count(), 0);
  }, at(8102));
  const noRole = server({ detailFor: (id) => detail(id, { is_active: false, roles: [], can_reactivate: false }) });
  await scene(noRole.handle, async (page) => {
    await page.getByText('This account has no active role, so it cannot be reactivated here.').waitFor();
    assert.equal(await page.getByRole('button', { name: 'Reactivate account' }).count(), 0);
  }, at(8104));
});

test('conflicts and errors show fixed messages, change nothing and are sent once', async () => {
  const replies = {
    8201: [[{ error: { code: 'account_status_conflict', reason: 'state_changed', message: 'x' } }, 409], "This account's status changed since you opened it.", true],
    8202: [[{ error: { code: 'account_status_conflict', reason: 'protected_account', message: 'x' } }, 409], 'This account is protected.', false],
    8203: [[{ error: { code: 'access_denied', message: 'x' } }, 403], 'You do not have permission to change this account.', false],
    8204: [[{ error: { code: 'rate_limited', message: 'x' } }, 429], 'Too many requests.', false],
    8205: [[{ error: { code: 'review_unavailable', message: 'x' } }, 503], 'Account changes are not available right now.', false],
  };
  const fake = server({ change: (id) => replies[id][0] });
  await scene(fake.handle, async (page) => {
    for (const [id, [, title, reload]] of Object.entries(replies)) {
      await page.goto(new URL(page.url()).origin + at(id));
      await page.getByRole('button', { name: 'Deactivate account' }).click();
      await page.getByRole('dialog').getByRole('button', { name: 'Confirm deactivation' }).click();
      const alert = page.getByRole('alert').filter({ hasText: title });
      await alert.waitFor();
      assert.ok(await alert.evaluate((el) => el === document.activeElement), id);
      assert.equal(await page.getByRole('button', { name: 'Reload account' }).count(), reload ? 1 : 0, id);
      assert.ok((await page.locator('main').innerText()).includes('Active: can sign in'), `${id} unchanged`);
      await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
      assert.equal(fake.state.posts.filter((p) => p.id === Number(id)).length, 1);
    }
  }, VIEW);
});

test('a stale account (404) and an uncertain result are handled without replay', async () => {
  const stale = server({ change: () => [{ error: { code: 'request_unavailable', message: 'x' } }, 404] });
  await scene(stale.handle, async (page) => {
    await page.getByRole('button', { name: 'Deactivate account' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Confirm deactivation' }).click();
    await page.getByRole('alert').filter({ hasText: 'This account is not available.' }).waitFor();
    assert.equal(stale.state.posts.length, 1);
  }, at(8301));
  const unsure = server({ change: () => 'abort' });
  await scene(unsure.handle, async (page) => {
    await page.getByRole('button', { name: 'Deactivate account' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Confirm deactivation' }).click();
    await page.getByRole('alert').filter({ hasText: 'We could not confirm the change.' }).waitFor();
    assert.ok(await page.getByRole('button', { name: 'Deactivate account' }).isDisabled());
    await new Promise((r) => setTimeout(r, 400));
    assert.equal(unsure.state.posts.length, 1);
    const reads = unsure.state.details.length;
    await page.getByRole('button', { name: 'Reload account' }).click();
    await until(() => unsure.state.details.length > reads, 're-read');
    await page.getByRole('heading', { name: 'Deactivate account', level: 3 }).waitFor();
    assert.ok(!(await page.getByRole('button', { name: 'Deactivate account' }).isDisabled()));
    assert.equal(unsure.state.posts.length, 1);
  }, at(8302));
});

test('while in flight the dialog cannot be dismissed or submitted twice', async () => {
  let release;
  const held = new Promise((r) => { release = r; });
  const fake = server({ change: async (id) => { await held; return [{ account_id: id, is_active: false }]; } });
  await scene(fake.handle, async (page) => {
    await page.getByRole('button', { name: 'Deactivate account' }).click();
    const dialog = page.getByRole('dialog');
    await dialog.getByRole('button', { name: 'Confirm deactivation' }).click();
    await dialog.getByRole('button', { name: 'Deactivating…' }).waitFor();
    assert.ok(await dialog.getByRole('button', { name: 'Cancel' }).isDisabled());
    await page.keyboard.press('Escape');
    assert.equal(await dialog.count(), 1);
    release();
    await page.getByRole('status').filter({ hasText: 'Account deactivated.' }).waitFor();
    assert.equal(fake.state.posts.length, 1);
  }, at(8401));
});

test('responsive 360–1440px in Light, System-dark and Dark with composited AA contrast', async () => {
  // 8501: legacy account (Not recorded, empty history); 8502: dated status and a full first history page.
  const fake = server({
    detailFor: (id) => (id === 8502
      ? detail(id, { approved_at: '2026-11-01T08:00:00+00:00', last_status_change: deactivated('2026-11-18T10:00:00+00:00') })
      : detail(id)),
    historyFor: (id, page) => (id === 8502
      ? historyPage([deactivated('2026-11-18T10:00:00+00:00'), reactivated('2026-11-17T10:00:00+00:00'),
        ...Array.from({ length: 18 }, (_, i) => deactivated(`2026-11-${String(16 - Math.floor(i / 2)).padStart(2, '0')}T0${i % 10}:00:00+00:00`, 'An administrator'))],
      page, true)
      : historyPage([], page)),
  });
  await scene(fake.handle, async (page) => {
    for (const [preference, scheme] of [['light', 'light'], ['system', 'dark'], ['dark', 'dark']]) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate((v) => localStorage.setItem('ctug-theme', v), preference);
      for (const width of [360, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        for (const target of [VIEW, at(8501), at(8502)]) {
          await page.goto(new URL(page.url()).origin + target);
          await page.getByRole('heading', { level: 2 }).first().waitFor();
          await page.waitForLoadState('networkidle');
          const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
          assert.ok(layout.scroll <= layout.width, `${preference} ${width}px ${target} overflow ${layout.scroll}`);
          const selector = `${DASHBOARD_TEXT}, main li p, main legend, dialog h3, dialog p, dialog button`;
          if (target === at(8502)) await page.getByRole('list', { name: 'Status history' }).waitFor();
          if (target !== VIEW) await page.getByRole('button', { name: 'Deactivate account' }).click();
          for (const { text, ratio } of await contrastReport(page, selector)) {
            assert.ok(ratio >= 4.5, `${preference} ${width}px ${target} "${text}" ${ratio.toFixed(2)}`);
          }
          if (target !== VIEW) {
            const box = await page.getByRole('dialog').boundingBox();
            assert.ok(box && box.x >= 0 && box.x + box.width <= width);
            await page.keyboard.press('Escape');
          }
        }
      }
    }
    assert.equal(fake.state.posts.length, 0);
  }, VIEW);
});

// -- WF-02.06 View account status and permitted history ---------------------------------------------
test('WF-02.06: a legacy account shows Not recorded and an empty history, without any write', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Account status', level: 3 }).waitFor();
    // Labels are CSS-uppercased (<dt>), so compare case-insensitively.
    const status = (await page.getByRole('region', { name: 'Account status' }).innerText()).toLowerCase();
    for (const text of ['Active: can sign in', 'Approved', 'Approved on', 'Last status change', 'Not recorded', 'not academic enrollment']) {
      assert.ok(status.includes(text.toLowerCase()), text);
    }
    await page.getByRole('heading', { name: 'No status changes recorded', level: 4 }).waitFor();
    // React StrictMode (dev) mounts effects twice; only page 1 is ever requested without a click.
    assert.ok(fake.state.histories.every(([id, n]) => id === 8601 && n === 1) && fake.state.histories.length <= 2);
    assert.equal(await page.getByRole('button', { name: 'Show older entries' }).count(), 0);
    assert.ok(!(await page.locator('main').innerText()).includes('Account history is a separate view'));
    assert.equal(fake.state.posts.length, 0);
  }, at(8601));
});

test('WF-02.06: dated status and newest-first history with server-made actor labels only', async () => {
  const fake = server({
    detailFor: (id) => detail(id, { is_active: false, approved_at: '2026-11-01T08:00:00+00:00',
      last_status_change: deactivated('2026-11-18T10:00:00+00:00') }),
    historyFor: (id, page) => historyPage([deactivated('2026-11-18T10:00:00+00:00'),
      reactivated('2026-11-17T09:30:00+00:00'), approval('2026-11-01T08:00:00+00:00')], page),
  });
  await scene(fake.handle, async (page) => {
    const list = page.getByRole('list', { name: 'Status history' });
    await list.waitFor();
    const status = await page.getByRole('region', { name: 'Account status' }).innerText();
    assert.ok(status.includes('Inactive: cannot sign in') && status.includes('Account deactivated') && status.includes('By you'), status);
    assert.ok(!status.includes('Not recorded'));
    const items = await list.getByRole('listitem').allInnerTexts();
    assert.equal(items.length, 3);
    assert.ok(items[0].startsWith('Account deactivated') && items[0].includes('By you') && items[0].includes('Active to Inactive'), items[0]);
    assert.ok(items[1].startsWith('Account reactivated') && items[1].includes('By an administrator') && items[1].includes('Inactive to Active'));
    assert.ok(items[2].startsWith('Registration approved') && items[2].includes('By an administrator') && !items[2].includes(' to '));
    assert.equal(await list.locator('time').first().getAttribute('datetime'), '2026-11-18T10:00:00+00:00');
    await page.getByRole('status').filter({ hasText: 'Showing all 3 entries.' }).waitFor();
    const main = await page.locator('main').innerText();
    for (const hidden of ['ADMIN-001', 'actor_account', 'eligibility', 'ctu_main_system', '@']) assert.ok(!main.includes(hidden), hidden);
  }, at(8602));
});

test('WF-02.06: older entries load once on request; a failed page keeps what is shown', async () => {
  const first = Array.from({ length: 20 }, (_, i) => deactivated(`2026-11-18T${String(23 - i).padStart(2, '0')}:00:00+00:00`, 'An administrator'));
  let failSecond = true;
  const fake = server({
    historyFor: (id, page) => {
      if (page === 1) return historyPage(first, 1, true);
      if (failSecond) { failSecond = false; return [{ error: { code: 'review_unavailable', message: 'x' } }, 503]; }
      return historyPage([approval('2026-11-01T08:00:00+00:00')], 2, false);
    },
  });
  await scene(fake.handle, async (page) => {
    const more = page.getByRole('button', { name: 'Show older entries' });
    await more.waitFor();
    await page.getByRole('status').filter({ hasText: 'Showing the 20 most recent entries.' }).waitFor();
    await more.click();
    await page.getByRole('alert').filter({ hasText: 'Status history is not available right now. The entries above are unchanged.' }).waitFor();
    assert.equal(await page.getByRole('list', { name: 'Status history' }).getByRole('listitem').count(), 20);
    await more.focus();
    await page.keyboard.press('Enter');
    await page.getByRole('status').filter({ hasText: 'Showing all 21 entries.' }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Show older entries' }).count(), 0);
    // Page 2 only on request: once (refused) and once more after the explicit retry; nothing beyond it.
    assert.deepEqual(fake.state.histories.filter(([, n]) => n !== 1), [[8603, 2], [8603, 2]]);
    assert.ok(fake.state.histories.filter(([, n]) => n === 1).length <= 2);
    assert.equal(fake.state.posts.length, 0);
  }, at(8603));
});

test('WF-02.06: denied, not-found and unavailable history keep the account status visible', async () => {
  const replies = {
    8611: [[{ error: { code: 'access_denied', message: 'x' } }, 403], 'You do not have permission to view this history.', false],
    8612: [[{ error: { code: 'request_unavailable', message: 'x' } }, 404], "This account's history is not available.", false],
    8613: [[{ error: { code: 'review_unavailable', message: 'x' } }, 503], 'Status history is not available right now.', true],
    8614: ['abort', "We couldn't load the history.", true],
  };
  let recovered = false;
  const fake = server({ historyFor: (id, page) => (recovered ? historyPage([], page) : replies[id][0]) });
  await scene(fake.handle, async (page) => {
    for (const [id, [, title, retry]] of Object.entries(replies)) {
      recovered = false;
      await page.goto(new URL(page.url()).origin + at(id));
      const alert = page.getByRole('alert').filter({ hasText: title });
      await alert.waitFor();
      assert.ok((await page.getByRole('region', { name: 'Account status' }).innerText()).includes('Active: can sign in'), id);
      assert.equal(await alert.getByRole('button', { name: 'Try again' }).count(), retry ? 1 : 0, id);
      if (retry) {
        recovered = true;
        await alert.getByRole('button', { name: 'Try again' }).click();
        await page.getByRole('heading', { name: 'No status changes recorded', level: 4 }).waitFor();
      }
    }
    assert.equal(fake.state.posts.length, 0);
  }, VIEW);
});

test('WF-02.06: after a confirmed change the status dates and history are re-read from the server', async () => {
  let changed = false;
  const fake = server({
    detailFor: (id) => detail(id, changed ? { last_status_change: deactivated('2026-11-18T10:00:00+00:00') } : {}),
    change: (id) => { changed = true; return [{ account_id: id, is_active: false }]; },
    historyFor: (id, page) => historyPage(changed ? [deactivated('2026-11-18T10:00:00+00:00')] : [], page),
  });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'No status changes recorded', level: 4 }).waitFor();
    await page.getByRole('button', { name: 'Deactivate account' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Confirm deactivation' }).click();
    await page.getByRole('status').filter({ hasText: 'Account deactivated.' }).waitFor();
    await page.getByRole('list', { name: 'Status history' }).waitFor();
    await until(async () => (await page.getByRole('region', { name: 'Account status' }).innerText()).includes('By you'), 'status re-read');
    assert.equal(fake.state.posts.length, 1);
    assert.ok(fake.state.details.length >= 2 && fake.state.histories.length >= 2);
    assert.ok((await page.getByRole('region', { name: 'Account status' }).innerText()).includes('Inactive: cannot sign in'));
  }, at(8604));
});
