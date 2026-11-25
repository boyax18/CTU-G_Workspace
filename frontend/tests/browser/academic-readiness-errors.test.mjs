// Current academic period in the dashboard header and actionable semester readiness. Every API call is mocked;
// the academic switches are on for this Vite only. No real database, session or period change.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport, DASHBOARD_TEXT } from './contrastProbe.mjs';

process.env.VITE_WORKSPACE_ACADEMIC_PERIODS_ENABLED = '1';
process.env.VITE_WORKSPACE_ACADEMIC_CATALOGUE_ENABLED = '1';
process.env.VITE_WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED = '1';
process.env.VITE_WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED = '1';

const CURRENT = '/api/v1/academic/catalogue/current-period/';
const ADMIN = ['academic.periods.manage', 'academic.catalogue.read', 'finance.fee_schedule.manage', 'academic.courses.manage'];
const period = { semester_id: 11, term: 'first', label: 'First semester', school_year_id: 1, school_year_label: '2026–2027',
  start_date: '2026-08-10', end_date: '2026-12-18' };
const checks = [{ key: 'valid_dates', status: 'ready', reason: '' },
  { key: 'approved_fee', status: 'missing', reason: 'fee_awaiting_approval' },
  { key: 'academic_offerings', status: 'missing', reason: 'no_valid_offerings' }];
const semester = (id, term) => ({ semester_id: id, term, label: term === 'first' ? 'First semester' : 'Second semester', status: 'Draft',
  start_date: '2026-08-10', end_date: '2026-12-18', version: 2, can_edit_dates: true,
  activation: { available: false, missing: ['approved_fee', 'academic_offerings'], checks }, updated_at: null });
const years = { results: [{ school_year_id: 1, start_year: 2026, end_year: 2027, label: '2026–2027', status: 'Draft',
  semesters: [semester(11, 'first'), semester(12, 'second')], can_delete: true, created_at: null, updated_at: null }],
page: 1, page_size: 20, has_next: false, features: { transitions: false, corrections: false } };

function server({ permissions = ADMIN, current = () => [{ active: period }, 200] } = {}) {
  const state = { currentReads: 0, posts: 0 };
  const handle = async ({ path, request, respond }) => {
    if (path.endsWith('/session/')) return respond({ authenticated: true, account: { school_id: 'ADMIN-001', roles: ['Admin'] }, permissions });
    if (request.method() === 'POST') { state.posts += 1; return respond({ error: { code: 'not_found' } }, 404); }
    if (path === CURRENT) { state.currentReads += 1; return respond(...current()); }
    if (path === '/api/v1/academic/school-years/') return respond(years);
    return respond({ error: { code: 'not_found' } }, 404);
  };
  return { state, handle };
}

const header = (page) => page.locator('header').getByText(/Academic period:/);

test('the header shows the server-provided current period', async () => {
  const fake = server({ permissions: ['academic.catalogue.read'] });
  await scene(fake.handle, async (page) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await header(page).getByText('S.Y. 2026–2027 · First semester').waitFor();
    assert.ok(fake.state.currentReads >= 1);
    assert.equal(fake.state.posts, 0);
  }, '/dashboard');
});

test('"no active semester" only from an explicit null; a failure never claims there is none', async () => {
  const none = server({ permissions: ['academic.catalogue.read'], current: () => [{ active: null }, 200] });
  await scene(none.handle, async (page) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await header(page).getByText('no active semester').waitFor();
  }, '/dashboard');
  const failing = server({ permissions: ['academic.catalogue.read'], current: () => [{ error: { code: 'academic_catalogue_unavailable' } }, 503] });
  await scene(failing.handle, async (page) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.waitForLoadState('networkidle');
    assert.ok((await header(page).innerText()).includes('not yet configured'));
  }, '/dashboard');
  const noPermission = server({ permissions: ['academic.periods.manage'] });
  await scene(noPermission.handle, async (page) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    await page.waitForLoadState('networkidle');
    assert.ok((await header(page).innerText()).includes('not yet configured'));
    assert.equal(noPermission.state.currentReads, 0);  // never requested without the exact code
  }, '/dashboard');
});

test('readiness explains what is missing and links only to pages the session can open', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'School years', level: 2 }).waitFor();
    const list = page.getByRole('list', { name: 'Activation readiness, First semester' });
    const text = await list.innerText();
    for (const expected of ['Ready', 'Missing configuration', 'Approve the Draft semester fee.',
      'Add at least one valid subject offering for this semester.']) assert.ok(text.includes(expected), expected);
    await list.getByRole('button', { name: 'Open semester fees for First semester' }).click();
    await page.waitForURL(/view=semester-fees/);
    assert.equal(fake.state.posts, 0);
  }, '/dashboard?view=school-periods');
  const limited = server({ permissions: ['academic.periods.manage'] });
  await scene(limited.handle, async (page) => {
    await page.getByRole('heading', { name: 'School years', level: 2 }).waitFor();
    const list = page.getByRole('list', { name: 'Activation readiness, First semester' });
    assert.ok((await list.innerText()).includes('Approve the Draft semester fee.'));
    assert.equal(await list.getByRole('button').count(), 0);  // no link to pages this session cannot open
  }, '/dashboard?view=school-periods');
});

test('header and readiness keep AA contrast and fit 360–1440px in all three themes', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    for (const [preference, scheme] of [['light', 'light'], ['system', 'dark'], ['dark', 'dark']]) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate((v) => localStorage.setItem('ctug-theme', v), preference);
      for (const width of [360, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await page.goto(new URL(page.url()).origin + '/dashboard?view=school-periods');
        await page.getByRole('list', { name: 'Activation readiness, First semester' }).waitFor();
        await page.waitForLoadState('networkidle');
        await page.waitForFunction(() => document.getAnimations().length === 0);
        const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
        assert.ok(layout.scroll <= layout.width, `${preference} ${width}px overflow ${layout.scroll}`);
        for (const { text, ratio } of await contrastReport(page, `${DASHBOARD_TEXT}, main li span, main li p, main li button`)) {
          assert.ok(ratio >= 4.5, `${preference} ${width}px "${text}" ${ratio.toFixed(2)}`);
        }
      }
    }
  }, '/dashboard?view=school-periods');
});
