// Dashboard Shell v0.1 (docs/design): one shared shell, permission-driven navigation, header,
// breadcrumbs, user menu, drawer and responsive/theme checks. Every API call is mocked.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';

process.env.VITE_WORKSPACE_REGISTRATION_REVIEW_LIST_ENABLED = '1';

const READ = 'accounts.registration_requests.read';
const GOVERNANCE = ['access_control.catalogue.read', 'access_control.role_permissions.manage',
  'access_control.account_permissions.manage', 'access_control.effective_permissions.inspect',
  'access_control.audit.read', 'access_control.diagnostics.read', 'access_control.admin_assignments.manage'];
const account = (roles, permissions) => ({ authenticated: true, account: { school_id: '7241001', roles }, permissions });
const schoolAdmin = account(['Admin'], [READ, 'access_control.role_assignments.ordinary.manage', 'access_control.audit.school.read']);
const superAdmin = account(['Admin', 'Technical Super Admin'], [READ, ...GOVERNANCE]);
const student = account(['Student'], []);

function server(session) {
  return ({ path, respond, route }) => {
    if (path.endsWith('/session/')) return respond(session);
    if (path === '/api/v1/admin/registration-requests/') return respond({ results: [], page: 1, page_size: 20, has_next: false });
    return route.abort('failed');
  };
}

const sidebarGroups = (page) => page.locator('nav[aria-label="Dashboard navigation"] [role="group"] > p')
  .evaluateAll((nodes) => nodes.map((node) => node.textContent.trim()));
const sidebarLinks = (page) => page.locator('nav[aria-label="Dashboard navigation"] a')
  .evaluateAll((nodes) => nodes.map((node) => node.textContent.replace('Soon', '').trim()));

test('School Admin: one shell, Overview and Account operations only, no governance links', async () => {
  await scene(server(schoolAdmin), async (page) => {
    await page.getByRole('heading', { name: 'Dashboard', level: 1 }).waitFor();
    assert.deepEqual(await sidebarGroups(page), ['Overview', 'Account operations']);
    assert.deepEqual(await sidebarLinks(page), ['Dashboard', 'Applicant reviews']);
    for (const name of ['Role permissions', 'Account overrides', 'Permission catalogue', 'Access audit logs', 'System health']) {
      assert.equal(await page.getByRole('link', { name }).count(), 0, name);
    }
    // Header: brand, academic-period context and profile menu; no unfinished Search or Alerts.
    const header = page.locator('header');
    assert.ok((await header.innerText()).includes('CTU-G Workspace'));
    assert.ok((await header.innerText()).includes('Academic period: not yet configured'));
    assert.equal(await page.getByRole('searchbox').count(), 0);
    assert.equal(await page.getByRole('button', { name: /notification|alert/i }).count(), 0);
    // Exactly one h1, provided by the shell.
    assert.equal(await page.locator('h1').count(), 1);
    // Pending applications widget is a link card without a count (D-33).
    const widget = page.locator('article').filter({ hasText: 'Pending applications' });
    assert.ok(!/\d/.test(await widget.innerText()));
    await widget.getByRole('button', { name: 'Open applicant reviews' }).click();
    await page.getByRole('heading', { name: 'Applicant reviews', level: 1 }).waitFor();
    const crumbs = await page.getByRole('navigation', { name: 'Breadcrumb' }).innerText();
    assert.equal(crumbs.replace(/\s+/g, ' ').trim(), 'Dashboard / Account operations / Applicant reviews');
    const current = await page.locator('nav[aria-label="Breadcrumb"] [aria-current="page"]').innerText();
    assert.equal(current.replace(/[\s/]+/g, ' ').trim(), 'Applicant reviews');
  }, '/dashboard');
});

test('Super Admin inherits School Admin operations and adds governance groups through permissions', async () => {
  await scene(server(superAdmin), async (page) => {
    await page.getByRole('heading', { name: 'Dashboard', level: 1 }).waitFor();
    assert.deepEqual(await sidebarGroups(page),
      ['Overview', 'Account operations', 'Access control', 'Security & audit', 'System operations']);
    const links = await sidebarLinks(page);
    assert.equal(new Set(links).size, links.length, 'deduplicated');
    // Unfinished governance modules are labelled and open a not-available page, never a working one.
    const roleLink = page.getByRole('link', { name: /Role permissions/ });
    assert.ok((await roleLink.innerText()).includes('Soon'));
    await roleLink.click();
    await page.getByRole('heading', { name: 'This module is not available yet' }).waitFor();
    assert.ok((await page.locator('main').innerText()).includes('Soon'));
  }, '/dashboard');
});

test('a direct URL to a module without permission is denied without revealing it', async () => {
  await scene(server(schoolAdmin), async (page) => {
    await page.getByRole('heading', { name: 'Section unavailable', level: 1 }).waitFor();
    await page.getByRole('heading', { name: 'This section is unavailable' }).waitFor();
    const main = await page.locator('main').innerText();
    assert.ok(!main.includes('Role permissions') && !main.includes('Permissions granted'));
    await page.getByRole('button', { name: 'Return to dashboard' }).click();
    await page.getByRole('heading', { name: 'Dashboard', level: 1 }).waitFor();
  }, '/dashboard?view=role-permissions');
});

test('an account with no modules sees the explanatory empty state', async () => {
  await scene(server(student), async (page) => {
    await page.getByRole('heading', { name: 'No modules are available to your account yet' }).waitFor();
    assert.deepEqual(await sidebarGroups(page), ['Overview']);
    assert.equal(await page.getByRole('heading', { name: 'At a glance' }).count(), 0);
  }, '/dashboard');
});

test('user menu: keyboard open, arrow navigation, Escape returns focus, items navigate', async () => {
  await scene(server(schoolAdmin), async (page) => {
    const trigger = page.getByRole('button', { name: /Account menu for 7241001/ });
    await trigger.focus();
    await page.keyboard.press('ArrowDown');
    await page.getByRole('menu', { name: 'Account' }).waitFor();
    const focused = () => page.evaluate(() => document.activeElement?.textContent?.trim());
    assert.equal(await focused(), 'My profile');
    await page.keyboard.press('ArrowDown');
    assert.equal(await focused(), 'Sign out of Workspace');
    await page.keyboard.press('ArrowDown');
    assert.equal(await focused(), 'My profile');
    await page.keyboard.press('Escape');
    assert.equal(await page.getByRole('menu').count(), 0);
    assert.ok(await trigger.evaluate((element) => element === document.activeElement));
    await trigger.click();
    await page.getByRole('menuitem', { name: 'My profile' }).click();
    await page.getByRole('heading', { name: 'My profile', level: 1 }).waitFor();
    assert.equal(await page.getByRole('menu').count(), 0);
  }, '/dashboard');
});

test('mobile drawer traps focus, closes on Escape and returns focus to the menu button', async () => {
  await scene(server(schoolAdmin), async (page) => {
    await page.setViewportSize({ width: 390, height: 844 });
    const open = page.getByRole('button', { name: 'Open navigation' });
    await open.click();
    const close = page.getByRole('button', { name: 'Close navigation', exact: true });
    assert.ok(await close.evaluate((element) => element === document.activeElement));
    const insideSidebar = () => page.evaluate(() => Boolean(document.activeElement?.closest('#workspace-sidebar')));
    for (let i = 0; i < 12; i++) { await page.keyboard.press('Tab'); assert.ok(await insideSidebar(), `tab ${i}`); }
    for (let i = 0; i < 4; i++) { await page.keyboard.press('Shift+Tab'); assert.ok(await insideSidebar(), `shift-tab ${i}`); }
    assert.ok(await page.locator('main').evaluate((element) => element.closest('[inert]') !== null));
    await page.keyboard.press('Escape');
    await page.waitForFunction(() => document.activeElement?.getAttribute('aria-label') === 'Open navigation');
    assert.equal(await open.getAttribute('aria-expanded'), 'false');
    // Navigating from the drawer closes it.
    await open.click();
    await page.getByRole('link', { name: 'Applicant reviews' }).click();
    await page.getByRole('heading', { name: 'Applicant reviews', level: 1 }).waitFor();
    assert.equal(await open.getAttribute('aria-expanded'), 'false');
  }, '/dashboard');
});

test('desktop sidebar collapses to an icon rail and keeps accessible names', async () => {
  await scene(server(schoolAdmin), async (page) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    const toggle = page.getByRole('button', { name: 'Collapse sidebar' });
    assert.equal(await toggle.getAttribute('aria-expanded'), 'true');
    await toggle.click();
    const expand = page.getByRole('button', { name: 'Expand sidebar' });
    assert.equal(await expand.getAttribute('aria-expanded'), 'false');
    const width = (value) => page.waitForFunction((expected) => Math.round(document.querySelector('#workspace-sidebar').getBoundingClientRect().width) === expected, value);
    await width(80);
    await page.getByRole('link', { name: 'Applicant reviews' }).click();
    await page.getByRole('heading', { name: 'Applicant reviews', level: 1 }).waitFor();
    await expand.click();
    await width(272);
  }, '/dashboard');
});

test('responsive 360–1440px in Light, System-dark and Dark: no page overflow, AA text in header and sidebar', async () => {
  await scene(server(superAdmin), async (page) => {
    for (const [preference, scheme] of [['light', 'light'], ['system', 'dark'], ['dark', 'dark']]) {
      await page.emulateMedia({ colorScheme: scheme });
      await page.evaluate((value) => localStorage.setItem('ctug-theme', value), preference);
      for (const width of [360, 768, 1024, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await page.reload();
        await page.getByRole('heading', { name: 'Dashboard', level: 1 }).waitFor();
        const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
        assert.ok(layout.scroll <= layout.width, `${preference} ${width}px: overflow ${layout.scroll}`);
        const sidebarShown = await page.locator('#workspace-sidebar').evaluate((element) => element.getBoundingClientRect().left >= 0);
        assert.equal(sidebarShown, width >= 1024, `${preference} ${width}px sidebar`);
        if (width < 1024) await page.getByRole('button', { name: 'Open navigation' }).click();
        const ratios = await page.evaluate(() => {
          const rgb = (value) => value.match(/[\d.]+/g).slice(0, 4).map(Number);
          const lum = ([r, g, b]) => {
            const c = [r, g, b].map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
            return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
          };
          // Solid background behind an element; the sidebar uses a gradient, so use its darkest/lightest stop.
          const background = (element) => {
            for (let node = element; node; node = node.parentElement) {
              const style = getComputedStyle(node);
              if (style.backgroundImage.includes('gradient')) {
                const stops = style.backgroundImage.match(/rgba?\([^)]+\)/g).map(rgb);
                return stops.reduce((best, stop) => (lum(stop) > lum(best) ? stop : best));
              }
              const color = rgb(style.backgroundColor);
              if (color.length < 4 || color[3] > 0.5) return color;
            }
            return [255, 255, 255];
          };
          const nodes = [...document.querySelectorAll('header p, header span, #workspace-sidebar p, #workspace-sidebar a span, nav[aria-label="Breadcrumb"] li, main h1')]
            .filter((element) => element.getClientRects().length && element.textContent.trim() && !element.closest('.sr-only'));
          return nodes.map((element) => {
            const a = lum(rgb(getComputedStyle(element).color)); const b = lum(background(element));
            return { text: element.textContent.trim().slice(0, 30), ratio: (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05) };
          });
        });
        for (const { text, ratio } of ratios) assert.ok(ratio >= 4.5, `${preference} ${width}px "${text}" ${ratio.toFixed(2)}`);
        if (width < 1024) await page.keyboard.press('Escape');
      }
    }
  }, '/dashboard');
});
