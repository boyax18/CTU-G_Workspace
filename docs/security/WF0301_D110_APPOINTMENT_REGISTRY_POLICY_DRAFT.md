# CTU-G Workspace — WF-03.01 D-110 appointment evidence registry (STAGED)

**20 November 2026. Source implementation only; migration not applied, no tests run, no routes activated, no governance permissions provisioned.**

## Purpose

Keep ordinary-role grants fail-closed until an appointment is independently confirmed from an official institutional record. A submitted document hash is a reference for comparison, **never self-proving evidence**. The workflow does **not** grant Treasurer/SSG Advisor to anyone by submitting or verifying a record. Technical Super Admin remains the only Workspace role assigner; School Admin never acquires role-management power.

## Intended separation of duties

1. **Appointment recorder:** active Approved School Admin with a stored effective `access_control.appointments.record` permission enters the eligible account, requested responsibility, SHA-256 of a separately obtained official appointment document, and dates. The record starts `Submitted` and has no granting effect.
2. **Independent appointment reviewer:** another active Approved School Admin with a separately provisioned effective `access_control.appointments.verify` permission checks the official document from an **independent institutional source**, calculates the digest independently, and explicitly verifies or rejects. Cannot review their own submission, their own appointment, or reuse the submitted digest from the review queue. A verified record is valid only in its date window.
3. **Role assigner:** a third distinct, authorized S1 Technical Super Admin with `access_control.role_assignments.ordinary.manage` assigns the ordinary responsibility through D-100. The D-100 gate, the D-110 evidence-use gate, and the D-101/D-102 governance release conditions all apply. The assigner must differ from both the recorder and reviewer. Role changes still invalidate sessions and emit their own atomic audit receipts.

**Open authority decision:** Which campus office/officer may receive `access_control.appointments.verify`, and what sources are officially valid for Treasurer versus SSG Advisor? This draft **does not grant either permission**, designate the verifier, or claim an externally authenticating service exists. Owner/stakeholder confirmation and protected governance provisioning are mandatory before activation.

## Security and data contract

- `ordinary_appointments` is a new optional table, created by migration `access_control.0004_ordinary_appointments` **only in a separately approved migration window**. No data migration, auto-created appointment, permission grant or role initialization.
- Submit/review decisions use local-review/sandbox routes only, an independent default-off registry gate, exact effective permissions, active Admin membership, active service state, three distinct accounts, row locks, MySQL READ COMMITTED, and writer-boundary refusal.
- Record fields: account, role, 64-character lowercase SHA-256 digest, valid-from/until (max 366 days), status, submitting/reviewing/revoking actor and timestamps. Unique target+role+document digests deter duplicate candidate records without blocking a shared official resolution; `Verified` state requires an independent review. No document file is uploaded into the database.
- Approved review is transactional with an append-only `account.appointment.*` audit receipt. The new table stores protected FKs to its own submit/review/revocation receipt IDs. **`audit.py` and its approved D-84 snapshot allowlist remain byte-for-byte unchanged.** No raw appointment reference, document bytes or PII is inserted in audit JSON.
- Revocation refuses while the ordinary role is still assigned; revoke the role first. This protects against silently retaining a grant after an evidence revocation.
- A date-window expiry currently stops **new** assignments only; D-100 role permissions already assigned are not continuously conditional on the document's expiry. **Before any real activation, implement/reconcile a runtime enforcement or atomic role-expiry removal policy, including session invalidation, audit and recovery.** This is a release blocker, not a test to waive.
- Default-off `WORKSPACE_ORDINARY_APPOINTMENT_EVIDENCE_ENABLED` is not enabled by any settings module. Even a migrated, verified appointment cannot unlock a D-100 grant until a separate policy/governance authorization changes this intentionally.
- Role creation/provisioning for `SSG Advisor` remains pending. Protected executor support and production URL mounting are excluded.

## Implemented code (not tested)

- `models.py`: `OrdinaryAppointment` and FK-linked audit receipts.
- Migration `0004_ordinary_appointments.py` authored but not applied.
- `appointment_registry.py`: submit, verify, reject, revoke and independent effective permission checks.
- `appointment_registry_api.py`: local-only isolated endpoints and minimal independent-review queue; server never returns the submitted digest in the review queue.
- `ordinary_appointment_evidence.py`: migrated, independently verified, current and separately gated record read for D-100 (returns False on unavailable storage).
- D-100 assignment path passes the actual grant actor ID to prevent approving one's own role assignment.
- New tests authored in `test_wf0301_d110_appointments.py`, **not executed**.

## Deferred test and release checklist

- [ ] Confirm official Treasurer and SSG Advisor appointing/verifying authorities and source records.
- [ ] Approve distinct permission codes and provisioning without School Admin role-management authority.
- [ ] Reconcile D-101 independent sign-off, D-102 S0-to-S1 extension and protected writer readiness.
- [ ] Resolve expiry/role revocation (already-assigned role enforcement) and appointment replacement/renewal policy.
- [ ] Initialize SSG Advisor role under separately approved governance procedure.
- [ ] Approve schema migration and backup/restore plan. Do not run migration now.
- [ ] After all WF-03 features implemented, run disposable MySQL tests, concurrency/deadlock tests, API CSRF/authorization/browser tests, migration checks, audits and full regressions.
- [ ] Complete WF-03.01 final Human Approval (not yet recorded).
