# CTU-G Workspace — Design Reference (for AI agents and frontend developers)

_Baseline: inspected from `frontend/src` on 16 November 2026 (React 19, Tailwind CSS 4 via `@tailwindcss/vite`, plain-CSS tokens). Re-inspect the source if this date is old._

This folder is the single design source for UI work. It records **what the current UI actually uses** (exact values, class names, file paths) and the **rules for new work**, so every screen looks and behaves the same no matter who or what builds it.

Agents: follow the exact values and class names here. Do not interpret adjectives ("modern", "clean"). If something you need is not covered, copy the closest existing pattern and list the gap in your report. Do not invent a new token or style.

## Files

| File | Use it for |
| --- | --- |
| [TOKENS.md](TOKENS.md) | Colors (light, green-dark, black-dark; public and dashboard surfaces), type scale, spacing, radius, elevation, z-index, icons, motion, breakpoints |
| [COMPONENTS.md](COMPONENTS.md) | Existing components and canonical class strings, with every state (default, hover, active, focus-visible, disabled, loading, error) |
| [PATTERNS.md](PATTERNS.md) | Layouts, responsive behavior, forms and validation, feedback, loading, empty and error states, tables, permission-gated UI, accessibility, microcopy |
| [AUDIT.md](AUDIT.md) | Inconsistencies and defects found in the current UI, with proposed fixes. Read it before touching an affected area |

## Status labels used in these docs

- **Current**: present in the code today. Follow it exactly.
- **Standard**: the rule for new code. Where the current code differs, the difference is listed in AUDIT.md.
- **Proposed**: a value or component that does not exist yet. Use it only when your task needs it, add it in the location named, and say so in your report.

These docs are a reference. They do **not** authorize changing approved screens, copy or workflows. Registration, OTP and review copy is owner-approved (see `docs/workflows/`). Do not reword or restyle it unless the task asks for it.

## Step 1: pick the surface

The app has two visual surfaces with **separate token sets**. Pick one per screen and never mix them.

| | Public surface | Dashboard surface |
| --- | --- | --- |
| Routes | `/`, `/register`, `/register/verify`, `/forgot-password`, `/reset-password`, 404 | `/dashboard` (all `?view=` pages) |
| Layout | `layouts/PublicLayout.tsx` | `layouts/DashboardLayout.tsx` → `components/dashboard/DashboardShell.tsx` |
| Tokens and classes | `css/theme.css`: `--fg-*`, `--accent*`, `.surface-glass`, `.fg-*`, `.btn-*`, `.field` | `css/dashboard.css`: `--db-*`, `.dashboard-panel`, `.dashboard-heading`, `.dashboard-muted`, `.dashboard-eyebrow` |
| Look | Full-page campus photo, frosted-glass cards (`backdrop-filter: blur(16px)`), scroll reveal | Flat solid panels on a pale (or dark) green-gray background, dark-green sidebar, no glass, no reveal |
| Motion | Scroll reveal and hover lift allowed | Color transitions and a 2px hover lift on module cards only |

New authenticated module pages (clearance, SSG finance, announcements and the rest) belong on the **dashboard surface**.

## The 15 rules that matter most

1. Use the existing tokens and classes (TOKENS.md). Never write a raw hex value or a Tailwind palette color (`text-emerald-700`, `bg-amber-50`) in new code unless TOKENS.md lists it as the current value for that exact role.
2. Every color must work in all **three themes**: Light, System-dark (green, `html.dark`) and Dark (pure black, `html.dark.theme-black`). Check every screen in all three.
3. Text contrast must meet WCAG AA: 4.5:1 for text under 18.66px bold or 24px regular, 3:1 for large text and UI boundaries. AUDIT.md lists the current failures. Don't copy them.
4. Never use color as the only signal. Pair it with text or an icon (for example, "Integration pending" text, not just a gray card).
5. Use the type scale in TOKENS.md §2. In new code use only Tailwind steps (`text-xs` to `text-5xl`), not arbitrary `text-[13px]` sizes.
6. Spacing is the Tailwind 4px grid. Use the listed steps only.
7. Every interactive element needs all of these states: default, hover, active, focus-visible, disabled, and loading where it triggers a request (COMPONENTS.md).
8. Focus is always visible: a 2px outline with a 2px offset. Never `outline: none` without a replacement ring.
9. Forms: the label is always visible above the field; a placeholder is never the label. Validate on submit, clear a field's error when it changes, and focus the first invalid field (PATTERNS.md §3).
10. Every data view ships with loading, empty, error and permission-denied states (PATTERNS.md §5).
11. Show only modules and actions that the session's **exact permission codes** allow. UI hints never authorize; Django checks every request (PATTERNS.md §7).
12. Destructive or account-changing actions always get a confirmation that states the consequence and that the action is audited.
13. Security copy must not reveal whether an ID or email exists. Reuse the generic conflict message.
14. Animate only `transform` and `opacity` (color transitions are fine). Respect `prefers-reduced-motion`. No reveal animation on dashboard or form content.
15. Use semantic HTML: `<button>` for actions, `<a>` for navigation, a single `h1` per view, and no skipped heading levels.

## Explicit don'ts

- Don't mix the public glass surface into the dashboard, or dashboard panels into public pages.
- Don't add a new font family. The app uses the Tailwind default system sans stack only.
- Don't use `#000` text on white. Use `--fg-strong` (`#111827`). The pure-black **background** in the Dark theme is intentional.
- Don't center-align paragraphs longer than two lines. Centered text is limited to the hero column, short form footers and empty states.
- Don't let content shift while it loads. Reserve the space (PATTERNS.md §5).
- Don't rely on hover alone for an affordance. Touch devices have no hover.
- Don't animate core dashboard or form content on page load.
- Don't use `z-index` values outside the scale in TOKENS.md §6.
- Don't use a spinner for a whole-page or whole-panel wait over about 300ms. Spinners belong inside buttons.
- Don't show raw error codes, stack traces or backend messages. A request reference is fine.
- Don't automatically retry POST, PUT or DELETE requests. Offer an explicit recovery action instead.
- Don't store anything except the theme preference (`ctug-theme`) in `localStorage`.
- Don't create a clickable `<div>`.
- Don't reword owner-approved copy (registration, OTP, conflict and review messages).

## Pre-merge checklist for any UI change

- [ ] Correct surface chosen, and only that surface's tokens and classes used
- [ ] Checked in Light, System-dark and Dark, at 360px, 768px, 1024px and 1440px widths
- [ ] Contrast meets AA for all new text and icon pairs (record any measured ratio in your report)
- [ ] Keyboard only: every action is reachable, focus is visible, Escape closes overlays, and focus returns to the trigger
- [ ] Loading, empty, error and permission-denied states exist and keep the layout stable
- [ ] Copy follows PATTERNS.md §9 (case, verbs, ellipsis `…`, dates `en-PH`)
- [ ] `prefers-reduced-motion` tested (OS setting or DevTools emulation)
- [ ] No new hex values, z-index values or font sizes outside the tokens, unless recorded as **Proposed** in your report
- [ ] `npm run lint` and `npm run build` pass in `frontend/`
