> **RECOVERED / RECONSTRUCTED DOCUMENT — NOT THE ORIGINAL FILE**  
> Reconstructed on 2026-11-07 from previous CTU-G Workspace development reports, known milestones, and the original C1 proposal. Statements about tests and environment are **historical reports supplied by Codex**, not newly run or independently verified. Exact original wording, every test assertion, source line, and implementation nuance may differ. Treat current backend code and test results as authoritative when discrepancies occur.  
> **Status:** Historical implementation handoff; **not an authorization** to initialize or change roles, privileges, services, or database records. Current SRS v0.3 revises the administrator use cases; earlier access-governance assumptions need reconciliation.  

# Phase 1H-B1 — Transactional Access-Control Audit Writer

## 1. Purpose and historical scope

Phase 1H-B1 introduced an internal audit-writing service to tie security-sensitive access changes to attributable audit records in a single database transaction. The original Codex handoff reported a completed implementation; this is a reconstructed summary.

Reported after this phase: 42 new audit tests; **175 backend tests passing** (previous 133 plus 42). No schema or existing migration changes were made.

## 2. Reported implementation

- `backend/apps/access_control/audit.py` — `record_access_audit()`.
- `backend/apps/access_control/test_audit.py` — audit tests.
- `docs/phase1h-b1-transactional-audit.md` — original phase report (this copy is reconstructed).
- Uses the existing `access_audit_logs` table.

Existing audit model concepts include: `access_audit_log_id`, `actor_account_id` (required FK), optional `target_account_id`, `role_id`, `permission_id`, `action`, bounded `old_value`/`new_value` JSON snapshots, optional `reason`, and created timestamp.

## 3. Writer contract

The reported service requires:

1. A **persisted, real actor account**; no fabricated or null actor attribution.
2. Execution within a caller-owned `transaction.atomic()` context.
3. Valid relevant FK references and allowed event action/reason codes.
4. Constrained, security-specific previous and new state snapshots.
5. Exclusion of passwords, hashes, reset tokens, session secrets, unrelated PII, and unrestricted business payloads.
6. Append-only usage of audit records through the writer's API.

**Authorization is the responsibility of the trusted caller.** A successful audit write by itself is not proof the caller was allowed to change a permission.

## 4. Transaction integrity

A successful trusted mutation should perform authorization, lock/recheck state, mutate the relevant row, and append the corresponding audit record within the **same** transaction. If either audit-writing or mutation fails, the entire transaction must roll back. The original report described positive committed visibility, rollback in both directions, concurrent append, and deferred callback checks.

The writer being append-only at the application API level is not itself a database-wide immutable/WORM guarantee. Database permissions, retention, backups, and independent monitoring require separate policies.

## 5. Historical verification summary

| Item | Historical report |
| --- | --- |
| Added audit tests | 42 |
| Backend tests total after B1 | 175 passing; none failed/skipped |
| Django checks | Passed |
| Audit log entries in local development | 0 |
| Database snapshot | 16 tables, 22 migrations, four roles |
| ERD changes / migrations | None |

The prior handoff said disposable MySQL test databases were cleaned up. This recovery did not rerun tests.

## 6. First-operator attribution blocker

The existing schema requires non-null `access_audit_logs.actor_account_id`. A fresh system has no accounts and no initialized technical operator; a bootstrap cannot legitimately claim a nonexistent actor. The C1 proposal describes alternatives needing explicit approval, independent external attestation, and a real named person. Neither option is approved by this document. Do not:

- Change the audit FK to nullable as a shortcut.
- Forge an actor account, swap to another person's ID, or use an unaudited hidden backdoor.
- Encode unapproved bootstrap evidence into unrelated JSON/reason fields.
- Treat Django's Superuser as an automatic application-level audit authority.

## 7. Scope and later work

B1 is an audit building block, not an administrative API, a Django session/login implementation, or a financial ledger. Catalogue metadata initialization, administrator provisioning, reviewer attribution, protected governance grants, and retention require separate explicit event contracts and review.

See the original (preserved) C1 proposal section 6.3 and 8.3 for later-discovered audit payload and first-operator gaps.

**Preservation rule:** this recovered document does not authorize audit/schema/model edits, database writes, or administrator initialization.

