// Current academic period (FR-ACA-07) and readiness-check parsing. Every request is mocked.
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
const catalogue = await import('../src/features/academic/academicCatalogueApi.ts');
const contract = await import('../src/features/academic/academicPeriodsContract.ts');
hooks.deregister();

const period = { semester_id: 9, term: 'first', label: 'First semester', school_year_id: 2, school_year_label: '2026–2027',
  start_date: '2026-08-10', end_date: '2026-12-18' };
const semester = (checks) => ({ semester_id: 7, term: 'first', label: 'First semester', status: 'Draft', start_date: null, end_date: null,
  version: 1, can_edit_dates: true, activation: { available: false, missing: ['valid_dates'], checks }, updated_at: null });
const year = (checks) => ({ school_year_id: 4, start_year: 2026, end_year: 2027, label: '2026–2027', status: 'Draft',
  semesters: [semester(checks), { ...semester(checks), semester_id: 8, term: 'second', label: 'Second semester' }], can_delete: true,
  created_at: null, updated_at: null });

test('the catalogue switch is off by default and nothing is fetched while off', async () => {
  assert.equal(catalogue.ACADEMIC_CATALOGUE_ENABLED, false);
  assert.equal(catalogue.CATALOGUE_CODE, 'academic.catalogue.read');
  const before = globalThis.fetch;
  let calls = 0;
  globalThis.fetch = async () => { calls += 1; throw new Error('must not fetch'); };
  try {
    await assert.rejects(catalogue.getCurrentPeriod(), (e) => e.code === 'academic_catalogue_unavailable');
  } finally { globalThis.fetch = before; }
  assert.equal(calls, 0);
});

test('the current period parses strictly; "no active semester" is an explicit null', () => {
  assert.equal(catalogue.parseCurrentPeriod({ active: null }), null);
  assert.equal(catalogue.parseCurrentPeriod({ active: period }).school_year_label, '2026–2027');
  for (const bad of [{}, null, { active: { ...period, term: 'summer' } }, { active: { ...period, start_date: '10/08/2026' } },
    { active: { ...period, semester_id: 0 } }]) {
    assert.throws(() => catalogue.parseCurrentPeriod(bad));
  }
});

test('a failed read is an error, never "no period"', async () => {
  const before = globalThis.fetch;
  globalThis.fetch = async () => ({ ok: false, status: 503, json: async () => ({ error: { code: 'academic_catalogue_unavailable' } }) });
  try {
    await assert.rejects(catalogue.getCurrentPeriod(true), (e) => e.status === 503);
  } finally { globalThis.fetch = before; }
});

test('readiness checks are allowlisted, distinct and optional for older payloads', () => {
  const checks = [{ key: 'valid_dates', status: 'missing', reason: 'dates_incomplete' },
    { key: 'approved_fee', status: 'unavailable', reason: 'fee_source_disabled' },
    { key: 'academic_offerings', status: 'ready', reason: '' }];
  assert.deepEqual(contract.parseSchoolYear(year(checks)).semesters[0].activation.checks, checks);
  assert.deepEqual(contract.parseSchoolYear(year(undefined)).semesters[0].activation.checks, []);
  for (const bad of [[{ key: 'free_pass', status: 'ready', reason: '' }], [{ ...checks[0], status: 'approved' }],
    [{ ...checks[0], reason: '<b>x</b>' }], [checks[0], checks[0]]]) {
    assert.throws(() => contract.parseSchoolYear(year(bad)));
  }
});
