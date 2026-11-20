// WF-02.02 P-07: read-only applicant detail inside Applicant reviews; every API call is mocked.
// The frontend read switch is turned on for this isolated Vite process only.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport, DASHBOARD_TEXT } from './contrastProbe.mjs';

process.env.VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED = '1';

const READ = 'accounts.registration_requests.read';
const LIST = '/api/v1/admin/registration-requests/';
const ENDED = 'Your session has ended. Sign in again to continue.';
const admin = { authenticated: true, account: { school_id: 'ADMIN-001', roles: ['Admin'] }, permissions: [READ] };
const anonymous = { authenticated: false };

const row = (n, role = 'Student') => ({
  account_id: 5000 + n, school_id: `72400${String(n).padStart(2, '0')}`, full_name: `Applicant ${n} Santos`,
  requested_role: role, created_at: '2026-11-10T09:15:00+08:00', email_verified: true,
});
const listPage = (number, hasNext) => ({
  results: Array.from({ length: hasNext ? 20 : 2 }, (_, i) => row(i + 1 + (number - 1) * 20, i % 2 ? 'Instructor' : 'Student')),
  page: number, page_size: 20, has_next: hasNext,
});
const detail = (id, overrides = {}) => ({
  account_id: id, school_id: '7240001', id_label: 'CTU-G ID',
  name: { first: 'Maria', middle: 'Luz', last: 'Santos', suffix: null }, full_name: 'Maria Luz Santos',
  email: 'maria.santos@example.edu', requested_role: 'Student', request_status: 'Pending',
  created_at: '2026-11-10T09:15:00+08:00',
  email_evidence: { state: 'verified', verified_at: '2026-11-10T09:20:00+08:00' },
  institutional_check: { subject: 'enrollment', verified_by_workspace: false },
  data_notes: [],
  ...overrides,
});

function server(detailResponder = (id) => [detail(id)]) {
  const state = { session: admin, lists: [], details: [], writes: 0 };
  const handle = ({ path, request, respond, route }) => {
    if (request.method() !== 'GET') { state.writes++; return route.abort('failed'); }
    if (path.endsWith('/session/')) return respond(state.session);
    if (path === LIST) {
      const query = new URL(request.url()).search;
      state.lists.push(query);
      return respond(listPage(query.includes('page=2') ? 2 : 1, !query.includes('page=2')));
    }
    const match = path.match(/^\/api\/v1\/admin\/registration-requests\/(\d+)\/$/);
    if (match) {
      state.details.push(Number(match[1]));
      const [body, status = 200] = detailResponder(Number(match[1]), state);
      return respond(body, status);
    }
    return route.abort('failed');
  };
  return { state, handle };
}

const VIEW = '/dashboard?view=registration-review';
async function until(check, label) {
  for (let i = 0; i < 100; i++) { if (check()) return; await new Promise((resolve) => setTimeout(resolve, 50)); }
  throw new Error('Timed out waiting for ' + label);
}
const crumbs = async (page) => (await page.getByRole('navigation', { name: 'Breadcrumb' }).innerText()).replace(/\s+/g, ' ').trim();

test('a reviewer opens one application read-only: three panels, exact evidence wording, no decision controls', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    await page.getByRole('link', { name: 'Review application for CTU-G ID 7240001' }).click();
    await page.getByRole('heading', { name: 'Maria Luz Santos', level: 2 }).waitFor();
    assert.ok(page.url().endsWith('applicant=5001'));
    assert.equal(await crumbs(page), 'Dashboard / Account operations / Applicant reviews / CTU-G ID 7240001');
    assert.equal(await page.locator('h1').innerText(), 'Applicant reviews');
    // Focus moves to the applicant heading for keyboard and screen-reader users.
    assert.ok(await page.getByRole('heading', { name: 'Maria Luz Santos', level: 2 }).evaluate((el) => el === document.activeElement));
    const main = await page.locator('main').innerText();
    for (const text of ['Applicant information', 'Email verification evidence', 'Institutional eligibility',
      'maria.santos@example.edu', 'Email ownership verified', 'does not confirm enrollment, employment or eligibility',
      'Enrollment not verified by CTU-G Workspace', "managed by CTU's main system", 'Pending review', 'Not recorded']) {
      assert.ok(main.includes(text), `missing ${text}`);
    }
    // Never a bare "Verified" and no decision or editing controls.
    assert.equal(await page.getByText('Verified', { exact: true }).count(), 0);
    for (const name of [/approve/i, /reject/i, /activate/i, /edit/i, /delete/i, /save/i]) {
      assert.equal(await page.getByRole('button', { name }).count(), 0, String(name));
    }
    assert.equal(fake.state.writes, 0);
    // React StrictMode (dev server) runs the mount effect twice; only this one application is read.
    assert.ok(fake.state.details.length >= 1 && fake.state.details.every((id) => id === 5001), JSON.stringify(fake.state.details));
  }, VIEW);
});

test('Back restores filters, sort and page without refetching, and returns focus to the opened link', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    await page.getByLabel('Sort by').selectOption('-submitted');
    await page.getByRole('button', { name: 'Apply filters' }).click();
    await until(() => fake.state.lists.some((q) => q.includes('sort=-submitted')), 'sorted list');
    await page.getByRole('button', { name: 'Next' }).click();
    await page.getByText('Page 2', { exact: true }).waitFor();
    const before = fake.state.lists.length;
    await page.getByRole('link', { name: 'Review application for CTU-G ID 7240021' }).click();
    await page.getByRole('heading', { level: 2, name: 'Maria Luz Santos' }).waitFor();
    await page.getByRole('button', { name: 'Back to pending applications' }).click();
    await page.getByText('Page 2', { exact: true }).waitFor();
    assert.equal(await page.getByLabel('Sort by').inputValue(), '-submitted');
    assert.equal(fake.state.lists.length, before, 'no refetch on Back');
    assert.equal(await crumbs(page), 'Dashboard / Account operations / Applicant reviews');
    const focused = await page.evaluate(() => document.activeElement?.getAttribute('data-review-link'));
    assert.equal(focused, '5021');
    // Browser Back/Forward and the breadcrumb work too.
    await page.goForward();
    await page.getByRole('heading', { level: 2, name: 'Maria Luz Santos' }).waitFor();
    await page.getByRole('navigation', { name: 'Breadcrumb' }).getByRole('link', { name: 'Applicant reviews' }).click();
    await page.getByText('Page 2', { exact: true }).waitFor();
    await page.goBack();
    await page.getByRole('heading', { level: 2, name: 'Maria Luz Santos' }).waitFor();
    await page.goBack();
    await page.getByText('Page 2', { exact: true }).waitFor();
  }, VIEW);
});

test('every evidence state, the Instructor CTU-G ID and missing data have their own wording', async () => {
  const cases = {
    5101: [detail(5101, { email_evidence: { state: 'no_proof', verified_at: null } }), 'No email proof on record', 'unconfirmed'],
    5102: [detail(5102, { email: 'now@example.edu', email_evidence: { state: 'address_changed', verified_at: null } }), 'Email address changed after verification', 'different address'],
    5103: [detail(5103, { email: null, email_evidence: { state: 'no_email', verified_at: null } }), 'No email address on record', 'no email address'],
    5104: [detail(5104, {
      school_id: '0012345', id_label: 'CTU-G ID', requested_role: 'Instructor', full_name: null,
      name: { first: null, middle: null, last: null, suffix: null }, data_notes: ['missing_profile'],
      institutional_check: { subject: 'employment', verified_by_workspace: false },
    }), 'Institutional eligibility not verified by CTU-G Workspace', 'employment or appointment'],
  };
  const fake = server((id) => [cases[id][0]]);
  await scene(fake.handle, async (page) => {
    for (const [id, [, badge, phrase]] of Object.entries(cases)) {
      await page.goto(new URL(page.url()).origin + `${VIEW}&applicant=${id}`);
      await page.getByRole('heading', { name: 'Email verification evidence' }).waitFor();
      const main = await page.locator('main').innerText();
      assert.ok(main.includes(badge), `${id} badge`);
      assert.ok(main.includes(phrase), `${id} explanation`);
      if (id !== '5104') assert.ok(!main.includes('Email ownership verified'), `${id} must not claim verification`);
    }
    const main = await page.locator('main').innerText();
    assert.ok(main.includes('CTU-G ID') && main.includes('0012345') && main.includes('Name not recorded'));
    assert.ok(main.includes('No name record exists for this application.'));
    assert.equal(await crumbs(page), 'Dashboard / Account operations / Applicant reviews / CTU-G ID 0012345');
  }, VIEW);
});

test('unavailable, expired, denied and failing reads show fixed messages and never sign out on 403', async () => {
  const replies = {
    5201: [{ error: { code: 'request_unavailable', message: 'x' } }, 404],
    5202: [{ error: { code: 'access_denied', message: 'maria.santos@example.edu' } }, 403],
    5203: [{ error: { code: 'review_unavailable', message: 'x' } }, 503],
    5204: [{ error: { code: 'rate_limited', message: 'x' } }, 429],
    5205: [{ ...detail(5205), password_hash: 'pbkdf2$secret' }, 200],
  };
  const expected = {
    5201: ['This application is no longer pending.', false], 5202: ['You do not have permission to review applications.', false],
    5203: ['Applications are not available right now.', true], 5204: ['Too many requests.', true],
    5205: ['The application could not be loaded.', true],
  };
  const fake = server((id) => replies[id]);
  await scene(fake.handle, async (page) => {
    for (const [id, [title, retry]] of Object.entries(expected)) {
      await page.goto(new URL(page.url()).origin + `${VIEW}&applicant=${id}`);
      await page.getByRole('alert').filter({ hasText: title }).waitFor();
      const main = await page.locator('main').innerText();
      assert.ok(!main.includes('maria.santos@example.edu') && !main.includes('pbkdf2'), `${id} leak`);
      assert.equal(await page.getByRole('button', { name: 'Try again' }).count(), retry ? 1 : 0, `${id} retry`);
      await page.getByRole('button', { name: 'Back to pending applications' }).waitFor();
      await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
    }
  }, VIEW);
});

test('an expired session (401) shows the session-ended screen and drops applicant data', async () => {
  const fake = server((_id, state) => { state.session = anonymous; return [{ error: { code: 'authentication_required', message: 'x' } }, 401]; });
  await scene(fake.handle, async (page) => {
    await page.getByText(ENDED).waitFor();
    assert.ok(!(await page.locator('body').innerText()).includes('7240001'));
  }, `${VIEW}&applicant=5301`);
});

test('a malformed applicant value is refused in the browser without any request', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    for (const value of ['abc', '0', '-5', '1e3', '99999999999']) {
      await page.goto(new URL(page.url()).origin + `${VIEW}&applicant=${value}`);
      await page.getByRole('alert').filter({ hasText: 'This application is no longer pending.' }).waitFor();
    }
    assert.deepEqual(fake.state.details, []);
  }, VIEW);
});

test('keyboard: the Review link is reachable and Enter opens the application', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    const link = page.getByRole('link', { name: 'Review application for CTU-G ID 7240002' });
    await link.focus();
    await page.keyboard.press('Enter');
    await page.getByRole('heading', { name: 'Maria Luz Santos', level: 2 }).waitFor();
    await page.keyboard.press('Shift+Tab');
    assert.equal(await page.evaluate(() => document.activeElement?.textContent?.trim()), '←Back to pending applications');
    await page.keyboard.press('Enter');
    await page.getByRole('table').waitFor();
  }, VIEW);
});

test('responsive 360–1440px in Light, System-dark and Dark with composited AA contrast', async () => {
  const fake = server((id) => [detail(id, { email_evidence: { state: 'no_proof', verified_at: null } })]);
  await scene(fake.handle, async (page) => {
    for (const [preference, scheme] of [['light', 'light'], ['system', 'dark'], ['dark', 'dark']]) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate((value) => localStorage.setItem('ctug-theme', value), preference);
      for (const width of [360, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await page.goto(new URL(page.url()).origin + `${VIEW}&applicant=5401`);
        await page.getByRole('heading', { name: 'Institutional eligibility' }).waitFor();
        const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
        assert.ok(layout.scroll <= layout.width, `${preference} ${width}px overflow ${layout.scroll}`);
        const ratios = await contrastReport(page, `${DASHBOARD_TEXT}, main dt, main dd, main li`);
        for (const { text, ratio } of ratios) assert.ok(ratio >= 4.5, `${preference} ${width}px "${text}" ${ratio.toFixed(2)}`);
      }
    }
  }, VIEW);
});
