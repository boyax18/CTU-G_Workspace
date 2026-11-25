// WF-11.01 lifecycle UI: activation, closure, corrections and history. Every API call is mocked; the three
// academic switches are on for this Vite only. No real database, session or period change.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport, DASHBOARD_TEXT } from './contrastProbe.mjs';

process.env.VITE_WORKSPACE_ACADEMIC_PERIODS_ENABLED = '1';
process.env.VITE_WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED = '1';
process.env.VITE_WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED = '1';

const VIEW = '/dashboard?view=school-periods';
const API = '/api/v1/academic/';
const session = { authenticated: true, account: { school_id: 'ADMIN-001', roles: ['Admin'] }, permissions: ['academic.periods.manage'] };
const NOTE = 'Registrar memorandum moved the opening week.';
const semester = (id, term, overrides = {}) => ({ semester_id: id, term, label: term === 'first' ? 'First semester' : 'Second semester',
  status: 'Draft', start_date: term === 'first' ? '2026-08-10' : '2027-01-11', end_date: term === 'first' ? '2026-12-18' : '2027-05-28',
  version: 2, can_edit_dates: true, activation: { available: false, missing: [] }, updated_at: '2026-11-25T05:00:00+00:00', ...overrides });
const year = (first = {}, second = {}, status = 'Draft') => ({ school_year_id: 1, start_year: 2026, end_year: 2027, label: '2026–2027',
  status, semesters: [semester(11, 'first', first), semester(12, 'second', second)], can_delete: status === 'Draft',
  created_at: '2026-11-25T05:00:00+00:00', updated_at: '2026-11-25T05:00:00+00:00' });
const ref = (s) => ({ semester_id: s.semester_id, term: s.term, label: s.label, status: s.status, start_date: s.start_date,
  end_date: s.end_date, version: s.version, school_year_id: 1, school_year_label: '2026–2027' });
const unavailable = (keys) => keys.map((key) => ({ key, status: 'unavailable', count: null, reason: 'module_not_implemented' }));
const OBLIGATIONS = ['outstanding_clearance_signatures', 'unpaid_fee_obligations', 'incomplete_onboarding'];
const IMPACTS = ['student_participation', 'fee_obligations', 'clearance_records'];

/** A small in-memory Django stand-in that applies confirmed transitions. */
function server({ prerequisitesReady = true, impactEvaluated = false } = {}) {
  const state = { year: year(), posts: [], history: [] };
  const find = (id) => state.year.semesters.find((s) => s.semester_id === id);
  const handle = async ({ path, request, respond }) => {
    if (path.endsWith('/session/')) return respond(session);
    if (path === `${API}school-years/` && request.method() === 'GET') {
      return respond({ results: [state.year], page: 1, page_size: 20, has_next: false, features: { transitions: true, corrections: true } });
    }
    if (path === `${API}school-years/1/history/`) {
      return respond({ results: state.history, page: 1, page_size: 20, has_next: false });
    }
    const match = path.match(/semesters\/(\d+)\/(activation|closure|archive|corrections)\/$/);
    if (!match) return respond({ error: { code: 'not_found' } }, 404);
    const target = find(Number(match[1]));
    const action = match[2];
    if (request.method() === 'GET') {
      if (action === 'activation') {
        const ready = prerequisitesReady ? 'ready' : 'unavailable';
        return respond({ semester: ref(target), current_active: null, warnings: ['outside_semester_dates'],
          prerequisites: [{ key: 'valid_dates', status: 'ready', reason: '' }, { key: 'approved_fee', status: ready, reason: '' },
            { key: 'academic_offerings', status: ready, reason: '' }],
          blockers: prerequisitesReady ? [] : ['prerequisites_missing'], feature_enabled: true, can_confirm: prerequisitesReady });
      }
      if (action === 'corrections') {
        const impact = impactEvaluated ? IMPACTS.map((key) => ({ key, status: 'evaluated', count: 0, reason: '' })) : unavailable(IMPACTS);
        return respond({ semester: ref(target), kind: target.status === 'Active' ? 'active_edit' : 'historical_correction', impact,
          affected: [], reason_codes: ['calendar_change', 'data_entry_correction', 'institutional_directive'],
          blockers: impactEvaluated ? [] : ['impact_unavailable'], feature_enabled: true, can_confirm: impactEvaluated });
      }
      return respond({ semester: ref(target), obligations: unavailable(OBLIGATIONS),
        warnings: OBLIGATIONS.map((k) => `${k}_unavailable`), blockers: [], feature_enabled: true, can_confirm: true });
    }
    const body = request.postDataJSON();
    state.posts.push({ path, body, csrf: request.headers()['x-csrftoken'] });
    if (action === 'corrections') {
      Object.assign(target, { start_date: body.start_date, end_date: body.end_date, version: target.version + 1 });
      state.history.unshift({ event: 'academic.semester.active_edit', description: 'Active semester edited',
        occurred_at: '2026-11-25T06:00:00+00:00', actor: 'You', semester: target.term,
        changes: { start_date: { before: '2026-08-10', after: body.start_date } }, reason: body.reason_code, note: body.reason_note });
      return respond(state.year);
    }
    const next = { activation: 'Active', closure: 'Closed', archive: 'Archived' }[action];
    Object.assign(target, { status: next, version: target.version + 1, can_edit_dates: false });
    state.year.status = next === 'Active' ? 'Active' : 'Between semesters';
    state.year.can_delete = false;
    return respond(ref(target));
  };
  return { state, handle };
}

const open = async (page) => {
  await page.goto(new URL(page.url()).origin + VIEW);
  await page.getByRole('heading', { name: 'School years', level: 2 }).waitFor();
};

test('activation requires reviewing warnings, then sends one confirmation with what was reviewed', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByRole('button', { name: 'Review activation for First semester, S.Y. 2026–2027' }).click();
    const dialog = page.getByRole('dialog', { name: 'Activate this semester?' });
    await dialog.getByText('Review before confirming').waitFor();
    const confirm = dialog.getByRole('button', { name: 'Activate semester' });
    assert.equal(await confirm.isDisabled(), true);  // warnings not yet reviewed
    await dialog.getByLabel('I reviewed these warnings').check();
    await confirm.click();
    await page.getByRole('status').filter({ hasText: 'First semester, S.Y. 2026–2027, was activated.' }).waitFor();
    assert.deepEqual(fake.state.posts.map((p) => [p.path, p.body]), [[`${API}semesters/11/activation/`,
      { confirmed: true, expected_version: 2, acknowledged_warnings: ['outside_semester_dates'], expected_active_semester_id: null }]]);
    assert.ok(fake.state.posts[0].csrf);
    await page.getByRole('button', { name: 'Review closure for First semester, S.Y. 2026–2027' }).waitFor();
  }, VIEW);
});

test('missing prerequisites keep activation disabled and nothing is sent', async () => {
  const fake = server({ prerequisitesReady: false });
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByRole('button', { name: 'Review activation for First semester, S.Y. 2026–2027' }).click();
    const dialog = page.getByRole('dialog', { name: 'Activate this semester?' });
    await dialog.getByText('This action is not possible until every requirement above is ready.').waitFor();
    assert.equal(await dialog.getByRole('button', { name: 'Activate semester' }).isDisabled(), true);
    assert.ok((await dialog.innerText()).includes('Not available yet'));
    assert.equal(fake.state.posts.length, 0);
  }, VIEW);
});

test('closure shows unavailable obligations as unknown, never zero, and confirms explicitly', async () => {
  const fake = server();
  fake.state.year = year({ status: 'Active', can_edit_dates: false, version: 3 }, {}, 'Active');
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByRole('button', { name: 'Review closure for First semester, S.Y. 2026–2027' }).click();
    const dialog = page.getByRole('dialog', { name: 'Close this semester?' });
    await dialog.getByRole('list', { name: 'Outstanding obligations' }).waitFor();
    const list = await dialog.getByRole('list', { name: 'Outstanding obligations' }).innerText();
    assert.equal((list.match(/Cannot be checked yet/g) ?? []).length, 3);
    assert.ok(!/\b0\b|None/.test(list), list);
    assert.ok((await dialog.innerText()).includes('Nobody is marked cleared and no payment is settled.'));
    await dialog.getByLabel('I reviewed these warnings').check();
    await dialog.getByRole('button', { name: 'Close semester' }).click();
    await page.getByRole('status').filter({ hasText: 'was closed.' }).waitFor();
    assert.deepEqual(fake.state.posts[0].body.acknowledged_warnings, OBLIGATIONS.map((k) => `${k}_unavailable`));
  }, VIEW);
});

test('active edit is refused while impact is unavailable, and saves with a reason when it can be evaluated', async () => {
  const blocked = server();
  blocked.state.year = year({ status: 'Active', can_edit_dates: false, version: 3 }, {}, 'Active');
  await scene(blocked.handle, async (page) => {
    await open(page);
    await page.getByRole('button', { name: 'Edit active semester for First semester, S.Y. 2026–2027' }).click();
    const dialog = page.getByRole('dialog', { name: 'Edit active semester dates?' });
    await dialog.getByText('Saving is not possible while the impact cannot be checked.').waitFor();
    assert.equal(await dialog.getByRole('button', { name: 'Save change' }).isDisabled(), true);
    assert.equal(blocked.state.posts.length, 0);
  }, VIEW);
  const fake = server({ impactEvaluated: true });
  fake.state.year = year({ status: 'Active', can_edit_dates: false, version: 3 }, {}, 'Active');
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByRole('button', { name: 'Edit active semester for First semester, S.Y. 2026–2027' }).click();
    const dialog = page.getByRole('dialog', { name: 'Edit active semester dates?' });
    await dialog.getByRole('list', { name: 'Impact on existing records' }).waitFor();
    await dialog.getByLabel('Start date').fill('2026-08-17');
    await dialog.getByRole('button', { name: 'Save change' }).click();
    await dialog.getByText('Choose the reason for this change.').waitFor();
    assert.equal(fake.state.posts.length, 0);
    await dialog.getByLabel('Reason').selectOption('calendar_change');
    await dialog.getByLabel('Explanation').fill('short');
    await dialog.getByRole('button', { name: 'Save change' }).click();
    await dialog.getByText('Explain the change in 10 to 500 characters.').waitFor();
    await dialog.getByLabel('Explanation').fill(NOTE);
    await dialog.getByRole('button', { name: 'Save change' }).click();
    await page.getByRole('status').filter({ hasText: 'the dates were updated.' }).waitFor();
    assert.deepEqual(fake.state.posts.map((p) => p.body), [{ start_date: '2026-08-17', end_date: '2026-12-18', expected_version: 3,
      reason_code: 'calendar_change', reason_note: NOTE }]);
    await page.getByRole('button', { name: 'View history of S.Y. 2026–2027' }).click();
    const history = page.getByRole('region', { name: 'History of S.Y. 2026–2027' });
    await history.getByText('Active semester edited').waitFor();
    const text = await history.innerText();
    for (const expected of ['Reason: Campus calendar change', NOTE, 'Aug 10, 2026 → Aug 17, 2026', 'You']) assert.ok(text.includes(expected), expected);
    assert.ok(!text.includes('ADMIN-001'));
  }, VIEW);
});

test('lifecycle dialogs keep AA contrast and fit 360–1440px in all three themes', async () => {
  const fake = server();
  fake.state.year = year({ status: 'Active', can_edit_dates: false, version: 3 }, {}, 'Active');
  await scene(fake.handle, async (page) => {
    for (const [preference, scheme] of [['light', 'light'], ['system', 'dark'], ['dark', 'dark']]) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate((v) => localStorage.setItem('ctug-theme', v), preference);
      for (const width of [360, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await open(page);
        for (const [button, name] of [['Review closure', 'Close this semester?'], ['Edit active semester', 'Edit active semester dates?']]) {
          await page.getByRole('button', { name: `${button} for First semester, S.Y. 2026–2027` }).click();
          const dialog = page.getByRole('dialog', { name });
          await dialog.getByRole('list').first().waitFor();
          const box = await dialog.boundingBox();
          assert.ok(box && box.x >= 0 && box.x + box.width <= width, `${preference} ${width}px ${name}`);
          for (const { text, ratio } of await contrastReport(page, `${DASHBOARD_TEXT}, dialog h3, dialog p, dialog li span, dialog label, dialog button`)) {
            assert.ok(ratio >= 4.5, `${preference} ${width}px ${name} "${text}" ${ratio.toFixed(2)}`);
          }
          await page.keyboard.press('Escape');
          await dialog.waitFor({ state: 'hidden' });
        }
      }
    }
  }, VIEW);
});
