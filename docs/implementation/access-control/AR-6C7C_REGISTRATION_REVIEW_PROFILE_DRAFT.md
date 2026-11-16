# AR-6C7C — Registration Review Activation Profile (DRAFT)

**State:** PREPARATION ONLY — UNSIGNED, NOT APPROVED FOR DATABASE WRITES OR RUNTIME ACTIVATION
**Architecture:** CTU-G Workspace, existing Django/DRF, MySQL, hybrid dynamic access control
**Source:** Unchanged `backend/apps/access_control/catalogue/v2_0.json` proposal

## Objective and boundaries

Prepare an **offline, versioned, exact-subset validation** for the existing Admin Registration Review workflow. This is not a new permission architecture and not an alternative initializer. Preserve role union, direct Deny precedence, record-level authorization, Django Superuser separation, and the existing user workflow:

**Registration → Pending → Admin Review → Approval/Rejected Decision → Authorized Login → Shared Dashboard.**

## Proposed exact subset (no activation authority)

| Kind | Candidate | Status |
|---|---|---|
| Service | `accounts` | Metadata/activation BLOCKED |
| Service | `access_control` | Metadata/activation BLOCKED |
| Permission | `accounts.registration_requests.read` | SCHOOL, GOV, proposed |
| Permission | `accounts.registration_requests.approve` | SCHOOL, GOV, proposed |
| Permission | `accounts.registration_requests.reject` | SCHOOL, GOV, proposed |
| Role default | `Admin` → each of the three above | BLOCKED |

**Explicit exclusions:** `accounts.profile.self.read`, any non-Admin role binding, individual account overrides, full v2 manifest application, AR-6C5D background queue, and ERD/migration changes.

## Files in this preparation package

- `backend/apps/access_control/catalogue/registration_review_profile_v0_1_draft.json` — proposed allowlist and explicit blocked gates.
- `backend/scripts/plan_registration_review_profile.py` — pure-stdlib offline validator, **not** a database planner or write command.
- `backend/scripts/test_registration_review_profile.py` — offline positive and negative tests.

These are **new files**; do not overwrite existing ones. The offline validator reads only its draft profile JSON and the existing v2 catalogue JSON. It does not import Django, use ORM, query MySQL, access `.env`, inspect `.venv`, open `.gitignore`, touch Git, or write files.

## Manual inspection and test procedure (PowerShell)

From `C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend`:

```powershell
python -B scripts\plan_registration_review_profile.py
python -B scripts\test_registration_review_profile.py
```

Expected validator: 2 proposed services, 3 proposed permissions, 3 proposed Admin bindings; all activation gates BLOCKED; database NOT checked or changed. Expected tests: **10 passed**. These are candidate-definition checks, not running-DB state verification.

## Required future approvals — do not skip

1. System owner and an authorized security reviewer sign the exact subset/source digests and object-scope/retention policy.
2. Decide independent execution and accountability for protected governance grants; identify a legitimate attributable actor and tested audit contract. Existing first Admin bootstrap is not proof of protected grant approval.
3. Design and test a separate read-only **actual database diff** and explicit preview of metadata/grant/service activation, including what remains inactive.
4. Test the one-time initializer and rollback on a **disposable MySQL database**; ensure transaction safety, no duplicates, consistent locks, atomic audit and ability to recover from partial errors.
5. Separately approve any development database writes, then separately approve live review URL routing, API gates and browser E2E release.
6. Preserve rejected-account retention pending separate explicit policy approval; do not change the registration workflow.

**No part of this package authorizes code execution that mutates the database, changes privilege flags, starts background workers, or activates any API.**
