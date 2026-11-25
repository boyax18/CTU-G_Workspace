// WF-11.01 School years & semesters. Every API call is mocked; no real database, session or period change.
// The academic-periods switch is on for this Vite only.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport, DASHBOARD_TEXT } from './contrastProbe.mjs';

process.env.VITE_WORKSPACE_ACADEMIC_PERIODS_ENABLED = '1';

const CODE = 'academic.periods.manage';
const VIEW = '/dashboard?view=school-periods';
const API = '/api/v1/academic/';
const session = (permissions = [CODE]) => ({ authenticated: true, account: { school_id: 'ADMIN-001', roles: ['Admin'] }, permissions });
const MISSING = ['valid_dates', 'approved_fee', 'academic_offerings'];
const semester = (id, term, overrides = {}) => ({ semester_id: id, term, label: term === 'first' ? 'First semester' : 'Second semester',
  status: 'Draft', start_date: null, end_date: null, version: 1, can_edit_dates: true,
  activation: { available: false, missing: MISSING }, updated_at: '2026-11-25T05:00:00+00:00', ...overrides });
const year = (id, start, overrides = {}) => ({ school_year_id: id, start_year: start, end_year: start + 1, label: `${start}–${start + 1}`,
  status: 'Draft', semesters: [semester(id * 10 + 1, 'first'), semester(id * 10 + 2, 'second')], can_delete: true,
  created_at: '2026-11-25T05:00:00+00:00', updated_at: '2026-11-25T05:00:00+00:00', ...overrides });

function server({ permissions, years = [], list = null, onPost = null } = {}) {
  const state = { years: [...years], posts: [], lists: 0 };
  const handle = async ({ path, request, respond }) => {
    if (path.endsWith('/session/')) return respond(session(permissions));
    if (request.method() === 'POST') {
      const body = request.postDataJSON();
      state.posts.push({ path, body, csrf: request.headers()['x-csrftoken'] });
      const custom = onPost?.(path, body, state);
      if (custom) return respond(custom[0], custom[1]);
      if (path === `${API}school-years/`) {
        const created = year(state.years.length + 1, body.start_year);
        state.years.unshift(created);
        return respond(created, 201);
      }
      const dates = path.match(/semesters\/(\d+)\/dates\/$/);
      if (dates) {
        const owner = state.years.find((y) => y.semesters.some((s) => s.semester_id === Number(dates[1])));
        owner.semesters = owner.semesters.map((s) => (s.semester_id === Number(dates[1])
          ? { ...s, start_date: body.start_date, end_date: body.end_date, version: s.version + 1 } : s));
        return respond(owner);
      }
      const removal = path.match(/school-years\/(\d+)\/delete\/$/);
      if (removal) {
        state.years = state.years.filter((y) => y.school_year_id !== Number(removal[1]));
        return respond({ deleted: true, school_year_id: Number(removal[1]) });
      }
    }
    if (path === `${API}school-years/`) {
      state.lists += 1;
      if (list) return respond(...list(state));
      return respond({ results: state.years, page: 1, page_size: 20, has_next: false });
    }
    return respond({ error: { code: 'not_found' } }, 404);
  };
  return { state, handle };
}

const open = async (page) => {
  await page.goto(new URL(page.url()).origin + VIEW);
  await page.getByRole('heading', { name: 'School years', level: 2 }).waitFor();
};

test('empty state, create with validation, then both Draft semesters appear with read-only prerequisites', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByText('No school years yet').waitFor();
    await page.getByRole('button', { name: 'Create school year' }).click();
    assert.equal(await page.getByText('Enter a starting year from 2000 to 2100.').count(), 1);
    assert.equal(await page.evaluate(() => document.activeElement?.id?.endsWith('-year')), true);
    assert.equal(fake.state.posts.length, 0);
    await page.getByLabel('Starting year').fill('2026');
    await page.getByRole('button', { name: 'Create school year' }).click();
    await page.getByRole('status').filter({ hasText: 'S.Y. 2026–2027 was created with Draft First and Second semesters.' }).waitFor();
    assert.deepEqual(fake.state.posts.map((p) => p.body), [{ start_year: 2026 }]);
    assert.ok(fake.state.posts[0].csrf);
    await page.getByRole('heading', { name: 'S.Y. 2026–2027', level: 3 }).waitFor();
    const main = await page.locator('main').innerText();
    for (const text of ['First semester', 'Second semester', 'Activation prerequisites', 'Not ready',
      'Review activation for the current details.']) assert.ok(main.includes(text), text);
    // No fee control is ever offered; lifecycle actions are reviews, not direct operations.
    assert.equal(await page.getByRole('button', { name: /fee/i }).count(), 0);
    assert.equal(await page.getByRole('button', { name: /^(activate|close|archive)/i }).count(), 0);
  }, VIEW);
});

test('with the lifecycle switches off, the activation review is read-only and nothing can be confirmed', async () => {
  const fake = server({ years: [year(1, 2026)] });
  const handle = async (args) => {
    if (args.path === `${API}semesters/11/activation/` && args.request.method() === 'GET') {
      return args.respond({ semester: { semester_id: 11, term: 'first', label: 'First semester', status: 'Draft',
        start_date: '2026-08-10', end_date: '2026-12-18', version: 2, school_year_id: 1, school_year_label: '2026–2027' },
      current_active: null, prerequisites: [{ key: 'valid_dates', status: 'ready', reason: '' },
        { key: 'approved_fee', status: 'unavailable', reason: 'fee_schedule_not_implemented' },
        { key: 'academic_offerings', status: 'unavailable', reason: 'curriculum_offerings_not_implemented' }],
      warnings: [], blockers: ['prerequisites_missing', 'feature_disabled'], feature_enabled: false, can_confirm: false });
    }
    return fake.handle(args);
  };
  await scene(handle, async (page) => {
    await open(page);
    await page.getByRole('button', { name: 'Review activation for First semester, S.Y. 2026–2027' }).click();
    const dialog = page.getByRole('dialog', { name: 'Activate this semester?' });
    await dialog.getByText('Feature unavailable').waitFor();
    const text = await dialog.innerText();
    for (const expected of ['Ready', 'Not available yet', 'Current Active semester: None']) assert.ok(text.includes(expected), expected);
    assert.equal(await dialog.getByRole('button', { name: 'Activate semester' }).isDisabled(), true);
    await page.keyboard.press('Escape');
    await dialog.waitFor({ state: 'hidden' });
    assert.equal(fake.state.posts.length, 0);
  }, VIEW);
});

test('date editing validates locally, saves once, and asks to confirm a cross-year overlap', async () => {
  let overlapRefused = false;
  const fake = server({ years: [year(1, 2026)], onPost: (path, body) => {
    if (path.endsWith('/dates/') && !body.acknowledge_cross_year_overlap && body.start_date === '2026-06-01' && !overlapRefused) {
      overlapRefused = true;
      return [{ error: { code: 'period_conflict', reason: 'cross_year_overlap', message: 'x' } }, 409];
    }
    return null;
  } });
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByRole('button', { name: 'Edit dates for First semester, S.Y. 2026–2027' }).click();
    await page.getByLabel('Start date').fill('2026-12-18');
    await page.getByLabel('End date').fill('2026-08-10');
    await page.getByRole('button', { name: 'Save dates' }).click();
    await page.getByText('The end date must be after the start date.').waitFor();
    assert.equal(fake.state.posts.length, 0);
    await page.getByLabel('Start date').fill('2026-06-01');
    await page.getByLabel('End date').fill('2026-12-18');
    await page.getByRole('button', { name: 'Save dates' }).click();
    const dialog = page.getByRole('dialog', { name: 'Save overlapping dates?' });
    await dialog.waitFor();
    assert.equal(await page.evaluate(() => document.activeElement?.textContent), 'Cancel');
    await dialog.getByRole('button', { name: 'Save anyway' }).click();
    await page.getByRole('status').filter({ hasText: 'First semester dates for S.Y. 2026–2027 were saved.' }).waitFor();
    assert.deepEqual(fake.state.posts.map((p) => p.body), [
      { start_date: '2026-06-01', end_date: '2026-12-18', expected_version: 1 },
      { start_date: '2026-06-01', end_date: '2026-12-18', expected_version: 1, acknowledge_cross_year_overlap: true },
    ]);
    assert.ok((await page.locator('main').innerText()).includes('Jun 1, 2026'));
  }, VIEW);
});

test('delete uses a destructive confirmation; Escape cancels and focus returns to the trigger', async () => {
  const fake = server({ years: [year(2, 2027), year(1, 2026, { can_delete: false, status: 'Active' })] });
  await scene(fake.handle, async (page) => {
    await open(page);
    assert.equal(await page.getByRole('button', { name: 'Delete S.Y. 2026–2027' }).count(), 0);
    const trigger = page.getByRole('button', { name: 'Delete S.Y. 2027–2028' });
    await trigger.click();
    const dialog = page.getByRole('dialog', { name: 'Delete this school year?' });
    await dialog.waitFor();
    assert.ok((await dialog.innerText()).includes('This action is audited.'));
    await page.keyboard.press('Escape');
    await dialog.waitFor({ state: 'hidden' });
    assert.equal(await page.evaluate(() => document.activeElement?.textContent), 'Delete S.Y. 2027–2028');
    assert.equal(fake.state.posts.length, 0);
    await trigger.click();
    await dialog.getByRole('button', { name: 'Delete school year' }).click();
    await page.getByRole('status').filter({ hasText: 'S.Y. 2027–2028 and its two Draft semesters were deleted.' }).waitFor();
    assert.deepEqual(fake.state.posts.map((p) => [p.path, p.body]), [[`${API}school-years/2/delete/`, { expected_start_year: 2027 }]]);
  }, VIEW);
});

test('permission-denied, role-context and unavailable states never show data or controls', async () => {
  const cases = [
    [{ error: { code: 'access_denied' } }, 403, 'You do not have permission to manage school years'],
    [{ error: { code: 'access_denied', reason: 'admin_context_required' } }, 403, 'Switch to your School Admin role'],
    [{ error: { code: 'academic_periods_unavailable' } }, 503, 'School years are not available right now'],
  ];
  for (const [body, status, title] of cases) {
    const fake = server({ list: () => [body, status] });
    await scene(fake.handle, async (page) => {
      await page.getByText(title).first().waitFor();
      assert.equal(await page.getByRole('button', { name: /Edit dates|Delete/ }).count(), 0);
    }, VIEW);
  }
  const hidden = server({ permissions: ['academic.catalogue.read'] });
  await scene(hidden.handle, async (page) => {
    await page.getByText('This section is unavailable').waitFor();
    assert.equal(hidden.state.lists, 0);
  }, VIEW);
});

test('responsive 360–1440px in Light, System-dark and Dark with composited AA contrast', async () => {
  const fake = server({ years: [year(1, 2026, { status: 'Between semesters', can_delete: false, semesters: [
    semester(11, 'first', { status: 'Closed', start_date: '2026-08-10', end_date: '2026-12-18', can_edit_dates: false,
      activation: { available: false, missing: ['approved_fee', 'academic_offerings'] } }),
    semester(12, 'second', { start_date: '2027-01-11' })] }), year(2, 2027)] });
  await scene(fake.handle, async (page) => {
    for (const [preference, scheme] of [['light', 'light'], ['system', 'dark'], ['dark', 'dark']]) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate((v) => localStorage.setItem('ctug-theme', v), preference);
      for (const width of [360, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await open(page);
        await page.waitForLoadState('networkidle');
        const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
        assert.ok(layout.scroll <= layout.width, `${preference} ${width}px overflow ${layout.scroll}`);
        await page.getByRole('button', { name: 'Edit dates for Second semester, S.Y. 2026–2027' }).click();
        const selector = `${DASHBOARD_TEXT}, main li span, main li p, main article p`;
        for (const { text, ratio } of await contrastReport(page, selector)) {
          assert.ok(ratio >= 4.5, `${preference} ${width}px "${text}" ${ratio.toFixed(2)}`);
        }
        await page.getByRole('button', { name: 'Cancel' }).click();
      }
    }
  }, VIEW);
});
