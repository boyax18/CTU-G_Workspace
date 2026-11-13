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
  getVisibleDashboardItems, canOpenDashboardView,
  getDashboardView, getDashboardHref,
} = await import('../src/features/dashboard/navigation.ts');
hooks.deregister();

const ids = (permissions) => getVisibleDashboardItems(permissions).map((item) => item.id);

test('no grants shows only the shared overview and account entries', () => {
  assert.deepEqual(ids([]), ['overview', 'account']);
});

test('role names do not authorize any module', () => {
  assert.deepEqual(ids(['Admin', 'Student', 'Treasurer']), ['overview', 'account']);
});

test('exact registration read grant reveals only its module', () => {
  assert.deepEqual(ids(['accounts.registration_requests.read']), ['overview', 'account', 'registration-review']);
  assert.equal(canOpenDashboardView('registration-review', []), false);
});

test('approval permission alone does not imply registration read permission', () => {
  assert.equal(canOpenDashboardView('registration-review', ['accounts.registration_requests.approve']), false);
});

test('explicit deny is not transformed into a grant by frontend', () => {
  assert.deepEqual(ids(['Deny:accounts.registration_requests.read']), ['overview','account']);
});

test('finance visibility requires an exact read permission', () => {
  assert.equal(canOpenDashboardView('finance', ['finance.summary.read']), true);
  assert.equal(canOpenDashboardView('finance', ['finance.payments.record']), false);
});

test('clearance checks authorized own or assigned read permission', () => {
  assert.equal(canOpenDashboardView('clearance', ['clearance.requests.self.read']), true);
  assert.equal(canOpenDashboardView('clearance', ['clearance.requests.assigned.read']), true);
  assert.equal(canOpenDashboardView('clearance', ['clearance.subject_requests.sign']), false);
});

test('academics and announcements require exact permission hints', () => {
  assert.equal(canOpenDashboardView('academic', ['academic.catalogue.read']), true);
  assert.equal(canOpenDashboardView('announcements', ['announcements.read']), true);
  assert.equal(canOpenDashboardView('announcements', ['announcements.create']), false);
});

test('querystring view is parsed only from known route keys', () => {
  assert.equal(getDashboardView('?view=account'), 'account');
  assert.equal(getDashboardView('?view=finance'), 'finance');
  assert.equal(getDashboardView('?view=unknown'), 'overview');
  assert.equal(getDashboardView(''), 'overview');
});

test('links stay within the single shared dashboard route', () => {
  assert.equal(getDashboardHref('overview'), '/dashboard');
  assert.equal(getDashboardHref('account'), '/dashboard?view=account');
});
