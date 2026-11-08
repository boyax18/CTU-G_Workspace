# Test Results and Evidence — CTU-G Workspace

_As of 2026-11-08. Results transcribed from shared local terminal output/conversation; rerun when code or settings change._

| Area | Command | Observed result | Notes |
| --- | --- | --- | --- |
| Frontend build | `cd frontend; npm run build` | Passed, Vite build completed | TypeScript build and bundling, not browser authorization proof |
| Frontend tests | `cd frontend; npm test` | 25/25 passed | Registration and session client tests |
| Backend session/registration regression | `python manage.py test apps.accounts.test_session_auth apps.accounts.test_registration --settings=config.test_settings --noinput` | 44/44 reported passing | Separate isolated database runs; original full output not preserved here |
| AR-6A1 registration review | `python manage.py test apps.accounts.test_registration_review --settings=config.test_settings --noinput --verbosity 2` | 17/17 reported passing | Separate isolated database; original full output not preserved here |
| AR-6A2 Admin bootstrap | `python manage.py test apps.accounts.test_admin_bootstrap --settings=config.test_settings --noinput --verbosity 2` | 15/15 passed | Isolated MySQL DB; migrations applied; DB destroyed afterward |
| Django system check | `python manage.py check` | 0 issues | Before bootstrap operation |
| Bootstrap preflight | `python manage.py bootstrap_workspace_admin` | One Admin assignment / one bootstrap event, read-only | Historical post-provision observation |
| Permission catalogue | `python manage.py plan_permission_catalogue_v2` | Read-only, 0 conflicts | 105 CREATE, 4 MATCH, 108 DEFER; explicitly not approved for application |

## Evidence-quality rules

- The CLI output is the evidence for what was observed; passing tests do not establish production readiness, privilege policy correctness, or successful end-to-end UI integration.
- Keep a **sanitized** terminal log or CI run URL for each future run; redact real school IDs, emails, tokens, passwords, private DB config and personal data.
- Before database-changing operations, record the target DB/settings and a reversible plan; after changes, run read-only verification and note rollback strategy.
- For permissions, test both successful authorized access and refusal of unauthorized, denied, suspended, pending, cross-account, and object-scope violations.

## Regression command set (PowerShell)

```powershell
# Run from repository root in separate backend/frontend shells.
cd frontend
npm run build
npm test

cd ..\backend
python manage.py check
python manage.py test apps.accounts.test_session_auth apps.accounts.test_registration --settings=config.test_settings --noinput
python manage.py test apps.accounts.test_registration_review apps.accounts.test_admin_bootstrap --settings=config.test_settings --noinput
```

## Next evidence needed

- V2 catalogue schema/import plan with controlled, auditable activation tests and explicit review approval.
- Registration approval API tests for permission denial, self-approval, retries, CSRF/session, and atomic audit.
- Browser integration test: anonymous denied, authorized Admin approved, role assignment reflected in subsequent session, logout invalidates access.
