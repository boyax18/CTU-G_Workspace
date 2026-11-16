# CTU-G Workspace — Core Task 2 / G1D-P3C5

**Status:** OFFLINE-TESTED DRAFT ONLY; 21 isolated MySQL privilege checks NOT RUN; production release BLOCKED
**Base checkpoint:** owner-local `ronald` / `e5e3481` (13 November 2026)
**Scope:** add-only Python rehearsal, offline tests and this runbook. **Do not** modify `ctug_workspace`, `.env`, official `docs/database/full_schema.dbml`, migrations, settings or live role records.

## Why this checkpoint exists

P3C1–P3C4 found application writer entry points and observed database principals/privileges, but **none of those reports proved a database writer fence**. P3C5 demonstrates a narrow real SQL permission boundary in a newly created, destroyed Docker MySQL 8.4 container. It is *not* production integration.

The runtime needs legitimate account approvals, but it must not be able to create/activate/assign a protected Technical Super Admin role by issuing unrestricted SQL directly. A table-wide `INSERT` grant on `account_roles` cannot distinguish an ordinary Student assignment from a protected role assignment. Django policy checks alone cannot protect against a direct SQL writer holding that grant.

## Verified source-specific writer categories

The table below maps *observed source paths*, not necessarily distinct DB principals. Current production privileges are **unknown** beyond the earlier partial MySQL reports. All paths require a real per-principal DBA and deployment review before release.

| Observed Django source | Writes | Required production boundary/action |
| --- | --- | --- |
| `apps/accounts/registration_review.py` | `AccountRole.create` | Registration approval must have a protected-role-excluding DB pathway; cannot keep unrestricted `INSERT account_roles` and claim row fencing |
| `apps/accounts/admin_bootstrap.py` | `AccountRole.create` for normal Admin | Needs separate reviewed *normal Admin bootstrap* authority; framework `is_superuser` must not grant Technical Super Admin privileges |
| `apps/access_control/mutations.py` | `RolePermission.create`, `AccountPermission.create`, and updates | DB writer permissions must be tightly scoped; custom per-account overrides and governance catalogues need a robust row/service policy |
| `apps/access_control/management/commands/init_system_roles.py` | `Role.get_or_create` | Deployment/initialization principal must be separate from long-lived Django runtime; protected name reserved |
| `apps/access_control/management/commands/init_registration_review_metadata_local_dev.py` | `Service.create`, `Permission.create` | Local-dev bootstrap only; must not be a deployable privileged routine in runtime |
| `apps/access_control/management/commands/init_registration_review_inactive_bindings_local_dev.py` | `RolePermission.create` | Local-dev-only catalogue binding requires explicit environment gate and separate credential |
| `apps/accounts/management/commands/seed_review_sandbox.py` | `Role`, `AccountRole`, `Service`, `Permission`, `RolePermission` creates | Disposable sandbox only; do not run against production/live dev data |
| `apps/access_control/management/commands/prepare_g1d_p1_protected_role.py` | **No writes**: `--apply` rejects | Keep fail-closed until signed/trusted one-use executor and *real* writer fence exist |

This is a scoped matrix, **not** an exhaustive writer inventory. Hidden ORM `.save()`, raw SQL, remote jobs, Django shells and DBA sessions remain separate writer classes. Original scanner reported 14 direct mutation call sites across seven source paths.

## What the Docker rehearsal actually proves

It starts a **new, disposable** `mysql:8.4` container with `--network none`, **no host ports and no persistent Docker volumes**. It does not import Django settings, read any Workspace `.env`, or open the existing local MySQL service. Random temporary credentials are generated for root, web and a placeholder executor. All accounts/tables are inside the throwaway container and removed by `docker rm --force` on normal exit.

The intentionally simplified **synthetic schema** contains `roles`, `accounts`, `account_roles`, `role_permissions`, `account_permissions`, `access_audit_logs`. It seeds Student/Instructor/Admin roles plus an **inactive synthetic protected role fixture**. This does *not* provision a role in the user's actual Workspace.

The disposable web credential receives only SELECT on two tables and EXECUTE on an intentionally minimal stored demo procedure. It does **not** receive table DML or DDL privileges. The stored demo procedure allows only Student/Instructor assignments, creates an audit row inside the same transaction, and rolls back on failures. Its use of a fixed synthetic actor and caller-selected target is **not** adequate real-world user authorization and must never be copied into production unchanged.

The 21 isolated checks must establish:

- The web credential can connect but **cannot** directly insert into roles, assign a protected role, activate a protected role, alter permission tables, forge audit records, delete assignments or drop tables.
- Attempts to assign `Admin`, `Technical Super Admin` or `NULL` through the base-role demo procedure are rejected by the server.
- Student and Instructor demo assignments work, and duplicate insertion rolls back rather than duplicating audit records.
- A separate placeholder executor has **no** protected mutation or stored-procedure authority by default.
- The protected synthetic role stays inactive/unassigned and exactly the expected ordinary assignments and audit rows exist.

A denial is counted **only** when MySQL reports an expected privilege or explicit stored-procedure refusal code; a syntax error, failed authentication or unavailable server is never counted as a passing fence test. The script prints check names/statuses, not credentials or SQL grant contents.

## Local acceptance (Windows PowerShell)

Use Docker Desktop with the Linux-container engine running; obtain the official `mysql:8.4` image if required. **Do not fall back to your normal MySQL Community Server or `ctug_workspace` to make the rehearsal pass.** This code is a self-contained Docker proof and has no migration.

From `backend` using the project `.venv`:

```powershell
python -B manage.py test apps.access_control.test_task2_g1d_p3c5_fencing_rehearsal --settings=config.test_settings --noinput
python -B -m apps.access_control.tests_support.g1d_p3c5_docker_fence_test_only --ack P3C5_ISOLATED_DOCKER_ONLY
```

The companion installation script tests the offline module, performs this isolated Docker rehearsal, runs the full Accounts/Access Control regression, verifies `makemigrations --check --dry-run`, and commits **only** the three new paths after all gates succeed. No `git push`.

If Docker is missing, startup fails, or an expected rejection does not occur, **STOP**. The files can remain uncommitted for inspection. Do not bypass Docker and do not grant any production or local-MySQL users extra permissions to force success.

## Explicit missing gates

- The Docker fixture is **not the official ERD schema**; the production `account_roles` flow still writes directly and cannot yet use its narrow stored operation.
- The demo stored procedure does not authenticate actor identity, re-evaluate approval, validate target roles or implement dynamic access controls. It would be unsafe to install as-is.
- We have **not** integrated runtime credential separation in Django or the live MySQL instance. The earlier P3C4 report observed **two globally write-capable accounts** (partial view); that finding remains unresolved.
- No independently protected signer root custody, production authorization evidence, approved production ledger, verified live admission/session fence, migration plan, crash replay, backup/restore attestation, or real Technical Super Admin role provisioning.
- Production release stays **`BLOCKED`** even if all 21 Docker checks and the full Django regression pass.

**Next acceptance step:** use the real-path matrix to design and review the actual Django registration/normal-Admin bootstrap and permission-mutation DB interface. Coordinate an independently attested DBA privilege plan for *all* live writers, then migrate only after official ERD change-control and backup/recovery gates. P4/P5 must not create/assign privileged roles until those gates are met.
## Windows no-Docker source checkpoint (offline-only)

The original Docker-gated installation stopped safely because Docker is absent.
The offline suite passed 30/30 checks, but the 21 *actual MySQL* permission
checks were NOT executed. This source-only draft checkpoint allows code review
and regression tracking; it is NOT proof of an effective database writer fence,
not completion of G1D-P3C5, and not approval for P4/P5 protected provisioning.
The Docker runner remains an optional isolated proof harness, not a required
technology in the CTU-G Workspace stack.

Before marking G1D-P3C5's real SQL tests verified, run equivalent checks in a
physically separate, freshly initialized, disposable MySQL 8.4 instance with
its own data directory, listener and credentials. Verify the instance identity
and isolation before any schema or GRANT/REVOKE statements. Never point this
rehearsal at the existing MySQL service, `ctug_workspace`, a shared server, or
the application's actual credentials. If the independent instance cannot be
verified, the database proof remains NOT RUN and release remains BLOCKED.

Only the three test-only files are committed by the separate Windows offline
verifier. No user provisioning, live grant mutation, migration, official ERD
edit, or GitHub push is authorized by this draft checkpoint.