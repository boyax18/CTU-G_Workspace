// Academic settings (courses, subjects, sections, curricula, offerings, instructors). Every API call is mocked;
// the configuration switches are on for this Vite only. No real database, session or record change.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport, DASHBOARD_TEXT } from './contrastProbe.mjs';

process.env.VITE_WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED = '1';
process.env.VITE_WORKSPACE_ACADEMIC_CURRICULUM_WRITES_ENABLED = '1';
process.env.VITE_WORKSPACE_ACADEMIC_OFFERING_WRITES_ENABLED = '1';
process.env.VITE_WORKSPACE_ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED = '1';

const VIEW = '/dashboard?view=academic-references';
const API = '/api/v1/academic/config/';
const ALL = ['academic.courses.manage', 'clearance.subjects.manage', 'academic.sections.manage', 'academic.periods.manage',
  'clearance.teaching_assignments.manage'];
const page = (results) => ({ results, page: 1, page_size: 50, has_next: false });
const course = (id, code, overrides = {}) => ({ course_id: id, code, name: `${code} program`, status: 'Active', version: 1, in_use: false,
  references: { curricula: 0, sections: 0, offerings: 0 }, created_at: null, updated_at: null, ...overrides });
const subject = (id, code) => ({ subject_id: id, code, title: `${code} title`, classification: null, lecture_units: '3.0', lab_units: null,
  status: 'Active', version: 1, in_use: false, references: { curriculum_entries: 0, offerings: 0 } });
const section = { section_id: 4, course: { course_id: 1, code: 'BSIT' }, year_level: 1, name: '1-A', status: 'Active', version: 1,
  in_use: false, references: { offerings: 0 } };
const semester = { semester_id: 9, term: 'first', label: 'First semester', status: 'Draft', school_year_id: 2, school_year_label: '2026–2027' };
const curriculum = (overrides = {}) => ({ curriculum_id: 7, course: { course_id: 1, code: 'BSIT', name: 'BSIT program' }, label: '2024',
  effective_start_year: 2024, status: 'Draft', version: 2, entry_count: 1, offering_count: 0, can_edit: true,
  entries: [{ curriculum_subject_id: 70, year_level: 1, term: 'first', subject: { ...subject(5, 'IT 101'), status: 'Active' } }], ...overrides });
const offering = (assignment = null) => ({ offering_id: 11, semester, section: { section_id: 4, name: '1-A', year_level: 1, course_code: 'BSIT' },
  subject: { subject_id: 5, code: 'IT 101', title: 'IT 101 title' }, curriculum: { curriculum_id: 7, label: '2024' }, assignment,
  ready_for_confirmation: Boolean(assignment?.eligible), can_remove: !assignment, created_at: null });
const instructor = { account_id: 31, ctug_id: '7261001', full_name: 'Maria Santos' };

function server({ permissions = ALL, features = { curriculum_writes: true, offering_writes: true, teaching_assignments: true } } = {}) {
  const state = { courses: [course(1, 'BSIT')], posts: [], offerings: [], curriculum: curriculum() };
  const handle = async ({ path, request, respond }) => {
    if (path.endsWith('/session/')) return respond({ authenticated: true, account: { school_id: 'ADMIN-001', roles: ['Admin'] }, permissions });
    if (request.method() === 'POST') {
      const body = request.postDataJSON();
      state.posts.push({ path, body, csrf: request.headers()['x-csrftoken'] });
      if (path === `${API}courses/`) {
        if (body.code.toUpperCase() === 'BSIT') return respond({ error: { code: 'configuration_conflict', reason: 'code_exists', message: 'x' } }, 409);
        const created = course(state.courses.length + 1, body.code.toUpperCase());
        state.courses.push(created);
        return respond(created, 201);
      }
      const status = path.match(/courses\/(\d+)\/status\/$/);
      if (status) {
        const target = state.courses.find((c) => c.course_id === Number(status[1]));
        Object.assign(target, { status: body.status, version: target.version + 1 });
        return respond(target);
      }
      if (path === `${API}curricula/7/publish/`) {
        state.curriculum = curriculum({ status: 'Published', can_edit: false, version: 3 });
        return respond(state.curriculum);
      }
      if (path === `${API}offerings/`) { state.offerings = [offering()]; return respond(state.offerings[0], 201); }
      if (path === `${API}offerings/11/instructor/`) {
        state.offerings = [offering({ assignment_id: 50, status: 'Active', instructor, eligible: true, assigned_at: null, ended_at: null, end_reason: null })];
        return respond(state.offerings[0]);
      }
      return respond({ error: { code: 'not_found' } }, 404);
    }
    const url = new URL(request.url());
    if (path === `${API}courses/`) return respond(page(url.searchParams.get('status') ? state.courses.filter((c) => c.status === 'Active') : state.courses));
    if (path === `${API}subjects/`) return respond(page([subject(5, 'IT 101')]));
    if (path === `${API}sections/`) return respond(page([section]));
    if (path === `${API}curricula/`) return respond({ ...page([state.curriculum]), features });
    if (path === `${API}curricula/7/`) return respond({ ...state.curriculum, features });
    if (path === `${API}semesters/`) return respond({ results: [semester], features });
    if (path === `${API}offerings/`) return respond({ semester, results: state.offerings, valid_offering_count: state.offerings.length,
      page: 1, page_size: 50, has_next: false, features });
    if (path === `${API}offerings/candidates/`) return respond({ semester, section_id: 4, results: state.offerings.length ? [] : [
      { curriculum_subject_id: 70, curriculum: { curriculum_id: 7, label: '2024' }, subject: { subject_id: 5, code: 'IT 101', title: 'IT 101 title' } }] });
    if (path === `${API}instructors/`) return respond({ results: [instructor] });
    if (path === `${API}offerings/11/instructor/history/`) return respond({ offering_id: 11, results: [] });
    return respond({ error: { code: 'not_found' } }, 404);
  };
  return { state, handle };
}

const open = async (page) => {
  await page.goto(new URL(page.url()).origin + VIEW);
  await page.getByRole('tablist', { name: 'Academic settings' }).waitFor();
};

test('tabs follow exact permission codes only', async () => {
  const fake = server({ permissions: ['clearance.subjects.manage'] });
  await scene(fake.handle, async (page) => {
    await open(page);
    const tabs = await page.getByRole('tab').allInnerTexts();
    assert.deepEqual(tabs, ['Subjects']);
    await page.getByRole('list', { name: 'Subjects' }).waitFor();
  }, VIEW);
  const none = server({ permissions: ['academic.catalogue.read', 'academic.advisers.manage'] });
  await scene(none.handle, async (page) => {
    await page.getByText('This section is unavailable').waitFor();
  }, VIEW);
});

test('courses: create, fixed conflict copy, and an audited destructive retire confirmation', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByRole('list', { name: 'Courses' }).waitFor();
    await page.getByLabel('Course code').fill('bsit');
    await page.getByLabel('Course name').fill('Duplicate');
    await page.getByRole('button', { name: 'Add course' }).click();
    await page.getByRole('alert').filter({ hasText: 'This code is already used.' }).waitFor();
    await page.getByLabel('Course code').fill('bsed');
    await page.getByLabel('Course name').fill('Education');
    await page.getByRole('button', { name: 'Add course' }).click();
    await page.getByRole('status').filter({ hasText: 'BSED was added. This change is audited.' }).waitFor();
    await page.getByRole('button', { name: 'Retire BSIT' }).click();
    const dialog = page.getByRole('dialog', { name: 'Retire: BSIT?' });
    await dialog.waitFor();
    assert.ok((await dialog.innerText()).includes('can never be used again'));
    assert.equal(await page.evaluate(() => document.activeElement?.textContent), 'Cancel');
    await page.keyboard.press('Escape');
    await dialog.waitFor({ state: 'hidden' });
    await page.getByRole('button', { name: 'Retire BSIT' }).click();
    await dialog.getByRole('button', { name: 'Retire' }).click();
    await page.getByRole('status').filter({ hasText: 'BSIT is now retired.' }).waitFor();
    assert.deepEqual(fake.state.posts.map((p) => [p.path, p.body]), [
      [`${API}courses/`, { code: 'bsit', name: 'Duplicate' }], [`${API}courses/`, { code: 'bsed', name: 'Education' }],
      [`${API}courses/1/status/`, { status: 'Retired', expected_version: 1 }]]);
    assert.ok(fake.state.posts.every((p) => p.csrf));
  }, VIEW);
});

test('curricula are read-only when the server has not enabled curriculum writes', async () => {
  const fake = server({ features: { curriculum_writes: false, offering_writes: false, teaching_assignments: false } });
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByRole('tab', { name: 'Curriculum versions' }).click();
    await page.getByText('Curriculum changes are not enabled.').waitFor();
    await page.getByRole('button', { name: 'Open BSIT 2024' }).click();
    await page.getByRole('list', { name: 'Year 1 · First semester' }).waitFor();
    for (const name of [/^Publish$/, /^Delete draft$/, /^Remove IT 101$/]) {
      assert.equal(await page.getByRole('button', { name }).count(), 0);
    }
    assert.equal(await page.getByRole('button', { name: 'Create draft' }).count(), 0);
    assert.equal(fake.state.posts.length, 0);
  }, VIEW);
});

test('curricula: publish is an explicit confirmation and the version becomes read-only', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByRole('tab', { name: 'Curriculum versions' }).click();
    await page.getByRole('button', { name: 'Open BSIT 2024' }).click();
    await page.getByRole('button', { name: 'Publish', exact: true }).click();
    const dialog = page.getByRole('dialog', { name: 'Publish this curriculum?' });
    assert.ok((await dialog.innerText()).includes('Existing student records are not changed.'));
    await dialog.getByRole('button', { name: 'Publish curriculum' }).click();
    await page.getByText('Published versions are read-only history.').waitFor();
    assert.deepEqual(fake.state.posts.map((p) => [p.path, p.body]), [[`${API}curricula/7/publish/`, { expected_version: 2, confirmed: true }]]);
  }, VIEW);
});

test('offerings: add from the published plan, assign an eligible instructor, and show readiness', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByRole('tab', { name: 'Offerings & instructors' }).click();
    await page.getByText('No offerings for this semester yet.').waitFor();
    assert.ok((await page.locator('main').innerText()).includes('Activation also requires an approved semester fee'));
    const form = page.getByRole('form', { name: 'Add an offering' });
    await form.getByLabel('Section').selectOption('4');
    await form.getByLabel('Curriculum subject').selectOption('70');
    await form.getByRole('button', { name: 'Add offering' }).click();
    await page.getByRole('status').filter({ hasText: 'IT 101 is now offered to BSIT 1-A.' }).waitFor();
    assert.ok((await page.getByRole('list', { name: 'Offerings' }).innerText()).includes('Students cannot confirm this subject'));
    await page.getByRole('button', { name: 'Assign instructor for IT 101 1-A' }).click();
    const dialog = page.getByRole('dialog', { name: 'Assign an instructor?' });
    await dialog.getByLabel('Maria Santos (CTU-G ID 7261001)').check();
    await dialog.getByRole('button', { name: 'Assign instructor' }).click();
    await page.getByRole('status').filter({ hasText: 'the instructor assignment was saved' }).waitFor();
    assert.ok((await page.getByRole('list', { name: 'Offerings' }).innerText()).includes('Ready for student subject confirmation'));
    assert.deepEqual(fake.state.posts.map((p) => [p.path, p.body]), [
      [`${API}offerings/`, { semester_id: 9, section_id: 4, curriculum_subject_id: 70 }],
      [`${API}offerings/11/instructor/`, { instructor_account_id: 31, expected_assignment_id: null }]]);
  }, VIEW);
});

test('Academic settings keep AA contrast and fit 360–1440px in all three themes', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    for (const [preference, scheme] of [['light', 'light'], ['system', 'dark'], ['dark', 'dark']]) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate((v) => localStorage.setItem('ctug-theme', v), preference);
      for (const width of [360, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await open(page);
        for (const tab of ['Courses', 'Curriculum versions', 'Offerings & instructors']) {
          await page.getByRole('tab', { name: tab }).click();
          await page.waitForLoadState('networkidle');
          // Let the tabs' 150ms colour transitions finish: measure the settled state, not a mid-fade frame.
          await page.waitForFunction(() => document.getAnimations().length === 0);
          const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
          assert.ok(layout.scroll <= layout.width, `${preference} ${width}px ${tab} overflow ${layout.scroll}`);
          for (const { text, ratio } of await contrastReport(page, `${DASHBOARD_TEXT}, main li span, main li p, main [role="tab"]`)) {
            assert.ok(ratio >= 4.5, `${preference} ${width}px ${tab} "${text}" ${ratio.toFixed(2)}`);
          }
        }
      }
    }
  }, VIEW);
});
