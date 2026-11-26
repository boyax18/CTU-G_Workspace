// Student Semester Onboarding and School Admin verification UI. Every API call is mocked; the onboarding
// switches are on for this Vite only. No real database, session, clearance, fee or student record changes.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport, DASHBOARD_TEXT } from './contrastProbe.mjs';

process.env.VITE_WORKSPACE_STUDENT_ONBOARDING_ENABLED = '1';
process.env.VITE_WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED = '1';
process.env.VITE_WORKSPACE_ENROLLMENT_VERIFICATION_ENABLED = '1';
process.env.VITE_WORKSPACE_HISTORICAL_PARTICIPATION_CORRECTION_ENABLED = '1';
process.env.VITE_WORKSPACE_ACADEMIC_CONFIGURATION_ENABLED = '1';

const ON = '/api/v1/academic/onboarding/';
const VER = '/api/v1/academic/verification/';
const semester = { semester_id: 9, label: 'First Semester', status: 'Active', school_year_label: '2026–2027',
  start_date: '2026-08-10', end_date: '2026-12-18' };
const previous = { semester_id: 8, label: 'Second Semester', status: 'Closed', school_year_label: '2025–2026' };
const course = { course_id: 1, code: 'BSIT', name: 'Bachelor of Science in Information Technology' };
const option = (id, code, title, instructor = 'Ana Cruz') => ({ offering_id: id, subject: { subject_id: id + 100, code, title,
  lecture_units: '3.0', lab_units: null }, section: { section_id: 2, name: '1-A', year_level: 1, course_code: 'BSIT' }, instructor,
  instructor_assigned: instructor !== null, ready_for_confirmation: instructor !== null });
const OPTIONS = [option(5, 'IT 101', 'Introduction to Computing'), option(6, 'MATH 101', 'Mathematics in the Modern World')];
const pending = (n) => ({ kind: 'subject_instructor', status: 'Pending', subject: { subject_id: n, code: `S${n}`, title: `Subject ${n}` }, signatory: 'Ana Cruz' });
const clearance = { clearance_id: 3, status: 'Uncleared', pending_count: 4, requirements: [pending(1), pending(2),
  { kind: 'treasurer_fee', status: 'Pending', subject: null, signatory: null }, { kind: 'school_admin_final', status: 'Pending', subject: null, signatory: null }] };
const STUDENT = ['academic.profile.self.read', 'clearance.requests.self.submit'];

function studentServer({ verified = false, state = 'onboarding', previousClearance = null, completed = false } = {}) {
  const s = { draft: null, completed, pending: false, posts: [] };
  const draftPayload = () => {
    const d = s.draft;
    if (!d) return { status: null, student_type: null, course: null, year_level: null, subjects: [], subjects_confirmed: false,
      course_confirmed: false, version: null, next_step: 1 };
    const next = !d.subjects_confirmed ? 2 : !d.course_confirmed ? 3 : 4;
    return { status: s.pending ? 'PendingVerification' : 'Draft', student_type: d.type, course: d.course ? course : null,
      year_level: d.year ?? null, subjects: d.subjects, subjects_confirmed: d.subjects_confirmed, course_confirmed: d.course_confirmed,
      version: d.version, next_step: next };
  };
  const result = () => ({ participation_id: 1, source: 'onboarding', student_type: 'Regular', course, year_level: 1,
    subjects: OPTIONS.map((o) => ({ subject_id: o.subject.subject_id, code: o.subject.code, title: o.subject.title, section: '1-A',
      instructor: 'Ana Cruz' })), clearance, fee: { obligation_id: 1, amount: '1500.00', currency: 'PHP', status: 'Unpaid' } });
  const status = () => {
    if (s.completed) return { state: 'completed', semester, dashboard_unlocked: true, result: result(), student: { ctug_id: 'STU-0001', full_name: 'Juan Dela Cruz' },
      features: { finalization_enabled: true } };
    const body = { semester, dashboard_unlocked: false, student: { ctug_id: 'STU-0001', full_name: 'Juan Dela Cruz' },
      features: { finalization_enabled: true }, correction_instructions: 'If a subject is missing or incorrect, visit the School Admin office in person.',
      eligibility: { status: state === 'onboarding' ? 'eligible' : state, basis: '', previous_semester: previous, missing_gaps:
        state === 'gap_verification_required' ? [previous] : [], older_uncleared: [] } };
    if (state !== 'onboarding') return { ...body, state, previous_clearance: previousClearance };
    return { ...body, state: s.pending ? 'pending_verification' : 'onboarding', onboarding: draftPayload(), prefill: null, verified_record_available: verified };
  };
  const handle = async ({ path, request, respond }) => {
    if (path.endsWith('/session/')) return respond({ authenticated: true, account: { school_id: 'STU-0001', roles: ['Student'] }, permissions: STUDENT });
    if (request.method() === 'POST') {
      const body = request.postDataJSON();
      s.posts.push({ path, body, csrf: request.headers()['x-csrftoken'] });
      if (path === `${ON}type/`) { s.draft = { type: body.student_type, subjects: [], subjects_confirmed: false, course_confirmed: false, version: 1 }; return respond(status()); }
      if (path === `${ON}subjects/`) {
        Object.assign(s.draft, { subjects: OPTIONS.filter((o) => body.offering_ids.includes(o.offering_id)), subjects_confirmed: true,
          course: true, year: body.year_level, version: s.draft.version + 1 });
        return respond(status());
      }
      if (path === `${ON}course/`) { Object.assign(s.draft, { course_confirmed: true, version: s.draft.version + 1 }); return respond(status()); }
      if (path === `${ON}finalize/`) {
        if (verified) { s.completed = true; return respond({ ...status(), outcome: 'completed' }); }
        s.pending = true; return respond({ ...status(), outcome: 'pending_verification' });
      }
    }
    if (path === `${ON}status/`) return respond(status());
    if (path === `${ON}context/`) return respond({ semester, courses: [{ ...course, year_levels: [1], sections: [{ section_id: 2, name: '1-A', year_level: 1 }] }] });
    if (path === `${ON}subject-options/`) return respond({ semester, student_type: 'Regular', options: OPTIONS, complete: true, correction_instructions: 'x' });
    if (path === `${ON}review/`) {
      return respond({ state: 'review', semester, student: { ctug_id: 'STU-0001', full_name: 'Juan Dela Cruz' }, onboarding: draftPayload(),
        fee: { revision_id: 7, amount: '1500.00', currency: 'PHP' }, fee_status: 'ready', verification: verified ? 'verified' : 'not_recorded',
        mismatched: [], eligibility: {}, blockers: [], can_confirm: true, correction_instructions: 'x' });
    }
    if (path === `${ON}my-semester/`) {
      s.mySemesterReads = (s.mySemesterReads ?? 0) + 1;
      if (!s.completed) return respond({ error: { code: 'onboarding_required', message: 'x', state: 'onboarding' } }, 409);
      return respond({ semester, student: { ctug_id: 'STU-0001', full_name: null }, result: result() });
    }
    if (path === `${ON}my-history/`) return respond({ results: s.completed ? [{ semester, source: 'onboarding', year_level: 1, course_code: 'BSIT', clearance, fee: { obligation_id: 1, amount: '1500.00', currency: 'PHP', status: 'Unpaid' } }] : [] });
    return respond({ error: { code: 'not_found' } }, 404);
  };
  return { s, handle };
}

async function walkSteps(page) {
  await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor();
  await page.getByRole('button', { name: 'Save and continue' }).click();
  await page.getByText('Choose Regular or Irregular.', { exact: true }).waitFor();
  await page.getByRole('radio', { name: /^Regular/ }).check();
  await page.getByRole('button', { name: 'Save and continue' }).click();
  await page.getByRole('heading', { name: 'Step 2: Subject confirmation' }).waitFor();
  await page.getByLabel('Course *', { exact: true }).selectOption('1');
  await page.getByLabel('Year level *', { exact: true }).selectOption('1');
  await page.getByLabel('Section *', { exact: true }).selectOption('2');
  await page.getByText('MATH 101 · Mathematics in the Modern World').waitFor();
  await page.getByRole('button', { name: 'Confirm subjects' }).click();
  await page.getByText('Confirm that this is your subject list.').waitFor();
  await page.getByLabel('I confirm this is my subject list for this semester *').check();
  await page.getByRole('button', { name: 'Confirm subjects' }).click();
  await page.getByRole('heading', { name: 'Step 3: Course and year level' }).waitFor();
  await page.getByRole('button', { name: 'Confirm course and year level' }).click();
  await page.getByRole('heading', { name: 'Step 4: Final review' }).waitFor();
  await page.getByText('₱1,500.00', { exact: true }).waitFor();
  const confirm = page.getByRole('button', { name: 'Confirm onboarding' });
  assert.equal(await confirm.isDisabled(), true);
  await page.getByLabel('I confirm these details are correct').check();
  await confirm.click();
}

test('the dashboard home routes to onboarding and the four steps end in Pending Verification', async () => {
  const fake = studentServer();
  await scene(fake.handle, async (page) => {
    // WF11-D17: a Student-only session is routed to onboarding automatically (no notice to click).
    await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor();
    assert.equal(new URL(page.url()).search, '?view=semester-onboarding');
    await page.locator('main dd').filter({ hasText: 'STU-0001' }).waitFor();
    assert.ok((await page.locator('main').innerText()).includes('2026–2027'));
    await walkSteps(page);
    await page.getByText(/Pending verification: no verified CTU enrollment record/).waitFor();
    assert.deepEqual(fake.s.posts.map((p) => p.path.replace(ON, '')), ['type/', 'subjects/', 'course/', 'finalize/']);
    assert.deepEqual(fake.s.posts[1].body, { course_id: 1, year_level: 1, offering_ids: [5, 6], expected_version: 1 });
    assert.deepEqual(fake.s.posts[3].body, { expected_version: 3, expected_fee_revision_id: 7, confirmed: true });
    for (const post of fake.s.posts) {
      assert.ok(post.csrf);
      assert.ok(!('student_account_id' in post.body) && !('amount' in post.body), JSON.stringify(post.body)); // own record; fee from the server
    }
  }, '/dashboard');
});

test('with a verified record the confirmation completes and unlocks my semester', async () => {
  const fake = studentServer({ verified: true });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Student Semester Onboarding' }).waitFor();
    await walkSteps(page);
    // Completion opens the normal dashboard, then My semester is available from the navigation.
    await page.getByRole('status').filter({ hasText: 'Your semester onboarding is complete.' }).waitFor();
    assert.equal(new URL(page.url()).search, '');
    await page.getByRole('link', { name: 'My semester' }).first().click();
    await page.getByRole('table', { name: 'Confirmed subjects' }).waitFor();
    const text = await page.locator('main').innerText();
    for (const expected of ['SSG Treasurer · organizational fee', 'School Admin · final approval', '4 requirements still pending.', 'Unpaid']) {
      assert.ok(text.includes(expected), expected);
    }
  }, '/dashboard?view=semester-onboarding');
});

test('a direct My semester URL is routed to onboarding before its data is requested', async () => {
  const fake = studentServer();
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor();
    assert.equal(new URL(page.url()).search, '?view=semester-onboarding');
    await page.getByText('No semester participation is recorded yet.').waitFor(); // own history stays available
    assert.equal(fake.s.mySemesterReads ?? 0, 0);
  }, '/dashboard?view=my-subjects');
});

test('Clearance Required and verification states show the requirement and no onboarding steps', async () => {
  const fake = studentServer({ state: 'clearance_required', previousClearance: { semester: previous, clearance, fee: { obligation_id: 2, amount: '1400.00', currency: 'PHP', status: 'Unpaid' } } });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Clearance required', exact: true }).waitFor();
    const text = await page.locator('main').innerText();
    assert.ok(text.includes('4 requirements still pending.') && text.includes('₱1,400.00'), text);
    assert.equal(await page.getByRole('heading', { name: /^Step / }).count(), 0);
  }, '/dashboard?view=semester-onboarding');
  const gap = studentServer({ state: 'gap_verification_required' });
  await scene(gap.handle, async (page) => {
    await page.getByRole('heading', { name: 'Official verification needed' }).waitFor();
    assert.ok((await page.locator('main').innerText()).includes('Second Semester, S.Y. 2025–2026'));
    assert.equal(gap.s.posts.length, 0);
  }, '/dashboard?view=semester-onboarding');
});

test('a School Admin records an in-person verification with validated, minimized input', async () => {
  const posts = [];
  const row = { semester, evidence: null, gap: null, participation: null, clearance_status: null, fee: null, onboarding_status: 'PendingVerification' };
  const handle = async ({ path, request, respond }) => {
    if (path.endsWith('/session/')) return respond({ authenticated: true, account: { school_id: 'ADMIN-001', roles: ['Admin'] },
      permissions: ['academic.enrollment_verifications.record', 'academic.courses.manage', 'clearance.subjects.manage'] });
    if (request.method() === 'POST') {
      posts.push({ path, body: request.postDataJSON(), csrf: request.headers()['x-csrftoken'] });
      return respond({ evidence_id: 4, semester_id: 9, source_type: 'in_person', entry_classification: 'continuing', course: { course_id: 1, code: 'BSIT' },
        year_level: 1, status: 'Verified', version: 1, subjects: [{ subject_id: 105, code: 'IT 101', title: 'Intro' }], verified_by: 'A School Admin' });
    }
    if (path === `${VER}students/`) return respond({ results: [{ account_id: 31, ctug_id: 'STU-0001', full_name: 'Juan Dela Cruz' }] });
    if (path === `${VER}students/31/`) return respond({ student: { account_id: 31, ctug_id: 'STU-0001', full_name: 'Juan Dela Cruz' }, periods: [row] });
    if (path.endsWith('/config/courses/')) return respond({ results: [{ ...course, status: 'Active', version: 1, in_use: true,
      references: { curricula: 1, sections: 1, offerings: 1 } }], page: 1, has_next: false });
    if (path.endsWith('/config/subjects/')) return respond({ results: [{ subject_id: 105, code: 'IT 101', title: 'Introduction to Computing',
      classification: null, lecture_units: '3.0', lab_units: null, status: 'Active', version: 1, in_use: true,
      references: { curriculum_entries: 1, offerings: 1 } }], page: 1, has_next: false });
    return respond({ error: { code: 'not_found' } }, 404);
  };
  await scene(handle, async (page) => {
    await page.getByRole('button', { name: 'Search students' }).click();
    await page.getByRole('button', { name: 'Open records' }).click();
    await page.getByRole('button', { name: 'Record verification' }).click();
    const dialog = page.getByRole('dialog', { name: 'Record verified CTU enrollment?' });
    await dialog.getByRole('button', { name: 'Record verification' }).click();
    await dialog.getByText('Choose the course shown on the CTU record.').waitFor();
    assert.equal(posts.length, 0);
    await dialog.getByLabel('Course *', { exact: true }).selectOption('1');
    await dialog.getByLabel('Year level *', { exact: true }).selectOption('1');
    await dialog.getByText('IT 101 · Introduction to Computing').click();
    await dialog.getByLabel('CTU record reference *', { exact: true }).fill('<b>');
    await dialog.getByRole('button', { name: 'Record verification' }).click();
    await dialog.getByText('Enter the CTU record reference (3 to 80 letters, digits, spaces, . - / #).').waitFor();
    await dialog.getByLabel('CTU record reference *', { exact: true }).fill('  CTU-REG   2026-0042 ');
    await dialog.getByRole('button', { name: 'Record verification' }).click();
    await page.getByRole('status').filter({ hasText: 'The student must still confirm their own onboarding.' }).waitFor();
    assert.deepEqual(posts.map((p) => [p.path, p.body]), [[`${VER}evidence/`, { student_account_id: 31, semester_id: 9,
      entry_classification: 'continuing', course_id: 1, year_level: 1, subject_ids: [105], source_reference: 'CTU-REG 2026-0042',
      source_as_of: null, expected_evidence_id: null }]]);
    assert.ok(posts[0].csrf);
  }, '/dashboard?view=student-verification');
});

const SCENES = [
  ['Step 1', () => studentServer(), 'semester-onboarding', 'Step 1: Student type'],
  ['completed', () => studentServer({ completed: true }), 'semester-onboarding', 'Onboarding completed'],
  ['clearance required', () => studentServer({ state: 'clearance_required', previousClearance: { semester: previous, clearance,
    fee: { obligation_id: 2, amount: '1400.00', currency: 'PHP', status: 'Unpaid' } } }), 'semester-onboarding', 'Clearance required'],
  ['my semester', () => studentServer({ completed: true }), 'my-subjects', 'Clearance and fee history'],
];
for (const [name, make, view, heading] of SCENES) {
  test(`onboarding (${name}) keeps AA contrast and fits 360–1440px in all three themes`, async () => {
    const fake = make();
    await scene(fake.handle, async (page) => {
      for (const [preference, scheme] of [['light', 'light'], ['system', 'dark'], ['dark', 'dark']]) {
        await page.emulateMedia({ colorScheme: scheme });
        await page.evaluate((v) => localStorage.setItem('ctug-theme', v), preference);
        for (const width of [360, 768, 1024, 1440]) {
          await page.setViewportSize({ width, height: 900 });
          await page.goto(`${new URL(page.url()).origin}/dashboard?view=${view}`);
          await page.getByRole('heading', { name: heading, exact: true }).waitFor();
          await page.waitForFunction(() => document.getAnimations().length === 0);
          const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
          assert.ok(layout.scroll <= layout.width, `${preference} ${width}px overflow ${layout.scroll}`);
          const selector = `${DASHBOARD_TEXT}, main dd, main dt, main label span, main legend, main li span, main td, main th, main p`;
          for (const { text, ratio } of await contrastReport(page, selector)) {
            assert.ok(ratio >= 4.5, `${preference} ${width}px "${text}" ${ratio.toFixed(2)}`);
          }
        }
      }
    }, `/dashboard?view=${view}`);
  });
}
