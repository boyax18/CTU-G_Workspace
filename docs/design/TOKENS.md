# Design tokens

Sources: `frontend/src/css/theme.css` (public surface and shared tokens) and `frontend/src/css/dashboard.css` (dashboard surface). Theme switching lives in `frontend/src/contexts/ThemeProvider.tsx`.

## 0. Themes

| Preference (UI label) | Classes on `<html>` | Look |
| --- | --- | --- |
| Light | none | Pale mint backgrounds, gray-900 text, green-700 accent |
| System default, on a dark OS | `dark` | Softer **forest-green** dark theme |
| Dark (explicit) | `dark theme-black` | **Pure black** background, neutral grays, same green accents |

- The preference is stored in `localStorage['ctug-theme']`. Nothing else is stored.
- While switching, `html.theme-transition` fades colors for 350ms. Don't add your own theme transitions.
- The dashboard has only light and dark token sets: `.dark .dashboard-app` applies to both dark themes. `theme-black` does not change dashboard tokens.
- Dark mode is a hand-mapped token set. Never invert colors or use `filter: invert`.

## 1. Color

### 1.1 Primitive palette (current hex values, with their Tailwind equivalents)

| Family | Values in use |
| --- | --- |
| Green (brand) | `#14532d` green-900 · `#166534` green-800 · `#15803d` green-700 (**primary**) · `#16a34a` green-600 · `#4ade80` green-400 · `#86efac` green-300 |
| Dashboard green | `#062e24` · `#093c2d` · `#0b5039` · `#0e543a` · `#116d48` · `#147647` (**dashboard primary**) · `#146a43` · `#228a5b` · `#78ba96` · `#87e9ad` · `#a3e0b7` · `#d3f9de` · `#e3f3e8` · `#244e35` |
| Neutral (light) | `#111827` gray-900 · `#374151` gray-700 · `#4b5563` gray-600 · `#9ca3af` gray-400 |
| Neutral (green-dark) | `#f3faf5` · `#c5d6ca` · `#9fb6a6` · `#86a08f` |
| Neutral (black) | `#fafafa` · `#b8b8b8` · `#8c8c8c` · `#707070` · `#0e0e0e` · `#000000` |
| Red | `#dc2626` red-600 (light error) · `#f87171` red-400 (dark error) |
| Amber | `#fffbeb` amber-50 · `#92400e` amber-800 · `#fbbf24` amber-400 · `#fcd34d` amber-300 |
| Backgrounds | light `#eef6ef` → `#ecfdf5` → `#dcfce7` · green-dark `#143823` → `#1a4a2e` → `#215b39` · dashboard `#f2f6f3` / `#101c17` |

### 1.2 Semantic mapping (generic role → token to use)

Use the **class** column in JSX and the **variable** column in CSS.

| Role | Public variable | Public class | Dashboard variable or class |
| --- | --- | --- | --- |
| Text primary (headings, values) | `--fg-strong` | `.fg-strong` | `--db-text` / `.dashboard-heading` |
| Text secondary (body copy) | `--fg-body` | `.fg-body` | `--db-text` (body inherits) |
| Text muted (helper text, captions, meta) | `--fg-muted` | `.fg-muted` | `--db-muted` / `.dashboard-muted` |
| Accent text and links | `--fg-accent` | `.fg-accent`, `.link-accent` | `.dashboard-eyebrow` color (`#147647` / dark `#a3e0b7`) |
| Primary action background | `--accent` | `.btn-primary` | `.dashboard-primary-link` (`#147647`, hover `#0b5039`) |
| Primary hover | `--accent-hover` | (built into `.btn-primary`) | (built in) |
| Text on primary | `--on-accent` (`#fff`) | — | `#fff` |
| Accent tint (chips, active nav) | `--accent-soft` | `.chip-accent`, `.nav-link[aria-current]` | `.dashboard-placeholder-icon` |
| Surface (card, panel) | `--glass-bg` + `--glass-border` | `.surface-glass` | `--db-panel` + `--db-edge` / `.dashboard-panel` |
| Page background | `--bg-from` (under photo) | `.app-bg` + `.site-bg` | `--db-background` / `.dashboard-app` |
| Header or topbar | `--header-bg` | `.surface-header`, `.surface-footer` | `--db-topbar` / `.dashboard-topbar` |
| Border, divider | `--glass-border`, `--field-border` | — | `--db-edge` (Tailwind `border` inside `.dashboard-app` takes the current color; set `border-color` with `.dashboard-panel`) |
| Field | `--field-bg`, `--field-border`, `--field-focus`, `--field-ring`, `--placeholder` | `.field`, `.field-error` | `.dashboard-panel` on the input + `border` |
| Error text | `--fg-error` | `.fg-error` | **Proposed** `--db-error` (AUDIT A-02) |
| Warning or notice block | `--notice-bg`, `--notice-fg` | `.notice` | current: `border-amber-300 bg-amber-50 text-amber-950` (preview banner only) |
| Success | **none**: see 1.4 | — | current: `text-emerald-700` (fails in dark mode, AUDIT A-01) |
| Info | **none**: see 1.4 | — | — |
| Focus ring | `--accent-bright` outline | `.btn:focus-visible`, `.field:focus` | `focus-visible:outline-emerald-700` (cards); `outline-white` (sidebar) |
| Overlay scrim | — | — | `bg-[#09271b]/70` (mobile sidebar) |

### 1.3 Token values per theme (public, `theme.css`)

| Token | Light | Green-dark (`html.dark`) | Black (`html.dark.theme-black`) |
| --- | --- | --- | --- |
| `--fg-strong` | `#111827` | `#f3faf5` | `#fafafa` |
| `--fg-body` | `#374151` | `#c5d6ca` | `#b8b8b8` |
| `--fg-muted` | `#4b5563` | `#9fb6a6` | `#8c8c8c` |
| `--fg-accent` | `#15803d` | `#86efac` | `#86efac` (inherits) |
| `--fg-error` | `#dc2626` | `#f87171` | `#f87171` (inherits) |
| `--accent` | `#15803d` | `#15803d` | `#15803d` |
| `--accent-hover` | `#166534` | `#16a34a` | `#16a34a` |
| `--accent-bright` | `#16a34a` | `#4ade80` | `#4ade80` |
| `--accent-soft` | `rgba(21,128,61,.12)` | `rgba(74,222,128,.16)` | inherits |
| `--glass-bg` | `rgba(255,255,255,.28)` | `rgba(255,255,255,.09)` | `rgba(255,255,255,.05)` |
| `--glass-border` | `rgba(255,255,255,.55)` | `rgba(255,255,255,.18)` | `rgba(255,255,255,.10)` |
| `--field-bg` | `rgba(255,255,255,.30)` | `rgba(255,255,255,.08)` | `rgba(255,255,255,.05)` |
| `--field-border` | `rgba(98,177,130,.529)` | `rgba(255,255,255,.20)` | `rgba(255,255,255,.14)` |
| `--field-focus` | `#5bde8b` | `#4ade80` | inherits |
| `--field-ring` | `rgba(134,239,172,.55)` | `rgba(74,222,128,.30)` | inherits |
| `--placeholder` | `#9ca3af` | `#86a08f` | `#707070` |
| `--notice-bg` / `--notice-fg` | `#fffbeb` / `#92400e` | `rgba(251,191,36,.12)` / `#fcd34d` | inherits |
| `--menu-bg` | `rgba(255,255,255,.94)` | `rgba(16,46,30,.96)` | `rgba(0,0,0,.97)` |

Other tokens (`--header-*`, `--pill-*`, `--secondary-*`, `--outline-*`, `--toggle-bg`, `--thumb-bg`, `--site-*`) are defined in `theme.css`. Read them there; don't duplicate them.

### 1.4 Dashboard tokens (`dashboard.css`)

| Token | Light | Dark (both dark themes) |
| --- | --- | --- |
| `--db-background` | `#f2f6f3` | `#101c17` |
| `--db-panel` | `#ffffff` | `#182820` |
| `--db-edge` | `#dae6dd` | `#345044` |
| `--db-text` | `#1a3025` | `#e9f5ec` |
| `--db-muted` | `#62746a` | `#b3c8ba` |
| `--db-topbar` | `rgba(255,255,255,.92)` | `rgba(24,40,32,.94)` |
| Sidebar | `linear-gradient(175deg,#0b5039 0%,#093c2d 58%,#062e24 100%)`, white text, in both themes | same |
| Hero | `linear-gradient(115deg,#0e543a 0%,#116d48 65%,#228a5b 100%)`, white text | same |

**Proposed** feedback tokens. Add them to `dashboard.css` under `.dashboard-app` and `.dark .dashboard-app` the first time a task needs them. Every text pair below passes AA (ratios measured 16 Nov 2026: error on its block 5.91 light and 8.12 dark on the panel; warning text 8.75 light and 10.68 dark; success text on its block 4.92 light and 6.75 dark).

| Token | Light | Dark | Use |
| --- | --- | --- | --- |
| `--db-accent` | `#147647` (5.66:1) | `#86efac` (10.97:1) | Accent text, success text, "Open module space" link |
| `--db-success-bg` / `--db-success-edge` | `#e3f3e8` / `#78ba96` | `#244e35` / `#3f7a58` | Success block |
| `--db-error` | `#b91c1c` (6.47:1) | `#fca5a5` (8.12:1) | Error text |
| `--db-error-bg` / `--db-error-edge` | `#fef2f2` / `#fca5a5` | `rgba(248,113,113,.12)` / `rgba(248,113,113,.45)` | Error block |
| `--db-warning-bg` / `--db-warning-edge` / `--db-warning-fg` | `#fffbeb` / `#fcd34d` / `#78350f` | `rgba(251,191,36,.12)` / `rgba(251,191,36,.45)` / `#fcd34d` | Warning or preview block |
| `--db-info-bg` / `--db-info-edge` | `#f2f6f3` / `#dae6dd` | `#101c17` / `#345044` | Neutral info block (text in `--db-text`) |

Public success and info use the existing tokens: success = `.chip-accent` tint + `.fg-accent` text + check icon; info = `.pill` surface + `.fg-body` text + info icon.

### 1.5 Measured contrast (WCAG ratios against the flat token background)

Public backgrounds are really photo + overlay + glass, so these ratios are approximate. Confirm in the browser.

| Pair | Light | Green-dark | Black |
| --- | --- | --- | --- |
| `--fg-strong` on page bg | 16.10 ✅ | 9.60 ✅ | — ✅ |
| `--fg-body` on page bg | 9.36 ✅ | 6.71 ✅ | 10.59 ✅ |
| `--fg-muted` on page bg | 6.86 ✅ | 4.71 ✅ (3.71 ❌ on the lightest `--bg-to`) | 6.25 ✅ |
| `--fg-accent` on page bg | 4.55 ✅ (borderline) | 7.25 ✅ | ✅ |
| `--fg-error` on page bg | 4.38 ❌ (4.83 on white) | 3.68 ❌ | 7.59 ✅ |
| `--placeholder` | 2.54 ❌ | 3.61 ❌ | 4.24 ❌ |
| White on `--accent` (primary button) | 5.02 ✅ | 5.02 ✅ | 5.02 ✅ |
| `--notice-fg` on `--notice-bg` | 6.84 ✅ | 7.06 ✅ | ✅ |
| `--db-text` / `--db-muted` on `--db-panel` | 14.06 / 4.97 ✅ | 13.74 / 8.72 ✅ | — |
| `--db-muted` on `--db-background` | 4.56 ✅ (borderline) | ✅ | — |
| `text-emerald-700` on `--db-panel` | 5.48 ✅ | **2.81 ❌** | — |
| White on `.dashboard-primary-link` | 5.66 ✅ | 5.66 ✅ | — |
| Sidebar text on the sidebar gradient | 11.83 ✅ | same | — |

Placeholders are allowed to be low-contrast only because a visible label always exists. Never put required information in a placeholder.

## 2. Typography

**Font family:** Tailwind default `font-sans` (`ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji", "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji"`). No web font is loaded. Monospace (if needed): Tailwind `font-mono`. Don't add families.

**Scale** (Tailwind defaults; px at 16px root):

| Class | Size / line-height | Used for |
| --- | --- | --- |
| `text-xs` | 12 / 16 | Labels, helper text, captions, table headers, footer, eyebrows |
| `text-sm` | 14 / 20 | **Default body**, buttons, inputs, nav, notices |
| `text-base` | 16 / 24 | Card titles (public), topbar title (mobile) |
| `text-lg` | 18 / 28 | Form-card H2, dashboard section H3, topbar title (≥640px), brand name |
| `text-xl` | 20 / 28 | Dashboard section H3 (strong), stat values, state-panel H1 |
| `text-2xl` | 24 / 32 | Page H1 on form pages, public section H2, dashboard page H2 (mobile), large stat values |
| `text-3xl` | 30 / 36 | Dashboard page H2 (≥640px), public hero H1 (mobile) |
| `text-4xl` | 36 / 40 | Public hero H1 (≥640px) |
| `text-5xl` | 48 / 1 | Public hero H1 (≥1024px) only |

Existing arbitrary sizes (`text-[10px]`, `text-[11px]`, `text-[13px]`, `text-[15px]`, `.dashboard-eyebrow` at `.7rem`) appear only in dashboard sidebar and topbar chrome. Don't use them elsewhere.

**Fluid type (public, current):** from 1280px to 1920px, `text-xs`, `text-sm`, `text-base`, `text-lg`, `text-2xl`, `text-3xl`, `sm:text-sm`, `sm:text-4xl` and `lg:text-5xl` grow by up to +2px (`--fluid-add`). Other classes do not scale. If you add a new size to a public page, add it to the list at the end of `theme.css`.

**Hierarchy map (Standard):**

| Element | Public | Dashboard |
| --- | --- | --- |
| Eyebrow | `fg-accent text-xs font-semibold uppercase tracking-widest` | `.dashboard-eyebrow` |
| H1 | Hero: `text-3xl sm:text-4xl lg:text-5xl font-bold leading-tight`. Page: `text-2xl font-bold` | Topbar: `text-base sm:text-lg font-bold` (set by the shell; pages don't render an h1) |
| H2 | Section: `text-2xl font-bold`. Form card: `text-lg font-semibold` | Page title: `text-2xl sm:text-3xl font-bold` + eyebrow above + muted `text-sm mt-2` subtitle |
| H3 | Card: `text-base font-semibold` | Section: `text-lg font-semibold` (or `text-xl font-bold` for a primary section) |
| H4 | — | Empty-state or sub-panel title: `font-semibold` (`text-base`) |
| Body | `text-sm leading-relaxed` | `text-sm` (`leading-relaxed` for multi-line) |
| Helper or caption | `fg-muted text-xs` | `dashboard-muted text-xs` |
| Label | `fg-body text-xs font-medium` | `dashboard-muted text-xs` (filter labels), `text-sm font-medium` (dialog fields) |
| Field-group legend | `fg-strong text-sm font-semibold border-b border-emerald-500/20 pb-3 mb-4`, numbered "01 — Title" | — |
| Table header | — | `dashboard-muted text-xs uppercase tracking-wide` |
| Stat value | — | `dashboard-heading text-xl font-bold` (cards) or `text-2xl font-bold` (summary) |

**Weights:** 400 for body; 500 (`font-medium`) for labels, buttons, nav and links; 600 (`font-semibold`) for card and section titles, legends and table key cells; 700 (`font-bold`) for headings and stat values; 800 only in `.dashboard-eyebrow`. Never bold whole paragraphs.

**Line length:** cap paragraphs at `max-w-lg` (32rem), `max-w-2xl` (42rem) or `max-w-3xl` (form card). That keeps lines at roughly 65–75 characters at `text-sm`.

**Letter-spacing:** only on uppercase text: `tracking-widest` (public eyebrow), `tracking-[0.18em]` (sidebar section and hero eyebrow), `tracking-wide` or `tracking-wider` (table headers, `dt`). `tracking-tight` only on the dashboard hero H2.

## 3. Spacing and sizing

Base unit: **4px** (the Tailwind spacing scale). Allowed steps for new code: `0.5` (2) · `1` (4) · `1.5` (6) · `2` (8) · `2.5` (10) · `3` (12) · `4` (16) · `5` (20) · `6` (24) · `7` (28) · `8` (32) · `10` (40) · `12` (48) · `14` (56) · `16` (64) · `20` (80) · `24` (96).

| Context | Current value |
| --- | --- |
| Label → field | `mb-1.5` |
| Field → error | `mt-1` |
| Fields in a form | `space-y-4`, grid `gap-4` |
| Field groups (fieldsets) | `space-y-6` / `space-y-7` |
| Card padding | Public `p-5` (small cards), `p-6 sm:p-8` (form cards). Dashboard `p-5` (stat or module), `p-4 sm:p-6` (data panels), `p-6 sm:p-8` (content panels) |
| Card grid gap | `gap-4` |
| Dashboard page stack | `space-y-5` (sub-pages), `space-y-7` (overview) |
| Page gutter | Public `px-4 sm:px-6 lg:px-8`. Dashboard main `p-4 sm:p-6 lg:p-10` |
| Button groups | `gap-2` (table rows, compact), `gap-3` (dialog or recovery actions) |
| Section vertical rhythm (public) | `py-14 md:py-16`; form pages `py-10 sm:py-14` |

**Fixed sizes:** public header `h-16` (64px). Dashboard topbar `h-[76px]`. Sidebar `w-[272px]`. Icon chips `h-10 w-10` (public) and `h-11 w-11`/`h-12 w-12` (dashboard). Logo `h-9 w-9` (header, footer) and `h-10 w-10` (sidebar).

## 4. Border radius

| Token (Tailwind) | px | Use |
| --- | --- | --- |
| `rounded-md` | 6 | Desktop nav links, in-field icon buttons (password toggle), sidebar close button |
| `rounded-lg` | 8 | **Buttons, inputs, selects, notices, icon buttons, table action buttons, public icon chips, the skip link** |
| `rounded-xl` | 12 | Dashboard icon chips, sidebar nav items, identity card, dashboard hero CTA |
| `rounded-2xl` | 16 | **Cards, panels, form cards, dialogs, mobile menu** |
| `rounded-3xl` | 24 | Dashboard hero only |
| `rounded-full` | 9999 | Pills, the theme toggle and its thumb, the back-to-top button |

## 5. Elevation (shadows)

| Level | Value | Use |
| --- | --- | --- |
| 0 | none | Inline elements, table rows |
| 1 | `0 8px 30px rgba(10,62,34,.035)` | `.dashboard-panel` (resting) |
| 2 | `0 14px 28px rgba(12,75,39,.08)` | `.dashboard-module-card:hover`; `0 6px 16px -6px var(--accent)` on primary button hover |
| 3 | `var(--glass-shadow)`: `0 24px 40px -12px rgba(20,83,45,.28), 0 8px 16px -8px rgba(20,83,45,.15)` (light) | `.surface-glass` cards |
| 4 | `0 24px 48px -16px rgba(0,0,0,.35)` | Floating menus (`.mobile-menu`); `0 10px 24px -8px rgba(0,0,0,.35)` on `.to-top` |
| Header | `--header-shadow` → `--header-shadow-scrolled` when `.is-scrolled` | Sticky header |

The dashboard state panels (loading, signed-out) use Tailwind `shadow-lg`. Use level 4 for a **Proposed** modal dialog.

## 6. Z-index scale

| Value | Layer | Current owner |
| --- | --- | --- |
| `-10` | Fixed page background | `.site-bg` |
| `10` | Local stacking inside a component | `.theme-opt`, hero content |
| `30` | Sticky dashboard topbar | `.dashboard-topbar` |
| `40` | Floating buttons, mobile scrim | `.to-top`, dashboard mobile overlay |
| `50` | Sticky public header, dashboard sidebar | `.surface-header`, `.dashboard-sidebar` |
| `60` | Dropdowns and menus anchored to the header | `.mobile-menu` |
| `70` | **Proposed:** modal scrim + dialog | (new Modal) |
| `80` | **Proposed:** toasts | (new Toast) |
| `100` | Skip link (always on top) | `.dashboard-skip-link` |

Use only these values. Dropdowns inside page content need no z-index above `10`, unless they overlap the sticky header (then use `60`).

## 7. Icons

- These are inline SVG components, with no icon library. Public icons are in `components/common/Icons.tsx` and dashboard icons in `components/dashboard/DashboardIcon.tsx`. Add new icons to the matching file in the same style.
- Style: 24×24 `viewBox`, `fill="none"`, `stroke="currentColor"`, `strokeWidth 1.8`, round caps and joins, `aria-hidden`.
- Sizes: **20px** default (public); **19px** in the dashboard; **18px** inside fields; **14–15px** inline with `text-xs` text and in the theme toggle.
- Icons take their color from text (`currentColor`). Never hard-code an icon color.
- An icon-only button must have an `aria-label`. A decorative icon next to text needs nothing extra (`aria-hidden` is already in the base).

## 8. Motion

| Token | Value |
| --- | --- |
| `--ease-out` | `cubic-bezier(0.22, 1, 0.36, 1)` for anything that moves (enter, slide, lift) |
| Color easing | `ease` |
| Micro (press, color) | 150ms (`.btn` transform), 200ms (color, background, border) |
| Standard (panels, menus) | 200ms (sidebar slide), 300ms (header shadow, menu transform) |
| Emphasis | 350ms (theme thumb, `.lift`, theme color fade), 400ms (`.to-top`) |
| Reveal (public landing only) | 900ms `reveal-in`, staggered 90ms. This exceeds the standard limit and is accepted only for the public home sections |

Rules:
- New motion lasts 500ms or less (except the existing reveal) and animates only `transform` and `opacity`. Color, border and shadow transitions are fine.
- Press feedback is `scale(0.98)`. Hover lift is `translateY(-4px)` (`.lift`, public cards) or `-translate-y-0.5` (2px, dashboard module cards).
- Overlays enter with opacity + `translate3d(0,-8px,0) scale(.97)` → none, and leave with the reverse. Hide them with `visibility` after the transition (copy `.mobile-menu`).
- `prefers-reduced-motion: reduce`: the public reveal becomes a 500ms fade; lift, menu, button and field transitions turn off; inside `.dashboard-app` all transitions drop to 0.01ms. Any new animation must add itself to these blocks.
- Never use `linear` easing for UI movement (the `visibility` delay trick is the only exception).

## 9. Breakpoints (mobile-first, Tailwind defaults + one custom)

| Name | Min width | What changes |
| --- | --- | --- |
| base | 0 | One column; 16px gutters (`px-4`) |
| `sm` | 640px | Two-column form grids; theme toggle moves into the header; gutters `px-6` |
| `md` | 768px | Footer becomes a row; topbar identity block appears |
| `lg` | 1024px | Dashboard sidebar is pinned (otherwise an off-canvas drawer); hero becomes two columns; gutters `px-8` / `p-10` |
| `min-[1152px]` | 1152px | Public header shows the full nav and auth buttons (below this, the hamburger menu) |
| `xl` | 1280px | Fluid type starts; module grid becomes 3 columns; nav link padding widens |
| (fluid end) | 1920px | Public container max width; fluid type at its maximum |

**Containers:** public `max-w-[1920px]`. Dashboard main `max-w-[1500px]`. Registration card `max-w-3xl`. Verification card `max-w-xl`. Login card `max-w-xl lg:max-w-md`. Dashboard state panel `max-w-md`.
