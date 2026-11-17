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
className="dashboard-primary-link inline-flex min-h-10 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
// Secondary (bordered)
className="inline-flex min-h-10 items-center justify-center gap-2 rounded-lg border px-4 py-2 text-sm font-medium transition-colors hover:bg-[var(--db-edge)] focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
// Compact (table row actions): replace px-4 py-2 text-sm with px-3 py-2 text-xs
```

| State | Primary | Secondary |
| --- | --- | --- |
| Default | bg `#147647`, white | `border` in `--db-edge`, `--db-text` |
| Hover | bg `#0b5039` | bg `--db-edge` |
| Active | none today. You may add `active:scale-[0.98]` | same |
| Focus-visible | 2px `emerald-600` outline, offset 2px (white outline inside the sidebar) | same |
| Disabled | `opacity-50` + `cursor-not-allowed`. Current code varies (40%/50%/60%); use 50% for new code | same |
| Loading | disable the button and change its label ("Approving…"). Optionally add `<LoadingSpinner />` before the text | same |

**Destructive (Proposed):** `bg-[#b91c1c] text-white hover:bg-[#991b1b]` + the same focus and disabled classes. Use it for the confirm button of reject, delete and deactivate actions, never for the button that opens the dialog.

**On-hero button (Current):** `rounded-xl border border-white/35 bg-white/15 px-4 py-2.5 text-sm font-semibold text-white hover:bg-white/25`. Use it only on `.dashboard-hero`.

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

**Dashboard field (Current):** `<label className="dashboard-muted flex flex-col gap-1 text-xs">Search<input className="dashboard-panel w-52 rounded-lg border px-3 py-2 text-sm" … /></label>`. **Standard addition:** `focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-emerald-600`.

**OTP code field (Current, `VerifyEmailPage.tsx`):** `inputMode="numeric"`, `autoComplete="one-time-code"`, `pattern="[0-9]{6}"`, **no `maxLength`** (so pasted "123-456" still works). Normalize to digits in `onChange`.

## 4. Cards and panels

| Name | Classes | Use |
| --- | --- | --- |
| Glass card (public) | `surface-glass rounded-2xl p-5` (feature), `p-6 sm:p-8` (form) | Service cards, login, registration, verification |
| Lift card (public) | add `lift` | Clickable or showcase cards only |
| Dashboard panel | `dashboard-panel rounded-2xl border p-5` / `p-4 sm:p-6` / `p-6 sm:p-8` | All dashboard content containers |
| Module card (dashboard) | `dashboard-panel dashboard-module-card group rounded-2xl border p-5 text-left transition-transform hover:-translate-y-0.5 focus-visible:outline focus-visible:outline-2 focus-visible:outline-emerald-700` on a `<button>` | Clickable navigation card |
| Stat card | `dashboard-panel rounded-2xl border p-5` → label `dashboard-muted text-xs font-semibold uppercase tracking-wide`, value `dashboard-heading mt-3 text-xl font-bold`, note `dashboard-muted mt-1 text-xs` | Overview metrics |
| Dashboard hero | `dashboard-hero relative overflow-hidden rounded-3xl p-6 sm:p-8 lg:p-10` + the decorative `dashboard-hero-ring` | Overview only. One per app |
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
- Scrim: `rgba(9,39,27,.70)` (same as the mobile sidebar). Panel: `dashboard-panel rounded-2xl border p-5 sm:p-6 w-[min(32rem,calc(100vw-2rem))]` with a level-4 shadow.
- Enter: opacity 0 → 1 and `translateY(8px) scale(.97)` → none, 200ms `--ease-out`. Exit: 150ms `ease-in`. Reduced motion: opacity only.
- Structure: H3 title phrased as a question ("Confirm rejection?"), a consequence sentence ("This is a real account action and will be audited."), any required inputs, then actions right-aligned with `gap-3`: **Cancel (secondary, first in DOM)**, then confirm. The confirm button uses the destructive style for destructive actions and primary otherwise.
- Focus goes to the first field, or to Cancel for destructive actions. Escape and Cancel close it. Focus returns to the trigger.

## 7. Navigation

| Item | Current |
| --- | --- |
| Public header (`components/navigation/Navbar.tsx`) | `surface-header sticky top-0 z-50 h-16`. Nav buttons use `nav-link rounded-md px-2 py-2 text-sm font-medium`; the active one has `aria-current="page"` (accent-soft bg). A scroll progress bar runs along the bottom edge |
| Public mobile menu | Hamburger below 1152px (`icon-btn h-10 w-10 rounded-lg`, `aria-expanded`, `aria-controls`). `.mobile-menu[data-open]` dropdown. Closes on outside pointer-down, Escape or item choice |
| Dashboard sidebar (`components/dashboard/DashboardShell.tsx`) | 272px, pinned at ≥1024px, off-canvas below. Links use `dashboard-nav-link min-h-11 rounded-xl px-3 py-2.5 text-sm font-medium`; the active one gets `.dashboard-nav-active` (white tint + 3px inset bar `#87e9ad`). Section labels use `text-[11px] font-semibold uppercase tracking-[0.18em] text-emerald-100/65` |
| Dashboard drawer behavior | Opening focuses the close button. Escape or the scrim closes it and focus returns to the menu button. The scrim is a `<button aria-label="Close navigation overlay">` |
| Topbar | `dashboard-topbar sticky top-0 z-30 h-[76px] border-b`: breadcrumb `Workspace / {title}` (`text-xs` muted) + H1 + theme toggle (≥640px) + identity (≥768px) |
| Skip link | `.dashboard-skip-link` → `#workspace-main` (main has `tabIndex={-1}`) |

Add new dashboard views only through `features/dashboard/navigation.ts` (`DASHBOARD_NAV_ITEMS`, each with its permission code and icon name).

## 8. Small components

| Component | Current |
| --- | --- |
| `ThemeToggle` | `role="radiogroup"` with three `role="radio"` buttons (Light, System default, Dark), arrow-key navigation and roving `tabIndex`. Don't rebuild it; place it as-is |
| `LoadingSpinner` | 16px SVG, `animate-spin`, `role="status"`, `aria-label="Loading"`. Use it only inside buttons or next to a short inline label |
| `Reveal` | Scroll-triggered fade and lift, which replays on every scroll in or out. **Public home sections only.** Put it directly on glass surfaces, not around them (it keeps the blur intact) |
| Pill | `pill w-fit rounded-full px-3.5 py-1.5 text-xs font-medium` (hero campus label) |
| Step badge | `step-badge` (accent bg, white text) for numbered steps (How it works) |
| Back to top | `ScrollToTop` (`.to-top`, a 44px circle with a progress ring). Public layout only |
| Links | `link-accent` (accent, underline on hover), `link-muted` (muted → accent on hover). Dashboard inline links use `text-emerald-700 font-semibold` today; use `--db-accent` once it is added (AUDIT A-01) |

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
