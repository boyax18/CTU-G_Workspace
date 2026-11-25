// WF-11.01 school years & semesters: contract, client-side rules and client. Every request is mocked.
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
const contract = await import('../src/features/academic/academicPeriodsContract.ts');
const api = await import('../src/features/academic/academicPeriodsApi.ts');
const config = await import('../src/features/academic/academicPeriodsConfig.ts');
const lifecycleContract = await import('../src/features/academic/academicLifecycleContract.ts');
const lifecycleApi = await import('../src/features/academic/academicLifecycleApi.ts');
const navigation = await import('../src/features/dashboard/navigation.ts');
hooks.deregister();

const ROOT = '/api/v1/academic/';
const semester = (id, term, overrides = {}) => ({
  semester_id: id, term, label: term === 'first' ? 'First semester' : 'Second semester', status: 'Draft',
  start_date: null, end_date: null, version: 1, can_edit_dates: true,
  activation: { available: false, missing: ['valid_dates', 'approved_fee', 'academic_offerings'] },
  updated_at: '2026-11-25T05:00:00+00:00', ...overrides,
});
const year = (overrides = {}) => ({
  school_year_id: 4, start_year: 2026, end_year: 2027, label: '2026–2027', status: 'Draft',
  semesters: [semester(7, 'first'), semester(8, 'second')], can_delete: true,
  created_at: '2026-11-25T05:00:00+00:00', updated_at: '2026-11-25T05:00:00+00:00', ...overrides,
});
const page = (results, overrides = {}) => ({ results, page: 1, page_size: 20, has_next: false, ...overrides });
const reply = (status, body) => ({ ok: status >= 200 && status < 300, status, headers: new Headers(), json: async () => {
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
const posts = (calls) => calls.filter((c) => c.method === 'POST');

test('the switch is off by default and the navigation item stays "Soon"', () => {
  assert.equal(config.ACADEMIC_PERIODS_ENABLED, false);
  assert.equal(config.ACADEMIC_PERIODS_ROUTE_ROOT, ROOT);
  assert.match(readFileSync(new URL('../src/features/academic/academicPeriodsConfig.ts', import.meta.url), 'utf8'),
    /VITE_WORKSPACE_ACADEMIC_PERIODS_ENABLED === '1'/);
  const item = navigation.getDashboardItem('school-periods');
  assert.equal(item.integration, 'planned');
  assert.deepEqual(item.requiredAny, ['academic.periods.manage']);
  assert.equal(navigation.canOpenDashboardView('school-periods', ['academic.catalogue.read']), false);
  assert.equal(navigation.canOpenDashboardView('school-periods', ['academic.periods.manage']), true);
});

test('no fee-setting client exists and lifecycle switches are independent and off', () => {
  const source = ['academicPeriodsApi.ts', 'academicPeriodsContract.ts', 'academicLifecycleApi.ts', 'academicLifecycleContract.ts']
    .map((f) => readFileSync(new URL(`../src/features/academic/${f}`, import.meta.url), 'utf8')).join('\n');
  for (const word of ['fee_schedule', 'fee_amount', '/fees', 'participation_correction']) assert.equal(source.includes(word), false, word);
  assert.deepEqual(Object.keys(api).filter((k) => typeof api[k] === 'function').sort(),
    ['AcademicApiError', 'createSchoolYear', 'deleteSchoolYear', 'getAcademic', 'listSchoolYears', 'sendAcademic', 'updateSemesterDates']);
  assert.equal(config.ACADEMIC_PERIOD_TRANSITIONS_ENABLED, false);
  assert.equal(config.ACADEMIC_PERIOD_CORRECTIONS_ENABLED, false);
  const text = readFileSync(new URL('../src/features/academic/academicPeriodsConfig.ts', import.meta.url), 'utf8');
  assert.match(text, /ACADEMIC_PERIODS_ENABLED &&\s+import\.meta\.env\?\.VITE_WORKSPACE_ACADEMIC_PERIOD_TRANSITIONS_ENABLED === '1'/);
  assert.match(text, /ACADEMIC_PERIODS_ENABLED &&\s+import\.meta\.env\?\.VITE_WORKSPACE_ACADEMIC_PERIOD_CORRECTIONS_ENABLED === '1'/);
});

test('while switched off, no request is ever sent', async () => {
  await withFetch(() => { throw new Error('must not fetch'); }, async (calls) => {
    for (const call of [() => api.listSchoolYears(1), () => api.createSchoolYear(2026),
      () => api.updateSemesterDates(7, { start_date: null, end_date: null, expected_version: 1 }), () => api.deleteSchoolYear(4, 2026)]) {
      await assert.rejects(call(), (error) => error.code === 'academic_periods_unavailable');
    }
    assert.equal(calls.length, 0);
  });
});

test('strict parsing accepts the server shape and rejects anything else', () => {
  const parsed = contract.parseSchoolYearPage(page([year()]), 1);
  assert.equal(parsed.results[0].semesters[1].term, 'second');
  const broken = [
    year({ semesters: [semester(7, 'first')] }), year({ end_year: 2028 }), year({ status: 'Open' }),
    year({ semesters: [semester(8, 'second'), semester(7, 'first')] }),
    year({ semesters: [semester(7, 'first', { start_date: '2026-02-30' }), semester(8, 'second')] }),
    year({ semesters: [semester(7, 'first', { activation: { available: false, missing: ['free_pass'] } }), semester(8, 'second')] }),
    year({ semesters: [semester(7, 'first', { status: 'Enrolled' }), semester(8, 'second')] }),
  ];
  for (const value of broken) assert.throws(() => contract.parseSchoolYear(value), (e) => e.code === 'invalid_response');
  assert.throws(() => contract.parseSchoolYearPage(page([year()], { page: 2 }), 1));
});

test('client-side rules mirror the server for early feedback', () => {
  assert.equal(contract.parseStartYear(' 2026 '), 2026);
  for (const bad of ['1999', '2101', '26', '2026a', '']) assert.equal(contract.parseStartYear(bad), null);
  assert.deepEqual(contract.validateSemesterRange('2026-08-10', '2026-12-18', 2026), {});
  assert.deepEqual(contract.validateSemesterRange('2026-08-10', null, 2026), {});
  assert.equal(contract.validateSemesterRange('2026-08-10', '2026-08-10', 2026).end_date, 'The end date must be after the start date.');
  assert.match(contract.validateSemesterRange('2025-12-31', null, 2026).start_date, /two calendar years/);
  assert.equal(contract.validateSemesterRange('2026-13-01', null, 2026).start_date, 'Enter a valid start date.');
  assert.equal(contract.semestersOverlap(['2026-08-01', '2026-12-20'], ['2026-12-21', '2027-05-30']), false);
  assert.equal(contract.semestersOverlap(['2026-08-01', '2026-12-20'], ['2026-12-20', '2027-05-30']), true);
  assert.equal(contract.semestersOverlap([null, null], ['2026-12-20', null]), false);
});

test('create sends one CSRF-protected POST with exactly the start year', async () => {
  await withFetch(() => reply(201, year()), async (calls) => {
    const created = await api.createSchoolYear(2026, true);
    assert.equal(created.label, '2026–2027');
    assert.deepEqual(posts(calls).map((c) => [c.path, JSON.parse(c.body), c.headers['X-CSRFToken']]),
      [[`${ROOT}school-years/`, { start_year: 2026 }, 'tok']]);
  });
});

test('dates send the confirmed version and only an explicit overlap acknowledgment', async () => {
  await withFetch(() => reply(200, year()), async (calls) => {
    await api.updateSemesterDates(7, { start_date: '2026-08-10', end_date: null, expected_version: 3 }, true);
    await api.updateSemesterDates(7, { start_date: '2026-08-10', end_date: null, expected_version: 3,
      acknowledge_cross_year_overlap: true }, true);
    assert.deepEqual(posts(calls).map((c) => [c.path, JSON.parse(c.body)]), [
      [`${ROOT}semesters/7/dates/`, { start_date: '2026-08-10', end_date: null, expected_version: 3 }],
      [`${ROOT}semesters/7/dates/`, { start_date: '2026-08-10', end_date: null, expected_version: 3,
        acknowledge_cross_year_overlap: true }],
    ]);
  });
});

test('delete confirms the year it saw and requires the exact server confirmation', async () => {
  await withFetch(() => reply(200, { deleted: true, school_year_id: 4 }), async (calls) => {
    await api.deleteSchoolYear(4, 2026, true);
    assert.deepEqual(JSON.parse(posts(calls)[0].body), { expected_start_year: 2026 });
  });
  await withFetch(() => reply(200, { deleted: true, school_year_id: 5 }), async () => {
    await assert.rejects(api.deleteSchoolYear(4, 2026, true), (e) => e.code === 'invalid_response');
  });
});

test('refusals keep allowlisted reasons and fixed field text only', async () => {
  await withFetch(() => reply(409, { error: { code: 'period_conflict', reason: 'cross_year_overlap', message: '<b>x</b>' } }), async () => {
    await assert.rejects(api.updateSemesterDates(7, { start_date: null, end_date: null, expected_version: 1 }, true),
      (e) => e.detail.reason === 'cross_year_overlap' && e.status === 409);
  });
  await withFetch(() => reply(409, { error: { code: 'period_conflict', reason: 'drop_tables' } }), async () => {
    await assert.rejects(api.createSchoolYear(2026, true), (e) => e.detail.reason === '');
  });
  await withFetch(() => reply(403, { error: { code: 'access_denied', reason: 'admin_context_required' } }), async () => {
    await assert.rejects(api.listSchoolYears(1, true), (e) => e.detail.code === 'access_denied' && e.detail.reason === 'admin_context_required');
  });
  await withFetch(() => reply(400, { error: { code: 'invalid_request', fields: {
    end_date: ['The end date must be after the start date.'], start_date: ['<img src=x>'], password: ['x'] } } }), async () => {
    await assert.rejects(api.updateSemesterDates(7, { start_date: null, end_date: null, expected_version: 1 }, true),
      (e) => JSON.stringify(e.detail.fields) === JSON.stringify({
        start_date: 'Enter a valid start date.', end_date: 'The end date must be after the start date.' }));
  });
});

test('an ambiguous mutation failure is outcome_unknown and is never retried', async () => {
  await withFetch(() => { throw new TypeError('network down'); }, async (calls) => {
    await assert.rejects(api.createSchoolYear(2026, true), (e) => e.code === 'outcome_unknown' && e.outcomeUnknown === true);
    assert.equal(posts(calls).length, 1);
  });
  await withFetch(() => reply(502, undefined), async (calls) => {
    await assert.rejects(api.deleteSchoolYear(4, 2026, true), (e) => e.code === 'outcome_unknown');
    assert.equal(posts(calls).length, 1);
  });
  await withFetch(() => reply(503, { error: { code: 'academic_periods_unavailable' } }), async () => {
    await assert.rejects(api.createSchoolYear(2026, true), (e) => e.code === 'academic_periods_unavailable' && !e.outcomeUnknown);
  });
});

// ---- Lifecycle, corrections and history (WF11-D02 to D14) ----------------------------------------
const ref = (overrides = {}) => ({ semester_id: 7, term: 'first', label: 'First semester', status: 'Draft',
  start_date: '2026-08-10', end_date: '2026-12-18', version: 2, school_year_id: 4, school_year_label: '2026–2027', ...overrides });
const activation = (overrides = {}) => ({ semester: ref(), current_active: null, prerequisites: [
  { key: 'valid_dates', status: 'ready', reason: '' },
  { key: 'approved_fee', status: 'unavailable', reason: 'fee_schedule_not_implemented' },
  { key: 'academic_offerings', status: 'unavailable', reason: 'curriculum_offerings_not_implemented' }],
warnings: [], blockers: ['prerequisites_missing'], feature_enabled: false, can_confirm: false, ...overrides });
const counts = (keys, status = 'unavailable', count = null) =>
  keys.map((key) => ({ key, status, count, reason: status === 'unavailable' ? 'x_not_implemented' : '' }));
const OBLIGATIONS = ['outstanding_clearance_signatures', 'unpaid_fee_obligations', 'incomplete_onboarding'];
const IMPACTS = ['student_participation', 'fee_obligations', 'clearance_records'];
const correction = (overrides = {}) => ({ start_date: '2026-08-11', end_date: '2026-12-18', expected_version: 3,
  reason_code: 'calendar_change', reason_note: 'Calendar was revised.', acknowledged_impacts: [],
  acknowledge_cross_year_overlap: false, ...overrides });

test('page features fail closed when absent or not exactly true', () => {
  assert.deepEqual(contract.parseSchoolYearPage(page([]), 1).features, { transitions: false, corrections: false });
  assert.deepEqual(contract.parseSchoolYearPage(page([], { features: { transitions: 'yes', corrections: true } }), 1).features,
    { transitions: false, corrections: true });
});

test('previews parse strictly and never turn unavailable into zero', () => {
  assert.equal(lifecycleContract.parseActivationPreview(activation()).prerequisites[1].status, 'unavailable');
  const base = { warnings: [], blockers: [], feature_enabled: true, can_confirm: true };
  const closure = lifecycleContract.parseObligationPreview({ ...base, semester: ref({ status: 'Active' }), obligations: counts(OBLIGATIONS),
    warnings: ['unpaid_fee_obligations_unavailable'] });
  assert.equal(closure.obligations[0].count, null);
  assert.equal(lifecycleContract.dependencyNote('unavailable', null), 'Cannot be checked yet');
  assert.equal(lifecycleContract.dependencyNote('evaluated', 0), 'None');
  for (const bad of [activation({ prerequisites: activation().prerequisites.slice(1) }), activation({ warnings: ['<script>'] }),
    activation({ semester: ref({ status: 'Reopened' }) })]) {
    assert.throws(() => lifecycleContract.parseActivationPreview(bad));
  }
  // "unavailable" with a count, or "evaluated" without one, is rejected.
  assert.throws(() => lifecycleContract.parseObligationPreview({ ...base, semester: ref(), obligations: counts(OBLIGATIONS, 'unavailable', 0) }));
  assert.throws(() => lifecycleContract.parseObligationPreview({ ...base, semester: ref(), obligations: counts(OBLIGATIONS, 'evaluated', null) }));
  assert.match(lifecycleContract.warningLabel('unpaid_fee_obligations_unavailable'), /cannot be checked yet/);
  assert.equal(lifecycleContract.warningLabel('surprise'), 'Another condition needs your review.');
});

test('confirmations are never sent while their own switch is off', async () => {
  await withFetch(() => { throw new Error('must not fetch'); }, async (calls) => {
    await assert.rejects(lifecycleApi.confirmTransition(7, 'activation', { expected_version: 2, acknowledged_warnings: [] }),
      (e) => e.code === 'feature_disabled');
    await assert.rejects(lifecycleApi.correctSemester(7, correction()), (e) => e.code === 'feature_disabled');
    await assert.rejects(lifecycleApi.getActivationPreview(7), (e) => e.code === 'academic_periods_unavailable');
    assert.equal(calls.length, 0);
  });
});

test('activation sends the reviewed version, Active semester and warnings exactly once', async () => {
  await withFetch(() => reply(200, ref({ status: 'Active', version: 3 })), async (calls) => {
    const result = await lifecycleApi.confirmTransition(7, 'activation', { expected_version: 2,
      acknowledged_warnings: ['previous_active_will_close'], expected_active_semester_id: 5 }, true);
    assert.equal(result.status, 'Active');
    assert.deepEqual(posts(calls).map((c) => [c.path, JSON.parse(c.body)]), [[`${ROOT}semesters/7/activation/`,
      { confirmed: true, expected_version: 2, acknowledged_warnings: ['previous_active_will_close'], expected_active_semester_id: 5 }]]);
  });
  await withFetch(() => reply(200, ref({ status: 'Closed', version: 4 })), async (calls) => {
    await lifecycleApi.confirmTransition(7, 'closure', { expected_version: 3, acknowledged_warnings: [] }, true);
    assert.deepEqual(JSON.parse(posts(calls)[0].body), { confirmed: true, expected_version: 3, acknowledged_warnings: [] });
  });
});

test('refusals expose only allowlisted reasons and dependency details', async () => {
  await withFetch(() => reply(409, { error: { code: 'period_conflict', reason: 'prerequisites_missing',
    details: ['approved_fee', 'academic_offerings', 'root_password'] } }), async () => {
    await assert.rejects(lifecycleApi.confirmTransition(7, 'activation', { expected_version: 2, acknowledged_warnings: [] }, true),
      (e) => e.detail.reason === 'prerequisites_missing' && JSON.stringify(e.detail.details) === '["approved_fee","academic_offerings"]');
  });
  await withFetch(() => reply(503, { error: { code: 'feature_disabled' } }), async () => {
    await assert.rejects(lifecycleApi.confirmTransition(7, 'archive', { expected_version: 2, acknowledged_warnings: [] }, true),
      (e) => e.detail.code === 'feature_disabled' && !e.outcomeUnknown);
  });
  await withFetch(() => reply(400, { error: { code: 'invalid_request',
    fields: { reason_note: ['Explain the change in 10 to 500 characters.'] } } }), async () => {
    await assert.rejects(lifecycleApi.correctSemester(7, correction({ reason_note: 'short' }), true),
      (e) => e.detail.fields.reason_note === 'Explain the change in 10 to 500 characters.');
  });
});

test('corrections send the reason, note and only explicit acknowledgments', async () => {
  await withFetch(() => reply(200, year()), async (calls) => {
    await lifecycleApi.correctSemester(7, correction(), true);
    await lifecycleApi.correctSemester(7, correction({ acknowledged_impacts: ['fee_obligations'], acknowledge_cross_year_overlap: true }), true);
    const [plain, acknowledged] = posts(calls).map((c) => JSON.parse(c.body));
    assert.deepEqual(plain, { start_date: '2026-08-11', end_date: '2026-12-18', expected_version: 3, reason_code: 'calendar_change',
      reason_note: 'Calendar was revised.' });
    assert.deepEqual(acknowledged.acknowledged_impacts, ['fee_obligations']);
    assert.equal(acknowledged.acknowledge_cross_year_overlap, true);
  });
  const preview = lifecycleContract.parseCorrectionPreview({ semester: ref({ status: 'Active' }), kind: 'active_edit',
    impact: counts(IMPACTS), affected: [], reason_codes: ['calendar_change', 'data_entry_correction', 'institutional_directive'],
    blockers: ['impact_unavailable'], feature_enabled: true, can_confirm: false });
  assert.equal(preview.can_confirm, false);
});

test('history parses minimized entries and rejects unexpected fields', async () => {
  const entry = { event: 'academic.semester.historical_correction', description: 'Historical correction',
    occurred_at: '2026-11-25T05:00:00+00:00', actor: 'You', semester: 'first',
    changes: { start_date: { before: '2026-08-10', after: '2026-08-17' } }, reason: 'calendar_change', note: 'Registrar memorandum.' };
  await withFetch(() => reply(200, { results: [entry], page: 1, page_size: 20, has_next: false }), async (calls) => {
    const first = await lifecycleApi.getSchoolYearHistory(4, 1, true);
    assert.equal(first.results[0].changes.start_date.after, '2026-08-17');
    assert.equal(calls[0].path, `${ROOT}school-years/4/history/`);
  });
  const wrap = (item) => ({ results: [item], page: 1, page_size: 20, has_next: false });
  assert.throws(() => lifecycleContract.parseHistoryPage(wrap({ ...entry, actor: 'ADMIN-001' }), 1));
  assert.throws(() => lifecycleContract.parseHistoryPage(wrap({ ...entry, changes: { password: { before: null, after: 'x' } } }), 1));
});
