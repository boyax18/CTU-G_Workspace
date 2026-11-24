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
const model = await import('../src/features/admin/registrationReviewLiveViewModel.ts');
const { REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT } = await import('../src/features/admin/registrationReviewLiveConfig.ts');
const { REGISTRATION_REVIEW_LIVE_API_ENABLED } = await import('../src/features/admin/registrationReviewApiGate.ts');
hooks.deregister();

const read = 'accounts.registration_requests.read';
const approve = 'accounts.registration_requests.approve';
const reject = 'accounts.registration_requests.reject';
const records = [
  { account_id: 9101, school_id: 'CTU-100', full_name: 'Ana Reyes', requested_role: 'Student', created_at: '2026-11-12T10:00:00+08:00', email_verified: true, email: 'ana.reyes@example.edu' },
  { account_id: 9102, school_id: 'CTU-200', full_name: null, requested_role: 'Instructor', created_at: '2026-11-12T10:00:00+08:00', email_verified: false, email: null },
];

test('live API gate stays disabled and approved route remains unset', () => {
  assert.equal(REGISTRATION_REVIEW_LIVE_API_ENABLED, false);
  assert.equal(REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT, null);
});

// WF-02.01 R-10: presentation follows the exact permission hint only; role names are never consulted.
// Django still requires the Admin assignment and the effective permission on every request.
test('panel follows only the exact read hint and the gate, never a role name', () => {
  assert.equal(model.mayShowReviewPanel.length, 2);
  assert.equal(model.mayShowReviewPanel([], true), false);
  assert.equal(model.mayShowReviewPanel(['Admin'], true), false);
  assert.equal(model.mayShowReviewPanel([approve, reject], true), false);
  assert.equal(model.mayShowReviewPanel([read], false), false);
  assert.equal(model.mayShowReviewPanel([read], true), true);
});

test('a read hint never implies decision privileges', () => {
  assert.equal(model.mayShowReviewPanel([read], true), true);
  assert.equal(model.mayShowDecision([read], 'approve'), false);
});

test('approve and reject require their exact respective permission hints', () => {
  assert.equal(model.mayShowDecision([read, approve], 'approve'), true);
  assert.equal(model.mayShowDecision([read, approve], 'reject'), false);
  assert.equal(model.mayShowDecision([read, reject], 'reject'), true);
  assert.equal(model.mayShowDecision([approve, reject], 'approve'), false);
  assert.equal(model.mayShowDecision([approve, reject], 'reject'), false);
});

test('unknown action is never treated as a grant', () => {
  assert.equal(model.mayShowDecision([read, approve, reject], 'bulk'), false);
});

test('filters only current page and leaves source records unchanged', () => {
  const result = model.filterCurrentPage(records, ' ctu-2 ', 'All');
  assert.deepEqual(result, [records[1]]);
  assert.equal(records.length, 2);
});

test('role filter is exact and search is case-insensitive', () => {
  assert.deepEqual(model.filterCurrentPage(records, 'ctu-', 'Student'), [records[0]]);
  assert.deepEqual(model.filterCurrentPage(records, '', 'Instructor'), [records[1]]);
  assert.deepEqual(model.filterCurrentPage(records, 'missing', 'All'), []);
});

test('errors never reveal arbitrary strings returned by server', () => {
  const sensitive = 'password_hash=abc secret-school-id=123';
  assert.doesNotMatch(model.safeReviewError({ code: 'other', message: sensitive }), /secret-school-id/);
  assert.doesNotMatch(model.safeReviewError(new Error(sensitive)), /password_hash/);
});

test('permission and session failures have safe user messaging', () => {
  assert.match(model.safeReviewError({ code: 'access_denied' }), /permission/i);
  assert.match(model.safeReviewError({ code: 'authentication_required' }), /Sign in/i);
  assert.match(model.safeReviewError({ code: 'request_unavailable' }), /processed|available/i);
});

test('live page has confirm-before-POST, no optimistic success, refresh and page limit', () => {
  const panel = readFileSync(new URL('../src/features/admin/RegistrationReviewLivePanel.tsx', import.meta.url), 'utf8');
  assert.match(panel, /if \(!selection \|\| submitting/);
  assert.match(panel, /await approveRegistrationRequest/);
  assert.match(panel, /await rejectRegistrationRequest/);
  assert.match(panel, /setRefreshVersion\(\(current\) => current \+ 1\)/);
  assert.match(panel, /page >= 10000/);
  assert.match(panel, /role="dialog"/);
  assert.match(panel, /!REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT/);
});

test('dashboard and backend are not modified by this add-only package', () => {
  const panel = readFileSync(new URL('../src/features/admin/RegistrationReviewLivePanel.tsx', import.meta.url), 'utf8');
  assert.doesNotMatch(panel, /\bfetch\s*\(/);
  assert.doesNotMatch(panel, /set_password|\.save\s*\(/);
  assert.match(panel, /listPendingRegistrationRequests/);
});
