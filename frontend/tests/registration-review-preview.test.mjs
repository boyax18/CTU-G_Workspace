import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { registerHooks } from 'node:module';
import { test } from 'node:test';
import ts from 'typescript';

const hooks = registerHooks({
  load(url, context, nextLoad) {
    if (url.endsWith('.ts')) {
      const { outputText } = ts.transpileModule(readFileSync(new URL(url), 'utf8'), {
        compilerOptions: { module: ts.ModuleKind.ESNext, target: ts.ScriptTarget.ESNext },
      });
      return { format: 'module', source: outputText, shortCircuit: true };
    }
    return nextLoad(url, context);
  },
});
const {
  DEMO_REGISTRATIONS, REJECTION_OPTIONS, filterPendingRegistrations,
  canSimulateDecision, applySimulatedDecision,
} = await import('../src/features/admin/registrationReviewPreviewModel.ts');
const { REGISTRATION_REVIEW_UI_PREVIEW_ENABLED } = await import('../src/features/admin/registrationReviewPreviewGate.ts');
hooks.deregister();

const original = () => DEMO_REGISTRATIONS.map((entry) => ({ ...entry }));

test('preview gate is hard-disabled', () => {
  assert.equal(REGISTRATION_REVIEW_UI_PREVIEW_ENABLED, false);
});

test('all sample requests are explicitly fictional, unique and pending', () => {
  assert.equal(DEMO_REGISTRATIONS.length, 5);
  assert.equal(new Set(DEMO_REGISTRATIONS.map((entry) => entry.account_id)).size, DEMO_REGISTRATIONS.length);
  assert.ok(DEMO_REGISTRATIONS.every((entry) => entry.status === 'Pending' && entry.school_id.startsWith('99')));
});

test('only read+approve enables mock approval', () => {
  assert.equal(canSimulateDecision([], 'approve'), false);
  assert.equal(canSimulateDecision(['Admin', 'accounts.registration_requests.approve'], 'approve'), false);
  assert.equal(canSimulateDecision(['accounts.registration_requests.read', 'accounts.registration_requests.approve'], 'approve'), true);
});

test('reject requires its own exact permission plus read', () => {
  assert.equal(canSimulateDecision(['accounts.registration_requests.read', 'accounts.registration_requests.approve'], 'reject'), false);
  assert.equal(canSimulateDecision(['accounts.registration_requests.read', 'accounts.registration_requests.reject'], 'reject'), true);
});

test('mock list limits to pending and matches role', () => {
  const records = original();
  assert.equal(filterPendingRegistrations(records, '', 'All').length, 5);
  assert.equal(filterPendingRegistrations(records, '', 'Instructor').length, 2);
});

test('mock search uses only exact School ID text, not name or email', () => {
  assert.equal(filterPendingRegistrations(original(), '9900002', 'All').length, 1);
  assert.equal(filterPendingRegistrations(original(), 'not found', 'All').length, 0);
});

test('approval updates only fictional state, without mutating input', () => {
  const records = original();
  const next = applySimulatedDecision(records, 910001, 'approve');
  assert.equal(records[0].status, 'Pending');
  assert.equal(next[0].status, 'Approved');
  assert.equal(filterPendingRegistrations(next, '', 'All').length, 4);
});

test('rejection requires a known bounded reason', () => {
  assert.throws(() => applySimulatedDecision(original(), 910001, 'reject'));
  assert.throws(() => applySimulatedDecision(original(), 910001, 'reject', 'invented_code'));
  assert.equal(applySimulatedDecision(original(), 910001, 'reject', REJECTION_OPTIONS[0].code)[0].status, 'Rejected');
});

test('approval does not accept a rejection reason', () => {
  assert.throws(() => applySimulatedDecision(original(), 910001, 'approve', REJECTION_OPTIONS[0].code));
});

test('already decided or unknown mock account cannot be decided', () => {
  const decided = applySimulatedDecision(original(), 910001, 'approve');
  assert.throws(() => applySimulatedDecision(decided, 910001, 'approve'));
  assert.throws(() => applySimulatedDecision(original(), 999999, 'approve'));
});

test('mock UI component has no HTTP request or real approval endpoint calls', () => {
  const panel = readFileSync(new URL('../src/features/admin/RegistrationReviewPreview.tsx', import.meta.url), 'utf8');
  const model = readFileSync(new URL('../src/features/admin/registrationReviewPreviewModel.ts', import.meta.url), 'utf8');
  for (const value of [panel, model]) {
    assert.doesNotMatch(value, /\bfetch\s*\(|\bpostJSON\s*\(|\baxios\s*\(|\/api\/v1\//);
  }
  assert.match(panel, /Fictional data/);
});
