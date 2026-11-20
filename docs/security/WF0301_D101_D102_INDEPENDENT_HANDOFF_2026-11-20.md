# WF-03.01 — D-101 Independent Review and D-102 Authorization Handoff

**Prepared:** 20 November 2026, after the owner's confirmed D-114 local commit `e3334f5` on `ronald`.
**Status:** AUTHOR-PREPARED HANDOFF ONLY. D-101 **OPEN**, D-102 **DESIGN APPROVED / IMPLEMENTATION BLOCKED**.
**Environment:** local development only. No feature activation, database migration, live grant, catalogue consumer switch or tests are authorized by this record.

## 1. Scope and established source of truth

Use the existing documents, not a replacement sign-off form:

- `docs/security/WF-03.01_D-89_CATALOGUE_V2_1_INTEGRITY_REVIEW_PACKAGE.md` §§7, 14, 15, 19 — independent reviewer decision forms, evidence, exact source bytes, handoff.
- `docs/security/WF-03.01_D-101_TECHNICAL_PRE_REVIEW.md` — findings F-1–F-7; author-side pre-review is **not** independence.
- `docs/security/WF-03.01_PROTECTED_PROVISIONING_READINESS.md` §§1, 3, 3.5, 3.6, 4 — D-102 owner-approved design, risks, and prerequisites.
- `docs/decisions/DOCUMENTATION_DECISION_REGISTER_DRAFT.md` — authoritative decision status; do not mark OPEN as approved merely because these files are committed.
- `docs/workflows/CTU-G_Workspace_System_Workflow_Catalogue.md` — keep its existing structure and Human Approval unchecked until evidence exists.

D-101 has a narrow scope: v2.1 pin chain **first** (`14125f9` and validator correction `9e259e7`), then v2.2 (`28d46e1`). Owner target D-104 is v2.2; v2.1 is only a verified dependency. The implementation author cannot provide independent approval. The original handoff records 19 pinned artifacts, exact Git blob IDs, expected SHA-256 digests and a reproduction procedure.

The owner's subsequent staged implementation commits (D-87, D-100, D-110, D-111, D-112, D-113, D-114) are **not** D-101 sign-offs and do not themselves authorize D-102. Source changes must be reviewed for scope drift before using old reported results.

## 2. Read-only static preflight (helper, NOT a review)

An optional author-produced tool is included: `docs/security/reviewer_tools/wf0301_d101_static_integrity.py`.
It reads committed Git blob bytes and compares the 19 pinned files with the expected Git blob ID and SHA-256 at the scoped historical commit and at HEAD. It does not use PowerShell binary pipes, Django, credentials or a database; it does not run tests.

From the repository root on Windows:

```powershell
$python = if (Test-Path 'backend\.venv\Scripts\python.exe') { 'backend\.venv\Scripts\python.exe' } else { 'python' }
& $python docs\security\reviewer_tools\wf0301_d101_static_integrity.py --repo .
if ($LASTEXITCODE -ne 0) { throw 'Static pin mismatch: STOP and reconcile source bytes.' }
```

A green output is only an author-provided convenience, **not** evidence of an independent sign-off. The reviewer must independently inspect trusted historical commits, verify the pin and delta semantics, reproduce validator results and tests under disposable test settings, and document any findings (original package §19.5). The agreed WF-03 test deferral means the required tests have **not** been rerun now; approval cannot be represented as complete on that basis.

## 3. D-101 decision gate — independent reviewer only

1. Confirm reviewer independence, role, and authority; obtain access to the exact commits. Given the user's `ronald` branch is locally ahead/remote behind, verify availability of historical objects rather than trusting `origin/ronald`.
2. Review v2.1 scope and correct F-1 validator: exact permitted move `access_control.role_assignments.ordinary.manage` from School Admin to Technical Super Admin, retained v2.0 guarantees and tamper refusals. Reproduce the expected checks using the original handoff, including its prescribed tests in a disposable database when testing resumes.
3. Complete original D-101 review package **§7** for v2.1, then — if approved — review the two v2.2 moves `access_control.school_access.inspect` and `access_control.audit.school.read` and complete **§15**. Use **§14** checklist. v2.2 must not be signed before v2.1.
4. Record reviewer name, role, dated approval reference, scope, findings and evidence. Only then may the owner reconcile D-101's decision register status. No author-side auto-approval or proxy signatures.

**No D-101 approval has been provided in this handoff.** Reproducing old author-reported test counts is part of the reviewer task, not a current result.

## 4. D-102 design already approved; separately authorized implementation still blocked

Owner-approved design OD-1–OD-7 and C-1 is recorded in `WF-03.01_PROTECTED_PROVISIONING_READINESS.md` §3. A valid existing S0 governance profile has six codes; S1 adds only these three extension codes, in exact v2.2 order:

1. `access_control.school_access.inspect`
2. `access_control.role_assignments.ordinary.manage`
3. `access_control.audit.school.read`

`access_control.diagnostics.read` and the three excluded `accounts.*` defaults are out of scope. `extend-technical-governance` must be a distinct, protected Django Superuser operation, confirm the exact database-bound operation, accept only a fully validated S0, refuse S1 or partial/forged profiles, write the three permission definitions, bindings, and corresponding audit receipts atomically, and preserve all account-specific Denies with C-1 evidence. The existing P3B/P3D/P4 profile checks and locks must understand **exactly S0 or S1** without silently expanding P4 rollback or compensation. No role-name, Django-superuser flag, or account-Grant bypass is permitted in Workspace authorization.

**Do not implement or run this operation until:**

- D-101 has two genuine independent sign-offs, first v2.1 then v2.2, with the necessary reviewed test evidence;
- the owner separately authorizes the protected D-102 implementation with exact file scope and acceptance criteria (OD-7);
- any future real development-database execution is separately approved under D-93/D-95 with backup and operator controls; and
- protected-executor compatibility, audit/checkpoint integrity, and any active-role scoping consequences are reconciled before enabling routes or governance permissions.

D-107 authorized the **local-development S0-first** path; the first S0 grant was reported on 20 November. It did **not** authorize S0-to-S1. No direct SQL, manual permission row insertion, gate override, migration, or role grant is part of this handoff.

## 5. Next safe handoff

The owner should give the independent reviewer the original §19 review package and repository access, and request independently recorded v2.1 then v2.2 decisions. When the reviewer completes these requirements, obtain **separate explicit D-102 implementation authorization**. Prepare protected-code changes only against a fresh clean checkout, with exact file/permission/receipt scope. After all WF-03 features are implemented, carry out the agreed deferred tests and obtain final Human Approval before activating or declaring the workflow complete.

**Status at issuance:** D-101 OPEN / D-102 IMPLEMENTATION BLOCKED / S0-to-S1 NOT AUTHORIZED / WF-03.01 HUMAN APPROVAL PENDING.
