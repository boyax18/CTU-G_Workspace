# ADR-004 — Django Superuser and Application Administrator Role Authority (Review Draft)

**Project:** CTU-G Workspace  
**Recorded:** 18 November 2026  
**Status:** Owner-directed functional requirement recorded; protected implementation decision **OPEN**. Not approval to provision or release.  
**Scope:** WF-03.01 and affected requirements, use cases, permission catalogue and test specification.

## Context

The previous WF-03.01 inspection found the operational development database had one School Admin (`Admin`), no Technical Super Admin role, and only a read-only Django Admin. Existing technical executor code supports `technical_role.provision` and `technical_admin.bootstrap` with two different Admin accounts, three independent Ed25519 signers, a tightly bound state hash and protected `wex-1` infrastructure. Its release status and operator setup were blocked. Older SRS text permitted School Admin to assign ordinary roles and earlier pinned governance material assigned some ordinary role permissions to `Admin`.

The owner clarified that an administrator is **not a separate registration type**. The user registers as an Instructor, passes approval, and is later assigned further roles. They specified that **Django Superuser has full configuration authority over CTU-G Workspace data and account roles** and is the **sole authority to grant/revoke Technical Super Admin**. This is a revised target, not evidence the old executor is safely replaceable.

## Owner-directed role and authority contract

| Identity / tier | Required effective role composition | May assign School Admin (`Admin`)? | May grant/revoke Technical Super Admin? | Can configure system data? |
|---|---|---|---|---|
| School Admin (Normal Administrator) | Approved Instructor + Admin | No | No | School operations only, through authorized Workspace services |
| Technical Super Admin (Super Administrator) | Approved Instructor + Admin + Technical Super Admin, with explicit effective governance grants | Yes, for eligible approved Instructors, subject to protected permissions | **No**, including self or peers | Authorized application governance only |
| Django Superuser (framework privileged operator) | Separate framework privileged account; does not require Workspace application roles | Yes, via protected, audited configuration action | **Yes; exclusive authority** | All CTU-G Workspace data/configuration through reviewed, authenticated, integrity-preserving procedures |

**Role continuity:** The original Instructor role remains when Admin and Technical Super Admin are assigned. A standalone privileged registration form is prohibited. The Django Superuser must not silently receive ordinary Workspace REST API capabilities from `is_superuser`; existing `has_permission`/Deny/service/resource checks continue to apply there. Its separate privileged configuration mechanism requires explicit code-level authorization and audit.

## Security migration issues requiring approval before implementation

1. **Admin surface** — Choose a protected Django Admin action or tightly scoped management command; the present Django Admin is read-only. No raw unrestricted ModelAdmin CRUD or direct SQL for governance/audit data.
2. **Target eligibility** — Approved active Instructor with retained Instructor membership for School Admin/Technical Super Admin assignment; validate account, approval status, role compatibility and prohibited self-target behavior.
3. **First operator and safety** — Adapt the current two-Admin/three-signer ceremony without removing provenance, independent oversight or last-effective-operator safeguards. The owner-designated superuser is the *exclusive technical authorizer* of Technical Super Admin membership; whether separate institutional and security signoffs are additionally required remains a security decision.
4. **Executor/writer** — Reconcile signed request protocol, root-signed roster, 120-second validity, `wex-1` storage/DDL approval, protected writer gating, current read-only Django Admin and compatibility with previous audit receipts. No executor activation from this ADR alone.
5. **Permission manifest** — Move `access_control.role_assignments.ordinary.manage` away from School Admin; preserve Technical Super Admin's explicit effective permission requirements. Pin-controlled `SRS_v1.md`, AR-2, AR-3A, AR-3B2A, historical C1, and missing runtime `v2_0.json` cannot be modified via docs ZIP. Require a versioned manifest/validator update with new approved digests and tests.
6. **P3B/P4 and compensation** — Existing snapshot and compensation logic refuse unexpected permission bindings or unsafe last-operator states. Design narrow compatibility and a supported recovery/release plan before activation.
7. **Audit/transaction/session** — Attribution of *Django Superuser framework actor*, target, exact changed role, evidence, approvals, timestamps and state digest; transactional mutation + append-only receipt; monotonic session invalidation on any privileged grant/revoke and protections against role removal/re-add session resurrection.
8. **Full-data administration** — Record-by-record maintenance operations may have other business integrity and privacy rules; explicitly review allowed surfaces and log protected updates. Superuser authority is not a blanket permission to bypass retention, erase audit history, or edit official enrollment data from CTU main system.
9. **Recovery** — Loss of Django Superuser access, first/last Technical Super Admin, dual-role conflicts, actor-target separation, review quorum and emergency break-glass need signed operational runbooks.

## Affected artifacts and tests

- SRS v0.4 editable draft: §3.5; FR-ADM-01..05; FR-DJA-04/06; FR-UI-02; UC-05 and AT-08/09.
- Use Case Specification v0.4.1 working copy: ACT-TS-07/08/11, ACT-SA-06 negative flow, UC-D05, WF-03 access matrix.
- Workflow Catalogue: WF-03.01, D-79..D-92, historical inspection preserved.
- Master Test Specification: TC-004, TC-009, TC-018 and planned TC-020..038.
- Requirements Traceability Matrix and `docs/security/ACCESS_CONTROL_GATES.md`.
- **Not modified:** pinned SRS v1/AR-2/AR-3A/AR-3B2A, both official DBML/ERD files, executor sources, permission manifest and production configuration.

## Decision gates

**Recorded owner policy:** Django Superuser is the exclusive Technical Super Admin role grant/revoke authority and may configure all system data/roles; Technical Super Admin manages eligible School Admin roles; School Admin has no access-control management authority.

**Still OPEN:** protected superuser implementation path, first operator and real-person institutional authorization, evidence/co-signing, wex-1/schema and DBA approval, catalogue pin migration, P3B/P4, recovery and last-operator policy, approved UAT, release activation.

**Next permitted engineering stage:** Inspect → Reconcile → explicit security/owner Approve → Implement → focused/affected Test → Commit. Full WF-03 regression at WF-03.06 after implementation and before category final acceptance. No role records, schema or runtime code were changed in this documentation package.
