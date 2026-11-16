# AR-6C7C.4 — Protected Initialization Preparation (DRAFT)

**Project:** CTU-G Workspace
**Status:** READ-ONLY PREPARATION; NOT AN AUTHORIZATION, INITIALIZER, ACTIVATION OR RELEASE
**Scope:** Registration Review permission metadata and protected Admin defaults only

## Purpose

Convert the existing version-pinned, offline `registration_review_profile_v0_1_draft.json` into a **read-only database-aware preflight**. Reuse the existing `build_plan_v2()` and its MySQL `READ ONLY` / SELECT-only snapshot. This new module cannot execute changes. Existing application models, Django session/CSRF, hybrid role union, account Deny precedence and Django Superuser separation are unchanged.

## Proposed subset; all write/activation gates remain blocked

| Kind | Exact proposed records | Intended future state, not applied |
|---|---|---|
| Service | `accounts`, `access_control` | Created as *inactive metadata*, only after metadata approval |
| Permission | `accounts.registration_requests.read`, `.approve`, `.reject` | Three definitions owned by `accounts`, `SCHOOL` scope, `GOV` protection |
| Role | Existing `Admin` | Reuse; no new Admin role, account or role assignment |
| Role default | `Admin` to each permission above | **DEFER** until independent protected-grant approval and auditable executor |
| Service activation | Both services | **BLOCKED**, separately approved after readiness testing |
| Registration Review routes/feature switches | Existing detached API | **BLOCKED**, separate API activation and acceptance |

**Not part of this work:** `accounts.profile.self.read`, direct account overrides, other catalogue permissions, additional roles, AR-6C5D bulk queue, new models/migrations, role-switch behavior, password recovery or changes to registration rejection policy.

## Added files

1. `backend/scripts/registration_review_initialization_preflight.py`: pure function extracting and validating only the proposed subset from an already generated v2 planner report. Fails closed on report conflicts, unexpected records, active grants, missing/duplicate matches, missing read-only evidence and changed static provenance. Has no DB imports or write operations.
2. `backend/apps/access_control/management/commands/plan_registration_review_initialization.py`: an **inspection-only** Django management command that calls the existing v2 read-only planner and pure preflight. Supports only `--format text|json`. No apply/execute/approve argument, ORM create/update/delete, or service/grant mutation.
3. `backend/scripts/test_registration_review_initialization_preflight.py`: standard-library, in-memory tests using constructed read-only report data. No Django, database, `.env`, `.venv`, Git or network access.

## Manual commands (Windows PowerShell)

From `C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend` with the existing virtual environment already activated:

```powershell
python -B -m unittest scripts.test_registration_review_initialization_preflight -v
python -B manage.py plan_registration_review_initialization --format text
```

The first is offline; the second makes SELECT queries in the **existing read-only MySQL planner transaction**. **Do not run a proposed write command; none is included.**

Expected summary in current known state: `CREATE` for 2 services and 3 permission definitions, `DEFER` for 3 Admin role bindings, `GATES all BLOCKED`, `EXECUTION AUTHORIZED NO`, `WRITES PERFORMED NO`.

This read-only preflight deliberately **refuses** to generate a seemingly ready plan if unexpected/retired/override records or conflicts are detected, even outside the limited subset. It requires independent manual review in those cases.

## Required future implementation design and approvals (not included)

- Record the institutional owner and independent security reviewer, exact accepted source/profile digest, scope and change-ticket evidence. The draft profile is intentionally unapproved and cannot be converted into an approval merely by changing a flag.
- Specify a separately reviewed protected execution entry point, a legitimate attributable operator **distinct from ordinary self-grant**, stable parent/role lock order, uniqueness enforcement, replay/idempotency and exact permitted write-set.
- Verify the audit contract for **every** metadata creation, protected role grant and service activation. The existing `access_audit_logs` restricts action, reason and snapshot fields; don't assume it already authorizes every new event type. Audit failure must roll back security mutation.
- Use isolated disposable MySQL for mutation, concurrency, rollback, duplicate-run, Deny precedence, inactive service, session revocation and negative-security tests. No live DB writes before explicit review of execution SQL and rollback impact.
- Approve **metadata creation**, **protected role grants**, **service activation**, **API routing/feature flags**, and **deployment** separately. The approved source manifest must not be silently altered; the 95-definition/106-binding v2 proposal is not an activation grant.
- For live Registration Review later: preserve `Registration → Pending → Admin Review → Decision → Authorized Login → Shared Dashboard`, with Student/Instructor base-role validation, object authorization, CSRF and transactional review audit.

## Acceptance status

This document and the added command provide **review evidence only**. Tests of the pure preflight do not establish a working DB initializer; MySQL integration must be verified on the owner's local machine. The governance sign-off remains blank.
