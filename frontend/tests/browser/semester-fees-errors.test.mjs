// Semester organizational fee UI. Every API call is mocked; the fee switches are on for this Vite only.
// No real database, session, fee or student record changes.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport, DASHBOARD_TEXT } from './contrastProbe.mjs';

process.env.VITE_WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED = '1';
process.env.VITE_WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED = '1';

const VIEW = '/dashboard?view=semester-fees';
const API = '/api/v1/finance/semester-fees/';
const semester = { semester_id: 9, term: 'first', label: 'First semester', status: 'Draft', school_year_id: 2, school_year_label: '2026–2027' };
const rev = (n, amount, status, overrides = {}) => ({ revision_id: n, revision_number: n, currency: 'PHP', amount, status, version: 1,
  change_reason: null, configured_by: 'You', configured_at: '2026-11-25T05:00:00+00:00', approved_by: status === 'Draft' ? null : 'You',
  approved_at: status === 'Draft' ? null : '2026-11-25T06:00:00+00:00', superseded_at: status === 'Superseded' ? '2026-11-25T07:00:00+00:00' : null,
  withdrawn_at: null, ...overrides });

function server({ permissions = ['finance.fee_schedule.manage'], denied = false, features = { configuration: true, approval: true }, approved = null } = {}) {
  const state = { draft: null, approved, history: approved ? [approved] : [], posts: [] };
  const snapshot = () => ({ semester, schedule_id: 1, schedule_version: 1,
    state: state.approved ? (state.draft ? 'approved_with_draft' : 'approved') : state.draft ? 'draft' : 'not_configured',
    current_approved: state.approved, draft: state.draft, revisions: [...(state.draft ? [state.draft] : []), ...state.history],
    editable: true, reason_required: Boolean(state.approved),
    readiness: state.approved ? { key: 'approved_fee', status: 'ready', reason: '' }
      : { key: 'approved_fee', status: 'missing', reason: state.draft ? 'fee_awaiting_approval' : 'no_fee_configured' }, features });
  const handle = async ({ path, request, respond }) => {
    if (path.endsWith('/session/')) return respond({ authenticated: true, account: { school_id: 'ADMIN-001', roles: ['Admin'] }, permissions });
    if (denied) return respond({ error: { code: 'access_denied', message: 'x' } }, 403);
    if (request.method() === 'POST') {
      const body = request.postDataJSON();
      state.posts.push({ path, body, csrf: request.headers()['x-csrftoken'] });
      if (path === `${API}9/draft/`) {
        const number = state.history.length + 1;
        state.draft = rev(number, body.amount, 'Draft', { change_reason: body.change_reason ?? null, version: (state.draft?.version ?? 0) + 1 });
        return respond(snapshot());
      }
      if (path === `${API}9/approval/`) {
        if (state.approved) state.history = state.history.map((r) => (r.status === 'Approved' ? { ...r, status: 'Superseded', superseded_at: '2026-11-25T07:00:00+00:00' } : r));
        state.approved = { ...state.draft, status: 'Approved', approved_by: 'You', approved_at: '2026-11-25T08:00:00+00:00' };
        state.history = [state.approved, ...state.history];
        state.draft = null;
        return respond(snapshot());
      }
    }
    if (path === API) return respond({ results: [{ semester, state: snapshot().state, approved_amount: state.approved?.amount ?? null,
      current_revision_number: state.approved?.revision_number ?? null }], features, viewer: 'You' });
    if (path === `${API}9/`) return respond(snapshot());
    if (path === `${API}9/approval/`) {
      const zero = state.draft?.amount === '0.00';
      return respond({ semester, proposed: state.draft, current_approved: state.approved,
        impact: state.approved ? { status: 'not_applicable', count: null, reason: 'semester_never_active' }
          : { status: 'not_applicable', count: null, reason: 'no_previous_rate' },
        warnings: [...(zero ? ['zero_amount'] : []), ...(state.approved ? ['replaces_approved_rate'] : [])],
        blockers: features.approval ? [] : ['feature_disabled'], feature_enabled: features.approval, can_confirm: features.approval });
    }
    return respond({ error: { code: 'not_found' } }, 404);
  };
  return { state, handle };
}

const open = async (page) => {
  await page.goto(new URL(page.url()).origin + VIEW);
  await page.getByLabel('Semester', { exact: true }).waitFor();
};

test('a refused account sees an explanation and no fee controls', async () => {
  const fake = server({ denied: true });
  await scene(fake.handle, async (page) => {
    await page.getByText('Semester fees are set by the School Admin').waitFor();
    assert.ok((await page.locator('main').innerText()).includes('School Admin responsibility'));
    assert.equal(await page.getByRole('button', { name: /Save draft|Approve|Review approval/ }).count(), 0);
  }, VIEW);
  const hidden = server({ permissions: ['finance.fee_schedule.read'] });
  await scene(hidden.handle, async (page) => {
    await page.getByText('This section is unavailable').waitFor();
  }, VIEW);
});

test('a missing fee is a warning; Drafts validate exactly and never approve', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByText('No fee is configured.').waitFor();
    const amount = page.getByLabel('Full organizational fee (PHP)');
    await page.getByRole('button', { name: 'Save draft' }).click();
    await page.getByText('Enter the fee amount. ₱0.00 must be entered explicitly.').waitFor();
    assert.equal(await page.evaluate(() => document.activeElement?.getAttribute('inputmode')), 'decimal');
    for (const bad of ['1,500', '-5', '1500.001']) {
      await amount.fill(bad);
      await page.getByRole('button', { name: 'Save draft' }).click();
      await page.getByText('Enter the full fee in pesos, from 0.00 to 100,000.00, with up to two decimal places.').waitFor();
    }
    assert.equal(fake.state.posts.length, 0);
    await amount.fill('1500');
    await page.getByRole('button', { name: 'Save draft' }).click();
    await page.getByRole('status').filter({ hasText: 'Draft saved: ₱1,500.00. It is not approved yet.' }).waitFor();
    assert.deepEqual(fake.state.posts.map((p) => p.body), [{ amount: '1500.00', expected_draft_version: null }]);
    assert.ok(fake.state.posts[0].csrf);
    await page.getByText('Not ready: the Draft fee has not been approved.').waitFor();
  }, VIEW);
});

test('approving ₱0.00 needs the warning review and its own confirmation', async () => {
  const fake = server();
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByLabel('Full organizational fee (PHP)').fill('0');
    await page.getByRole('button', { name: 'Save draft' }).click();
    await page.getByRole('button', { name: 'Review approval' }).click();
    const dialog = page.getByRole('dialog', { name: 'Approve this semester fee?' });
    await dialog.getByText('The full fee for this semester will be ₱0.00.').waitFor();
    const confirm = dialog.getByRole('button', { name: 'Approve fee' });
    assert.equal(await confirm.isDisabled(), true);
    await dialog.getByLabel('I reviewed these warnings').check();
    assert.equal(await confirm.isDisabled(), true);  // zero still needs its own confirmation
    await dialog.getByLabel('I confirm the full organizational fee for this semester is ₱0.00').check();
    assert.ok((await dialog.innerText()).includes('Approval does not activate the semester'));
    await confirm.click();
    await page.getByRole('status').filter({ hasText: 'The semester fee of ₱0.00 was approved.' }).waitFor();
    assert.deepEqual(fake.state.posts[1].body, { revision_id: 1, expected_version: 1, expected_current_approved_revision_id: null,
      acknowledged_warnings: ['zero_amount'], confirmed: true, confirm_zero_amount: true });
    await page.getByText('Ready: an approved fee is available for semester activation.').waitFor();
  }, VIEW);
});

test('revisions need a reason and keep the previous approved fee in history', async () => {
  const fake = server({ approved: rev(1, '1500.00', 'Approved') });
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByLabel('Full organizational fee (PHP)').fill('1750');
    await page.getByRole('button', { name: 'Save draft' }).click();
    await page.getByText('Explain the change in 10 to 500 characters.').waitFor();
    await page.getByLabel('Reason for revising the approved fee').fill('Council resolution revised the fee.');
    await page.getByRole('button', { name: 'Save draft' }).click();
    await page.getByRole('button', { name: 'Review approval' }).click();
    const dialog = page.getByRole('dialog', { name: 'Approve this semester fee?' });
    await dialog.getByText('This replaces the current approved fee.').waitFor();
    await dialog.getByLabel('I reviewed these warnings').check();
    await dialog.getByRole('button', { name: 'Approve fee' }).click();
    // Revision #2 is already listed as a Draft before approval: wait for the confirmed, reloaded state.
    await page.getByRole('status').filter({ hasText: 'The semester fee of ₱1,750.00 was approved.' }).waitFor();
    const history = page.getByRole('list', { name: 'Fee revisions' });
    await history.getByText('Superseded', { exact: true }).waitFor();
    const text = await history.innerText();
    assert.ok(text.includes('Revision #1 · ₱1,500.00') && text.includes('Superseded'), text);
    assert.ok(!text.includes('ADMIN-001'));
  }, VIEW);
});

test('with server approval switched off the review is read-only', async () => {
  const fake = server({ features: { configuration: true, approval: false } });
  await scene(fake.handle, async (page) => {
    await open(page);
    await page.getByLabel('Full organizational fee (PHP)').fill('1500');
    await page.getByRole('button', { name: 'Save draft' }).click();
    await page.getByRole('button', { name: 'Review approval' }).click();
    const dialog = page.getByRole('dialog', { name: 'Approve this semester fee?' });
    await dialog.getByText('Feature unavailable').waitFor();
    assert.equal(await dialog.getByRole('button', { name: 'Approve fee' }).isDisabled(), true);
    await page.keyboard.press('Escape');
    await dialog.waitFor({ state: 'hidden' });
    assert.equal(fake.state.posts.filter((p) => p.path.endsWith('/approval/')).length, 0);
  }, VIEW);
});

test('semester fees keep AA contrast and fit 360–1440px in all three themes', async () => {
  const fake = server({ approved: rev(1, '1500.00', 'Approved') });
  await scene(fake.handle, async (page) => {
    for (const [preference, scheme] of [['light', 'light'], ['system', 'dark'], ['dark', 'dark']]) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate((v) => localStorage.setItem('ctug-theme', v), preference);
      for (const width of [360, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await open(page);
        await page.getByRole('list', { name: 'Fee revisions' }).waitFor();
        await page.waitForFunction(() => document.getAnimations().length === 0);
        const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
        assert.ok(layout.scroll <= layout.width, `${preference} ${width}px overflow ${layout.scroll}`);
        for (const { text, ratio } of await contrastReport(page, `${DASHBOARD_TEXT}, main li p, main li span, main dd, main dt`)) {
          assert.ok(ratio >= 4.5, `${preference} ${width}px "${text}" ${ratio.toFixed(2)}`);
        }
      }
    }
  }, VIEW);
});
