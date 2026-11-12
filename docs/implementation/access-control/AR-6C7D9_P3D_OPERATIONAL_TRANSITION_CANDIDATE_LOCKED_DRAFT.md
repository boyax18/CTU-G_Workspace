# AR-6C7D.9 — P3D Operational Transition Candidate (Local Writes Locked)

**Project:** CTU-G Workspace
**Status:** Test candidate only; NOT approved for local activation or release
**Baseline:** `ronald` at `dc9f6a2`; P3C 249/249 tests passed, exact Admin scope ID `3`
**Database:** Local MySQL `ctug_workspace` is read-only for this milestone; isolated `config.test_settings` is used for transition tests

## 1. Scope

This change adds a **previewable operational transition candidate** for the existing Registration Review catalogue. It does NOT change the ERD, add migrations, change accounts, assign or remove roles, enable any flags, mount URLs, send email, or execute an activation on `ctug_workspace`.

The candidate reuses existing P1/P2/P3B/P3C security checks: MySQL target identity, frozen catalogue and audit provenance, exact Admin role account IDs, no account-level overrides, transaction isolation, unmounted review URLs, and disabled API flags. The **local-development write gate is hard-coded shut** in the new command. Even `--apply` cannot bypass it in `config.settings`; there is no live execution confirmation token.

## 2. Files

1. `backend/apps/access_control/management/commands/transition_registration_review_p3d.py` — read-only local preview and test-only transactional transition candidate.
2. `backend/apps/access_control/test_registration_review_operational_transition_p3d.py` — isolated MySQL tests for preview, activation, compensation, audit, rollback and local-write refusal.
3. This design/release-blocker document.

## 3. Planned transitions (test database only)

**Activation:** Verify exact P1/P2 rows and eight original receipts, current inactive services and three inactive Admin role bindings, exact eligible Admin account IDs, disabled feature flags, and zero effective review permissions. Acquire the shared advisory lock and a durable MySQL transaction. Activate **two services** and **three bindings** with exactly **five** transition receipts. Re-check provenance and the precise effective grant set before committing.

**Compensation:** Require the already active exact five rows and verified activation receipts; refuse any earlier compensation. In one durable transaction deactivate three Admin bindings **before** deactivating two services, append five compensation receipts, check no unintended effective grants, and keep all previous audit rows. Do not delete or undo audit receipts.

At all times an unexpected or framework-privileged Admin assignment, per-account override, altered receipt, partial transition, enabled API flag, changed route, database mismatch or mid-transaction audit failure must fail closed. This is a candidate, not a claim of comprehensive security assurance or production readiness.

## 4. Install and run local tests

Extract the ZIP to the CTU-G Workspace **root**. From `backend/`, with `.venv` active:

```powershell
python -B manage.py test apps.access_control.test_registration_review_operational_transition_p3d --settings=config.test_settings --noinput
if ($LASTEXITCODE -ne 0) { throw 'P3D isolated tests failed; stop.' }
```

Run the full P3C 249-test regression **plus** the P3D test module after the isolated tests pass. Do not use `--keepdb` and do not run the tests using `config.settings`.

## 5. Read-only local preview

```powershell
python -B manage.py transition_registration_review_p3d --mode activate --actor-account-id 3 --expected-admin-account-ids 3
```

Expected on the previously inspected inactive state: `PREVIEW PASSED; ... ACTUAL WRITES BLOCKED`. This read-only check does not prove that a backup exists or that it can be restored. **Do not use `--apply` against `ctug_workspace`**: the code explicitly rejects it. Previewing compensation while services are inactive is expected to refuse; compensation preview is meaningful only for an actual active exact state.

## 6. Hard blockers before a separate operational release

- A full private schema-and-data export of `ctug_workspace` and successful **restore to a separate schema**, with matching tables/counts, documented operator/time and backup location **outside Git**. Never restore over the source during rehearsal.
- An impact review and explicit owner approval for the complete eligible Admin ID set, rechecked just before any write. Previous inspection showed only `3`; that is not a permanent guarantee.
- A separately reviewed operational release adapter that can safely enable local writes **without weakening** the target, scope, transaction, audit or feature flags checks. The current package intentionally does not include that adapter.
- Authenticated API negative and positive tests; concurrent registration decisions, session/CSRF/Origin, notifications/outbox, and emergency disable/runbook evidence. P3C covers important authorization cases but not every production scenario.
- Separate decision and coordination for service/grant activation versus API route and frontend rollout. **Activating services/bindings creates effective grants, even while the API route is unmounted.**

The only operations permitted by this P3D package are an inspection of the existing local database and disposable test transitions. Neither a local Git commit nor a 249-test pass demonstrates a restorable MySQL backup.

## 7. Git safety

After tests pass, stage only the three paths in Section 2 on `ronald`; check `git diff --cached --name-status` and `git diff --cached --check`. Never stage unrelated `docs/database/full_schema.dbml`, `.env`, `backend/apps/config/`, or other draft files. A commit is not a push.
