# Components and states

Reuse before you create. Each entry lists the file, the canonical markup or classes, and **every state**. Paths are relative to `frontend/src/`.

State vocabulary (every interactive element needs each one that applies): **Default · Hover · Active (pressed) · Focus-visible · Disabled · Loading · Error**.

---

## 1. Button: public surface (`components/common/Button.tsx`) — Current

```tsx
<Button>Save changes</Button>                      // variant="primary", size="md"
<Button variant="outline" size="sm">Sign In</Button>
<Button variant="secondary">Explore Services</Button>
<Button type="submit" loading={busy} fullWidth>{busy ? 'Saving…' : 'Save changes'}</Button>
```

Base: `btn btn-{variant} inline-flex min-h-[40px] items-center justify-center gap-2 rounded-lg border font-medium text-sm`. Sizes: `sm` = `px-3.5 py-2`, `md` = `px-5 py-2.5`. The default `type` is `"button"`. Pass `type="submit"` explicitly for form submits.

| State | primary | outline | secondary |
| --- | --- | --- | --- |
| Default | bg `--accent`, white text | transparent, `--outline-fg` text, `--outline-border` | `--secondary-bg` (glass, blur 12px), `--secondary-fg`, `--secondary-border` |
| Hover | bg `--accent-hover` + shadow `0 6px 16px -6px var(--accent)` | bg `--outline-hover` | bg `--secondary-hover` |
| Active | `scale(0.98)`, 150ms | same | same |
| Focus-visible | 2px solid `--accent-bright`, offset 2px | same | same |
| Disabled | `opacity-70`, `cursor-not-allowed`, no hover (hover rules use `:not(:disabled)`) | same | same |
| Loading | `loading` prop: disables the button and prepends a 16px `LoadingSpinner`. **Also change the label** to the present participle + `…` ("Signing in…") | same | same |

Rules:
- One primary button per view or form. Use `outline` or `secondary` for the rest.
- **There is no destructive variant (Proposed).** Add `danger` to `Button.tsx` when the first destructive public action is needed. Class `.btn-danger`: bg `#b91c1c`, hover `#991b1b`, white text (6.47:1), same focus ring. On the dashboard, see §2.
- Don't use `Button` inside `.dashboard-app`. Its secondary variant is glass. Use §2.

## 2. Button: dashboard surface — Current classes, Standard composition

There is no dashboard button component yet. Copy these strings exactly. They are the current classes plus the focus and disabled states that are missing today (AUDIT A-05).

```tsx
// Primary
className="dashboard-primary-link inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)] disabled:cursor-not-allowed disabled:opacity-50"
// Secondary (outline, matches the public .btn-outline)
className="dashboard-outline-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)] disabled:cursor-not-allowed disabled:opacity-50"
// Compact (table row actions): replace px-4 py-2 text-sm with px-3 py-2 text-xs
```

| State | Primary | Secondary |
| --- | --- | --- |
| Default | bg `--db-button` (= public `--accent` `#15803d`), white | `--db-accent` text, `--db-outline-border` border |
| Hover | bg `--db-button-hover` (= `--accent-hover`) | bg `--db-accent-soft` |
| Active | none today. You may add `active:scale-[0.98]` | same |
| Focus-visible | 2px `--db-focus` outline, offset 2px, in every theme and in the sidebar. Write it as `outline-[color:var(--db-focus)]`; without the `color:` hint Tailwind does not apply it | same |
| Disabled | `opacity-50` + `cursor-not-allowed`. Current code varies (40%/50%/60%); use 50% for new code | same |
| Loading | disable the button and change its label ("Approving…"). Optionally add `<LoadingSpinner />` before the text | same |

**Destructive (Proposed):** `bg-[#b91c1c] text-white hover:bg-[#991b1b]` + the same focus and disabled classes. Use it for the confirm button of reject, delete and deactivate actions, never for the button that opens the dialog.

**On-hero button (Current):** `dashboard-hero-button rounded-xl border px-4 py-2.5 text-sm font-semibold` (6% white fill; hover darkens, so contrast never drops over the photo) + a white focus outline. Use it only on `.dashboard-hero`.

## 3. Text input (`components/common/Input.tsx`) — Current

```tsx
<Input id="register-email" label="Email *" type="email" autoComplete="email"
  value={v} onChange={…} error={errors.email} announceError={false} />
```

- The label is rendered above the field (`fg-body mb-1.5 block text-xs font-medium`), tied by `htmlFor` and `id`.
- Field: `field w-full rounded-lg px-3 py-2.5 text-sm`.
- `error` adds `.field-error`, `aria-invalid`, and `<p id="{id}-error" class="fg-error mt-1 text-xs">`, linked through `aria-describedby`.
- `announceError`: pass `false` when the form shows an `ApiErrorNotice` summary, so screen readers hear the error once.
- `rightAdornment`: in-field icon button, adds `pr-10`. Password toggle: `icon-btn flex h-8 w-8 items-center justify-center rounded-md`, `aria-label="Show password"`/`"Hide password"`, `aria-pressed`, `aria-controls`.

| State | Look |
| --- | --- |
| Default | `--field-bg`, 1px `--field-border`, `--fg-strong` text, `--placeholder` placeholder |
| Hover | no change (intentional) |
| Focus | border `--field-focus` + `box-shadow: 0 0 0 3px var(--field-ring)`, no outline. `:focus-visible` also gets the 2px `--accent-bright` outline |
| Error | border `--fg-error`; on focus, ring `rgba(248,113,113,.30)`; error text below |
| Success | none. Don't add green "valid" states |
| Disabled | inherits from `<fieldset disabled>` or `disabled`. Add `disabled:cursor-not-allowed disabled:opacity-60` when a field is disabled on its own |
| Autofill | handled by `.field:-webkit-autofill` (`--autofill-bg`) |

**Select (Current):** a native `<select>` with the same `field w-full rounded-lg px-3 py-2.5 text-sm`, a separate `<label>` and the same error pattern (see the "Register as" select in `features/auth/RegisterPage.tsx`).

**Dashboard field (Current):** `<label className="dashboard-muted flex flex-col gap-1 text-xs">Search<input className="dashboard-panel w-52 rounded-lg border px-3 py-2 text-sm" … /></label>`. **Standard addition:** `focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]`.

**OTP code field (Current, `VerifyEmailPage.tsx`):** `inputMode="numeric"`, `autoComplete="one-time-code"`, `pattern="[0-9]{6}"`, **no `maxLength`** (so pasted "123-456" still works). Normalize to digits in `onChange`.

## 4. Cards and panels

| Name | Classes | Use |
| --- | --- | --- |
| Glass card (public) | `surface-glass rounded-2xl p-5` (feature), `p-6 sm:p-8` (form) | Service cards, login, registration, verification |
| Lift card (public) | add `lift` | Clickable or showcase cards only |
| Dashboard panel | `dashboard-panel rounded-2xl border p-5` / `p-4 sm:p-6` / `p-6 sm:p-8` | Every **data** surface: tables, forms, filters, financial and administrative screens, menus, states. Nearly solid (`--db-panel`, 94–96%; a charcoal gradient in Dark), with `--db-sheen` and `--db-shadow` for depth |
| Dashboard glass | `dashboard-glass rounded-2xl p-5` (border, `--db-sheen` + `--db-glass-shadow` and 16px blur are built in) | **Overview only**: the "At a glance" widgets and module cards. Never for data. Dashboard-specific; don't use the public `.surface-glass` in the dashboard |
| Module card (dashboard) | `dashboard-glass dashboard-module-card group rounded-2xl p-5 text-left transition-transform hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-[color:var(--db-focus)]` on a `<button>` | Clickable navigation card on the dashboard overview |
| Stat card | `dashboard-panel rounded-2xl border p-5` → label `dashboard-muted text-xs font-semibold uppercase tracking-wide`, value `dashboard-heading mt-3 text-xl font-bold`, note `dashboard-muted mt-1 text-xs` | Overview metrics |
| Dashboard hero | `dashboard-hero relative overflow-hidden rounded-3xl p-6 sm:p-8 lg:p-10` with `style={{ '--db-hero-photo': url(campus-building.jpg) }}` + the decorative `dashboard-hero-ring`. Text uses `.dashboard-hero-eyebrow`, white `h2`, `.dashboard-hero-text` | Overview only. One per app. The forest-green overlay keeps white text ≥ 4.5:1 over any crop of the photo |
| Icon chip | Public `chip-accent flex h-10 w-10 items-center justify-center rounded-lg`. Dashboard `dashboard-placeholder-icon flex h-11 w-11 items-center justify-center rounded-xl` | Leading icon on a card |

Hover is never the only affordance. Clickable cards are `<button>` or `<a>` elements with a visible text cue ("Open module space ›").

## 5. Notices and alerts

| Component | Markup | When |
| --- | --- | --- |
| `ApiErrorNotice` (`components/common/ApiErrorNotice.tsx`) — Current | `<ApiErrorNotice error={apiError}>{recovery buttons}</ApiErrorNotice>`: amber `.notice` block, `role="alert"`, focuses itself on mount, prints "Request reference: …" | **Every** failed API call and form-level validation summary on the public surface. Put recovery actions as children |
| Inline notice (public) — Current | `<p role="status" className="notice rounded-lg px-3 py-2 text-xs">` (or `p-3 text-sm`) | Non-error information that needs attention ("Security check refreshed…") |
| Inline status text — Current | `<p role="status" aria-live="polite" className="fg-body mt-4 text-sm">` (dashboard: `dashboard-panel rounded-lg border p-3 text-sm`) | Success or progress confirmations ("A new code was sent…") |
| Preview banner (dashboard) — Current | `rounded-xl border border-amber-300 bg-amber-50 p-4 text-sm text-amber-950` | Mock or preview warnings only. Replace with `--db-warning-*` when those are added |
| Error, warning, success and info blocks (dashboard) — Proposed | `rounded-xl border p-4 text-sm` + `--db-{kind}-bg/-edge` + leading 19px icon + text | New dashboard feedback. Errors use `role="alert"`; the others use `role="status"` |

## 6. Dialog (confirmation) — Current behavior and the Proposed `Modal`

`components/common/Modal.tsx` exists but is **empty**. The current confirmations (`features/admin/RegistrationReviewLivePanel.tsx`) are inline `<section role="dialog" aria-modal="true" aria-labelledby>` blocks with no scrim and no focus trap (AUDIT A-06).

**Proposed `Modal` spec** (implement in `Modal.tsx` the first time a task needs a true modal):
- Native `<dialog>` opened with `showModal()` (it provides inert background, Escape and top-layer stacking). Otherwise use z-index `70` with a focus trap.
- Scrim: `.dashboard-scrim` (`--db-scrim`, the same as the mobile drawer). Panel: `dashboard-panel rounded-2xl border p-5 sm:p-6 w-[min(32rem,calc(100vw-2rem))]` with a level-4 shadow.
- Enter: opacity 0 → 1 and `translateY(8px) scale(.97)` → none, 200ms `--ease-out`. Exit: 150ms `ease-in`. Reduced motion: opacity only.
- Structure: H3 title phrased as a question ("Confirm rejection?"), a consequence sentence ("This is a real account action and will be audited."), any required inputs, then actions right-aligned with `gap-3`: **Cancel (secondary, first in DOM)**, then confirm. The confirm button uses the destructive style for destructive actions and primary otherwise.
- Focus goes to the first field, or to Cancel for destructive actions. Escape and Cancel close it. Focus returns to the trigger.

## 7. Navigation

| Item | Current |
| --- | --- |
| Public header (`components/navigation/Navbar.tsx`) | `surface-header sticky top-0 z-50 h-16`. Nav buttons use `nav-link rounded-md px-2 py-2 text-sm font-medium`; the active one has `aria-current="page"` (accent-soft bg). A scroll progress bar runs along the bottom edge |
| Public mobile menu | Hamburger below 1152px (`icon-btn h-10 w-10 rounded-lg`, `aria-expanded`, `aria-controls`). `.mobile-menu[data-open]` dropdown. Closes on outside pointer-down, Escape or item choice |
| Dashboard shell layout (`components/dashboard/DashboardShell.tsx`, Dashboard Shell v0.1) | One shell for every role: a **full-width global header** on top, the sidebar below it on the left, and the main column (breadcrumb/context row, page header, module outlet, footer) on the right |
| Global header | `dashboard-topbar sticky top-0 z-30 h-16 border-b`: drawer button (<1024px) or collapse toggle (≥1024px, `aria-expanded`, `aria-controls="workspace-sidebar"`), logo + "CTU-G Workspace" / "Ginatilan Campus", academic-period context (≥768px in the header, in the breadcrumb row below; "not yet configured" until academic periods exist), theme toggle (≥640px), user menu. Search and Alerts from the v0.1 wireframe are **not shown** until their workflows exist |
| User menu (`components/dashboard/UserMenu.tsx`) | Menu button (`aria-haspopup="menu"`, `aria-expanded`) with a user icon, School ID and roles (≥768px). `role="menu"` panel at `z-[60]`: the Account utility links (My profile, Account settings when permitted) and "Sign out of Workspace". Enter/Space/ArrowDown open on the first item, ArrowUp on the last; arrows, Home and End move; Escape closes and returns focus; Tab or an outside click closes |
| Dashboard sidebar (`components/dashboard/DashboardNavigation.tsx`) | 272px, `top-16` under the header and pinned at ≥1024px; collapses to an 80px icon rail (labels become `sr-only` plus a `title`); an off-canvas drawer below 1024px. Groups come from the registry and render as `role="group"` with a `.dashboard-nav-group` label (`text-xs font-semibold uppercase tracking-[0.16em]`); a group with no permitted link is not rendered. Links use `dashboard-nav-link min-h-11 rounded-xl px-3 py-2.5 text-sm font-medium`; the active one gets `.dashboard-nav-active` (`--db-sidebar-active` tint, `--db-sidebar-active-fg` text, 3px inset bar `--db-sidebar-bar`) and `aria-current="page"`. The sidebar is frosted (`--db-sidebar`, a vertical gradient with `--db-sheen`, 18px blur) at ≥1024px and opaque (`--db-sidebar-solid`, no blur) as the mobile drawer; its text uses `--db-sidebar-text`, `.dashboard-sidebar-strong` and `.dashboard-nav-group`. Unfinished modules carry a `.dashboard-nav-soon` "Soon" badge. The footer holds the Account utility links, the identity card and Sign out |
| Dashboard drawer behavior | Opening focuses the close button ("Close navigation"). Tab and Shift+Tab are trapped inside the drawer; the header and main column are `inert`. Escape, the close button or the scrim closes it and focus returns to "Open navigation"; choosing a link closes it; widening to ≥1024px closes it. The scrim is a `<button aria-label="Close navigation overlay">` |
| Breadcrumbs and page header (`components/dashboard/PageHeader.tsx`) | `<nav aria-label="Breadcrumb">` with an `<ol>`: Dashboard (link) / group label (text) / page (`aria-current="page"`). `PageHeader` renders the view's **only `h1`** (`text-2xl sm:text-3xl font-bold`), the registry description (`dashboard-muted text-sm`), an optional status badge ("Soon") and an optional quick-action slot |
| Shared states (`components/dashboard/DashboardStates.tsx`) | `DashboardState` (panel + icon chip + `h2` + muted text + optional secondary button) and its presets: `AccessDenied` ("This section is unavailable"), `ModuleUnavailable` ("This module is not available yet", for "Soon" modules) and `NoModules` ("No modules are available to your account yet") |
| Overview widgets (`features/dashboard/SessionDashboardPage.tsx`) | "At a glance" shows only permitted, **working** widgets and never counts the API does not provide (today: the Pending applications link card). "Your modules" lists every permitted module by group as cards with an "Available" or "Soon" text badge |
| Skip link | `.dashboard-skip-link` → `#workspace-main` (main has `tabIndex={-1}`) |

Add new dashboard views only through the registry in `features/dashboard/navigation.ts`: a `DASHBOARD_NAV_ITEMS` entry with its group, label, icon, one-sentence description, exact catalogue permission code(s) and `integration` (`'shell'` when the page works, `'planned'` otherwise). Every code must exist in `backend/apps/access_control/catalogue/v2_0.json` (unit-tested); a proposed link with no catalogue code is left out, not invented.

## 8. Small components

| Component | Current |
| --- | --- |
| `ThemeToggle` | `role="radiogroup"` with three `role="radio"` buttons (Light, System default, Dark), arrow-key navigation and roving `tabIndex`. Don't rebuild it; place it as-is |
| `LoadingSpinner` | 16px SVG, `animate-spin`, `role="status"`, `aria-label="Loading"`. Use it only inside buttons or next to a short inline label |
| `Reveal` | Scroll-triggered fade and lift, which replays on every scroll in or out. **Public home sections only.** Put it directly on glass surfaces, not around them (it keeps the blur intact) |
| Pill | `pill w-fit rounded-full px-3.5 py-1.5 text-xs font-medium` (hero campus label) |
| Step badge | `step-badge` (accent bg, white text) for numbered steps (How it works) |
| Back to top | `ScrollToTop` (`.to-top`, a 44px circle with a progress ring). Public layout only |
| Links | `link-accent` (accent, underline on hover), `link-muted` (muted → accent on hover). Dashboard inline links use `.dashboard-accent` (`--db-accent`) with `font-semibold` |

## 9. Proposed components (don't exist yet)

Build each only when a task requires it, and place it where listed:

| Component | Location | Spec |
| --- | --- | --- |
| `Skeleton` | `components/common/Skeleton.tsx` + `.skeleton` in `dashboard.css` | PATTERNS.md §5.1 |
| `EmptyState` | `components/dashboard/EmptyState.tsx` | PATTERNS.md §5.2 |
| `Modal` | `components/common/Modal.tsx` | §6 above |
| `Toast` | `components/common/Toast.tsx` | PATTERNS.md §4. z-index 80 |
| `DashboardButton` | `components/dashboard/DashboardButton.tsx` | Wraps the §2 class strings (variants `primary`, `secondary`, `danger`; sizes `md`, `sm`; `loading`) |
| `StatusBadge` | `components/dashboard/StatusBadge.tsx` | `inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-medium` + `--db-{kind}-*` + a leading dot or icon. The text always names the status ("Pending", "Approved", "Rejected") |
