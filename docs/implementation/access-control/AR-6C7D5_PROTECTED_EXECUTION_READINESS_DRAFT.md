# AR-6C7D.5 — Protected Registration Review Execution Readiness

**Status:** REVIEW DRAFT — NOT AUTHORIZATION, NOT AN EXECUTION RUNBOOK
**Project:** CTU-G Workspace
**Branch:** `ronald`
**Last owner-verified committed baseline:** `1307c3c` (AR-6C7D.4)
**Scope:** Existing School Admin's three Registration Review permissions only

## 1. Decisions and evidence

On **2026-11-12**, the project owner stated approval for the proposed default assignment of three Registration Review permissions to the existing `Admin` role. This is **scope approval only**. No evidence has been supplied for an independent security reviewer, authorized execution operator, change ticket, production/development-database write permission, or separate activation approval. Those fields remain **unverified**. Do not infer institutional signoff or produce signatures from chat text.

The pinned, existing AR-6C7C.5 execution contract is intentionally `DRAFT_UNAPPROVED`, its authorization fields are `null`, all four stages are `BLOCKED`, `execution_authorized` is `false`, and `database_writes_authorized` is `false`. **Do not edit those values to manufacture approval.** A separately reviewed, authenticated authorization record and a distinct operational implementation would be required later.

## 2. Exact proposed write-set, not executed

| Phase | Records or changes proposed | Required inactive/safety state | Current authority |
|---|---|---|---|
| 1 — Metadata | `services`: `accounts`, `access_control` (2). `permissions`: exact three codes below (3). | Both service rows **inactive**; definitions have no separate `is_active` column. Zero grants in this phase. | **BLOCKED — separate metadata write approval needed** |
| 2 — Protected bindings | `role_permissions`: three exact `Admin` → permission bindings (3). | Each binding initially **inactive**, attributed to the authorized actor, audited transactionally. No account overrides. | **BLOCKED — independent protected-grant authorization needed** |
| 3 — Service activation | Review and potentially activate *only* `accounts` and `access_control`; separately review binding activation. | Do not imply an inactive binding becomes active merely because its service does. Recheck effective permissions and Deny precedence. | **BLOCKED — separate activation approval needed** |
| 4 — API/UI activation | Future mounted Registration Review URL prefix, two backend gates, frontend API gate/UI gate. | No new routes now; do not activate until independent review and authenticated security E2E. | **BLOCKED — separate deployment approval needed** |

Exact Admin permissions (all from the pinned `catalogue-v2.0` proposal, `SCHOOL` scope, `GOV` protection):

- `accounts.registration_requests.read`
- `accounts.registration_requests.approve`
- `accounts.registration_requests.reject`

Pinned source SHA-256: `12746bcb7b5b73041606768b9641ced10cec75fec0c6ea7d1b9dae16f3f6f315`. This is a **proposal provenance digest**, not authorization. The full v2 proposal contains more services/permissions and **must not** be bulk-seeded here.

## 3. Existing verified safety evidence

| Evidence | Verified outcome | Limitation |
|---|---|---|
| AR-6C7D.4 isolated MySQL tests | 17/17 passed | No live database write rights established |
| Access-control combined security tests | 137/137 passed | Isolated, not production execution |
| AR-6C7D.2 frontend contract tests | 41/41 passed | Client rejects network while gated |
| AR-6C7D.3 Django runtime gate check | Both flags `False`; review route not mounted | Snapshot only, recheck before release |
| AR-6C7D.4 isolated candidate | 2 inactive services, 3 permission definitions, 3 inactive bindings, 8 *synthetic/test* audit receipts | Test audit actions (`test.*`) do **not** establish an approved operational audit vocabulary |

No live DB mutations, permission activation, or release can be inferred from these tests. The last reported development DB was `ctug_workspace`, with **zero active catalogue services** and no effective Admin permissions; this must be re-verified using a fresh read-only preflight before any approved operation.

## 4. Independent authorization and change-management evidence checklist

Do not enter secrets, passwords, API tokens or `.env` content into this document. Any eventual evidence should be authenticated and link to the **exact** source digest, file revision, permission scope, target environment and phase, using institutionally accepted records.

| Required evidence | Current record |
|---|---|
| Project-owner scope decision | **Recorded in conversation, 2026-11-12**; exact 3 Admin defaults only |
| System-owner identity and authenticated authorization of *metadata writes* | **Missing / not verified** |
| Independent security reviewer identity, authority and signoff | **Missing / not verified** |
| Change ticket, scope, diff and approved execution window | **Missing / not verified** |
| Authorized non-self-grant execution operator (actor account and separation of duties) | **Missing / not verified** |
| Approved, narrowly scoped operational initializer and audit event contract | **Missing / not verified** |
| Concurrency, rollback, and audit-failure tests for that operational initializer | **Missing / not verified** |
| Fresh MySQL read-only diff with no conflicts, overrides or source drift | **Must be rechecked** |
| Tested backup/restore and incident-recovery plan for target DB | **Missing / not verified** |
| Separate protected-grant approval | **Missing / not verified** |
| Separate service/binding activation approval | **Missing / not verified** |
| Separate API route/flag activation and release approval | **Missing / not verified** |

**Segregation of duties:** an existing School Admin assignment is not sufficient to approve protected governance grants. The proposed future Technical Super Admin and Django framework superuser are **not** substitutes for recorded independent authorization. A protected initializer must enforce the approved authority and must not reuse an ordinary self-grant pathway.

## 5. Operator plan for a future separately approved change — not executable today

1. **Verify provenance and signoffs** for this exact three-permission scope; reject missing/ambiguous evidence, an unapproved operator or a changed catalogue source. An offline validation result does not prove authenticated approval.
2. **Fresh read-only MySQL planning:** use the existing `plan_registration_review_initialization` command; capture evidence, require zero `CONFLICT`, unexpected entries, retirement/override review and no unexplained drift. If the observed state differs, **stop**, do not repair or seed automatically.
3. **Review implementation:** a future operational initializer must use the approved locked-row order, exact allowlist, uniqueness constraints, MySQL transaction isolation expectations, audit attribution, idempotent full-state verification and fail-closed behavior. The current `tests_support/` fixture may **never** be used against `ctug_workspace`.
4. **Phase-specific transaction acceptance:** do not partially publish an operation on audit failure; ensure transactional rollback is confirmed. If an earlier phase was separately committed, do **not** silently delete its audited records as a blanket rollback. Use an explicitly authorized, separately audited compensating plan after impact review.
5. **Postcondition:** verify only authorized records exist, actor and audit entries are correct, service and bindings remain inactive unless their respective activation phase was separately approved, no direct overrides or account-role assignments were introduced, and effective Admin access remains denied until explicitly activated.
6. **Release:** only after distinct approvals, mount the existing review URLconf under an agreed prefix, turn on the two backend gates and the frontend route/client gates, and run authenticated positive and negative E2E (CSRF, 401/403/404/429/503, direct Deny, concurrency, stale request, rollback, notification audit). The expected workflow remains Registration → Pending → Admin Review → Approval/Rejection → Authorized Login → Shared Dashboard.

## 6. Read-only/local readiness commands

All commands below operate from `backend/` in the existing virtual environment. None writes to the business database; the offline steps do not load Django or MySQL at all.

```powershell
python -B -m unittest scripts.test_registration_review_execution_readiness -v
python -B -m scripts.report_registration_review_execution_readiness --format text
python -B -m scripts.validate_registration_review_execution_contract
python -B manage.py plan_registration_review_initialization --format text
```

The last command runs the existing **MySQL READ ONLY** planner and may fail closed if the current schema changed. It is not an initializer. Do not pass invented `--apply`, `--seed`, `--execute`, `--keepdb` or approval flags. Do not turn on backend/frontend review flags merely to make a check pass.

Expected offline readiness summary: **2 services, 3 permissions, 3 Admin bindings, four blocked stages, writes NO, execution NO, release NO.** A successful readiness report explicitly means the *draft is consistent but still blocked*; it is not a green light to run database mutations.

## 7. Protected out-of-scope work

No changes to official `docs/database/full_schema.dbml`, `backend/.env`, `.gitignore`, credentials, the existing AR-6C7C.5 contract, bulk-queue AR-6C5D proposals, `config/urls.py`, Django business models, `delegation.py`, `mutations.py`, frontend live API flags or the `ctug_workspace` data. No Git push by this package.

**Exit criterion for AR-6C7D.5:** a read-only report, a documented exact four-phase change plan and an explicit record of missing independent authorizations. **Exit does not mean execution readiness is approved.**
