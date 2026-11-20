# Frontend agent instructions (CTU-G Workspace)

These instructions apply to any work under `frontend/`.

## Read first (required for any UI, styling or copy change)

1. `../docs/design/README.md`: choosing a surface, the 15 core rules, the don'ts, and the pre-merge checklist
2. `../docs/design/TOKENS.md`: colors (three themes), type, spacing, radius, elevation, z-index, icons, motion, breakpoints
3. `../docs/design/COMPONENTS.md`: reuse existing components and class strings, with every state
4. `../docs/design/PATTERNS.md`: forms, feedback, loading, empty and error states, tables, permission-gated UI, accessibility, copy
5. `../docs/design/AUDIT.md`: known inconsistencies. Don't copy them. Fix one only when your task covers that area

If a design need is not covered there, copy the closest existing pattern and report the gap. Don't invent new tokens, colors, font sizes or z-index values.

## Stack

- React 19 + TypeScript, Vite 8, Tailwind CSS 4 (`@import "tailwindcss"` in `src/index.css`, no Tailwind config file)
- Design tokens are plain CSS: `src/css/theme.css` (public surface) and `src/css/dashboard.css` (dashboard surface)
- Routing is path-based in `src/App.tsx` (no router library). Dashboard views use `?view=`, configured in `src/features/dashboard/navigation.ts`
- API calls go through `src/api/client.ts`. The dev server proxies `/api` to Django (`CTUG_API_TARGET`, default `http://127.0.0.1:8000`)

## Commands (run from `frontend/`)

| Task | Command |
| --- | --- |
| Dev server | `npm run dev` |
| Type-check + build | `npm run build` |
| Lint | `npm run lint` |
| Unit tests | `npm test` |
| Registration browser tests | `npm run test:registration-ui` |

Run `npm run lint` and `npm run build` before reporting a UI change as done. Report test results exactly as observed, including any failures.

## Non-negotiables

- Pick one surface per screen: public (glass, `theme.css`) or dashboard (flat panels, `dashboard.css`). Never mix them. New authenticated module pages go on the dashboard.
- Every change must work in Light, System-dark (`html.dark`) and Dark (`html.dark.theme-black`), and at 360, 768, 1024 and 1440px widths.
- Keep WCAG AA contrast, visible focus, keyboard access, Escape to close overlays, and `prefers-reduced-motion` support.
- Show modules and actions by **exact permission code**, never by role name. UI hints never authorize; Django checks every request. Don't bypass the `*_ENABLED` feature gates.
- Never auto-retry POST, PUT or DELETE requests. Never claim success the server has not confirmed. Never reveal whether an ID or email exists.
- Don't reword or restyle owner-approved registration, OTP, conflict or review copy unless the task explicitly asks for it (see `../docs/workflows/`).
- Store only the theme preference (`ctug-theme`) in `localStorage`. Never store credentials, tokens or personal data in the browser.
- Don't change backend code, migrations, the ERD or permissions as part of a frontend task.

## When you change the design system

If you add or change a token, shared component or convention, update the matching file in `../docs/design/` in the same change. Mark new items **Current** and close the related AUDIT entry.
