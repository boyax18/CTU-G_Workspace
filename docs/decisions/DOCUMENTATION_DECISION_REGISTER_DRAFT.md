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
| D-89 | Permission Catalogue v2.1 overlay (ordinary-role management to Technical Super Admin) | Implemented 19 Nov 2026 (local development; validated specification only, not provisioned): AR-3B2A v2.1 addendum (pinned 78a3c7e2e0afd07a7c4c052e13f3503378076dc7f487d9ecf3bf1dc940e1afb7), v2_1_delta.json, validation_v2_1.py; v2 byte-identical; independent pin review OPEN; SRS v0.5 and Use Case v0.4.2 amendments not issued. Validator corrected 19 Nov 2026 in commit 9e259e7 (D-101 F-1: the v2 base is parsed only from the verified bytes; pins and effective digest unchanged). v2.1 is a historical validated dependency only; operational adoption must use the approved v2.2 chain (D-101 F-2). |
| D-101 | Independent review of the catalogue v2.1 and v2.2 addendum pins | OPEN: review package prepared 19 Nov 2026 and extended to v2.2 (docs/security/WF-03.01_D-89_CATALOGUE_V2_1_INTEGRITY_REVIEW_PACKAGE.md; separate v2.1 and v2.2 sign-offs); not reviewed; adoption of either catalogue blocked until approved by a reviewer other than the author, v2.1 first. Technical pre-review (non-independent, automated; no sign-off) 19 Nov 2026 at edbaf9f: digests, deltas and the validator chain reproduced, 97/97 tests passed, CONDITIONAL PASS with findings F-1 to F-7 (docs/security/WF-03.01_D-101_TECHNICAL_PRE_REVIEW.md). F-1 (unverified second read in validation_v2_1) corrected under owner authorization the same day in commit 9e259e79000be960569a55a82b8bc1841257dc37 (validation_v2_1.py blob e176f9267b69baae7546d060064254d26a3e7df7a106b6505e941cb5b83d98b3) with 4 regression tests (focused 101/101); v2.1 review scope 14125f9 + 9e259e7; documentation corrections D-1 (probe count: 39 genuine tamper probes rejected) and D-2 (commit reference) recorded; F-2 recorded: Permission Catalogue v2.1 is a historical validated dependency only, and operational adoption must use the approved v2.2 chain, subject to independent sign-off and separate activation authorization. Independent approval of v2.1 (including the corrected validator) and then v2.2 still required; sign-offs blank. |
| D-102 | P3B compatibility with the v2.1 ordinary-role code | OPEN: cause verified; proposal limited to an exactly proven, reviewed extension set of the governance profile (generalized by D-103), compensation still refused, P4 scope unchanged. Exact v2.2 requirements (extension set of three codes, diagnostics.read excluded, receipts 1 + (6 + k) + (6 + k), locks and P4 scope unchanged) recorded 19 Nov 2026 in docs/security/WF-03.01_PROTECTED_PROVISIONING_READINESS.md; not implemented; needs D-101 sign-off and separate authorization. |
| D-103 | School Admin read-only access_control defaults (school_access.inspect, audit.school.read) | Option A implemented 19 Nov 2026 (local development; validated specification only, not provisioned): Permission Catalogue v2.2 overlay moves both defaults from Admin to Technical Super Admin; addendum pinned 4285837e51f5331bb54fab50246c25d4efb0bbd65905a567368ba7e6681f8fdd; independent review OPEN (D-101). |
| D-104 | Permission Catalogue target specification | Owner direction 19 Nov 2026: Permission Catalogue v2.2 is the current target specification; v2.1 is maintained only as its verified dependency, not a separate operational target. Not an operational adoption: every runtime consumer (framework_roles, P3B/P4, the WF-02.05 companion, planners) still reads v2.0, and nothing is provisioned. Adoption requires the D-101 independent sign-offs (v2.1, then v2.2), D-102, D-93/D-95 and separate consumer-switch and provisioning authorization. |
| D-100 | Ordinary-role assignment and continuous role composition | OPEN: Technical Super Admin assignment of ordinary roles (Treasurer, SSG Advisor) is not implemented and their eligibility rules are undecided. Tracked here (D-101 F-4): any future path that removes Instructor must refuse while Admin or Technical Super Admin is held, or has_technical_authority must also require Instructor. |
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
