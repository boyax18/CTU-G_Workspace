// Student Semester Onboarding and CTU-verification client and contract. Every request is mocked.
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { registerHooks } from 'node:module';
import { test } from 'node:test';
import ts from 'typescript';

const hooks = registerHooks({
  load(url, _context, nextLoad) {
    if (url.endsWith('.ts')) {
      const { outputText } = ts.transpileModule(readFileSync(new URL(url), 'utf8'), {
        compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ESNext },
      });
      return { format: 'module', source: outputText, shortCircuit: true };
    }
    return nextLoad(url);
  },
});
const config = await import('../src/features/onboarding/onboardingConfig.ts');
const api = await import('../src/features/onboarding/onboardingApi.ts');
const navigation = await import('../src/features/dashboard/navigation.ts');
hooks.deregister();

const ON = { root: '/api/v1/academic/onboarding/', enabled: true, unavailable: 'student_onboarding_unavailable' };
const semester = { semester_id: 9, label: 'First Semester', status: 'Active', school_year_label: '2026–2027',
  start_date: '2026-08-10', end_date: '2026-12-18' };
const option = (overrides = {}) => ({ offering_id: 5, subject: { subject_id: 3, code: 'MATH 101', title: 'Mathematics', lecture_units: '3.0',
  lab_units: null }, section: { section_id: 2, name: '1-A', year_level: 1, course_code: 'BSIT' }, instructor: 'Ana Cruz',
  instructor_assigned: true, ready_for_confirmation: true, ...overrides });
const draft = (overrides = {}) => ({ status: 'Draft', student_type: 'Regular', course: { course_id: 1, code: 'BSIT', name: 'IT' }, year_level: 1,
  subjects: [option()], subjects_confirmed: true, course_confirmed: true, version: 4, next_step: 4, ...overrides });
const status = (overrides = {}) => ({ state: 'onboarding', semester, dashboard_unlocked: false, student: { ctug_id: 'STU-1', full_name: null },
  features: { finalization_enabled: true }, eligibility: { status: 'eligible', basis: 'no_prior_period', previous_semester: null,
    missing_gaps: [], older_uncleared: [] }, correction_instructions: 'Visit the School Admin office in person.', onboarding: draft(),
  prefill: null, verified_record_available: false, ...overrides });
const reply = (code, body) => ({ ok: code >= 200 && code < 300, status: code, headers: new Headers(), json: async () => {
  if (body === undefined) throw new SyntaxError('not json');
  return body;
} });
async function withFetch(handler, run) {
  const calls = [];
  const before = globalThis.fetch;
  globalThis.fetch = async (path, init = {}) => {
    calls.push({ path, method: init.method ?? 'GET', body: init.body, headers: init.headers ?? {} });
    if (path === '/api/v1/auth/csrf/') return reply(200, { csrfToken: 'tok' });
    return handler(path, init);
  };
  try { return await run(calls); } finally { globalThis.fetch = before; }
}

test('every switch is off by default and dependent switches need their parent', () => {
  for (const name of ['STUDENT_ONBOARDING_ENABLED', 'STUDENT_ONBOARDING_FINALIZATION_ENABLED', 'ENROLLMENT_VERIFICATION_ENABLED',
    'HISTORICAL_PARTICIPATION_CORRECTION_ENABLED']) assert.equal(config[name], false, name);
  const source = readFileSync(new URL('../src/features/onboarding/onboardingConfig.ts', import.meta.url), 'utf8');
  assert.match(source, /STUDENT_ONBOARDING_FINALIZATION_ENABLED: boolean = STUDENT_ONBOARDING_ENABLED\s*&& flag/);
  assert.match(source, /HISTORICAL_PARTICIPATION_CORRECTION_ENABLED: boolean = ENROLLMENT_VERIFICATION_ENABLED\s*&& flag/);
});

test('navigation is driven by exact permission codes and stays planned while switched off', () => {
  for (const [view, code, group] of [['semester-onboarding', 'academic.profile.self.read', 'academic'],
    ['my-subjects', 'academic.profile.self.read', 'academic'], ['student-verification', 'academic.profiles.manage', 'academic-configuration']]) {
    const item = navigation.getDashboardItem(view);
    assert.deepEqual([item.integration, item.group, item.requiredAny], ['planned', group, [code]], view);
    assert.equal(navigation.canOpenDashboardView(view, [code]), true);
    assert.equal(navigation.canOpenDashboardView(view, ['clearance.requests.self.submit', 'academic.catalogue.read']), false);
  }
});

test('no request is sent while switched off, including finalization and School Admin actions', async () => {
  await withFetch(() => { throw new Error('must not fetch'); }, async (calls) => {
    await assert.rejects(api.getStatus(), (e) => e.code === 'student_onboarding_unavailable');
    await assert.rejects(api.saveStudentType('Regular', null), (e) => e.code === 'student_onboarding_unavailable');
    await assert.rejects(api.finalizeOnboarding({ fee: { revision_id: 1 }, onboarding: draft() }), (e) => e.code === 'feature_disabled');
    await assert.rejects(api.searchStudents('STU'), (e) => e.code === 'verification_unavailable');
    await assert.rejects(api.getHistoricalPreview(1, 2), (e) => e.code === 'historical_correction_unavailable');
    assert.equal(calls.length, 0);
  });
});

test('Student requests never carry a student identifier', () => {
  const source = readFileSync(new URL('../src/features/onboarding/onboardingApi.ts', import.meta.url), 'utf8');
  const student = source.slice(source.indexOf('// ---- Student operations'), source.indexOf('// ---- School Admin operations'));
  assert.ok(student.length > 500);
  assert.doesNotMatch(student, /student_account_id|account_id|school_id/);
});

test('responses are parsed strictly and fail closed', () => {
  const parsed = api.parseStatus(status());
  assert.equal(parsed.state, 'onboarding');
  assert.equal(parsed.finalization_enabled, false); // the build switch is off, whatever the server says
  assert.equal(parsed.onboarding.subjects[0].ready_for_confirmation, true);
  assert.equal(api.parseOption(option({ instructor_assigned: false })).ready_for_confirmation, false);
  for (const bad of [{ state: 'cleared' }, { semester: { ...semester, status: 'Open' } }, { onboarding: draft({ next_step: 5 }) },
    { onboarding: draft({ subjects: [option({ offering_id: 0 })] }) }]) {
    assert.throws(() => api.parseStatus(status(bad)), (e) => e.code === 'invalid_response', JSON.stringify(bad));
  }
  assert.throws(() => api.parseFee({ amount: '1500.00', currency: 'USD', status: 'Unpaid' }), (e) => e.code === 'invalid_response');
  assert.throws(() => api.parseFee({ amount: '1500', currency: 'PHP', status: 'Unpaid' }), (e) => e.code === 'invalid_response');
  assert.equal(api.parseFee(null), null);
  const clearance = api.parseClearance({ clearance_id: 1, status: 'Uncleared', pending_count: 3, requirements: [
    { kind: 'subject_instructor', status: 'Pending', subject: { subject_id: 3, code: 'MATH 101', title: 'Math' }, signatory: 'Ana Cruz' },
    { kind: 'treasurer_fee', status: 'Pending', subject: null, signatory: null }] });
  assert.equal(clearance.requirements[1].signatory, null);
  assert.throws(() => api.parseClearance({ status: 'Cleared', pending_count: 0, requirements: [{ kind: 'payment', status: 'Pending',
    subject: null, signatory: null }] }), (e) => e.code === 'invalid_response');
  assert.equal(api.peso('1500.00'), '₱1,500.00');
});

test('errors map to fixed copy and never echo server text', () => {
  const conflict = api.parseOnboardingError(409, { error: { code: 'onboarding_conflict', reason: 'instructor_unassigned', message: 'RAW' } });
  assert.deepEqual([conflict.code, conflict.reason], ['onboarding_conflict', 'instructor_unassigned']);
  const required = api.parseOnboardingError(409, { error: { code: 'onboarding_required', state: 'clearance_required' } });
  assert.deepEqual([required.code, required.state], ['onboarding_required', 'clearance_required']);
  const context = api.parseOnboardingError(403, { error: { code: 'access_denied', reason: 'student_context_required' } });
  const text = (detail) => api.onboardingErrorText(new api.OnboardingApiError('x', detail));
  assert.equal(text(context), 'Switch to your Student role, then try again.');
  assert.equal(text(conflict), 'A selected subject has no assigned instructor yet. Visit the School Admin in person.');
  assert.equal(text(api.parseOnboardingError(409, { error: { code: 'onboarding_conflict', reason: '<script>' } })),
    'The change conflicts with the current records. Reload and try again.');
  assert.equal(api.parseOnboardingError(403, { error: { code: 'csrf_failed' } }).code, 'csrf_failed');
  assert.equal(api.parseOnboardingError(503, { error: { code: 'feature_disabled' } }).code, 'feature_disabled');
  assert.equal(api.parseOnboardingError(503, {}, 'verification_unavailable').code, 'verification_unavailable');
  const fields = api.parseOnboardingError(400, { error: { fields: { source_reference: ['RAW SERVER TEXT'], other: ['x'] } } }).fields;
  assert.deepEqual(fields, { source_reference: 'Enter the CTU record reference (3 to 80 letters, digits, spaces, . - / #).' });
});

test('a write is sent once with CSRF and an uncertain outcome is never retried', async () => {
  await withFetch(async () => { throw new TypeError('network down'); }, async (calls) => {
    await assert.rejects(api.send(ON, 'finalize/', { expected_version: 4, expected_fee_revision_id: 7, confirmed: true }),
      (e) => e.code === 'outcome_unknown' && e.outcomeUnknown === true);
    const posts = calls.filter((c) => c.method === 'POST');
    assert.equal(posts.length, 1);
    assert.equal(posts[0].headers['X-CSRFToken'], 'tok');
  });
  await withFetch(async () => reply(502, { error: { code: 'bad_gateway' } }), async () => {
    await assert.rejects(api.send(ON, 'type/', { student_type: 'Regular' }), (e) => e.code === 'outcome_unknown');
  });
  await withFetch(async () => reply(409, { error: { code: 'onboarding_conflict', reason: 'fee_changed' } }), async (calls) => {
    await assert.rejects(api.send(ON, 'finalize/', {}), (e) => e.detail.reason === 'fee_changed');
    assert.equal(calls.filter((c) => c.method === 'POST').length, 1);
  });
  await withFetch(async (path) => reply(200, path.includes('status') ? status() : {}), async (calls) => {
    assert.equal(api.parseStatus(await api.get(ON, 'status/')).state, 'onboarding');
    assert.equal(calls[0].path, '/api/v1/academic/onboarding/status/');
  });
});
