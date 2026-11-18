# CTU-G Workspace — Open Decision Register (Draft)

**Document ID:** CTUG-DEC-001 | **Date:** November 11, 2026  
**Status:** OPEN ITEMS AND PROPOSED OWNERS ONLY; no automatic approvals.  
**Existing source:** SRS v0.4 `OD-01..19` (these IDs are **not renumbered**). New finance questions `FIN-D01..06` are proposed SRS companion decisions.

## 1. Decision register

| Source ID | Decision required | Suggested review parties | State | Implementation blocked until |
|---|---|---|---|---|
| OD-01..04 | Admin vs protected governance profile, role composition/role name; single SSG Advisor/Finance Monitor responsibility | Project owner + security + school operations | Open | No new role or default grants |
| OD-05..06 | Finance Monitor's three **read-only** scopes and Student+Treasurer/Instructor+Admin conflicts | SSG finance owner + operations + privacy | Open | No monitoring write access or conflicting role privilege |
| OD-07 | Safe Normal Admin auth-event view and retention | Security + privacy | Open | No log viewer exposed |
| OD-08..09 | Super Admin role-template limits, first operator attribution, recovery and last-operator safeguards | System owner + security | Open | No unguarded governance mutation |
| OD-10 | Django Superuser integration compatibility | Backend maintainer + security | Partially implemented/tested per November 11 snapshot; release review still open | No generic custom bypass or schema guess |
| OD-11..12 | Direct override delegation and revised permission catalogue / role grants | Security/governance + project owner | Open | No active catalogue/default grants |
| OD-13 | Session revocation after role/permission changes | Backend/security | Open | No stale-session assumptions |
| OD-14 | Performance, privacy, retention, recovery and deployment acceptance | Campus operations + security/privacy | Open | No production certification |
| OD-15 | Outbox encryption rotation, email sender, retry monitoring and retention | Operations + security/privacy | Open | No real notification worker/sender activation |
| OD-16 | AR-6C5D queue schema/checks, migration, worker and recovery | DB maintainer + security + owner | ERD *text* approved only; implementation not approved | No 0004 migration or worker activation |
| OD-17 | Separate release flags for review/password recovery/SMTP/permissions | Owner + security/operations | Open | Flags remain off, review endpoints detached |
| OD-18 | Verified session/permission API and multi-role dashboard behavior | Frontend/backend + security | Shell tested; contract/release gate open | No trust in visibility-only authorization |
| OD-19 | Authoritative CTU enrollment verification and fee liability rules | CTU enrollment representative + SSG finance owner | Open | No automatic organization-fee eligibility implementation |
| FIN-D01..06 | Verification source, recurrence, withdrawal/transfer/proration, waivers, uniqueness and corrections | CTU enrollment + SSG finance + privacy | Proposed questions only | No new fee model/ERD/migration |

### WF-03.01 — Administrator role policy amendment (owner-stated 18 November 2026)

| Decision reference | Owner-directed desired behavior | Implementation/contract status |
|---|---|---|
| D-79 / D-82 | School Admin is approved Instructor+Admin; cannot mutate any role. Technical Super Admin is approved Instructor+Admin+Technical Super Admin and may manage eligible ordinary/School Admin roles. | Requirement intent stated; change to protected manifest and SRS v1 needs controlled versioning. |
| D-91 | Django Superuser can configure CTU-G Workspace system data and add/remove all account roles; only Django Superuser can grant/revoke Technical Super Admin. | Configuration channel not yet implemented; existing Django Admin read-only. |
| D-92 | Protected and auditable Django Superuser configuration; no normal Workspace API bypass; reconcile first-operator ceremony, signed evidence, audit/session, P3B/P4 and last-operator safety. | OPEN for owner/security/DBA decision; **not permission to execute bootstrap**. |
| D-80/D-81/D-88/D-90 | Existing two-Admin executor, first target, storage and recovery. | OPEN; new authority model conflicts with earlier mechanisms. |
| D-89 | Permission Catalogue v2.1 overlay (ordinary-role management to Technical Super Admin) | Implemented 19 Nov 2026 (local development; validated specification only, not provisioned): AR-3B2A v2.1 addendum (pinned 78a3c7e2e0afd07a7c4c052e13f3503378076dc7f487d9ecf3bf1dc940e1afb7), v2_1_delta.json, validation_v2_1.py; v2 byte-identical; independent pin review OPEN; SRS v0.5 and Use Case v0.4.2 amendments not issued. |
| D-85 | P3B/P4 compatibility with the Technical Super Admin governance rows | Implemented 18 Nov 2026 (local development, disposable test database only): exact governance profile verified against catalogue v2 and its receipts; compensation refused while the governance profile exists; not applied to ctug_workspace. |
| D-93 / D-95 | Protected Django-Superuser command; designated, re-authenticated operator | Implemented 18 Nov 2026 for the disposable test database only (configure_workspace_roles); development-database use and evidence/co-signoff still OPEN. |
| D-94 / D-97 | Legacy Admin-only operator protected; School Admin removal safeguards | Implemented 18 Nov 2026 (Admin without Instructor, Technical Super Admin holders and the last School Admin cannot lose Admin through WF-03.01); operator-transfer plan OPEN. |
| D-96 | Old bootstrap paths | Not changed: executor bootstrap stays dormant and release-blocked; retirement OPEN. |
| D-98 | WF-03.01 lint baseline | OPEN: `npm run lint` still fails on the two unchanged pre-existing findings; no WF-03.01 exception has been approved. |

See `docs/decisions/ADR-004-django-superuser-role-authority-amendment.md`. The change is a **documentation alignment** only: no live data, permission, ERD, migration or protected writer changes.

## 2. Change request record (use for each approved item)

**Request ID:** ____  
**Linked SRS/decision ID:** ____  
**Current document and digest:** ____  
**Proposed change and reason:** ____  
**Impact on public behavior, role grants, data, privacy and ERD:** ____  
**Security/operational negative cases:** ____  
**Reviewers and affected campus stakeholders:** ____  
**Decision:** Approved / Rejected / Deferred  
**Approval date and evidence:** ____  
**Approved implementation scope and prohibited work:** ____  
**New/updated test cases:** ____  
**Code/DBML/migration impact (separate authorization if applicable):** ____  
**Rollout and rollback ownership:** ____

## 3. Recommended meeting order

First: confirm authoritative campus fee/enrollment obligations and Admin/profile authority **as requirements**, without coding. Second: freeze the revised catalogue/record-scoping contract and API review policy. Third: approve narrow implementation stages and isolated tests; treat DB changes and feature activation as **separate decisions**. Finally: complete production privacy/operations/UAT acceptance before release.

## 4. Source control and sign-off

Keep `docs/database/full_schema.dbml` unchanged until a dedicated schema change is reviewed. The historically reported official AR-6C5D DBML SHA-256 (text-only amendment) is `BEFB42DF64A6D10B1AA0828A8E2A0A62FF3167B2B35DADCFA973FECF6D54C6D1`; future changes would require explicit approval and new hash recording. Do not modify authorization code/roles by editing this decision log.

**Pending sign-off:** Project owner ____ | SSG finance representative ____ | CTU enrollment-source representative ____ | Security/privacy reviewer ____ | Date ____.
