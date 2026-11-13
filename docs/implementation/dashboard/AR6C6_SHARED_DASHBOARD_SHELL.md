# CTU-G Workspace — AR-6C6 Shared Dashboard Shell

**Scope:** Shared responsive dashboard foundation (React, TypeScript, Tailwind + existing CTU-G theme).

## Existing architecture retained

`frontend/src/App.tsx` already mounts `<DashboardLayout><SessionDashboardPage /></DashboardLayout>` for `/dashboard`. This patch extends the **existing** `DashboardLayout.tsx` and `SessionDashboardPage.tsx`. It does not create a second Admin dashboard or register new backend routes.

`DashboardLayout` fetches the existing `/api/v1/auth/session/` using the existing `session.ts`. Until the backend returns `authenticated: true`, neither the sidebar nor dashboard content appears. Failed session requests fail closed with a retry option.

The shared shell provides a responsive sidebar, mobile navigation overlay, header, breadcrumbs, theme switch, school-ID summary, and CSRF-protected sign-out using the existing session client. The view is controlled by `/dashboard?view=<module>`; the root `/dashboard` remains Overview.

## Navigation and access policy

`navigation.ts` is the only list of navigation items. Overview and My Account are always available **only inside a verified session**. Additional module spaces require an exact *read* permission hint in `session.permissions`; matching a role name never grants navigation access. A module is only a clearly labeled placeholder until its live API and UI have been approved.

**Important:** Client-side navigation filtering is not authorization. Every protected backend endpoint must validate the current Django session and effective Hybrid Dynamic Access Control permissions. The frontend never invents permissions, grants access, or bypasses Deny rules.

AR-6C5C Admin registration review and AR-6C5D bulk processing remain detached/disabled. No new database model, migration, `.env` value, frontend dependency, or backend route is added by this patch.

## Compatibility guard

The installer checks SHA-256 hashes of these two **existing** files against the November 8 project snapshot:

- `frontend/src/layouts/DashboardLayout.tsx`
- `frontend/src/features/dashboard/SessionDashboardPage.tsx`

If either is different, installation **stops without writing**. Inspect the current versions before attempting a manual merge; do not force overwrite. A successful apply writes a private backup of both files **outside the Git repository**.

## After installation

From project root:

```powershell
cd frontend
npm test
npm run build
npm run dev
```

Visit the actual frontend Vite URL at `/dashboard` while Django is running and you are signed in with an approved Workspace account. If not authenticated, the shell correctly displays "Sign in required". Sidebar module spaces are revealed only when the session endpoint returns corresponding effective read-permission hints.

Use `git diff --check`, `git status --short`, and review the diff before staging changes. Keep the unrelated technical inspection file unstaged unless intentionally included.

## Verification performed on an earlier project snapshot

- TypeScript `tsc -b`: passed.
- ESLint on changed source files: passed.
- 35/35 frontend Node tests passed using a Node 22 type-stripping flag; 10 new dashboard navigation tests included.
- Full Vite bundle was not executable in the Linux validation environment because the uploaded Windows `node_modules` archive lacked the Linux Rolldown native binding. Verify `npm run build` locally on Windows.

## Deferred scope

Admin registration review table, live module pages, notifications, role/permission management, and 200-account background queue are separate development phases. This patch deliberately creates no fake financial totals, clearance statuses, or registration counts.
