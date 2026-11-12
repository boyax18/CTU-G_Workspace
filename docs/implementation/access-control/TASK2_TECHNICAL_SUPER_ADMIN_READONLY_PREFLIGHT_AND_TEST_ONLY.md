# CTU-G Workspace — Task 2 Technical Super Admin
## Approved D1–D5: read-only preflight and isolated test-only contract (candidate)

**Status:** implementation candidate, **not activated**, **not committed**; Windows/Django/MySQL acceptance tests pending.

**Source reconciliation:** inspected uploaded `CTU-G Workspace - Copy (2).zip` source snapshot based on `df29a52`, and the separately uploaded Task 1 files/patches. The project owner reported current local `ronald` HEAD `462f4ec`. This package adds only new files; current local working tree and live database cannot be inspected from the authoring environment. The operator must confirm `git` preflight and run the tests before staging or committing anything.

**Process:** Inspect → Reconcile → Approve (D1–D5) → Implement (this candidate) → Test (pending on Windows) → Document (this draft) → Commit (pending) → Continue (pending).

## Approved boundaries

- Exactly **two application administrator profiles**: Normal Admin (`Admin`) and Technical Super Admin (`Admin` plus protected `Technical Super Admin` role). Separate Django `is_superuser` is framework maintenance, **not** application Technical Super Admin.
- Exact case-sensitive protected role label: `Technical Super Admin`. No new role is created by this package.
- Effective permissions must still come from the existing `services`, `permissions`, `role_permissions`, and `account_permissions` evaluator, including account-level Deny precedence and active/approved account state.
- Ordinary delegation has a reserved-role prohibition; no generic API may grant or revoke the protected role.
- A Technical Super Admin *identity/profile* requires both active role assignments, but governance permission checks alone are not proof of this composition. The existing evaluator grants a role's specific permission to an eligible account assigned **only** the technical role. **Therefore, an eventual protected governance endpoint must check both the complete profile and specific evaluated permission under a trusted, freshly locked transaction before modifying anything.** The new reference helper demonstrates this only in test fixtures; it is **not** deployed as a production authorization guard.
- No first-admin bootstrap, governance permission catalogue, technical role grants, activation, last-effective-Super-Admin protection, recovery flow, or operational management endpoint is implemented or approved for live use.

## Files in this add-only candidate

1. `backend/apps/access_control/management/commands/report_technical_super_admin_preflight_p2.py` — exact-scope read-only local inventory. Requires current `config.settings`, DEBUG true, MySQL loopback, configured and connected DB `ctug_workspace`, `--expected-db ctug_workspace`, and `--ack READ_ONLY_PREFLIGHT`. It issues SELECT only, reports aggregate counts and stops on ambiguous protected role names. It prints no account IDs, School IDs, email addresses, secrets, or credentials. It does **not** attest effective privilege or readiness for provisioning.
2. `backend/apps/access_control/tests_support/technical_super_admin_test_only.py` — **simulation helper strictly for disposable test fixtures**. There is no registration of it in routing, authentication, settings, or real governance services.
3. `backend/apps/access_control/test_task2_technical_super_admin_contract.py` — disposable MySQL test suite requiring `config.test_settings` and independently checking the generated test schema. Covers role composition, exact permission unions, explicit Deny precedence, status/service gates, role-only privilege risk, framework superuser separation, and absent write operations in the helper.
4. This documentation.

## Commands (VS Code PowerShell, non-mutating preflight)

From `backend`, with virtualenv active:

```powershell
python -B manage.py report_technical_super_admin_preflight_p2 --settings=config.settings --expected-db ctug_workspace --ack READ_ONLY_PREFLIGHT
```

The command only reads `ctug_workspace` and produces aggregate counts. It does not establish that a candidate is safe to elevate. If any protected roles or grants already exist, reconcile their history before further design.

## Commands (isolated tests — never `config.settings`)

```powershell
python -B manage.py test apps.access_control.test_task2_technical_super_admin_contract --settings=config.test_settings --noinput
```

`config.test_settings` uses an unpredictable `test_ctug_registration_...` MySQL schema and the custom isolated test runner. The tests create fictional roles, accounts, grants, and overrides **inside that disposable test database only**, and the runner destroys it after testing. Never run this test module with normal or local review settings. It deliberately refuses those settings.

Follow with prior access-control + accounts tests, then `makemigrations --check --dry-run --settings=config.settings` when the read-only stage is accepted. No migrations or ERD modifications should be needed; any drift stops the phase.

## Known outstanding gates (not solved by green tests)

1. Approve the precise governance catalogue and default grants, including protected mutation permission codes.
2. Approve first Technical Super Admin trusted bootstrap, identity proof, dual-authorization and emergency recovery; never auto-promote existing Admin ID 3 or a framework superuser.
3. Implement protected role assignment/removal and governance management as a separate authorized and audited service. Require complete two-role profile, fresh permission evaluation, self-promotion denial, effective-last-Super-Admin protection, transaction/concurrency safeguards, evidence receipts, and session-revocation approach.
4. Establish verified backup/restore readiness before any governance writes to the real database.
5. Implement UI only after service contracts exist, gate real operations disabled by default, and verify audit and permission boundaries with isolated tests.
6. Preserve normal Registration Review, reapplication, SMTP, and bulk approval/rejection gates unchanged.

## Acceptance / commit discipline

- Confirm current branch `ronald` and HEAD `462f4ec` before extracting; if different, reconcile rather than overwriting or cherry-picking blindly.
- Confirm the four destination files do not already exist; these are **add-only**. Do not stage or commit `docs/database/full_schema.dbml`, `.env`, `review_only`, `Scripts`, or teammates' other files.
- Static compile and static no-write inspection may be executed in the candidate environment; **Django/MySQL tests and actual read-only inventory must run locally**, since the authoring environment does not have Django or the user's MySQL database.
- Do not commit until the user reports test and preflight outputs, checks migration drift, and reviews the exact staging list.

**Approval scope:** the owner approved D1–D5 for read-only preflight and isolated test-only implementation only. No privilege elevation or live activation is authorized.
