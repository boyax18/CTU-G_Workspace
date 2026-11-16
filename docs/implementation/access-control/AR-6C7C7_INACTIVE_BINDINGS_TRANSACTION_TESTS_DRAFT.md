# AR-6C7C.7 — Isolated Inactive Admin-Binding Transaction Tests

**Project:** CTU-G Workspace

**Status:** Test-support code only. NOT approved for live grants, service activation, APIs, or deployment.

## Purpose

Exercise the existing `RolePermission` model and transactional access audit in disposable MySQL without creating effective user privileges. This is not a protected production initializer and does not supply governance approval.

## Strict boundaries

- The test-support module refuses non-`config.test_settings` disposable database names and verifies the selected MySQL database via the existing AR-6C7C.6 test guard.
- Reuses the frozen blocked registration-review profile and metadata fixture, unchanged.
- Creates only three **inactive** Admin role bindings with a persisted synthetic test actor, with one bounded audit record per new binding.
- Does not activate either service, assign users to roles, create individual overrides, or modify the official ERD.
- Running again against the same matching fixture creates no duplicate bindings or audit events.
- No management command, API, worker or production service calls this fixture.
- A synthetic test actor provides audit attribution **only**. It is not authority to make protected grants in the real application.

## Files

- `backend/apps/access_control/tests_support/registration_review_inactive_grants.py`
- `backend/apps/access_control/test_registration_review_inactive_grants.py`

## Test command

Run in `backend/` using a separately created temporary MySQL test database, never `ctug_workspace`:

```powershell
python -B manage.py test apps.access_control.test_registration_review_inactive_grants --settings=config.test_settings --noinput
```

Do not add `--keepdb` or `--parallel`. Afterwards, run combined regression with existing audit, mutation and metadata tests.

## Future work (not authorized by this test package)

The real protected-grant workflow requires institutionally approved operator authority, independent review, an approved versioned activation profile, live-DB preview, transactional audit and explicit activation/rollback gates. The current documentation remains unsigned. No part of this package grants or implies such authority.
