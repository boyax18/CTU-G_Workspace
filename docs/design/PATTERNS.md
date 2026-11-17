# Patterns and rules

## 1. Page layouts

### 1.1 Public form page (Current: `/register`, `/register/verify`, `/forgot-password`)

```tsx
<section className="mx-auto w-full max-w-3xl px-4 py-10 sm:px-6 sm:py-14" aria-labelledby="x-title">
  <div className="surface-glass rounded-2xl p-6 sm:p-8">
    <p className="fg-accent text-xs font-semibold uppercase tracking-widest">CTU-G Workspace</p>
    <h1 id="x-title" className="fg-strong mt-2 text-2xl font-bold">…</h1>
    <p className="fg-muted mt-2 text-sm leading-relaxed">One-sentence purpose.</p>
    <form noValidate className="mt-6 space-y-6">…</form>
  </div>
</section>
```
Use `max-w-xl` for single-purpose steps (verification, reset). Put the back link last: `link-accent block text-center text-sm`.

### 1.2 Public home sections (Current)
Each section is `screen-section scroll-mt-16` (fills the viewport under the 64px header and snaps). Content sits in `mx-auto w-full max-w-[1920px] px-4 sm:px-6 lg:px-8`. Add a section id to `PAGE_SECTION_IDS` in `utils/constants.ts`, and to `NAV_ITEMS` if it belongs in the nav. Snap scrolling is enabled on `/` only.

### 1.3 Dashboard view (Current: `features/dashboard/SessionDashboardPage.tsx`)

```tsx
// The shell renders <Breadcrumbs/> and <PageHeader title={item.label} description={item.description}/>.
<div className="space-y-5">
  <section className="dashboard-panel rounded-2xl border p-4 sm:p-6" aria-labelledby="…">
    <h2 id="…" className="dashboard-heading text-lg font-semibold">Pending applications</h2>
    …
  </section>
</div>
```
**Surfaces:** the dashboard sits on the public mint / forest-green / black gradient. Use `.dashboard-panel` (nearly solid) for every data surface: tables, forms, filters, financial and administrative screens, menus and states. Use `.dashboard-glass` only on the overview (welcome widgets and module cards). Text never sits directly on raw transparency without a verified composited contrast check, and blur falls back to solid colours where it is unsupported.

The shell (Dashboard Shell v0.1) supplies the global header, the breadcrumb/context row and the page `h1` from the navigation registry (label and description), plus the `<main>`. Views never render their own page title: they start at `h2` for their sections. Use `.dashboard-eyebrow` only for small group labels inside a view (for example the module groups on the dashboard).

## 2. Responsive rules

| Pattern | Below the breakpoint | At or above it |
| --- | --- | --- |
| Public nav | Hamburger → dropdown menu (`<1152px`) | Inline nav + Sign In / Get Started |
| Dashboard nav | Off-canvas drawer + scrim (`<1024px`) | Pinned 272px sidebar |
| Hero | Stacked, centered (`<1024px`) | Two columns: text left, login card right |
| Card grids | 1 column | `sm:grid-cols-2` → `lg:grid-cols-4` (public services), `sm:grid-cols-2 xl:grid-cols-3` (dashboard modules), `sm:grid-cols-2 lg:grid-cols-3` (stats) |
| Form fields | 1 column | `sm:grid-cols-2` |
| Button rows | `flex-col` full width (hero) or `flex-wrap gap-3` | `sm:flex-row` |
| Tables | `overflow-x-auto` wrapper; the table keeps `min-w-[580px]` | Full width |
| Theme toggle | In the mobile menu (public) or hidden from the topbar (`<640px`) | In the header or topbar |
| Typography | Hero H1 30px → 36px (`sm`) → 48px (`lg`); dashboard H2 24px → 30px (`sm`) | Fluid +2px from 1280 to 1920 (public) |

Touch targets: new controls are **at least 44×44px** on touch layouts (`min-h-11`, as the sidebar links already are). Today's `Button` is 40px tall and the theme-toggle options are 32×28 (AUDIT A-11). Don't go smaller than these existing sizes.

Test at 360, 768, 1024 and 1440px. No horizontal page scroll at 360px. Only tables may scroll horizontally, inside their wrapper.

## 3. Forms and validation (Standard, matching the current registration and login forms)

1. **Labels are always visible** above the field. Placeholders are optional examples ("Enter your School ID"), never the label.
2. **Required marking:** append ` *` to required labels and ` (optional)` to optional ones, and say once near the top: "Fields marked * are required." (`fg-muted text-xs`).
3. **Helper text:** below the field or group, `fg-muted mt-3 text-xs leading-relaxed`, linked with `aria-describedby` (see `register-credentials-hint`).
4. **Validation timing:** validate **on submit**. When a field changes, clear that field's error (and the form-level failure). Don't validate on every keystroke. Don't add blur validation to existing approved forms.
5. **On a failed submit:** set field errors, show an `ApiErrorNotice` summary ("Check the highlighted registration fields."), pass `announceError={false}` to the fields, and **focus the first invalid field**.
6. **Error messages** are specific and actionable, in the shape "what is wrong + how to fix it": "Please enter your School ID.", "Enter the six-digit code from your email." Never "Invalid input".
7. **The submit button stays enabled**. Disable it only while a request is in flight, while a throttle countdown runs, or while a hard prerequisite is missing (for example, no code has been delivered yet). A disabled button needs visible text that explains why ("Try again in 42 seconds.").
8. **Double-submit guard:** an `inFlight` ref plus the `loading` state. Wrap fields in `<fieldset disabled={loading}>` while submitting, and set `aria-busy` on the form.
9. **Secrets:** clear password and OTP inputs after conflict, security, delivery or uncertain outcomes. Keep the safe values so the user can correct them.
10. **Group long forms** in `<fieldset>` + `<legend>` sections numbered "01 — Login Credentials", "02 — Personal Information".
11. Use `noValidate` on the `<form>`. Validation is handled in code so the messages stay consistent.
12. Use correct `autoComplete` values (`username`, `email`, `new-password`, `current-password`, `given-name`, `family-name`, `one-time-code`).

## 4. Feedback: which pattern to use

| Situation | Pattern | Notes |
| --- | --- | --- |
| A field is wrong | Inline field error | §3 |
| A form or request failed | `ApiErrorNotice` at the top of the form, focused, with **recovery buttons** inside ("Refresh security check", "Check registration status", "Try again") | Never auto-retry a write |
| An action succeeded and the page stays | Inline `role="status"` text near the action ("A new code was sent. The earlier code is no longer valid.") | |
| An action succeeded and the context changes | A replacement result view with a heading ("Registration submitted"), focused | |
| A background or non-blocking success | **Proposed** toast: bottom-right, z-index 80, `role="status"`, auto-dismisses after **4s** (pauses on hover or focus), close button, slides in 200ms | Never toast errors that need action |
| A persistent page-level condition (preview mode, maintenance) | Banner at the top of the view (`role="status"`) | |
| An account-changing or destructive action | Confirmation dialog (COMPONENTS.md §6) stating the consequence and that it is audited | Confirm button: destructive style for reject, delete or deactivate |
| A wait over about 1s | Button loading label + spinner. Over about 3s, add a status line ("Checking your registration…") | |
| Rate limited (429) | Countdown text "Try again in N seconds." + disable the action until it ends | Seconds come from the server (`retryAfter`) |
| Uncertain outcome (network failure or timeout after a write) | State that completion could not be confirmed + an explicit "Check status" action | Never assume success or failure |

## 5. Loading, empty, error and edge states (required for every data view)

### 5.1 Loading
- **Current:** text-only status lines (`role="status"`: "Loading pending requests…", "Checking your session…").
- **Standard for new views:** a skeleton that matches the real layout (same panel, same row count and heights, line widths of 60–90%), so nothing shifts when data arrives. **Proposed** CSS for `dashboard.css`:
  ```css
  .skeleton { background: var(--db-edge); border-radius: .375rem; position: relative; overflow: hidden; }
  .skeleton::after { content: ''; position: absolute; inset: 0; transform: translateX(-100%);
    background: linear-gradient(90deg, transparent, rgba(255,255,255,.45), transparent);
    animation: skeleton-shimmer 1.4s ease-in-out infinite; }
  .dark .skeleton::after { background: linear-gradient(90deg, transparent, rgba(255,255,255,.06), transparent); }
  @keyframes skeleton-shimmer { to { transform: translateX(100%); } }
  @media (prefers-reduced-motion: reduce) { .skeleton::after { animation: none; } }
  ```
  Put `aria-hidden="true"` on the skeleton, with a visually hidden `role="status"` "Loading …" next to it.
- Use a spinner only inside buttons, or for waits expected to be under about 300ms.

### 5.2 Empty
`dashboard-panel rounded-2xl border p-6` + an optional icon chip + an `h4` (`dashboard-heading font-semibold`) + one muted sentence explaining why it is empty + a primary action **only if the user is permitted to take one**. Filtered-empty and truly-empty states are different: "No matching pending registrations on this page." vs "No additional module spaces yet".

### 5.3 Error
Say in plain language what failed and offer a recovery action ("We could not verify your session." + **Try again**). Show the request reference when one exists. Never show raw codes, exceptions or backend text.

### 5.4 Permission denied or unavailable (Current)
"This section is unavailable" + "Your current session does not report the required module permission." + **Return to overview**. Don't reveal what the permission would unlock.

### 5.5 Overflow and formatting
- Long single-line values (names, IDs, roles in the sidebar and topbar): `truncate` + `min-w-0` on the flex child. Add a `title` attribute when the full value is otherwise unavailable.
- Lists: paginate server-side (the review queue uses 20 per page, with Previous / Page N / Next). Disable Next when the page has fewer than the page size.
- Dates: `toLocaleDateString('en-PH', { year: 'numeric', month: 'short', day: 'numeric' })` → "Nov 16, 2026".
- Numbers: `Intl.NumberFormat('en-PH')`. Currency (**Proposed**, for SSG finance): `Intl.NumberFormat('en-PH', { style: 'currency', currency: 'PHP' })` → "₱1,250.00". Keep amounts right-aligned with `tabular-nums`.
- Counts: show exact numbers (no "1.2k" abbreviations). Volumes are small and records are official.

### 5.6 Optimistic UI
**Not allowed** for account, permission, review, clearance or financial actions. Update the UI only after the server confirms. Optimistic updates are allowed only for local view state (filters, the theme, a collapsed panel).

## 6. Tables (Current: the registration review queue)

```tsx
<div className="overflow-x-auto">
  <table className="w-full min-w-[580px] text-left text-sm">
    <thead><tr className="dashboard-muted border-b text-xs uppercase tracking-wide">
      <th scope="col" className="px-2 py-3">School ID</th>…</tr></thead>
    <tbody><tr className="border-b last:border-0">
      <td className="dashboard-heading px-2 py-3 font-semibold">…</td>…</tr></tbody>
  </table>
</div>
```
The key column is first and `font-semibold`. Dates are muted. Actions are compact buttons in `flex gap-2` (primary first). Filters sit above the table in `flex flex-wrap gap-3` with labelled inputs. If a filter applies only to the current page, say so ("Filters search only the current page").

## 7. Permission-gated UI (project rule)

- Navigation items and module cards appear only when the session holds the item's **exact permission code** (`getVisibleDashboardItems`, `getVisibleNavGroups`). Never gate by role name. Groups follow Dashboard Shell v0.1 (Overview, Account operations, Academic, Finance, Teaching, Clearance, Academic services, Financial management, Reports, Academic configuration, Clearance oversight, Campus, Access control, Security & audit, System operations, Account); a group with no permitted link is hidden, and a multi-role session sees each module once.
- A School Admin never sees Access control, Security & audit or System operations links: those groups use governance codes bound only to the Technical Super Admin role. A Super Admin sees School Admin operations only through the Admin role's grants.
- Inside a view, an action the user cannot perform is **disabled**, not hidden, when its presence matters for context (Approve or Reject in the queue). Hide it when it would only confuse.
- Make it clear that UI hints are hints: "Role names and permission hints never authorize an API call. Django verifies access on every protected request."
- Planned or unconnected modules are labelled with text ("Soon") in the sidebar, the module cards and the page header, and open the `ModuleUnavailable` state, never a page that looks like it works. A direct URL to a module the session lacks shows `AccessDenied` with the neutral title "Section unavailable".
- Feature gates (`*_ENABLED` constants in `features/admin/*Gate.ts`) decide whether a view exists at all. Don't bypass them in UI work.

## 8. Accessibility (non-negotiable)

- Semantic elements: `<button>` for actions, `<a href>` for navigation, `<nav aria-label>`, `<main>`, `<header>`, `<footer>`, `<section aria-labelledby>`, `<dl>` for label/value lists, `<table>` with `scope="col"`.
- One `h1` per view, with no skipped levels. Dashboard: topbar `h1` → view `h2` → section `h3` → `h4`.
- Focus: visible on every interactive element (2px outline, 2px offset). After route-like changes, focus the result or the error. Escape closes menus, drawers and dialogs, and focus returns to the trigger. Dialogs trap focus.
- Live regions: `role="alert"` (assertive) for errors that need action, and `role="status"` / `aria-live="polite"` for confirmations. Announce once: don't pair a summary alert with per-field alerts.
- Icon-only buttons need an `aria-label`, and toggles use `aria-pressed` or `aria-expanded`. A button's visible text must equal (or start) its accessible name (WCAG 2.5.3). Put countdowns in `aria-describedby`, not in the label.
- Images: give meaningful ones `alt` text. Decorative images and logos next to the brand name get `alt=""`. Decorative SVGs are `aria-hidden`.
- Keep the dashboard skip link working and add `tabIndex={-1}` to new focus targets that are not controls.
- Contrast and reduced motion: see TOKENS.md §1.5 and §8.

## 9. Content and microcopy

| Rule | Standard |
| --- | --- |
| Case | **Sentence case** for new headings, buttons, labels and menu items ("Verify your email", "Resend code", "View account details"). The existing public and registration Title Case labels ("Sign In", "Get Started", "Create Account", "First Name", "Proceed Email Verification") stay as they are until the owner approves a copy pass. Inside an existing screen, match that screen's case |
| Buttons | Start with a verb and name the result: "Refresh list", "Resend code", "Return to overview", "Confirm rejection". No "OK", "Submit" or "Yes" |
| In progress | Present participle + `…` (U+2026, not three dots): "Signing in…", "Requesting verification…" |
| Confirmations | Title phrased as a question ("Confirm approval?") + a consequence sentence |
| Product terms | **School ID** (students), **Staff ID** (instructors), **School Admin**, **Workspace**, **CTU-G Workspace**, **sign in / sign out** (not log in or log out), "registration", "verification code" |
| Brand and campus | Import `BRAND_NAME` and `CAMPUS_NAME` from `utils/constants.ts`. Don't retype them |
| Tone | Plain, calm and factual. Second person ("your account"). No exclamation marks, jokes or blame |
| Security copy | Never confirm whether an ID or email exists. Reuse: "We could not complete this registration. Please check your information or contact support." Don't invent support contacts (the official contact is pending owner input) |
| Honesty | Never claim completion that has not been confirmed (for example, don't claim an email was "sent" until the backend accepts it) |
| Errors | What happened + what to do next. Include "Request reference: …" when one is available |
| Separators | `·` between metadata items ("Administration · UI rehearsal"). An em dash `—` in numbered legends |
