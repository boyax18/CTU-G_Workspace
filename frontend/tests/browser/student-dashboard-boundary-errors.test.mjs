// WF11-D17 Student dashboard boundary. Every API call is mocked; the onboarding switches are on for this
// Vite only. No real database, session, clearance, fee or student record changes.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';

process.env.VITE_WORKSPACE_STUDENT_ONBOARDING_ENABLED = '1';
process.env.VITE_WORKSPACE_STUDENT_ONBOARDING_FINALIZATION_ENABLED = '1';

const ON = '/api/v1/academic/onboarding/';
const STUDENT_CODES = ['academic.profile.self.read', 'clearance.requests.self.submit', 'academic.catalogue.read'];
const semester = { semester_id: 9, label: 'First Semester', status: 'Active', school_year_label: '2026–2027',
  start_date: '2026-08-10', end_date: '2026-12-18' };
const previous = { semester_id: 8, label: 'Second Semester', status: 'Closed', school_year_label: '2025–2026' };
const course = { course_id: 1, code: 'BSIT', name: 'Bachelor of Science in Information Technology' };
const option = { offering_id: 5, subject: { subject_id: 105, code: 'IT 101', title: 'Introduction to Computing', lecture_units: '3.0',
  lab_units: null }, section: { section_id: 2, name: '1-A', year_level: 1, course_code: 'BSIT' }, instructor: 'Ana Cruz',
  instructor_assigned: true, ready_for_confirmation: true };
const clearance = { clearance_id: 3, status: 'Uncleared', pending_count: 3, requirements: [
  { kind: 'subject_instructor', status: 'Pending', subject: { subject_id: 105, code: 'IT 101', title: 'Intro' }, signatory: 'Ana Cruz' },
  { kind: 'treasurer_fee', status: 'Pending', subject: null, signatory: null },
  { kind: 'school_admin_final', status: 'Pending', subject: null, signatory: null }] };
const fee = { obligation_id: 1, amount: '1500.00', currency: 'PHP', status: 'Unpaid' };
const ROUTE = { completed: 'dashboard', no_active_semester: 'period_unavailable', clearance_required: 'clearance_required',
  onboarding: 'onboarding', pending_verification: 'onboarding' };
const roleContext = (active) => ({ enabled: true, active_role_id: active, choices: [{ role_id: 1, role_name: 'Student' }, { role_id: 2, role_name: 'Instructor' }] });
const studentSession = () => ({ authenticated: true, account: { school_id: 'STU-0001', roles: ['Student', 'Instructor'] },
  permissions: STUDENT_CODES, role_context: roleContext(1) });
const instructorSession = () => ({ authenticated: true, account: { school_id: 'STU-0001', roles: ['Student', 'Instructor'] },
  permissions: ['academic.catalogue.read'], role_context: roleContext(2) });

/** A server whose Student state can change between requests (a new semester, another tab finalizing). */
function server({ state = 'onboarding', step = 1, session = studentSession(), statusError = null } = {}) {
  const s = { state, step, session, statusError, counts: { status: 0, mySemester: 0, posts: 0 } };
  const draft = () => (s.step === 1 && s.state === 'onboarding'
    ? { status: null, student_type: null, course: null, year_level: null, subjects: [], subjects_confirmed: false, course_confirmed: false,
      version: null, next_step: 1 }
    : { status: s.state === 'pending_verification' ? 'PendingVerification' : 'Draft', student_type: 'Regular',
      course: s.step >= 3 ? course : null, year_level: s.step >= 3 ? 1 : null, subjects: s.step >= 3 ? [option] : [],
      subjects_confirmed: s.step >= 3, course_confirmed: s.step >= 4, version: s.step, next_step: s.step });
  const result = () => ({ participation_id: 1, source: 'onboarding', student_type: 'Regular', course, year_level: 1,
    subjects: [{ subject_id: 105, code: 'IT 101', title: 'Introduction to Computing', section: '1-A', instructor: 'Ana Cruz' }], clearance, fee });
  const status = () => {
    const base = { state: s.state, dashboard_route: ROUTE[s.state] ?? 'verification_required', semester: s.state === 'no_active_semester' ? null : semester,
      dashboard_unlocked: s.state === 'completed', student: { ctug_id: 'STU-0001', full_name: null }, features: { finalization_enabled: true },
      correction_instructions: 'Visit the School Admin office in person.' };
    if (s.state === 'completed') return { ...base, result: result() };
    if (s.state === 'clearance_required') return { ...base, eligibility: { status: 'clearance_required', basis: '', previous_semester: previous,
      missing_gaps: [], older_uncleared: [] }, previous_clearance: { semester: previous, clearance, fee } };
    if (s.state === 'no_active_semester') return base;
    return { ...base, eligibility: { status: 'eligible', basis: '', previous_semester: null, missing_gaps: [], older_uncleared: [] },
      onboarding: draft(), prefill: null, verified_record_available: true };
  };
  const handle = async ({ path, request, respond }) => {
    if (path.endsWith('/auth/session/')) return respond(s.session);
    if (path.endsWith('/auth/role-context/')) {
      const { role_id: roleId } = request.postDataJSON();
      s.session = roleId === 2 ? instructorSession() : studentSession();
      return respond(s.session);
    }
    if (path === `${ON}status/`) {
      s.counts.status++;
      if (s.statusError) return respond({ error: { code: s.statusError.code, reason: s.statusError.reason, message: 'x' } }, s.statusError.status);
      if (!s.session.permissions.includes('academic.profile.self.read')) return respond({ error: { code: 'access_denied', reason: 'student_context_required' } }, 403);
      return respond(status());
    }
    if (path === `${ON}my-history/`) return respond({ results: s.state === 'clearance_required' || s.state === 'completed'
      ? [{ semester: previous, source: 'onboarding', year_level: 1, course_code: 'BSIT', clearance, fee }] : [] });
    if (path === `${ON}my-semester/`) {
      s.counts.mySemester++;
      if (s.state !== 'completed') return respond({ error: { code: 'onboarding_required', state: s.state, route: ROUTE[s.state] } }, 409);
      return respond({ semester, student: { ctug_id: 'STU-0001', full_name: null }, result: result() });
    }
    if (path === `${ON}context/`) return respond({ semester, courses: [{ ...course, year_levels: [1], sections: [{ section_id: 2, name: '1-A', year_level: 1 }] }] });
    if (path === `${ON}review/`) {
      if (s.state === 'completed') return respond({ state: 'completed', semester, result: result() });
      return respond({ state: 'review', semester, student: { ctug_id: 'STU-0001', full_name: null }, onboarding: draft(),
        fee: { revision_id: 7, amount: '1500.00', currency: 'PHP' }, fee_status: 'ready', verification: 'verified', mismatched: [],
        eligibility: {}, blockers: [], can_confirm: true, correction_instructions: 'x' });
    }
    if (path === `${ON}finalize/`) {
      s.counts.posts++;
      s.state = 'completed';
      return respond({ ...status(), outcome: 'completed' });
    }
    return respond({ error: { code: 'not_found' } }, 404);
  };
  return { s, handle };
}

const search = (page) => page.evaluate(() => window.location.search);
const pushView = (page, view) => page.evaluate((v) => {
  window.history.pushState(null, '', v ? `/dashboard?view=${v}` : '/dashboard');
  window.dispatchEvent(new PopStateEvent('popstate'));
}, view);

test('an eligible Student is routed to onboarding from home, direct URLs and Back, without loops', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor();
    assert.equal(await search(page), '?view=semester-onboarding');
    const length = await page.evaluate(() => window.history.length);
    await pushView(page, 'my-subjects');
    await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor();
    assert.equal(await page.evaluate(() => window.history.length), length + 1); // one push; each redirect replaced its entry
    await page.goto(new URL(page.url()).origin + '/dashboard?view=my-subjects');
    await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor();
    assert.equal(await search(page), '?view=semester-onboarding');
    assert.equal(fake.s.counts.mySemester, 0); // the protected view never mounted, so its data was never requested
    await pushView(page, 'account');
    await page.getByRole('heading', { name: 'Account details' }).waitFor(); // profile stays available
    await pushView(page, 'my-subjects'); // a stale or bookmarked protected entry
    await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor();
    await page.goBack(); // back to the profile, then back again lands on the permitted onboarding view
    await page.getByRole('heading', { name: 'Account details' }).waitFor();
    await page.goBack();
    await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor();
    const before = fake.s.counts.status;
    await page.waitForTimeout(600);
    assert.equal(await search(page), '?view=semester-onboarding');
    assert.ok(fake.s.counts.status - before <= 1, `no redirect loop (${fake.s.counts.status - before} extra status reads)`);
    assert.deepEqual(await page.evaluate(() => Object.keys(sessionStorage)), []);
    assert.ok((await page.evaluate(() => Object.keys(localStorage))).every((k) => k === 'ctug-theme'));
  }, '/dashboard');
});

test('Clearance Required is the routed view and own history stays available', async () => {
  const fake = server({ state: 'clearance_required' });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Clearance required', exact: true }).waitFor();
    assert.equal(await search(page), '?view=semester-onboarding');
    await page.getByRole('heading', { name: 'Clearance and fee history' }).waitFor();
    await page.getByText('Second Semester, S.Y. 2025–2026 · BSIT Year 1').waitFor();
    assert.equal(await page.getByRole('heading', { name: /^Step / }).count(), 0);
  }, '/dashboard?view=my-subjects');
  const none = server({ state: 'no_active_semester' });
  await scene(none.handle, async (page) => {
    await page.getByRole('heading', { name: 'No active semester' }).waitFor();
    await page.getByRole('heading', { name: 'Clearance and fee history' }).waitFor();
    assert.equal(none.s.counts.posts, 0);
  }, '/dashboard');
});

test('Pending Verification keeps the Draft, and a refresh resumes the server Draft', async () => {
  const fake = server({ state: 'pending_verification', step: 4 });
  await scene(fake.handle, async (page) => {
    await page.getByText(/Pending verification: no verified CTU enrollment record/).waitFor();
    await page.getByRole('heading', { name: 'Step 4: Final review' }).waitFor();
    fake.s.state = 'onboarding'; fake.s.step = 3;
    await page.reload();
    await page.getByRole('heading', { name: 'Step 3: Course and year level' }).waitFor(); // recovered from the server
  }, '/dashboard');
});

test('completion opens the normal dashboard once, then never redirects back', async () => {
  const fake = server({ step: 4 });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Step 4: Final review' }).waitFor();
    await page.getByLabel('I confirm these details are correct').check();
    await page.getByRole('button', { name: 'Confirm onboarding' }).click();
    await page.getByRole('status').filter({ hasText: 'Your semester onboarding is complete.' }).waitFor();
    assert.equal(await search(page), '');
    await page.getByRole('heading', { name: 'Student workspace' }).waitFor();
    await pushView(page, 'my-subjects');
    await page.getByRole('table', { name: 'Confirmed subjects' }).waitFor();
    await page.reload();
    await page.getByRole('table', { name: 'Confirmed subjects' }).waitFor();
    assert.equal(await search(page), '?view=my-subjects');
    assert.equal(fake.s.counts.posts, 1);
  }, '/dashboard');
});

test('a newly activated semester and another tab are picked up from the server, not from storage', async () => {
  const fake = server({ state: 'completed' });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Student workspace' }).waitFor();
    fake.s.state = 'onboarding'; // the School Admin activated a new semester
    await page.evaluate(() => window.dispatchEvent(new Event('focus')));
    await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor();
    assert.equal(await search(page), '?view=semester-onboarding');

    // Second tab of the same browser: it stays routed until this tab's finalization pings it.
    const other = await page.context().newPage();
    let otherReads = 0;
    await other.route('**/*', async (route) => {
      const url = new URL(route.request().url());
      if (!url.pathname.startsWith('/api/')) return route.continue();
      const respond = (body, statusCode = 200) => route.fulfill({ status: statusCode, contentType: 'application/json', body: JSON.stringify(body) });
      if (url.pathname.endsWith('/csrf/')) return respond({ csrfToken: 'tok' });
      if (url.pathname === `${ON}status/`) otherReads++;
      return fake.handle({ path: url.pathname, request: route.request(), route, respond });
    });
    fake.s.step = 4;
    await other.goto(new URL(page.url()).origin + '/dashboard');
    await other.getByRole('heading', { name: 'Step 4: Final review' }).waitFor();
    await page.reload();
    await page.getByRole('heading', { name: 'Step 4: Final review' }).waitFor();
    await page.getByLabel('I confirm these details are correct').check();
    const reads = otherReads;
    await page.getByRole('button', { name: 'Confirm onboarding' }).click();
    await page.getByRole('heading', { name: 'Student workspace' }).waitFor();
    const deadline = Date.now() + 5000;
    while (otherReads === reads && Date.now() < deadline) await other.waitForTimeout(50);
    assert.ok(otherReads > reads, 'the other tab re-read the server after the ping');
    await pushView(other, ''); // in-app navigation, no reload: the boundary already reflects the server
    await other.getByRole('heading', { name: 'Student workspace' }).waitFor();
    await other.close();
  }, '/dashboard');
});

test('other role contexts and multi-role sessions keep their own modules', async () => {
  const instructor = server({ session: instructorSession() });
  await scene(instructor.handle, async (page) => {
    await page.getByRole('heading', { name: 'Instructor workspace' }).waitFor();
    assert.equal(instructor.s.counts.status, 0); // no Student read code in this context: no boundary at all
  }, '/dashboard');

  const switching = server();
  await scene(switching.handle, async (page) => {
    await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor();
    await page.getByLabel('Active role').selectOption('2');
    await page.getByRole('heading', { name: 'Instructor workspace' }).waitFor();
    await page.waitForTimeout(300);
    assert.equal(await search(page), '');
    await page.getByLabel('Active role').selectOption('1');
    await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor(); // the Student context is gated again
  }, '/dashboard');

  const refused = server({ statusError: { status: 403, code: 'access_denied', reason: 'student_context_required' } });
  await scene(refused.handle, async (page) => {
    await page.getByRole('heading', { name: 'Student workspace' }).waitFor();
    await page.waitForTimeout(300);
    assert.equal(await search(page), '');
  }, '/dashboard');

  const multi = server({ session: { authenticated: true, account: { school_id: 'ADM-STU', roles: ['Student', 'Admin'] },
    permissions: [...STUDENT_CODES, 'academic.periods.manage'] } });
  await scene(multi.handle, async (page) => {
    await page.getByRole('heading', { name: 'Complete your semester onboarding' }).waitFor(); // a notice, not a redirect
    assert.equal(await search(page), '');
    await pushView(page, 'my-subjects');
    await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor();
  }, '/dashboard');
});

test('an unconfirmable onboarding state fails closed for semester views only', async () => {
  const fake = server({ statusError: { status: 500, code: 'server_error' } });
  await scene(fake.handle, async (page) => {
    await page.getByRole('alert').filter({ hasText: 'We could not confirm your semester onboarding' }).waitFor();
    assert.equal(fake.s.counts.mySemester, 0);
    await pushView(page, 'account');
    await page.getByRole('heading', { name: 'Account details' }).waitFor();
    fake.s.statusError = null;
    await pushView(page, '');
    await page.getByRole('button', { name: 'Try again' }).click();
    await page.getByRole('heading', { name: 'Step 1: Student type' }).waitFor();
  }, '/dashboard');
});
