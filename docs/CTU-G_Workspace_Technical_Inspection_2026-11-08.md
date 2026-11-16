# CTU-G Workspace — Technical Inspection Report

**Inspection date:** 2026-11-08  
**Source:** User-supplied project ZIP (`CTU-G Workspace - Copy(1).zip`)  
**Method:** Static source and documentation review; isolated frontend tests; static catalogue check. Read-only; no project source files or databases modified.  
**Scope limitations:** Django/MySQL integration tests and live database checks were **not** rerun here. Git remote status and browser end-to-end behavior were **not** verified.

## Executive summary

**Assessment:** Authentication, registration, session handling, and the hybrid access-control foundation have substantial implementation and meaningful tests. The live Admin registration-review flow is deliberately disconnected. Academic, Finance, Clearance, Group Rating, Announcements, Notifications, Support, and Reports apps are scaffolded but lack business models/views. The shared dashboard is a session/profile placeholder rather than a permission-driven campus portal.

**Planning estimate:** About **25%** of the full proposed system is implemented; this is a rough scope estimate, **not** a measured requirements-completion metric. The core foundation is much further along than the full product.

## 1. What is implemented

| Area | Evidence in ZIP | Finding |
| --- | --- | --- |
| Django account and profile models | `backend/apps/accounts/models.py` | `Account`, `UserProfile`, requested role, review fields, custom auth manager; implementation present |
| Hybrid access-control storage | `backend/apps/access_control/models.py` | Roles, services, permissions, role/default grants, account overrides, audit logs |
| Effective permission evaluation | `backend/apps/access_control/services.py` | Database-derived, fail-closed evaluation; active assignment prerequisites; individual Deny precedence |
| Public Student/Instructor registration | `backend/apps/accounts/views.py`, `serializers.py`, `services.py`; frontend registration components | Payload validation, pending/inactive account creation, duplicate response handling, CSRF and throttling logic |
| Browser session login/logout | `backend/apps/accounts/session_auth.py`; `frontend/src/features/auth/session.ts`; `frontend/src/features/home/components/HeroSection.tsx` | Session API wired to embedded homepage login; session rechecks account/assigned-role eligibility |
| Registration approval service | `backend/apps/accounts/registration_review.py` | Transactional approval/rejection and audit logic with guarded feature flag |
| Registration Review API | `backend/apps/accounts/registration_review_api.py`, `registration_review_urls.py` | Candidate pending-list/approve/reject endpoints with authorization and CSRF controls; **not wired into live `config/urls.py`** |
| First Workspace Admin bootstrap | `backend/apps/accounts/admin_bootstrap.py`; management command | One-time bootstrap logic exists; local provisioning is reported in docs, not rerun here |
| Permission catalogue planning | `backend/apps/access_control/catalogue/v2_0.json` and scripts | 10 services, 95 permissions, 106 proposed role bindings; planning-only and approval blocked |
| Project documentation | `docs/SRS`, `docs/database`, `docs/implementation`, `docs/testing` | Detailed SRS, two ERD files, decisions, status, API contract, test matrix, changelog |

### Routes actually present in the root configuration

`backend/config/urls.py` includes Django Admin (`/admin/`) and authentication URLs (`/api/v1/auth/`). `backend/apps/accounts/urls.py` defines CSRF, registration, login, logout, and session routes. The three registration-review endpoints exist **only in a separate URLconf** and are not available through the application's root URLconf.

### Frontend routes actually selected by `App.tsx`

`/` (homepage with embedded login), `/register`, and `/dashboard`; other paths currently show the not-found component. Homepage About/Services/Announcements/Help/Contact components exist as sections, but standalone routes for them are not configured here. `SessionDashboardPage.tsx` displays the current school ID, assigned roles, and sign-out, not the final permission-driven modules.

## 2. Main gaps against the SRS and 42-table ERD

- The full ERD contains **42 application tables**; the auth-only ERD contains **9**. The code has concrete app models for the 9 authentication/access-control tables; most other ERD areas remain unimplemented.
- The following installed Django applications have near-empty `models.py` and `views.py`: `academic`, `finance`, `clearance`, `group_rating`, `announcements`, `notifications`, `support`, `reports`.
- No live Admin registration-approval interface or active registration-review API integration.
- No activated V2 service/permission catalogue or approved role-permission defaults.
- No complete permission-aware dashboard or Admin role/permission customization screens.
- No connected academic, payment/receipt, clearance, rating, messaging, reporting, or notification workflows.
- No verified complete browser registration -> Admin approval -> login -> dashboard acceptance flow.
- Flutter mobile and AI-agent features are future scope, not present as completed integrations in this snapshot.

## 3. Independently performed verification

| Check | Command/method | Result |
| --- | --- | --- |
| Frontend Node tests | `node --experimental-strip-types --test tests/*.test.mjs` from extracted `frontend/`; only needed JS dependencies copied from ZIP | **25/25 passed** |
| Python syntax | `ast.parse` of all extracted project backend `.py` files | **126/126 parsed** |
| Registration-review catalogue check | `python scripts/check_registration_review_catalogue.py` from extracted `backend/` | **Passed**; 10/95/106 planning records and three proposed Admin review permissions confirmed |
| Django/MySQL integration and migration history | Not executed: no project Django/MySQL development environment available in inspection runtime | **Not independently verified**; previous successful runs are historical user-provided evidence |
| Vite production build / browser tests | Not executed in this inspection runtime | **Not independently verified**; historical frontend build claim is documented |

A direct Node test run without the `--experimental-strip-types` flag initially failed because this inspection runtime's Node 22.16 did not enable TypeScript type stripping by default. Retesting with the flag succeeded (25/25); this was an **environment invocation issue**, not an application test failure.

## 4. Findings requiring attention

### F-01 — HIGH: Private/local files included in shared archive

**Evidence:** The uploaded ZIP contains `backend/.env`, `backend/db.sqlite3`, `.git/`, `.venv/`, and `node_modules/`. They were intentionally excluded from the analysis copy; their contents were not inspected. Do **not** forward the original ZIP to teammates. Repackage source-only files, review the resulting archive, and rotate any actual credentials if they were shared beyond a trusted channel. `.gitignore` alone does not remove files already copied into a ZIP.

### F-02 — HIGH: Protected ERD hashes no longer match recorded pins

**Evidence:** `backend/scripts/verify_catalogue_plan.py` and several docs pin these raw SHA-256 values:

| File | Expected prefix | SHA-256 in ZIP (prefix) |
| --- | --- | --- |
| `docs/database/full_schema.dbml` | `e9235a87555ffcd5…` | `e4362be913280ab6…` |
| `docs/database/schema.dbml` | `f050f7b910038532…` | `3bc2060ae35fce16…` |

The snapshot files use CRLF line endings; converting to LF in memory **also did not reproduce** the recorded pins. This might reflect edits or another byte-level normalization/version difference, but the exact cause is **not established**. The read-only verifier is written to refuse mismatched fingerprints. **Do not overwrite, normalize, re-pin, or regenerate either ERD automatically.** Compare the current files with the approved original and Git history, then document an authorized resolution.

### F-03 — HIGH/BLOCKER: Admin approval is intentionally not operational

**Evidence:** `backend/config/urls.py` does not include `registration_review_urls.py`. `registration_review_api.py` checks both `WORKSPACE_REGISTRATION_REVIEW_API_ENABLED` and `WORKSPACE_REGISTRATION_APPROVAL_ENABLED`, each defaulting to `False` if absent. Permission grants/services remain unactivated. This is a **planned security gate**, not an accidental missing endpoint. Do not bypass it to make the UI appear functional.

### F-04 — MEDIUM: Full campus workflows are not yet implemented

**Evidence:** The eight business-service apps still contain default model/view placeholders. Only 9 authentication/access-control models have substantial implementation compared with the 42-table target ERD. Finance, Clearance, Academic, Group Rating, Reports and related workflows need requirements-to-ERD mapping and planned migrations **after** authorization.

### F-05 — MEDIUM: Development-only deployment configuration

**Evidence:** `backend/config/settings.py` hardcodes `DEBUG = True` and `ALLOWED_HOSTS = []`; no production-ready `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, proxy/host settings, configured distributed throttling cache, or production logging policy appears in the inspected settings. Fine for a restricted local development workflow; not production-ready. Existing DRF rate throttles rely on the default cache unless otherwise configured; that should be reviewed before multi-worker deployment.

### F-06 — LOW: Repository hygiene and status wording

**Evidence:** `backend/apps/accounts/admin_bootstrap.py.bak`, `backend/apps/accounts/management/commands/__init__ (2).py`, and `frontend/src/hooks/useInView,.ts` appear to be duplicate/backup or stray files. Confirm their purpose before cleanup. `backend/requirements.txt` is UTF-16LE; UTF-8 would be more conventional for cross-platform tooling, subject to review. `docs/DEVELOPMENT_STATUS.md` accurately lists AR-6C2 as tested but its last line still says documentation synchronization is underway. Git remote push status cannot be confirmed from the code snapshot alone.

## 5. Recommended execution order

1. **Repository/privacy and integrity check:** Ensure a source-only share archive; confirm Git tracking and remote branch; investigate mismatched protected ERD fingerprints without editing the ERD.
2. **AR-6C3 readiness:** Record exact API security/governance blockers, state/permission dependencies, release gates, and deployment constraints. Do not activate endpoints.
3. **Explicit governance decision and controlled catalogue initialization:** Approve applicable V2 codes, role defaults, service activation and audit/session policies before enabling real registration approval.
4. **Admin Registration Management UI:** After authorization, implement a permission-aware pending queue, approve/reject confirmation, denial states, and audit-aware feedback; keep the server as the final authority.
5. **First complete vertical slice:** Verify Student/Instructor registration -> Pending -> authorized Admin review -> assigned role -> login -> real dashboard end-to-end in a controlled environment.
6. **Business modules:** Map SRS workflows to the protected ERD; build Academic foundations followed by Finance/Clearance and supporting modules, with tests and documentation each phase.

## 6. Suggested next coding task

**Do not start a new Finance or Clearance implementation yet.** Start with a narrowly scoped **AR-6C3 readiness + ERD fingerprint provenance check**, using read-only commands and existing source files. This gives the team a concrete list of blockers before any live permission activation or new schema migration.

---

**Report integrity:** This report documents what could be verified from the uploaded archive and explicitly distinguishes source-code presence, local automated tests, historical reports, and unverified operational claims. No changes were made to the user's original project ZIP.
