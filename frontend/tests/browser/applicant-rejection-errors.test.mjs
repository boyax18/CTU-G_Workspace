// WF-02.04 P-09: the rejection section of the applicant detail. Every API call is mocked; no real
// database, session or email. The read, approval and rejection switches are on for this Vite only.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport, DASHBOARD_TEXT } from './contrastProbe.mjs';

process.env.VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED = '1';
process.env.VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED = '1';
process.env.VITE_WORKSPACE_REGISTRATION_REJECTION_ENABLED = '1';

const READ = 'accounts.registration_requests.read';
const APPROVE = 'accounts.registration_requests.approve';
const REJECT = 'accounts.registration_requests.reject';
const LIST = '/api/v1/admin/registration-requests/';
const VIEW = '/dashboard?view=registration-review';
const IDENTITY = 'Registration identity could not be verified';
const session = (permissions) => ({ authenticated: true, account: { school_id: 'ADMIN-001', roles: ['Admin'] }, permissions });

const row = (n) => ({
  account_id: 7000 + n, school_id: `72420${String(n).padStart(2, '0')}`, full_name: `Applicant ${n} Lim`,
  requested_role: 'Student', created_at: '2026-11-10T09:15:00+08:00', email_verified: true,
});
const detail = (id, overrides = {}) => ({
  account_id: id, school_id: '7242001', id_label: 'CTU-G ID',
  name: { first: 'Maria', middle: 'Luz', last: 'Santos', suffix: null }, full_name: 'Maria Luz Santos',
  email: 'maria.santos@example.edu', requested_role: 'Student', request_status: 'Pending',
  created_at: '2026-11-10T09:15:00+08:00',
  email_evidence: { state: 'verified', verified_at: '2026-11-10T09:20:00+08:00' },
  institutional_check: { subject: 'enrollment', verified_by_workspace: false },
  data_notes: [],
  ...overrides,
});

function server({ permissions = [READ, REJECT], detailFor = (id) => detail(id),
  reject = (id) => [{ account_id: id, status: 'Rejected', notification: 'queued' }] } = {}) {
  const state = { session: session(permissions), lists: 0, details: [], rejections: [], approvals: 0 };
  const handle = async ({ path, request, respond, route }) => {
    if (path.endsWith('/session/')) return respond(state.session);
    if (request.method() === 'POST') {
      if (path.endsWith('/approve/')) { state.approvals++; return route.abort('failed'); }
      const match = path.match(/^\/api\/v1\/admin\/registration-requests\/(\d+)\/reject\/$/);
      if (!match) return route.abort('failed');
      state.rejections.push({ id: Number(match[1]), body: request.postDataJSON(), csrf: request.headers()['x-csrftoken'] });
      const result = await reject(Number(match[1]), state);
      if (result === 'abort') return route.abort('failed');
      return respond(result[0], result[1] ?? 200);
    }
    if (path === LIST) {
      state.lists++;
      return respond({ results: [row(1), row(2)], page: 1, page_size: 20, has_next: false });
    }
    const match = path.match(/^\/api\/v1\/admin\/registration-requests\/(\d+)\/$/);
    if (match) { state.details.push(Number(match[1])); return respond(detailFor(Number(match[1]), state)); }
    return route.abort('failed');
  };
  return { state, handle };
}

const at = (id) => `${VIEW}&applicant=${id}`;
const focusedText = (page) => page.evaluate(() => document.activeElement?.textContent?.trim() ?? '');
async function until(check, label) {
  for (let i = 0; i < 100; i++) { if (await check()) return; await new Promise((resolve) => setTimeout(resolve, 50)); }
  throw new Error('Timed out waiting for ' + label);
}
const section = (page) => page.getByRole('region', { name: 'Reject application' });
async function chooseReason(page, label = IDENTITY) {
  await page.getByLabel('Rejection reason *').selectOption({ label });
}
async function openDialog(page) {
  await section(page).getByRole('button', { name: 'Reject application' }).click();
  return page.getByRole('dialog', { name: 'Confirm rejection?' });
}

test('a reviewer picks a fixed reason, confirms in a destructive dialog, and rejects with exactly one POST', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Reject application', level: 3 }).waitFor();
    assert.equal(await page.getByRole('heading', { name: 'Approve application' }).count(), 0, 'no approve permission');
    const options = await page.getByLabel('Rejection reason *').locator('option').allInnerTexts();
    assert.deepEqual(options, ['Choose a reason', 'Incomplete registration information',
      'Registration eligibility could not be confirmed', IDENTITY, 'Duplicate registration request']);
    assert.equal(await page.locator('main textarea, main input[type="text"]').count(), 0, 'no free text');
    assert.ok((await page.locator('main').innerText()).includes('A rejection email can be queued for maria.santos@example.edu'));

    // No reason: a field error, focus on the select, no dialog.
    await section(page).getByRole('button', { name: 'Reject application' }).click();
    await page.getByText('Choose the reason for rejecting this application.').waitFor();
    assert.ok(await page.getByLabel('Rejection reason *').evaluate((el) => el === document.activeElement));
    assert.equal(await page.getByRole('dialog').count(), 0);

    await chooseReason(page);
    let dialog = await openDialog(page);
    await dialog.waitFor();
    assert.equal(await focusedText(page), 'Cancel', 'Cancel first and focused');
    const text = await dialog.innerText();
    assert.ok(text.includes(`Reject Maria Luz Santos (CTU-G ID 7242001) with the reason “${IDENTITY}”?`));
    assert.ok(text.includes('deletes the applicant\'s account and registration data'));
    assert.ok(text.includes('queues a rejection email to maria.santos@example.edu'));
    const confirm = dialog.getByRole('button', { name: 'Confirm rejection' });
    assert.equal(await confirm.evaluate((el) => getComputedStyle(el).backgroundColor), 'rgb(185, 28, 28)', 'destructive style');

    await page.keyboard.press('Escape');
    await until(async () => (await page.getByRole('dialog').count()) === 0, 'dialog closed');
    assert.equal(await focusedText(page), 'Reject application');
    await openDialog(page);
    await page.getByRole('dialog').getByRole('button', { name: 'Cancel' }).click();
    assert.equal(await focusedText(page), 'Reject application');
    assert.equal(fake.state.rejections.length, 0);

    const lists = fake.state.lists;
    dialog = await openDialog(page);
    await dialog.getByRole('button', { name: 'Confirm rejection' }).click();
    const done = page.getByRole('heading', { name: 'Application rejected', level: 2 });
    await done.waitFor();
    assert.ok(await done.evaluate((el) => el === document.activeElement));
    const result = await page.locator('main').innerText();
    assert.ok(result.includes('A rejection email has been queued for delivery'));
    assert.ok(result.includes('not confirmed here'));
    assert.ok(!/email (was|has been) (sent|delivered)/i.test(result), 'never claims delivery');
    assert.equal(fake.state.rejections.length, 1);
    assert.deepEqual(fake.state.rejections[0].body, { rejection_code: 'identity_mismatch' });
    assert.ok(fake.state.rejections[0].csrf);
    await until(() => fake.state.lists > lists, 'list refresh');
    assert.equal(fake.state.approvals, 0);
  }, at(7001));
});

test('no rejection section without the reject permission; an unverified address blocks rejection', async () => {
  const readOnly = server({ permissions: [READ] });
  await scene(readOnly.handle, async (page) => {
    await page.getByRole('heading', { name: 'Institutional eligibility' }).waitFor();
    assert.equal(await page.getByRole('heading', { name: 'Reject application' }).count(), 0);
    assert.equal(await page.getByRole('button', { name: /reject/i }).count(), 0);
  }, at(7002));
  for (const state of ['no_proof', 'address_changed', 'no_email']) {
    const evidence = { state, verified_at: null };
    const fake = server({ detailFor: (id) => detail(id, { email_evidence: evidence, email: state === 'no_email' ? null : 'now@example.edu' }) });
    await scene(fake.handle, async (page) => {
      await page.getByRole('heading', { name: 'Reject application' }).waitFor();
      assert.ok((await page.locator('main').innerText()).includes('A rejection needs a verified email address'), state);
      assert.equal(await section(page).getByRole('button', { name: 'Reject application' }).count(), 0, state);
      assert.equal(fake.state.rejections.length, 0);
    }, at(7003));
  }
});

test('approval and rejection sections coexist when both are permitted', async () => {
  const fake = server({ permissions: [READ, APPROVE, REJECT] });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Approve application' }).waitFor();
    await page.getByRole('heading', { name: 'Reject application' }).waitFor();
    assert.ok((await page.locator('main').innerText()).includes('Django verifies your permission and the decision rules'));
  }, at(7004));
});

test('conflicts and errors show fixed messages, keep the application pending and are never resent', async () => {
  const replies = {
    7101: [[{ error: { code: 'rejection_not_allowed', reason: 'recipient_unverified', message: 'maria.santos@example.edu' } }, 409], 'Rejection was refused: the email address is not verified.', true],
    7102: [[{ error: { code: 'rejection_not_allowed', reason: 'direct_permissions', message: 'x' } }, 409], 'This application cannot be rejected here.', false],
    7103: [[{ error: { code: 'rejection_not_allowed', reason: 'protected_history', message: 'x' } }, 409], 'This application cannot be rejected here.', false],
    7104: [[{ error: { code: 'access_denied', message: 'x' } }, 403], 'You do not have permission to reject applications.', false],
    7105: [[{ error: { code: 'rate_limited', message: 'x' } }, 429], 'Too many requests.', false],
    7106: [[{ error: { code: 'review_unavailable', message: 'x' } }, 503], 'Rejection is not available right now.', false],
  };
  const fake = server({ reject: (id) => replies[id][0] });
  await scene(fake.handle, async (page) => {
    for (const [id, [, title, reload]] of Object.entries(replies)) {
      await page.goto(new URL(page.url()).origin + at(id));
      await page.getByRole('heading', { name: 'Reject application' }).waitFor();
      await chooseReason(page);
      await (await openDialog(page)).getByRole('button', { name: 'Confirm rejection' }).click();
      const alert = page.getByRole('alert').filter({ hasText: title });
      await alert.waitFor();
      assert.ok(await alert.evaluate((el) => el === document.activeElement), `${id} focus`);
      assert.equal(await page.getByRole('button', { name: 'Reload application' }).count(), reload ? 1 : 0, `${id} reload`);
      const main = await page.locator('main').innerText();
      assert.ok(!main.includes('Application rejected'), `${id}`);
      assert.ok(!main.includes('maria.santos@example.edu x'));
      await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
      assert.equal(fake.state.rejections.filter((r) => r.id === Number(id)).length, 1, `${id} sent once`);
    }
  }, VIEW);
});

test('a stale application (404) shows that it is no longer pending', async () => {
  const fake = server({ reject: () => [{ error: { code: 'request_unavailable', message: 'x' } }, 404] });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Reject application' }).waitFor();
    await chooseReason(page);
    await (await openDialog(page)).getByRole('button', { name: 'Confirm rejection' }).click();
    await page.getByRole('alert').filter({ hasText: 'This application is no longer pending.' }).waitFor();
    assert.equal(fake.state.rejections.length, 1);
  }, at(7201));
});

test('an uncertain result pauses rejection until reload and is never replayed', async () => {
  const fake = server({ reject: () => 'abort' });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Reject application' }).waitFor();
    await chooseReason(page);
    await (await openDialog(page)).getByRole('button', { name: 'Confirm rejection' }).click();
    await page.getByRole('alert').filter({ hasText: 'We could not confirm whether the application was rejected.' }).waitFor();
    assert.ok(await section(page).getByRole('button', { name: 'Reject application' }).isDisabled());
    await new Promise((resolve) => setTimeout(resolve, 500));
    assert.equal(fake.state.rejections.length, 1);
    const reads = fake.state.details.length;
    await page.getByRole('button', { name: 'Reload application' }).click();
    await until(() => fake.state.details.length > reads, 'detail re-read');
    await page.getByRole('heading', { name: 'Reject application' }).waitFor();
    assert.equal(fake.state.rejections.length, 1);
  }, at(7301));
});

test('while in flight the dialog cannot be dismissed or submitted twice', async () => {
  let release;
  const held = new Promise((resolve) => { release = resolve; });
  const fake = server({ reject: async (id) => { await held; return [{ account_id: id, status: 'Rejected', notification: 'queued' }]; } });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Reject application' }).waitFor();
    await chooseReason(page);
    const dialog = await openDialog(page);
    await dialog.getByRole('button', { name: 'Confirm rejection' }).click();
    await dialog.getByRole('button', { name: 'Rejecting…' }).waitFor();
    assert.ok(await dialog.getByRole('button', { name: 'Rejecting…' }).isDisabled());
    assert.ok(await dialog.getByRole('button', { name: 'Cancel' }).isDisabled());
    await page.keyboard.press('Escape');
    assert.equal(await dialog.count(), 1);
    await until(() => fake.state.rejections.length === 1, 'one POST');
    release();
    await page.getByRole('heading', { name: 'Application rejected' }).waitFor();
    assert.equal(fake.state.rejections.length, 1);
  }, at(7401));
});

test('keyboard only: Tab to the reason, choose, open, Tab inside the dialog and confirm with Enter', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Reject application' }).waitFor();
    await page.getByLabel('Rejection reason *').focus();
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    const dialog = page.getByRole('dialog', { name: 'Confirm rejection?' });
    await dialog.waitFor();
    await page.keyboard.press('Tab');
    assert.equal(await focusedText(page), 'Confirm rejection');
    await page.keyboard.press('Enter');
    await page.getByRole('heading', { name: 'Application rejected' }).waitFor();
    assert.deepEqual(fake.state.rejections[0].body, { rejection_code: 'incomplete_submission' });
  }, at(7501));
});

test('responsive 360–1440px in Light, System-dark and Dark with composited AA contrast, dialog included', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    for (const [preference, scheme] of [['light', 'light'], ['system', 'dark'], ['dark', 'dark']]) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate((value) => localStorage.setItem('ctug-theme', value), preference);
      for (const width of [360, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await page.goto(new URL(page.url()).origin + at(7601));
        await page.getByRole('heading', { name: 'Reject application' }).waitFor();
        await section(page).getByRole('button', { name: 'Reject application' }).click();
        await page.getByText('Choose the reason for rejecting this application.').waitFor();
        let layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
        assert.ok(layout.scroll <= layout.width, `${preference} ${width}px overflow ${layout.scroll}`);
        const selector = `${DASHBOARD_TEXT}, main legend, dialog h3, dialog p, dialog button`;
        for (const { text, ratio } of await contrastReport(page, selector)) {
          assert.ok(ratio >= 4.5, `${preference} ${width}px "${text}" ${ratio.toFixed(2)}`);
        }
        await chooseReason(page);
        const dialog = await openDialog(page);
        const box = await dialog.boundingBox();
        assert.ok(box && box.x >= 0 && box.x + box.width <= width, `${preference} ${width}px dialog fits`);
        layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
        assert.ok(layout.scroll <= layout.width);
        for (const { text, ratio } of await contrastReport(page, selector)) {
          assert.ok(ratio >= 4.5, `${preference} ${width}px dialog "${text}" ${ratio.toFixed(2)}`);
        }
        await page.keyboard.press('Escape');
      }
    }
    assert.equal(fake.state.rejections.length, 0);
  }, VIEW);
});
