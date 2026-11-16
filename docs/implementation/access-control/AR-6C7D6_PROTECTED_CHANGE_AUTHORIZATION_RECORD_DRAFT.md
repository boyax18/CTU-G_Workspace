# AR-6C7D.6 — Protected Registration Review Change Authorization Record

**Project:** CTU-G Workspace
**Document status:** DRAFT / INCOMPLETE — NO EXECUTION AUTHORITY
**Prepared:** 2026-11-12
**Branch / verified baseline:** `ronald` / `8f2abba`
**Change class:** Protected governance permission initialization
**Environment:** Local development MySQL, database `ctug_workspace` (target for a *future*, separately authorized change)
**Parent contract:** `AR-6C7C5-REGISTRATION-REVIEW-DRAFT` — remains `DRAFT_UNAPPROVED`
**Pinned proposal SHA-256:** `12746bcb7b5b73041606768b9641ced10cec75fec0c6ea7d1b9dae16f3f6f315`

> **Control statement:** This document records a narrow permission-scope decision and outstanding approval evidence. It is not a signed change ticket, operational command, privilege grant, database-write authorization, service-activation approval, or deployment approval. Do not turn any `BLOCKED` gate into `APPROVED` merely because this draft exists.

## 1. Scope decision already communicated

On **2026-11-12**, the project owner said they approved the **three proposed Registration Review permission assignments for the existing School Admin (`Admin`) role**. This communication confirms intended *functional scope* only; it has **not** been independently authenticated as institutional change authorization, nor has an independent security reviewer signed off. The user's statement does **not** authorize a writer, change window, protected database mutation, or activation.

| Scope dimension | In scope | Explicitly excluded |
|---|---|---|
| Role | Existing `Admin` role only | Creating new Admin accounts/roles, Technical Super Admin bootstrap, Django superuser privileges |
| Services | `accounts`, `access_control` | Other services or a bulk catalogue rollout |
| Permission definitions | `accounts.registration_requests.read`; `accounts.registration_requests.approve`; `accounts.registration_requests.reject` | All other permission codes, including unrelated self-profile grants |
| Protected role defaults | Exactly three `Admin` → corresponding permission bindings, **initially inactive** | Direct `account_permissions` overrides, changing `account_roles`, self-grants |
| User workflow | Registration → Pending → Admin Review → Approval/Rejection → Authorized Login → Shared Dashboard | Enrollment administration, AR-6C5D bulk queue modifications, role-switching changes |
| Schema and authority | Existing official ERD and Hybrid Dynamic Access Control | ERD modification, permission-Deny bypass, Django superuser bypass |

The bounded catalogue proposal is **not** the already-approved full v2 catalogue. The full v2 seed remains outside this change.

## 2. Required approval evidence — current record

Each evidence reference must point to an authentic, access-controlled institutional/project record identifying the exact digest, target environment, allowed phase, and named accountable people. **Do not write passwords, tokens, raw credentials, email app passwords, `.env` values or identifying student records here.** A link or internal document ID is sufficient; never fabricate a signature or sign for another person.

| ID | Evidence required | Status as of 2026-11-12 | Evidence reference / accountable approver |
|---|---|---|---|
| E01 | Authenticated system-owner authorization specifically for *inactive metadata database writes*, not just permission scope | **MISSING** | NOT PROVIDED |
| E02 | Independent security reviewer identity, authority, and phase-specific signoff | **MISSING** | NOT PROVIDED |
| E03 | Approved change ticket, execution operator identity, defined execution window and environment | **MISSING** | NOT PROVIDED |
| E04 | Separately reviewed operational initializer, final audit-event vocabulary, bounded write-set, and concurrency/rollback design | **MISSING** | NOT IMPLEMENTED/APPROVED |
| E05 | Fresh read-only MySQL difference report plus verified recovery/backup procedure and same-database postchecks | **PARTIAL** — read-only diff passed; backup/restore and execution-day recheck missing | Prior `plan_registration_review_initialization` output; new change-time evidence required |
| E06 | Distinct approvals for metadata, protected bindings, service/binding activation, and API/UI release | **MISSING** — scope decision exists only | NOT PROVIDED |
| E07 | Authenticated role, CSRF, failure, deny-precedence and negative-path end-to-end evidence before release | **MISSING** — isolated tests do not replace E2E | NOT EXECUTED |

**Record interpretation:** The current offline readiness report says **seven outstanding evidence items**. This table corresponds to those seven categories, without presenting partial historical testing as a completed authorization. Keep the original AR-6C7C.5 contract unchanged; if authentic approvals are obtained, issue a new reviewed and versioned authorization record, preserving this draft.

## 3. Approval/decision ledger — all phases blocked

| Phase | Decision | Specific approval still needed | Who may execute / witness |
|---|---|---|---|
| P1 — Metadata | **BLOCKED** | Authenticated owner approval for exactly 2 inactive services + 3 definitions, approved operational implementation and audited transaction | Operator NOT IDENTIFIED; independent reviewer NOT IDENTIFIED |
| P2 — Protected role bindings | **BLOCKED** | Independent permission-governance authorization for exactly 3 inactive Admin defaults; no self-grant | Operator NOT IDENTIFIED; independent reviewer NOT IDENTIFIED |
| P3 — Service and binding activation | **BLOCKED** | Separate, explicit activation and impact authorization; binding activation cannot be implied by service activation | Operator and reviewer NOT IDENTIFIED |
| P4 — API / UI release | **BLOCKED** | Separate route/flag release approval and authenticated security E2E acceptance | Release owner and reviewer NOT IDENTIFIED |

Authorization **must not** be granted by a person solely on the basis of holding the existing School Admin role. A future Technical Super Admin is not yet an implemented or independently approved governance bootstrap. Django `is_superuser` likewise does not automatically confer CTU-G Workspace authorization. The operator must not approve or perform their own protected privilege escalation. Approval and execution evidence must be attributable, independently reviewable, and phase-scoped.

## 4. Review of available technical evidence (not approval)

| Evidence | Observed result | What it does **not** prove |
|---|---|---|
| AR-6C7D.4 disposable MySQL candidate | 17/17 isolated tests passed; 137/137 combined security tests passed | No authorized live initializer or independent approval |
| AR-6C7D.2 frontend typed contract | 41/41 Node tests and TypeScript/Vite build passed | No live API authorization or actual registration review |
| AR-6C7D.3 Django disabled-state check | Both backend review flags `False`; review URL not mounted | It will remain so after any future deployment |
| AR-6C7D.5 offline report | 7/7 tests passed; four execution stages `BLOCKED` | No human authentication or database write authority |
| Development MySQL read-only planner | 2 services and 3 permissions proposed as `CREATE`; 3 Admin bindings `DEFER`; writes `NO` | No change-time diff, approval to execute, or rollback plan |

The AR-6C7D.4 fixture's **eight test audit receipts** use `test.*` event codes and **must not** be treated as approved operational audit codes or reused as a production entrypoint. The `tests_support/` modules are disposable-test-only.

## 5. Future evidence capture and release signoff template — intentionally unsigned

- **Change ticket/reference:** NOT ISSUED
- **Reviewed document revision and digest:** THIS DRAFT; final revision NOT APPROVED
- **Target environment and exact database:** Local development MySQL / `ctug_workspace`; operator re-verification pending
- **System owner / authentication of approval:** NOT VERIFIED
- **Independent security reviewer / signoff evidence:** NOT VERIFIED
- **Authorized executing operator and non-self-grant check:** NOT VERIFIED
- **Permitted phase (P1/P2/P3/P4) and exact write-set:** NONE AUTHORIZED
- **Approved execution window:** NOT PROVIDED
- **Preflight output and backup/restore evidence:** INCOMPLETE
- **Approved operational initializer revision and tests:** NOT AVAILABLE
- **Verified postcondition, transaction/audit receipts and incident escalation:** NOT APPLICABLE — NO EXECUTION
- **Release / rollback decision:** BLOCKED / no release

An authenticated approval must be recorded **outside this draft** using the project's accepted governance process, with a reference back here. Do not fill a blank by inference from prior chat, a Git commit, a Django role assignment, or a passed test.

## 6. Nonnegotiable stop conditions

**STOP** if any of the following occurs: independent approval missing; actor identity or role bootstrap ambiguous; any phase signed off by its own operator; source digest changed; unexpected DB objects or direct account overrides; missing or inconsistent audit contract; untested concurrency or restore; incompatible MySQL transaction isolation; a test-only fixture is proposed for live execution; any active grant/service is introduced prematurely; or a deployed route/flag is found enabled before approved release.

**End-of-milestone conclusion:** Owner permission **scope** communicated; all execution and activation phases **BLOCKED**. Proceed only with independent evidence collection and reviewed design, not live writes.
