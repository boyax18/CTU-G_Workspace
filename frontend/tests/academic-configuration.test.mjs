// Academic configuration client and contract. Every request is mocked.
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
const config = await import('../src/features/academic/academicConfigurationConfig.ts');
const api = await import('../src/features/academic/academicConfigurationApi.ts');
const navigation = await import('../src/features/dashboard/navigation.ts');
hooks.deregister();

const ROOT = '/api/v1/academic/config/';
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
const course = (overrides = {}) => ({ course_id: 3, code: 'BSIT', name: 'Information Technology', status: 'Active', version: 1,
  in_use: false, references: { curricula: 0, sections: 0, offerings: 0 }, created_at: null, updated_at: null, ...overrides });
const subject = (overrides = {}) => ({ subject_id: 5, code: 'IT 101', title: 'Introduction', classification: null,
  lecture_units: '2.0', lab_units: null, status: 'Active', version: 1, in_use: false,
  references: { curriculum_entries: 0, offerings: 0 }, ...overrides });
const semester = { semester_id: 9, term: 'first', label: 'First semester', status: 'Draft', school_year_id: 2, school_year_label: '2026–2027' };
const offering = (overrides = {}) => ({ offering_id: 11, semester, section: { section_id: 4, name: '1-A', year_level: 1, course_code: 'BSIT' },
  subject: { subject_id: 5, code: 'IT 101', title: 'Introduction' }, curriculum: { curriculum_id: 7, label: '2024' },
  assignment: null, ready_for_confirmation: false, can_remove: true, created_at: null, ...overrides });

test('every switch is off by default and the navigation item stays "Soon"', () => {
  for (const name of ['ACADEMIC_CONFIGURATION_ENABLED', 'ACADEMIC_CURRICULUM_WRITES_ENABLED', 'ACADEMIC_OFFERING_WRITES_ENABLED',
    'ACADEMIC_TEACHING_ASSIGNMENTS_ENABLED']) assert.equal(config[name], false, name);
  const text = readFileSync(new URL('../src/features/academic/academicConfigurationConfig.ts', import.meta.url), 'utf8');
  for (const flag of ['CURRICULUM_WRITES', 'OFFERING_WRITES', 'TEACHING_ASSIGNMENTS']) {
    assert.match(text, new RegExp(`ACADEMIC_CONFIGURATION_ENABLED\\s*&& flag\\(import\\.meta\\.env\\?\\.VITE_WORKSPACE_ACADEMIC_${flag}_ENABLED\\)`));
  }
  const item = navigation.getDashboardItem('academic-references');
  assert.equal(item.integration, 'planned');
  assert.equal(item.label, 'Academic settings');
  assert.equal(navigation.canOpenDashboardView('academic-references', ['academic.catalogue.read']), false);
  assert.equal(navigation.canOpenDashboardView('academic-references', ['clearance.subjects.manage']), true);
  assert.equal(navigation.canOpenDashboardView('academic-references', ['academic.advisers.manage']), false);
  assert.deepEqual(config.AREA_CODES, { courses: 'academic.courses.manage', subjects: 'clearance.subjects.manage',
    sections: 'academic.sections.manage', curricula: 'academic.courses.manage', offerings: 'academic.periods.manage',
    teaching: 'clearance.teaching_assignments.manage' });
});

test('no request is sent while the configuration switch is off', async () => {
  await withFetch(() => { throw new Error('must not fetch'); }, async (calls) => {
    await assert.rejects(api.listCourses(), (e) => e.code === 'academic_configuration_unavailable');
    await assert.rejects(api.createCourse({ code: 'BSIT', name: 'IT' }), (e) => e.code === 'academic_configuration_unavailable');
    assert.equal(calls.length, 0);
  });
});

test('strict parsing accepts the server shape and rejects anything else', () => {
  assert.equal(api.parseCourse(course()).code, 'BSIT');
  assert.equal(api.parseSubject(subject()).lecture_units, '2.0');
  for (const bad of [course({ status: 'Deleted' }), course({ course_id: 0 }), course({ references: null }), course({ code: '' })]) {
    assert.throws(() => api.parseCourse(bad));
  }
  for (const bad of [subject({ lecture_units: 3 }), subject({ lecture_units: '3' }), subject({ lab_units: '100.0' })]) {
    assert.throws(() => api.parseSubject(bad));
  }
  assert.equal(api.parseOffering(offering()).ready_for_confirmation, false);
  assert.throws(() => api.parseOffering(offering({ semester: { ...semester, status: 'Reopened' } })));
  assert.deepEqual(api.parseFeatures({ curriculum_writes: 'true', offering_writes: true }),
    { curriculum_writes: false, offering_writes: true, teaching_assignments: false });
});

test('refusals use allowlisted codes, reasons and field text only', () => {
  const conflict = api.parseConfigError(409, { error: { code: 'configuration_conflict', reason: 'in_use', message: '<b>x</b>' } });
  assert.deepEqual([conflict.code, conflict.reason], ['configuration_conflict', 'in_use']);
  assert.equal(api.parseConfigError(409, { error: { reason: 'drop_tables' } }).reason, '');
  assert.equal(api.parseConfigError(503, { error: { code: 'feature_disabled' } }).code, 'feature_disabled');
  assert.equal(api.parseConfigError(403, { error: { code: 'access_denied', reason: 'admin_context_required' } }).reason,
    'admin_context_required');
  const fields = api.parseConfigError(400, { error: { fields: { code: ['<img src=x>'], name: ['Enter a name.'], password: ['x'] } } }).fields;
  assert.deepEqual(fields, { code: 'Check this value.', name: 'Enter a name.' });
  assert.equal(api.configErrorText(new api.ConfigApiError('x', conflict)),
    'This record is already used by curricula or offerings, so this change is not allowed.');
});

test('writes send one CSRF-protected POST with exactly the fields shown', async () => {
  await withFetch(() => reply(201, course()), async (calls) => {
    await api.createCourse({ code: 'BSIT', name: 'IT' });
  }).catch((e) => assert.equal(e.code, 'academic_configuration_unavailable')); // still off in this build
  const enabledPost = async (path, body) => api.configPost(path, body, true);
  await withFetch(() => reply(200, offering({ assignment: null })), async (calls) => {
    await enabledPost('offerings/11/instructor/', { instructor_account_id: 8, expected_assignment_id: null });
    assert.deepEqual(posts(calls).map((c) => [c.path, JSON.parse(c.body), c.headers['X-CSRFToken']]),
      [[`${ROOT}offerings/11/instructor/`, { instructor_account_id: 8, expected_assignment_id: null }, 'tok']]);
  });
});

test('an ambiguous mutation failure is outcome_unknown and never retried; definite 503s are refusals', async () => {
  await withFetch(() => { throw new TypeError('network down'); }, async (calls) => {
    await assert.rejects(api.configPost('courses/', { code: 'BSIT', name: 'IT' }, true), (e) => e.code === 'outcome_unknown' && e.outcomeUnknown);
    assert.equal(posts(calls).length, 1);
  });
  await withFetch(() => reply(503, { error: { code: 'feature_disabled' } }), async () => {
    await assert.rejects(api.configPost('curricula/', {}, true), (e) => e.code === 'feature_disabled' && !e.outcomeUnknown);
  });
  await withFetch(() => reply(500, undefined), async () => {
    await assert.rejects(api.configPost('courses/', {}, true), (e) => e.code === 'outcome_unknown');
  });
});

test('GET queries are built from defined values only', async () => {
  await withFetch(() => reply(200, { results: [], page: 1, page_size: 50, has_next: false }), async (calls) => {
    await api.configGet('courses/', { q: 'bs', status: undefined, page: 1 }, true);
    assert.equal(calls[0].path, `${ROOT}courses/?q=bs&page=1`);
  });
});
