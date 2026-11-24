// WF-02.01 P-07: read-only pending applications on the real dashboard; every API call is mocked.
// The frontend list switch is turned on for this isolated Vite process only.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport } from './contrastProbe.mjs';

process.env.VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED = '1';

const READ = 'accounts.registration_requests.read';
const LIST = '/api/v1/admin/registration-requests/';
const ENDED = 'Your session has ended. Sign in again to continue.';
const PRIVATE_EMAIL = 'private.applicant@example.edu';
const admin = { authenticated: true, account: { school_id: 'ADMIN-001', roles: ['Admin'] }, permissions: [READ] };
const anonymous = { authenticated: false };

const row = (n, overrides = {}) => ({
  account_id: 5000 + n, school_id: `72400${String(n).padStart(2, '0')}`,
  full_name: `Applicant ${n} Santos`, requested_role: n % 2 ? 'Instructor' : 'Student',
  created_at: '2026-11-10T09:15:00+08:00', email_verified: n % 3 !== 0, ...overrides,
});
const page = (results, number = 1, hasNext = false) => ({ results, page: number, page_size: 20, has_next: hasNext });

function server(listResponder) {
  const state = { session: admin, lists: [] };
  const handle = ({ path, request, respond, route }) => {
    if (path.endsWith('/session/')) return respond(state.session);
    if (path === LIST && request.method() === 'GET') {
      const query = new URL(request.url()).search;
      state.lists.push(query);
      const [body, status = 200] = listResponder(query, state);
      return respond(body, status);
    }
    return route.abort('failed');
  };
  return { state, handle };
}

const VIEW = '/dashboard?view=registration-review';
async function until(check, label) {
  for (let i = 0; i < 100; i++) { if (check()) return; await new Promise((resolve) => setTimeout(resolve, 50)); }
  throw new Error('Timed out waiting for ' + label);
}
const heading = (page) => page.getByRole('heading', { name: 'Pending applications', level: 2 });
// React StrictMode (dev server) runs the mount effect twice; the first response is discarded.
// Tests therefore assert on requests made after the initial render.
const initialOnly = (lists) => lists.length >= 1 && lists.every((query) => query === '?page=1&status=Pending');

test('an authorized reviewer sees the list and no decision controls without decision availability', async () => {
  const fake = server(() => [page([
    row(1),
    row(3, { full_name: null }),
    row(4, { school_id: '7240004', full_name: 'Maria Luz Santos Jr.' }),
  ])]);
  await scene(fake.handle, async (page) => {
    await heading(page).waitFor();
    const table = page.getByRole('table');
    await table.waitFor();
    const text = await table.innerText();
    for (const expected of ['7240001', 'Applicant 1 Santos', 'Instructor', 'Nov 10, 2026', 'Email verified',
      'No email proof on record', 'Not recorded', 'Maria Luz Santos Jr.', 'Pending review']) {
      assert.ok(text.includes(expected), `missing ${expected}`);
    }
    assert.equal(await page.locator('time[datetime="2026-11-10T09:15:00+08:00"]').first().count(), 1);
    // Without decision availability there are no selection checkboxes and no decision toolbar.
    assert.equal(await page.getByRole('checkbox').count(), 0);
    for (const name of [/^Approve/, /^Reject/, 'Unselect All']) {
      assert.equal(await page.getByRole('button', { name }).count(), 0);
    }
    for (const name of [/delete/i, /confirm/i]) {
      assert.equal(await page.getByRole('button', { name }).count(), 0);
    }
    const body = await page.locator('body').innerText();
    assert.ok(!body.includes(PRIVATE_EMAIL) && !/password|token|hash/i.test(body));
    // Navigation item is live (no "Soon") and was shown from the exact permission hint.
    const nav = page.getByRole('link', { name: 'Applicant reviews' }).first();
    assert.equal(await nav.getAttribute('aria-current'), 'page');
    assert.ok(!(await nav.innerText()).includes('Soon'));
    assert.ok(initialOnly(fake.state.lists), JSON.stringify(fake.state.lists));
  }, VIEW);
});

test('search is debounced, dropdowns apply at once, and every control combines into one server query', async () => {
  const fake = server((query) => [page(query.includes('q=') ? [row(2)] : [row(1), row(2)])]);
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    assert.equal(await page.getByRole('button', { name: 'Apply filters' }).count(), 0);
    const baseline = fake.state.lists.length;
    const search = page.getByLabel('Search CTU-G ID or name');
    await search.pressSequentially('  santos ', { delay: 40 });
    await until(() => fake.state.lists.length === baseline + 1, 'one debounced search request');
    await page.waitForTimeout(500);
    assert.equal(fake.state.lists.length, baseline + 1, 'typing sends one request after the pause, not one per keystroke');
    assert.equal(fake.state.lists.at(-1), '?page=1&status=Pending&q=santos');
    await page.getByLabel('Requested role').selectOption('Instructor');
    await until(() => fake.state.lists.at(-1) === '?page=1&status=Pending&q=santos&role=Instructor', 'role applies at once');
    await page.getByLabel('Email proof').selectOption('legacy');
    await until(() => fake.state.lists.at(-1) === '?page=1&status=Pending&q=santos&role=Instructor&proof=legacy', 'proof applies at once');
    await page.getByLabel('Sort by').selectOption('-submitted');
    await until(() => fake.state.lists.at(-1) === '?page=1&status=Pending&q=santos&role=Instructor&proof=legacy&sort=-submitted', 'sort applies at once');
    await page.getByText('7240002').first().waitFor();
    assert.equal(await search.inputValue(), '  santos ', 'the input is never rewritten while typing');
    // Enter applies immediately; clearing the search restores the unsearched results.
    await search.fill('7240');
    await search.press('Enter');
    await until(() => fake.state.lists.at(-1) === '?page=1&status=Pending&q=7240&role=Instructor&proof=legacy&sort=-submitted', 'Enter applies');
    await search.fill('');
    await until(() => fake.state.lists.at(-1) === '?page=1&status=Pending&role=Instructor&proof=legacy&sort=-submitted', 'cleared search');
  }, VIEW);
});

test('invalid search text is refused in the browser without a request', async () => {
  const fake = server(() => [page([row(1)])]);
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    const baseline = fake.state.lists.length;
    const search = page.getByLabel('Search CTU-G ID or name');
    await search.fill('Ñame');
    await page.getByRole('alert').filter({ hasText: 'no accents' }).waitFor();
    assert.equal(await search.getAttribute('aria-invalid'), 'true');
    await page.waitForTimeout(400);
    assert.equal(fake.state.lists.length, baseline);
    await page.getByRole('table').waitFor(); // the current results stay
  }, VIEW);
});

test('empty and filtered-empty states are distinct, and Clear filters restores the list', async () => {
  const fake = server(() => [page([])]);
  await scene(fake.handle, async (page) => {
    await page.getByRole('heading', { name: 'No pending applications.' }).waitFor();
    await page.getByLabel('Requested role').selectOption('Student');
    await page.getByRole('heading', { name: 'No applications match these filters.' }).waitFor();
    await page.getByRole('button', { name: 'Clear filters' }).first().click();
    await page.getByRole('heading', { name: 'No pending applications.' }).waitFor();
    assert.equal(fake.state.lists.at(-1), '?page=1&status=Pending');
    assert.equal(await page.getByLabel('Requested role').inputValue(), '');
  }, VIEW);
});

test('a filter change returns to page 1', async () => {
  const fake = server((query) => {
    if (query.includes('page=2')) return [page([row(21)], 2, false)];
    return [page(Array.from({ length: 20 }, (_, i) => row(i + 1)), 1, true)];
  });
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    await page.getByRole('button', { name: 'Next' }).click();
    await until(() => fake.state.lists.at(-1) === '?page=2&status=Pending', 'page 2');
    await page.getByText('Page 2', { exact: true }).waitFor();
    await page.getByLabel('Email proof').selectOption('verified');
    await until(() => fake.state.lists.at(-1) === '?page=1&status=Pending&proof=verified', 'reset to page 1');
    await page.getByText('Page 1', { exact: true }).waitFor();
  }, VIEW);
});

test('pagination follows has_next exactly', async () => {
  const fake = server((query) => query.includes('page=2')
    ? [page([row(21)], 2, false)]
    : [page(Array.from({ length: 20 }, (_, i) => row(i + 1)), 1, true)]);
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    const next = page.getByRole('button', { name: 'Next' });
    const previous = page.getByRole('button', { name: 'Previous' });
    assert.ok(await previous.isDisabled());
    await next.click();
    await page.getByText('Page 2', { exact: true }).waitFor();
    await page.getByText('7240021').first().waitFor();
    assert.ok(await next.isDisabled());
    assert.equal(fake.state.lists.at(-1), '?page=2&status=Pending');
    await previous.click();
    await page.getByText('Page 1', { exact: true }).waitFor();
    assert.equal(fake.state.lists.at(-1), '?page=1&status=Pending');
  }, VIEW);
});

test('an expired session (401) shows the session-ended screen and drops applicant data', async () => {
  const fake = server((_query, state) => { state.session = anonymous; return [{ error: { code: 'authentication_required', message: PRIVATE_EMAIL } }, 401]; });
  await scene(fake.handle, async (page) => {
    await page.getByText(ENDED).waitFor();
    await page.getByRole('heading', { name: 'Sign in required' }).waitFor();
    const body = await page.locator('body').innerText();
    assert.ok(!body.includes('ADMIN-001') && !body.includes(PRIVATE_EMAIL));
  }, VIEW);
});

test('a permission denial (403) shows no records and never signs the reviewer out', async () => {
  const fake = server(() => [{ error: { code: 'access_denied', message: PRIVATE_EMAIL } }, 403]);
  await scene(fake.handle, async (page) => {
    await page.getByRole('alert').filter({ hasText: 'You do not have permission to view applications.' }).waitFor();
    assert.equal(await page.getByRole('table').count(), 0);
    assert.equal(await page.getByRole('button', { name: 'Try again' }).count(), 0);
    await page.getByRole('button', { name: 'Sign out', exact: true }).waitFor();
    assert.equal(await page.getByText(ENDED).count(), 0);
    assert.ok(!(await page.locator('body').innerText()).includes(PRIVATE_EMAIL));
  }, VIEW);
});

test('400, 429, 503 and malformed responses show fixed messages; Try again re-requests once', async () => {
  const cases = [
    [[{ error: { code: 'invalid_request', message: 'x' } }, 400], 'The search or filters could not be used.', false],
    [[{ error: { code: 'rate_limited', message: 'x' } }, 429], 'Too many requests.', true],
    [[{ error: { code: 'review_unavailable', message: PRIVATE_EMAIL } }, 503], 'Pending applications are not available right now.', true],
    [[{ ...page([row(1)]), total: 99 }, 200], 'Applications could not be loaded.', true],
    [[page([{ ...row(1), email: PRIVATE_EMAIL }]), 200], 'Applications could not be loaded.', true],
  ];
  for (const [reply, message, retry] of cases) {
    const fake = server(() => reply);
    await scene(fake.handle, async (page) => {
      await page.getByRole('alert').filter({ hasText: message }).waitFor();
      assert.equal(await page.getByRole('table').count(), 0);
      assert.ok(!(await page.locator('body').innerText()).includes(PRIVATE_EMAIL));
      assert.equal(await page.getByRole('button', { name: 'Try again' }).count(), retry ? 1 : 0);
      if (retry) {
        const baseline = fake.state.lists.length;
        await page.getByRole('button', { name: 'Try again' }).click();
        await until(() => fake.state.lists.length === baseline + 1, 'Try again');
        await page.getByRole('alert').filter({ hasText: message }).waitFor();
      }
    }, VIEW);
  }
});

test('keyboard: the search form is reachable and operable without a pointer', async () => {
  const fake = server(() => [page([row(1)])]);
  await scene(fake.handle, async (page) => {
    await page.getByRole('table').waitFor();
    const baseline = fake.state.lists.length;
    await page.getByLabel('Search CTU-G ID or name').focus();
    const order = [];
    for (let i = 0; i < 3; i++) {
      await page.keyboard.press('Tab');
      order.push(await page.evaluate(() => document.activeElement?.closest('label')?.firstChild?.textContent?.trim()));
    }
    assert.deepEqual(order, ['Requested role', 'Email proof', 'Sort by']);
    await page.getByLabel('Requested role').focus();
    await page.keyboard.press('ArrowDown');
    await until(() => fake.state.lists.length === baseline + 1, 'keyboard change applies');
    await page.getByRole('table').waitFor();
    assert.equal(fake.state.lists.at(-1), '?page=1&status=Pending&role=Student');
  }, VIEW);
});

test('responsive at 360, 768, 1024 and 1440px in Light, System-dark and Dark themes', async () => {
  const fake = server(() => [page([row(1), row(3, { full_name: 'A very long applicant name that must wrap without forcing horizontal scrolling' })])]);
  await scene(fake.handle, async (page) => {
    await heading(page).waitFor();
    const themes = [
      ['light', 'light', ''],
      ['system', 'dark', 'dark'],
      ['dark', 'dark', 'dark theme-black'],
    ];
    for (const [preference, scheme, classes] of themes) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate((value) => localStorage.setItem('ctug-theme', value), preference);
      for (const width of [360, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await page.reload();
        await heading(page).waitFor();
        await page.getByText('7240001').first().waitFor({ state: 'attached' });
        const html = await page.evaluate(() => document.documentElement.className);
        for (const name of classes.split(' ').filter(Boolean)) assert.ok(html.includes(name), `${preference}: ${html}`);
        const layout = await page.evaluate(() => ({
          scroll: document.documentElement.scrollWidth, width: window.innerWidth,
          table: getComputedStyle(document.querySelector('table').parentElement).display,
          cards: getComputedStyle(document.querySelector('ul[aria-label^="Pending applications"]')).display,
        }));
        assert.ok(layout.scroll <= layout.width, `${preference} ${width}px: horizontal page scroll ${layout.scroll}`);
        assert.equal(layout.table === 'none', width < 768, `${preference} ${width}px table display ${layout.table}`);
        assert.equal(layout.cards === 'none', width >= 768, `${preference} ${width}px card display ${layout.cards}`);
        // WCAG AA (composited through every translucent layer) for badges, muted text and the table.
        const ratios = await contrastReport(page, 'main [class*="rounded-full"], main .dashboard-muted, main .dashboard-heading, main td, main th, main label');
        for (const { text, ratio } of ratios) assert.ok(ratio >= 4.5, `${preference} ${width}px "${text}" contrast ${ratio.toFixed(2)}`);
      }
    }
  }, VIEW);
});
