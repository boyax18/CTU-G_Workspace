# Hybrid Dynamic Access Control — Release Gates

**Status:** Catalogue V2 remains a **review proposal**, not an activation authorization.  
**Last planner run referenced:** 2026-11-08; pinned SHA-256 `56ccd699a127ac7a734bd53a2cb7d4a30a1d3953413e4c423897b4a9c9398b78`.

## Catalogue planner snapshot

- Proposed: 10 services, 95 permissions, 106 role-permission bindings, 6 roles, 1 retired definition tombstone.
- Existing role matches: Student, Instructor, Treasurer, Admin.
- Deferred roles: Technical Super Admin, SSG Advisor.
- Outcomes: 105 CREATE (definitions/services only), 4 MATCH, 108 DEFER, 0 CONFLICT.
- MySQL planner performed a read-only consistent snapshot; no writes or grants.

## Required decisions before activation

The original planner marked the following concerns blocked; see the source manifest and reviewer notes for the full V2-01–V2-10 wording:

1. Explicit approval of 95 codes, tombstone, metadata changes, six role definitions, and 106 proposed default pairs; changes require versioned recomputation.
2. Role eligibility and protected extra-role assignment/removal rules; SSG Advisor design and duration.
3. Scope/minimization of finance monitoring views and coexistence rules.
4. Separation of ordinary role administration, governance grant/template changes, identity creation, and recovery.
5. Independence of reviewers/executors, binding to exact reviewed state, expiry, replay prevention, source-of-authority and self-benefit checks.
6. Effective last-operator protection, quorum/availability, simultaneous revocation races, recovery ordering.
7. First-real-operator proof and independent institutional approval, first initialization serialization, audit event contract.
8. Authentication/audit source definitions, retention/access, unknown-subject failure events, and session revocation or step-up design.
9. Framework flags/admin-site restrictions and recovery boundaries (schema changes handled separately).
10. Business-specific finance, signatures, ratings, messaging, reports, privacy, settings readiness, and service activation.

**Additionally blocked by planner:** initialization, grants, service activation, live mutations, administrator provisioning (for the catalogue workflow), first-operator attribution, independent review evidence, effective-last-operator, object authorization, session revocation, authentication events, and Django superuser changes.

## Minimum registration-review capability (PROPOSED, NOT ACTIVE)

| Permission | Intended role | Mandatory scope |
| --- | --- | --- |
| `accounts.registration_requests.read` | Admin | Eligible requests only; protect sensitive fields |
| `accounts.registration_requests.approve` | Admin | Pending eligible Student/Instructor requests; no self-approval; audited |
| `accounts.registration_requests.reject` | Admin | Pending eligible Student/Instructor requests; no self-review; audited |
| `accounts.profile.self.read` | Admin | Authenticated account's own profile only |

A smaller activation scope would require an explicit, versioned, approved catalogue revision, not cherry-picked silent inserts into the database.

## Policy enforcement checklist

- [ ] Service and permission definitions reviewed and versioned
- [ ] Effective permission evaluator and Deny precedence tested at backend boundary
- [ ] Object-level authorization and cross-account protections approved/tested
- [ ] Role default binding approval evidence recorded
- [ ] Audited, transactional, idempotent/controlled activation implementation
- [ ] Independent review and protected-governance rules resolved
- [ ] Revocation/session invalidation behavior tested
- [ ] Negative-path security tests and regression suite passing
- [ ] Rollback/recovery runbook reviewed
- [ ] Architecture/SRS/ERD/API/phase documents updated

**Do not mark the catalogue live until the actual implementation and approvals satisfy these gates.**

## 18 November 2026 owner-directed Django Superuser role-authority amendment (review-only)

The target model: an approved Instructor may acquire School Admin (`Admin`) through an authorized Technical Super Admin or Django Superuser; only Django Superuser can grant/revoke the Technical Super Admin role. Django Superuser may configure system data and any role, **but only through reviewed, authenticated, audited and protected configuration operations**. School Admin cannot manage role assignments. Technical Super Admin has `Instructor + Admin + Technical Super Admin`, with exact access-control permissions, and cannot elevate another Technical Super Admin. No public privileged registration.

**Conflict and gate:** The existing two-Admin, three-signer protected executor/bootstrap and the integrity-pinned catalogue still encode older policy. This document does not approve bypassing them or turning on Django Admin's currently read-only mutation interface. Approval is needed for revised `v2_0.json`/validator pins, protected writer path, bootstrap/evidence, `wex-1` storage, P3B/P4 compensation, last-operator and recovery, session epochs, and actual safe Superuser provisioning. See WF-03.01 D-79/D-91/D-92, editable SRS §3.5 and ADR-004. All governance release gates remain **BLOCKED**.

## 18 November 2026 — WF-03.01 staged implementation (local development only)

Implemented behind default-off gates and NOT activated: the protected Django-Superuser role command (disposable test database only; `DEVELOPMENT_DATABASE_APPROVED = False`; designated operators unset), the Technical Super Admin School Admin assignment service and its isolated, unmounted API (`WORKSPACE_ROLE_ASSIGNMENT_ENABLED` unset), the role-change session epoch, and the Role assignments page (`VITE_WORKSPACE_ROLE_ASSIGNMENT_ENABLED` unset). Every catalogue v2 operational gate stays BLOCKED, the writer boundary stays `RELEASE_STATUS = "BLOCKED"`, both new paths refuse while the protected writer is enabled, and no governance permission or role exists in `ctug_workspace`. Creating the Technical Super Admin governance rows would make P4 compensation refuse (verified in the disposable database), so D-85 must be approved before any development-database use.

**D-85 (18 November 2026, local development only):** the protected P3B snapshot now recognizes only the exact governance profile (six catalogue v2 codes on access_control, six active bindings on the active Technical Super Admin role and nothing else, 1 + 6 + 6 field-exact receipts from one framework operator after the registration P4 activation) and refuses any other, missing, altered or unproven row. P4 compensation keeps its scope and refuses, under row locks serialized with the superuser procedure, while the governance profile exists (an effective holder, a non-effective assignment, or the profile alone). No gate was opened; nothing changed in `ctug_workspace`; development-database use still needs D-93/D-95.

**D-89 (19 November 2026, local development only):** Permission Catalogue v2.1 exists as a validated, versioned specification overlay. Validation runs the unchanged v2 validator first, checks the v2 manifest and the AR-3B2A v2.1 addendum against independently maintained pins, and accepts only the authorized delta: `access_control.role_assignments.ordinary.manage` moves from Admin to Technical Super Admin. School Admin therefore holds no access-control management default under v2.1. Every v2 guarantee is unchanged: governance codes bound only to Technical Super Admin, Deny precedence, no role-name or Django Superuser bypass, delegation OFF and all operational gates BLOCKED. **Availability is not provisioning:** no permission, binding or role was created in any real database, no consumer reads v2.1 yet, and independent review or signing of the addendum pin is OPEN.

**D-103 (19 November 2026, local development only):** Permission Catalogue v2.2 is a second validated overlay. It validates v2.0 and v2.1 unchanged first and pins the effective v2.1 digest and the v2.2 addendum. Its only change moves `access_control.school_access.inspect` and `access_control.audit.school.read` from Admin to Technical Super Admin, so School Admin holds no `access_control.*` default and keeps its WF-02 `accounts.*` permissions. Every guarantee is unchanged, and no route, navigation item or audit screen is added (WF-12 must define any audit view). Nothing is provisioned. P3B/P4 are unchanged and still refuse any extra governance row until D-102. Independent review of both addendum pins is OPEN (D-101).

**D-101 F-1 and D-104 (19 November 2026, local development only):** The v2.1 validator now parses the v2.0 base only from the bytes it has hashed and validated (commit `9e259e7`; pins and effective digests unchanged). Owner direction D-104 makes Permission Catalogue v2.2 the current target specification, with v2.1 only as its verified dependency. Every gate stays BLOCKED, and no runtime consumer reads v2.1 or v2.2. Before any consumer switch or provisioning: D-101 independent sign-off of v2.1 and then v2.2, D-102 (exact requirements in `docs/security/WF-03.01_PROTECTED_PROVISIONING_READINESS.md`), D-93/D-95 and a separate owner authorization. Any future security or audit interface must authorize with `has_technical_authority`, because an account-specific Grant reaches `has_permission` (D-101 F-5; WF-12).

**D-102 design approved, implementation blocked (19 November 2026):** The owner approved OD-1 to OD-7. P3B, P3D and P4 will accept only the governance states S0 (6 codes) and S1 (6 codes plus `access_control.school_access.inspect`, `access_control.role_assignments.ordinary.manage` and `access_control.audit.school.read`), each verified field by field with exact receipts and one operator per receipt block. Any other state, including a partial extension or a partial base, is refused and never repaired. S0 becomes S1 only through the explicit Superuser-only `extend-technical-governance` operation. A target's own Deny on any provisioned code refuses the grant. C-1 (owner approved): an S0-to-S1 extension may proceed despite an existing holder's Deny, which stays unchanged and keeps precedence. The extension never removes, modifies or overrides a Deny; it reports affected holders to the operator and records them in deny-preservation receipts. `access_control.diagnostics.read` and Technical Super Admin's `accounts.*` defaults are not provisioned. D-85 compensation refusal and the P4 rollback scope are unchanged. Every gate stays BLOCKED: the protected code is unchanged and still reads v2.0 until the D-101 independent sign-off and a separate implementation authorization. R-1 (the lock-order inversion between the snapshot and the role procedures) was corrected on 19 November 2026 for K-1, K-2, K-3 and K-5: every protected snapshot and Superuser role change now locks the shared service rows first. K-4 and K-6 were corrected the same day for the tested scenarios: the P1, P2 and WF-02.05 initializers now also lock the service rows first. As defence in depth they must still not be rerun concurrently with role changes, P3D or P4 until the owner decides otherwise. R-2 remains open. Contract: `docs/security/WF-03.01_PROTECTED_PROVISIONING_READINESS.md` section 3.

**R-2 Option D phase 1 (19 November 2026; verified on disposable databases, NOT applied):** SR-1 (confirmed, activation blocker): the session epoch is the account's latest suspension or role-change receipt ID, so deleting that receipt moves the epoch backwards, and a session signed in before the change and not used since (not yet flushed) becomes valid again within its idle/absolute lifetime. Its permissions still follow the current roles. Exploiting it needs database write access. This is an activation blocker for real grants. A least-privilege runtime account (no UPDATE, DELETE or DDL on `access_audit_logs`, no trigger or user rights), a separate migration account and a read-only external-checkpoint prototype (`report_access_audit_checkpoint`) are designed and tested. None is applied to `ctug_workspace`, whose application still connects as `root`. Decisions: D-105.

**SR-1 Stage A (19 November 2026; implemented and tested in isolation, NOT activated):** SR-1 Stage A (19 Nov 2026): the session hash now binds the persistent accounts.session_revocation_version counter (v2 domain, no fallback) instead of the receipt-derived status_epoch; every approved session-ending event advances it once in the same transaction, so deleting, changing or forging receipts no longer revives a session. Migration 0006 is authored but NOT applied to ctug_workspace (still at 0005; the branch's application therefore fails closed there with MySQL 1054 until a controlled deployment is authorized); the trigger was tested only on disposable databases and is NOT installed; the authoritative ERD is NOT updated; restricted MySQL accounts, external checkpoints and the restore procedure are NOT activated. SR-1a (CSRF polling keeps a revoked session row alive) is confirmed and left unchanged pending approval. Decision: D-106.
