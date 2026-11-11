# CTU-G Workspace — AR-6C7D.1 Mock-Only Admin Registration Review UI

**Status:** TEST/REHEARSAL DESIGN ONLY; NOT LIVE; NOT PERMISSION GRANT OR FEATURE ACTIVATION APPROVAL.

## Scope

This package adds a **fictional**, client-local preview of the existing Registration Review dashboard module. It uses the shared React `DashboardLayout` and existing `registration-review` navigation ID; it does **not** create a separate login, alter role aggregation, or modify the registration workflow.

### New files

- `frontend/src/features/admin/RegistrationReviewPreview.tsx` — sample pending queue, role and School ID filters, individually simulated approval/rejection, non-sensitive bounded reason selections, and prominent mock-data warning.
- `frontend/src/features/admin/registrationReviewPreviewModel.ts` — fictional data and pure simulation functions.
- `frontend/src/features/admin/registrationReviewPreviewGate.ts` — hard-disabled `REGISTRATION_REVIEW_UI_PREVIEW_ENABLED: boolean = false`.
- `frontend/tests/registration-review-preview.test.mjs` — offline logic/security regression tests.
- `frontend/scripts/apply_ar6c7d1_preview_patch.py` — user-opt-in targeted patch for the existing dashboard page with baseline digest validation and a Downloads backup.

### Existing file requiring one narrow edit

- `frontend/src/features/dashboard/SessionDashboardPage.tsx`: add two imports and a branch that renders the preview **only when** the existing permission check passed **and** the new flag is enabled. The flag remains `false`. If disabled, the existing placeholder is unchanged.

## Security and development gates

1. **No actual API requests, CSRF bootstrap, HTTP mutations or MySQL access.** All data is invented, never derived from student records.
2. Mock action buttons additionally depend on exact `read` + `approve` or `read` + `reject` hints. This is UI-only; it is never authorization.
3. Live Registration Review routes in Django remain detached; both backend feature gates remain disabled.
4. No services, permissions, role assignments or grants are created or activated.
5. Preserve existing `Admin` vs Django Superuser, multi-role union, direct Deny precedence, and pending-review/approval workflows.
6. AR-6C5D bulk queue and official DBML are untouched. No real bulk actions are implemented.

## Installation and verification

1. Extract only the provided add-only files. Stop on any pre-existing destination.
2. At repository root, execute `python -B frontend/scripts/apply_ar6c7d1_preview_patch.py --check`; review the preflight output.
3. Only if approved, execute the same script with `--apply`. Its backup is saved in Downloads.
4. Inside `frontend/`, run `node --test tests/registration-review-preview.test.mjs`, `npm run build`, `npm test`, and, if available, `npm run lint`.
5. Review the Git diff and stage only approved AR-6C7D.1 files; don't use `git add .`.

**Acceptance at this milestone:** Code builds and new and existing tests pass. Do not claim that an Admin can actually review real registrations. Live integration comes after separate security/governance approvals.
