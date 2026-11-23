// Dashboard Shell v0.1 (docs/design): one shared shell, permission-driven navigation, header,
// breadcrumbs, user menu, drawer and responsive/theme checks. Every API call is mocked.
import assert from 'node:assert/strict';
import { test } from 'node:test';
import { scene } from './registrationHarness.mjs';
import { contrastReport, DASHBOARD_TEXT, HERO_RING } from './contrastProbe.mjs';

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

test('School Admin: one shell, Overview and Account management only, no governance links', async () => {
  await scene(server(schoolAdmin), async (page) => {
    await page.getByRole('heading', { name: 'Dashboard', level: 1 }).waitFor();
    assert.deepEqual(await sidebarGroups(page), ['Overview', 'Account management']);
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
    assert.equal(crumbs.replace(/\s+/g, ' ').trim(), 'Dashboard / Account management / Applicant reviews');
    const current = await page.locator('nav[aria-label="Breadcrumb"] [aria-current="page"]').innerText();
    assert.equal(current.replace(/[\s/]+/g, ' ').trim(), 'Applicant reviews');
  }, '/dashboard');
});

test('Super Admin inherits School Admin operations and adds governance groups through permissions', async () => {
  await scene(server(superAdmin), async (page) => {
    await page.getByRole('heading', { name: 'Dashboard', level: 1 }).waitFor();
    assert.deepEqual(await sidebarGroups(page),
      ['Overview', 'Account management', 'Access control', 'Security & audit', 'System operations']);
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

const THEMES = [['light', 'light'], ['system', 'dark'], ['dark', 'dark']];
const WIDTHS = [360, 768, 1024, 1440];

async function useTheme(page, preference, scheme) {
  await page.emulateMedia({ colorScheme: scheme });
  await page.evaluate((value) => localStorage.setItem('ctug-theme', value), preference);
}

test('responsive 360–1440px in Light, System-dark and Dark: no overflow, composited AA text everywhere', async () => {
  await scene(server(superAdmin), async (page) => {
    for (const [preference, scheme] of THEMES) {
      await useTheme(page, preference, scheme);
      for (const width of WIDTHS) {
        await page.setViewportSize({ width, height: 900 });
        await page.reload();
        await page.getByRole('heading', { name: 'Dashboard', level: 1 }).waitFor();
        const layout = await page.evaluate(() => ({ scroll: document.documentElement.scrollWidth, width: window.innerWidth }));
        assert.ok(layout.scroll <= layout.width, `${preference} ${width}px: overflow ${layout.scroll}`);
        const sidebarShown = await page.locator('#workspace-sidebar').evaluate((element) => element.getBoundingClientRect().left >= 0);
        assert.equal(sidebarShown, width >= 1024, `${preference} ${width}px sidebar`);
        const checks = [await contrastReport(page, DASHBOARD_TEXT, HERO_RING)];
        if (width < 1024) {
          await page.getByRole('button', { name: 'Open navigation' }).click();
          checks.push(await contrastReport(page, '#workspace-sidebar p, #workspace-sidebar a span, #workspace-sidebar button span'));
          await page.keyboard.press('Escape'); // the open drawer makes the header inert
        }
        await page.getByRole('button', { name: /Account menu/ }).click();
        checks.push(await contrastReport(page, '[role="menu"] button'));
        await page.keyboard.press('Escape');
        for (const { text, ratio } of checks.flat()) assert.ok(ratio >= 4.5, `${preference} ${width}px "${text}" ${ratio.toFixed(2)}`);
      }
    }
  }, '/dashboard');
});

test('three distinct appearances: light, forest-green System-dark and black Dark', async () => {
  await scene(server(schoolAdmin), async (page) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    const sample = () => page.evaluate(() => {
      const app = getComputedStyle(document.querySelector('.dashboard-app'));
      const css = (name) => app.getPropertyValue(name).trim();
      const rgb = (value) => value.match(/[\d.]+/g).slice(0, 3).map(Number);
      return {
        html: document.documentElement.className,
        background: getComputedStyle(document.querySelector('.dashboard-app')).backgroundImage,
        // The frosted sidebar is a vertical gradient: sample its top stop.
        sidebar: rgb(getComputedStyle(document.querySelector('#workspace-sidebar')).backgroundImage.match(/rgba?\([^)]+\)/)[0]),
        panel: css('--db-panel'),
        blur: getComputedStyle(document.querySelector('#workspace-sidebar')).backdropFilter,
      };
    });
    const seen = {};
    for (const [preference, scheme] of THEMES) {
      await useTheme(page, preference, scheme);
      await page.reload();
      await page.getByRole('heading', { name: 'Dashboard', level: 1 }).waitFor();
      seen[preference] = await sample();
    }
    const greenness = ([r, g, b]) => g - Math.max(r, b);
    // Light: light frosted sidebar on the public mint gradient.
    assert.ok(seen.light.sidebar.every((v) => v > 200), `light sidebar ${seen.light.sidebar}`);
    assert.ok(seen.light.background.includes('gradient'));
    // System-dark: forest-green sidebar and gradient, not near-black.
    assert.ok(seen.system.html.includes('dark') && !seen.system.html.includes('theme-black'));
    // Deep forest green: a green hue (not near-black, not grey), deeper than the public header.
    assert.ok(greenness(seen.system.sidebar) >= 10 && seen.system.sidebar[1] >= 35, `green sidebar ${seen.system.sidebar}`);
    assert.ok(seen.system.background.includes('rgb(20, 56, 35)'), seen.system.background);
    // Dark: black, distinct from System-dark.
    assert.ok(seen.dark.html.includes('theme-black'));
    assert.ok(seen.dark.sidebar.every((v) => v <= 15), `black sidebar ${seen.dark.sidebar}`);
    assert.ok(seen.dark.background.includes('rgb(0, 0, 0)'), seen.dark.background);
    assert.notEqual(seen.system.panel, seen.dark.panel);
    // Desktop sidebar is frosted in every theme.
    for (const theme of Object.values(seen)) assert.match(theme.blur, /blur/);
  }, '/dashboard');
});

test('mobile drawer is opaque (no backdrop blur) and the welcome banner stays AA over any photo crop', async () => {
  await scene(server(schoolAdmin), async (page) => {
    for (const [preference, scheme] of THEMES) {
      await useTheme(page, preference, scheme);
      for (const width of [360, 1440]) {
        await page.setViewportSize({ width, height: 900 });
        await page.reload();
        await page.getByRole('heading', { name: 'Dashboard', level: 1 }).waitFor();
        const banner = await page.locator('.dashboard-hero').evaluate((element) => getComputedStyle(element).backgroundImage);
        assert.match(banner, /url\(/, 'campus photo present');
        const hero = await contrastReport(page, '.dashboard-hero p, .dashboard-hero h2, .dashboard-hero button', HERO_RING);
        assert.equal(hero.length, 4);
        for (const { text, ratio } of hero) assert.ok(ratio >= 4.5, `${preference} ${width}px hero "${text}" ${ratio.toFixed(2)}`);
        if (width === 360) {
          const drawer = await page.locator('#workspace-sidebar').evaluate((element) => {
            const style = getComputedStyle(element);
            return { alpha: Number((style.backgroundColor.match(/[\d.]+/g) ?? [])[3] ?? 1), blur: style.backdropFilter };
          });
          assert.equal(drawer.alpha, 1, `${preference} drawer opaque`);
          assert.equal(drawer.blur, 'none');
        }
      }
    }
  }, '/dashboard');
});

test('keyboard focus rings are visible (3:1) on the sidebar, header and content in every theme', async () => {
  await scene(server(schoolAdmin), async (page) => {
    await page.setViewportSize({ width: 1280, height: 900 });
    for (const [preference, scheme] of THEMES) {
      await useTheme(page, preference, scheme);
      await page.reload();
      await page.getByRole('heading', { name: 'Dashboard', level: 1 }).waitFor();
      for (const target of [
        page.getByRole('link', { name: 'Applicant reviews' }),
        page.getByRole('button', { name: 'Collapse sidebar' }),
        page.getByRole('button', { name: 'Open applicant reviews' }),
      ]) {
        await target.focus();
        await page.keyboard.press('Shift+Tab');
        await page.keyboard.press('Tab');
        await page.waitForTimeout(250); // outline-color is part of transition-colors (150ms)
        const ring = await target.evaluate((element) => {
          const style = getComputedStyle(element);
          return { width: style.outlineWidth, color: style.outlineColor, style: style.outlineStyle };
        });
        assert.equal(ring.style, 'solid', `${preference} ${ring.style}`);
        assert.equal(ring.width, '2px');
        const report = await page.evaluate((color) => {
          const rgb = color.match(/[\d.]+/g).slice(0, 3).map(Number);
          return rgb;
        }, ring.color);
        const lum = ([r, g, b]) => {
          const c = [r, g, b].map((v) => { v /= 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; });
          return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
        };
        // Against the lightest (light theme) or darkest (dark themes) surface the ring can sit on.
        const surface = preference === 'light' ? [255, 255, 255] : preference === 'system' ? [20, 56, 35] : [0, 0, 0];
        const a = lum(report); const b = lum(surface);
        const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
        assert.ok(ratio >= 3, `${preference} focus ring ${ring.color} ${ratio.toFixed(2)}`);
      }
    }
  }, '/dashboard');
});
