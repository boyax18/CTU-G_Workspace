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
