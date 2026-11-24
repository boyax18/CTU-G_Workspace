// WF-02.03 P-08: the approval section of the applicant detail. Every API call is mocked; no real
// database, session or email. The read and approval switches are on for this isolated Vite only.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport, DASHBOARD_TEXT } from './contrastProbe.mjs';

process.env.VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED = '1';
process.env.VITE_WORKSPACE_REGISTRATION_APPROVAL_ENABLED = '1';
process.env.VITE_WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED = '1';

const READ = 'accounts.registration_requests.read';
const APPROVE = 'accounts.registration_requests.approve';
const LIST = '/api/v1/admin/registration-requests/';
const VIEW = '/dashboard?view=registration-review';
const STUDENT_SOURCE = 'CTU main system enrollment records';
const session = (permissions) => ({ authenticated: true, account: { school_id: 'ADMIN-001', roles: ['Admin'] }, permissions });

const row = (n) => ({
  account_id: 6000 + n, school_id: `72410${String(n).padStart(2, '0')}`, full_name: `Applicant ${n} Cruz`,
  requested_role: 'Student', created_at: '2026-11-10T09:15:00+08:00', email_verified: true,
});
const detail = (id, overrides = {}) => ({
  account_id: id, school_id: '7241001', id_label: 'CTU-G ID',
  name: { first: 'Maria', middle: 'Luz', last: 'Santos', suffix: null }, full_name: 'Maria Luz Santos',
  email: 'maria.santos@example.edu', requested_role: 'Student', request_status: 'Pending',
  created_at: '2026-11-10T09:15:00+08:00',
  email_evidence: { state: 'verified', verified_at: '2026-11-10T09:20:00+08:00' },
  institutional_check: { subject: 'enrollment', verified_by_workspace: false },
  data_notes: [],
  ...overrides,
});

/** approve(id, state) returns [body, status] or 'abort'; it may be async (to hold the request open). */
function server({
  permissions = [READ, APPROVE], actions = 'approve,reject', bulkActions = '',
  listPage = () => ({ results: [row(1), row(2)], page: 1, page_size: 20, has_next: false }),
  detailFor = (id) => detail(id),
  approve = (id) => [{ account_id: id, status: 'Approved', notification: 'queued' }],
  bulkDecision = (body) => {
    const outcome = body.action === 'approve' ? 'Approved' : 'Rejected';
    const counts = { Approved: 0, Rejected: 0, Skipped: 0, Failed: 0, Unconfirmed: 0 };
    counts[outcome] = body.account_ids.length;
    return [{
      action: body.action, requested: body.account_ids.length, processed: body.account_ids.length,
      remaining: 0, interrupted: false, counts,
      results: body.account_ids.map((account_id) => ({ account_id, outcome, notification: 'queued' })),
    }];
  },
} = {}) {
  const state = { session: session(permissions), lists: 0, details: [], approvals: [], bulkDecisions: [] };
  const handle = async ({ path, request, respond, route }) => {
    if (path.endsWith('/session/')) return respond(state.session);
    if (request.method() === 'POST') {
      if (path === `${LIST}bulk/`) {
        const body = request.postDataJSON();
        state.bulkDecisions.push({ body, csrf: request.headers()['x-csrftoken'] });
        const result = await bulkDecision(body, state);
        if (result === 'abort') return route.abort('failed');
        return respond(result[0], result[1] ?? 200);
      }
      const match = path.match(/^\/api\/v1\/admin\/registration-requests\/(\d+)\/approve\/$/);
      if (!match) return route.abort('failed');
      state.approvals.push({ id: Number(match[1]), body: request.postDataJSON(), csrf: request.headers()['x-csrftoken'] });
      const result = await approve(Number(match[1]), state);
      if (result === 'abort') return route.abort('failed');
      return respond(result[0], result[1] ?? 200);
    }
    if (path === LIST) {
      state.lists++;
      return respond(listPage(Number(new URL(request.url()).searchParams.get('page') || '1')),
        200, bulkActions ? { 'X-Workspace-Available-Actions': bulkActions } : {});
    }
    const match = path.match(/^\/api\/v1\/admin\/registration-requests\/(\d+)\/$/);
    if (match) { state.details.push(Number(match[1])); return respond(detailFor(Number(match[1]), state), 200, { 'X-Workspace-Available-Actions': actions }); }
    return route.abort('failed');
  };
  return { state, handle };
}

const at = (id) => `${VIEW}&applicant=${id}`;

const ALL = 'approve,reject,bulk-approve,bulk-reject';
const selectAll = (page) => page.getByRole('checkbox', { name: 'Select all applicants on this page' });

test('without decision availability there are no checkboxes and no decision toolbar', async () => {
  const fake = server({ actions: '' });
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    assert.equal(await page.getByRole('checkbox').count(), 0);
    for (const name of [/^Approve/, /^Reject/, /Select All/, 'Unselect All']) {
      assert.equal(await page.getByRole('button', { name }).count(), 0);
    }
    await page.getByText('Approve and Reject are not available in this session.').waitFor();
    assert.equal(fake.state.approvals.length, 0);
  }, VIEW);
});

test('selection comes first, the toolbar appears only with a selection, and labels follow it', async () => {
  const fake = server({ bulkActions: ALL });
  await scene(fake.handle, async (page) => {
    const table = page.getByRole('table');
    await table.waitFor();
    const headers = await table.locator('thead th').allInnerTexts();
    assert.equal(headers[1].trim().toUpperCase(), 'CTU-G ID', JSON.stringify(headers));
    assert.equal(await table.locator('tbody tr').first().locator('td').first().locator('input[type="checkbox"]').count(), 1);
    assert.equal(await page.getByRole('button', { name: /^Approve/ }).count(), 0, 'decision buttons hidden with no selection');
    // Select All is offered even before anything is ticked.
    await page.getByRole('button', { name: 'Select All', exact: true }).click();
    await page.getByText('2 applicants selected on this page').waitFor();
    await page.getByRole('button', { name: 'Approve All' }).waitFor();
    await page.getByRole('button', { name: 'Unselect All' }).click();
    await page.getByText('Select applicants to approve or reject them.').waitFor();
    await page.getByRole('checkbox', { name: 'Select CTU-G ID 7241001' }).check();
    await page.getByText('1 applicant selected on this page').waitFor();
    assert.equal(await page.getByRole('button', { name: 'Approve', exact: true }).isEnabled(), true);
    assert.equal(await page.getByRole('button', { name: 'Reject', exact: true }).isEnabled(), true);
    await page.getByRole('button', { name: 'Select All', exact: true }).click();
    await page.getByText('2 applicants selected on this page').waitFor();
    await page.getByRole('button', { name: 'Approve All' }).waitFor();
    await page.getByRole('button', { name: 'Reject All' }).waitFor();
    assert.equal(await page.getByRole('button', { name: 'Select All', exact: true }).count(), 0);
    await page.getByRole('button', { name: 'Unselect All' }).click();
    assert.equal(await page.getByRole('button', { name: /^Approve/ }).count(), 0, 'toolbar hidden after Unselect All');
    assert.equal(fake.state.approvals.length + fake.state.bulkDecisions.length, 0);
  }, VIEW);
});

test('Select All includes every matching applicant on every page; groups of 20 are sent in turn', async () => {
  const fake = server({
    bulkActions: ALL,
    listPage: (n) => (n === 1
      ? { results: Array.from({ length: 20 }, (_, i) => row(i + 1)), page: 1, page_size: 20, has_next: true }
      : { results: [row(21)], page: 2, page_size: 20, has_next: false }),
  });
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    await page.getByRole('button', { name: 'Select All', exact: true }).click();
    await page.getByText('21 applicants selected, including 1 on other pages').waitFor();
    await page.getByRole('button', { name: 'Approve All' }).waitFor();
    // The selection survives moving to the next page.
    await page.getByRole('button', { name: 'Next' }).click();
    await page.getByText('Page 2', { exact: true }).waitFor();
    assert.equal(await page.getByRole('checkbox', { name: 'Select CTU-G ID 7241021' }).isChecked(), true);
    await page.getByRole('button', { name: 'Approve All' }).click();
    const dialog = page.getByRole('dialog', { name: 'Confirm approval of 21 applicants?' });
    await dialog.waitFor();
    assert.ok((await dialog.innerText()).includes('groups of up to 20'));
    await dialog.getByRole('checkbox').check();
    await dialog.getByRole('button', { name: 'Confirm bulk approval' }).click();
    const summary = page.getByRole('status', { name: 'Decision results' });
    await summary.getByText('Approved 21; rejected 0').waitFor();
    assert.deepEqual(fake.state.bulkDecisions.map((d) => d.body.account_ids.length), [20, 1]);
    assert.deepEqual(new Set(fake.state.bulkDecisions.flatMap((d) => d.body.account_ids)).size, 21);
  }, VIEW);
});

test('a rate-limited group stops the run without retrying and reports the rest as not attempted', async () => {
  const fake = server({
    bulkActions: ALL,
    listPage: (n) => (n === 1
      ? { results: Array.from({ length: 20 }, (_, i) => row(i + 1)), page: 1, page_size: 20, has_next: true }
      : { results: [row(21), row(22)], page: 2, page_size: 20, has_next: false }),
    bulkDecision: (body, state) => {
      if (state.bulkDecisions.length > 1) return [{ error: { code: 'rate_limited', message: 'Too many attempts. Try later.' } }, 429];
      const counts = { Approved: body.account_ids.length, Rejected: 0, Skipped: 0, Failed: 0, Unconfirmed: 0 };
      return [{ action: 'approve', requested: body.account_ids.length, processed: body.account_ids.length, remaining: 0,
        interrupted: false, counts, results: body.account_ids.map((account_id) => ({ account_id, outcome: 'Approved', notification: 'queued' })) }];
    },
  });
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    await page.getByRole('button', { name: 'Select All', exact: true }).click();
    await page.getByText('22 applicants selected, including 2 on other pages').waitFor();
    await page.getByRole('button', { name: 'Approve All' }).click();
    const dialog = page.getByRole('dialog', { name: 'Confirm approval of 22 applicants?' });
    await dialog.getByRole('checkbox').check();
    await dialog.getByRole('button', { name: 'Confirm bulk approval' }).click();
    const summary = page.getByRole('status', { name: 'Decision results' });
    await summary.getByText('Approved 20; rejected 0').waitFor();
    assert.ok((await summary.innerText()).includes('2 applicant(s) were not attempted'));
    await page.getByRole('alert').filter({ hasText: '3 group decisions per minute' }).waitFor();
    assert.equal(fake.state.bulkDecisions.length, 2, 'the refused group is never resent');
  }, VIEW);
});

test('one selected applicant is approved through the individual endpoint after confirmation', async () => {
  const fake = server({ bulkActions: ALL });
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    await page.getByRole('checkbox', { name: 'Select CTU-G ID 7241001' }).check();
    await page.getByRole('button', { name: 'Approve', exact: true }).click();
    const dialog = page.getByRole('dialog', { name: 'Confirm approval?' });
    await dialog.waitFor();
    assert.ok((await dialog.innerText()).includes(STUDENT_SOURCE));
    assert.equal(await dialog.getByRole('button', { name: 'Confirm approval' }).isDisabled(), true);
    await dialog.getByRole('checkbox').check();
    await dialog.getByRole('button', { name: 'Confirm approval' }).click();
    const summary = page.getByRole('status', { name: 'Decision results' });
    await summary.waitFor();
    assert.ok((await summary.innerText()).includes('7241001 — Approved (email queued; delivery not confirmed)'));
    assert.equal(fake.state.bulkDecisions.length, 0);
    assert.equal(fake.state.approvals.length, 1);
    assert.deepEqual(fake.state.approvals[0], {
      id: 6001, body: { eligibility_confirmed: true, eligibility_source: 'ctu_main_system_records' },
      csrf: fake.state.approvals[0].csrf,
    });
    assert.ok(fake.state.approvals[0].csrf);
  }, VIEW);
});

test('an uncertain single approval is reported as unconfirmed and never retried', async () => {
  const fake = server({ bulkActions: ALL, approve: () => 'abort' });
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    await page.getByRole('checkbox', { name: 'Select CTU-G ID 7241002' }).check();
    await page.getByRole('button', { name: 'Approve', exact: true }).click();
    const dialog = page.getByRole('dialog', { name: 'Confirm approval?' });
    await dialog.getByRole('checkbox').check();
    await dialog.getByRole('button', { name: 'Confirm approval' }).click();
    const summary = page.getByRole('status', { name: 'Decision results' });
    await summary.waitFor();
    assert.ok((await summary.innerText()).includes('unconfirmed 1'));
    assert.ok((await summary.innerText()).includes('not retried automatically'));
    assert.equal(fake.state.approvals.length, 1);
  }, VIEW);
});

test('bulk approval confirms the selected count and reports independently queued outcomes', async () => {
  const fake = server({ bulkActions: ALL });
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    await selectAll(page).check();
    await page.getByText('2 applicants selected on this page').waitFor();
    await page.getByRole('button', { name: 'Approve All' }).click();
    const dialog = page.getByRole('dialog', { name: 'Confirm approval of 2 applicants?' });
    await dialog.waitFor();
    assert.ok((await dialog.innerText()).includes('process 2 selected applicants independently'));
    await dialog.getByRole('checkbox').check();
    await dialog.getByRole('button', { name: 'Confirm bulk approval' }).click();
    const summary = page.getByRole('status', { name: 'Decision results' });
    await summary.waitFor();
    assert.ok((await summary.innerText()).includes('Approved 2; rejected 0; skipped 0; failed 0; unconfirmed 0.'));
    assert.ok((await summary.innerText()).includes('7241001 — Approved (email queued; delivery not confirmed)'));
    assert.equal(fake.state.bulkDecisions.length, 1);
    assert.deepEqual(fake.state.bulkDecisions[0].body, {
      action: 'approve', account_ids: [6001, 6002], eligibility_confirmed: true,
    });
    assert.ok(fake.state.bulkDecisions[0].csrf);
  }, VIEW);
});

test('bulk rejection is explicitly irreversible, uses one fixed reason, and reports outcomes', async () => {
  const fake = server({ bulkActions: ALL });
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    await selectAll(page).check();
    await page.getByRole('button', { name: 'Reject All' }).click();
    const dialog = page.getByRole('dialog', { name: 'Confirm rejection of 2 applicants?' });
    await dialog.waitFor();
    assert.ok((await dialog.innerText()).includes('Irreversible'));
    await dialog.getByLabel('Reason for every selected applicant').selectOption('identity_mismatch');
    await dialog.getByRole('button', { name: 'Confirm bulk rejection' }).click();
    const summary = page.getByRole('status', { name: 'Decision results' });
    await summary.waitFor();
    assert.ok((await summary.innerText()).includes('Approved 0; rejected 2; skipped 0; failed 0; unconfirmed 0.'));
    assert.equal(fake.state.bulkDecisions.length, 1);
    assert.deepEqual(fake.state.bulkDecisions[0].body, {
      action: 'reject', account_ids: [6001, 6002], rejection_code: 'identity_mismatch',
    });
    assert.ok(fake.state.bulkDecisions[0].csrf);
  }, VIEW);
});

test('disabled backend approval stays hidden with a frontend flag and approve permission', async () => {
  const fake = server({ actions: '' });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Institutional eligibility', level: 3 }).waitFor();
    assert.equal(await page.getByRole('heading', { name: 'Approve application', level: 3 }).count(), 0);
    assert.equal(fake.state.approvals.length, 0);
  }, at(7001));
});
const focusedText = (page) => page.evaluate(() => document.activeElement?.textContent?.trim() ?? '');
async function until(check, label) {
  for (let i = 0; i < 100; i++) { if (await check()) return; await new Promise((resolve) => setTimeout(resolve, 50)); }
  throw new Error('Timed out waiting for ' + label);
}
async function fillAttestation(page, source = STUDENT_SOURCE) {
  await page.getByLabel('Where you checked eligibility *').selectOption({ label: source });
  await page.getByRole('checkbox').check();
}

test('a reviewer confirms eligibility, sees a confirmation dialog, and approves with exactly one POST', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Approve application', level: 3 }).waitFor();
    const main = await page.locator('main').innerText();
    for (const text of ['Email ownership is verified for the current address.', 'CTU-G Workspace does not verify enrollment',
      'Role to assign', 'Student', 'Fields marked * are required.']) assert.ok(main.toLowerCase().includes(text.toLowerCase()), `missing ${text}`);
    assert.equal(await page.getByRole('button', { name: /reject/i }).count(), 0);
    // The role is read-only text, never a control.
    assert.equal(await page.getByRole('combobox', { name: /role/i }).count(), 0);

    // Submitting without the attestation shows field errors and focuses the first one.
    await page.getByRole('button', { name: 'Approve application' }).click();
    await page.getByText('Choose the source where you checked eligibility.').waitFor();
    assert.ok(await page.getByLabel('Where you checked eligibility *').evaluate((el) => el === document.activeElement));
    assert.equal(await page.getByRole('dialog').count(), 0);
    // The only selectable source is the fixed one for the role.
    const options = await page.getByLabel('Where you checked eligibility *').locator('option').allInnerTexts();
    assert.deepEqual(options, ['Choose the source you checked', STUDENT_SOURCE]);

    await fillAttestation(page);
    const trigger = page.getByRole('button', { name: 'Approve application' });
    await trigger.click();
    const dialog = page.getByRole('dialog', { name: 'Confirm approval?' });
    await dialog.waitFor();
    assert.equal(await focusedText(page), 'Cancel');
    const dialogText = await dialog.innerText();
    assert.ok(dialogText.includes('Approve Maria Luz Santos (CTU-G ID 7241001) as a Student?'));
    assert.ok(dialogText.includes('It is audited and cannot be undone here.'));

    // Escape closes it, focus returns to the trigger, and nothing was sent.
    await page.keyboard.press('Escape');
    await until(async () => (await page.getByRole('dialog').count()) === 0, 'dialog closed');
    assert.equal(await focusedText(page), 'Approve application');
    assert.equal(fake.state.approvals.length, 0);

    // Cancel does the same.
    await trigger.click();
    await dialog.getByRole('button', { name: 'Cancel' }).click();
    assert.equal(await focusedText(page), 'Approve application');
    assert.equal(fake.state.approvals.length, 0);

    const listsBefore = fake.state.lists;
    await trigger.click();
    await dialog.getByRole('button', { name: 'Confirm approval' }).click();
    const done = page.getByRole('heading', { name: 'Application approved', level: 2 });
    await done.waitFor();
    assert.ok(await done.evaluate((el) => el === document.activeElement), 'focus moves to the result');
    const result = await page.locator('main').innerText();
    assert.ok(result.includes('is now active with the Student role'));
    assert.ok(result.includes('depends on the permissions set for the Student role'));
    assert.ok(result.includes('An approval email has been queued for delivery. Delivery happens separately and is not confirmed here.'));
    assert.deepEqual(fake.state.approvals, [{ id: 6001, body: { eligibility_confirmed: true, eligibility_source: 'ctu_main_system_records' }, csrf: fake.state.approvals[0].csrf }]);
    assert.ok(fake.state.approvals[0].csrf, 'CSRF header sent');
    await until(() => fake.state.lists > listsBefore, 'list refresh after approval');
    await page.getByRole('button', { name: 'Back to pending applications' }).click();
    await page.getByRole('table').waitFor();
  }, at(6001));
});

test('no approval section without the approve permission; an unverified email blocks approval', async () => {
  const readOnly = server({ permissions: [READ] });
  await scene(readOnly.handle, async (page) => {
    await page.getByRole('heading', { name: 'Institutional eligibility' }).waitFor();
    assert.equal(await page.getByRole('heading', { name: 'Approve application' }).count(), 0);
    assert.equal(await page.getByRole('button', { name: /approve/i }).count(), 0);
    assert.ok((await page.locator('main').innerText()).includes('This page is read-only.'));
  }, at(6001));

  const unverified = server({ detailFor: (id) => detail(id, { email_evidence: { state: 'address_changed', verified_at: null }, email: 'new@example.edu' }) });
  await scene(unverified.handle, async (page) => {
    await page.getByRole('heading', { name: 'Approve application' }).waitFor();
    const main = await page.locator('main').innerText();
    assert.ok(main.includes('Email ownership is not verified for the current address.'));
    assert.ok(main.includes('This application cannot be approved.'));
    assert.equal(await page.getByRole('button', { name: 'Approve application' }).count(), 0);
    assert.equal(unverified.state.approvals.length, 0);
  }, at(6002));
});

test('an Instructor cites institutional employment records only', async () => {
  const fake = server({ detailFor: (id) => detail(id, {
    school_id: '0012345', id_label: 'CTU-G ID', requested_role: 'Instructor',
    institutional_check: { subject: 'employment', verified_by_workspace: false },
  }) });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Approve application' }).waitFor();
    const options = await page.getByLabel('Where you checked eligibility *').locator('option').allInnerTexts();
    assert.deepEqual(options, ['Choose the source you checked', 'Institutional employment records']);
    assert.ok((await page.locator('main').innerText()).includes('employment or appointment in institutional employment records'));
    await fillAttestation(page, 'Institutional employment records');
    await page.getByRole('button', { name: 'Approve application' }).click();
    const dialog = page.getByRole('dialog', { name: 'Confirm approval?' });
    assert.ok((await dialog.innerText()).includes('as an Instructor?'));
    await dialog.getByRole('button', { name: 'Confirm approval' }).click();
    await page.getByRole('heading', { name: 'Application approved' }).waitFor();
    assert.equal(fake.state.approvals[0].body.eligibility_source, 'institutional_employment_records');
  }, at(6003));
});

test('refusals show fixed messages, keep the application pending and are never resent', async () => {
  const replies = {
    6101: [[{ error: { code: 'approval_not_allowed', reason: 'email_unverified', message: 'maria.santos@example.edu' } }, 409], 'Approval was refused: the email address is not verified.', true],
    6102: [[{ error: { code: 'approval_not_allowed', reason: 'eligibility_unconfirmed', message: 'x' } }, 409], 'Approval was refused: the eligibility confirmation was not accepted.', false],
    6103: [[{ error: { code: 'access_denied', message: 'x' } }, 403], 'You do not have permission to approve applications.', false],
    6104: [[{ error: { code: 'rate_limited', message: 'x' } }, 429], 'Too many requests.', false],
    6105: [[{ error: { code: 'review_unavailable', message: 'x' } }, 503], 'Approval is not available right now.', false],
  };
  const fake = server({ approve: (id) => replies[id][0] });
  await scene(fake.handle, async (page) => {
    for (const [id, [, title, reload]] of Object.entries(replies)) {
      await page.goto(new URL(page.url()).origin + at(id));
      await page.getByRole('heading', { name: 'Approve application' }).waitFor();
      await fillAttestation(page);
      await page.getByRole('button', { name: 'Approve application' }).click();
      await page.getByRole('dialog').getByRole('button', { name: 'Confirm approval' }).click();
      const alert = page.getByRole('alert').filter({ hasText: title });
      await alert.waitFor();
      assert.ok(await alert.evaluate((el) => el === document.activeElement), `${id} focus on the message`);
      assert.equal(await page.getByRole('dialog').count(), 0);
      assert.equal(await page.getByRole('button', { name: 'Reload application' }).count(), reload ? 1 : 0, `${id} reload`);
      const main = await page.locator('main').innerText();
      assert.ok(!main.includes('Application approved') && !main.includes('maria.santos@example.edu x'), `${id}`);
      await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor(); // 403 never signs out
      assert.equal(fake.state.approvals.filter((a) => a.id === Number(id)).length, 1, `${id} sent once`);
    }
    // eligibility_unconfirmed clears the confirmation so it must be given again.
    await page.goto(new URL(page.url()).origin + at(6102));
    await page.getByRole('heading', { name: 'Approve application' }).waitFor();
    await fillAttestation(page);
    await page.getByRole('button', { name: 'Approve application' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Confirm approval' }).click();
    await page.getByRole('alert').waitFor();
    assert.equal(await page.getByRole('checkbox').isChecked(), false);
  }, VIEW);
});

test('a stale application (404) shows that it is no longer pending', async () => {
  const fake = server({ approve: () => [{ error: { code: 'request_unavailable', message: 'x' } }, 404] });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Approve application' }).waitFor();
    await fillAttestation(page);
    await page.getByRole('button', { name: 'Approve application' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Confirm approval' }).click();
    await page.getByRole('alert').filter({ hasText: 'This application is no longer pending.' }).waitFor();
    assert.equal(fake.state.approvals.length, 1);
  }, at(6201));
});

test('an uncertain result locks approval until the application is re-read, and nothing is replayed', async () => {
  const fake = server({ approve: () => 'abort' });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Approve application' }).waitFor();
    await fillAttestation(page);
    await page.getByRole('button', { name: 'Approve application' }).click();
    await page.getByRole('dialog').getByRole('button', { name: 'Confirm approval' }).click();
    await page.getByRole('alert').filter({ hasText: 'We could not confirm whether the application was approved.' }).waitFor();
    assert.ok(await page.getByRole('button', { name: 'Approve application' }).isDisabled());
    assert.ok((await page.locator('main').innerText()).includes('Approval is paused until you reload the application.'));
    await new Promise((resolve) => setTimeout(resolve, 500));
    assert.equal(fake.state.approvals.length, 1, 'never replayed');
    const reads = fake.state.details.length;
    await page.getByRole('button', { name: 'Reload application' }).click();
    await until(() => fake.state.details.length > reads, 'detail re-read');
    await page.getByRole('heading', { name: 'Approve application' }).waitFor();
    assert.ok(!(await page.getByRole('button', { name: 'Approve application' }).isDisabled()));
    assert.equal(fake.state.approvals.length, 1);
  }, at(6301));
});

test('while the request is in flight the dialog cannot be dismissed or submitted twice', async () => {
  let release;
  const held = new Promise((resolve) => { release = resolve; });
  const fake = server({ approve: async (id) => { await held; return [{ account_id: id, status: 'Approved', notification: 'queued' }]; } });
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'Approve application' }).waitFor();
    await fillAttestation(page);
    await page.getByRole('button', { name: 'Approve application' }).click();
    const dialog = page.getByRole('dialog', { name: 'Confirm approval?' });
    const confirm = dialog.getByRole('button', { name: 'Confirm approval' });
    await confirm.click();
    await dialog.getByRole('button', { name: 'Approving…' }).waitFor();
    assert.ok(await dialog.getByRole('button', { name: 'Approving…' }).isDisabled());
    assert.ok(await dialog.getByRole('button', { name: 'Cancel' }).isDisabled());
    await page.keyboard.press('Escape');
    assert.equal(await dialog.count(), 1, 'Escape ignored while busy');
    await until(() => fake.state.approvals.length === 1, 'one POST');
    release();
    await page.getByRole('heading', { name: 'Application approved' }).waitFor();
    assert.equal(fake.state.approvals.length, 1);
  }, at(6401));
});

test('responsive 360–1440px in Light, System-dark and Dark with composited AA contrast, dialog included', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    for (const [preference, scheme] of [['light', 'light'], ['system', 'dark'], ['dark', 'dark']]) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate((value) => localStorage.setItem('ctug-theme', value), preference);
      for (const width of [360, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await page.goto(new URL(page.url()).origin + at(6501));
        await page.getByRole('heading', { name: 'Approve application' }).waitFor();
        // Show a field error too, so its color is checked.
        await page.getByRole('button', { name: 'Approve application' }).click();
        await page.getByText('Choose the source where you checked eligibility.').waitFor();
        let layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
        assert.ok(layout.scroll <= layout.width, `${preference} ${width}px overflow ${layout.scroll}`);
        const selector = `${DASHBOARD_TEXT}, main li span, main h4, main legend, dialog h3, dialog p, dialog button`;
        for (const { text, ratio } of await contrastReport(page, selector)) {
          assert.ok(ratio >= 4.5, `${preference} ${width}px "${text}" ${ratio.toFixed(2)}`);
        }
        await fillAttestation(page);
        await page.getByRole('button', { name: 'Approve application' }).click();
        const box = await page.getByRole('dialog').boundingBox();
        assert.ok(box && box.x >= 0 && box.x + box.width <= width, `${preference} ${width}px dialog fits`);
        layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
        assert.ok(layout.scroll <= layout.width, `${preference} ${width}px overflow with dialog`);
        for (const { text, ratio } of await contrastReport(page, selector)) {
          assert.ok(ratio >= 4.5, `${preference} ${width}px dialog "${text}" ${ratio.toFixed(2)}`);
        }
        await page.keyboard.press('Escape');
      }
    }
    assert.equal(fake.state.approvals.length, 0);
  }, VIEW);
});
