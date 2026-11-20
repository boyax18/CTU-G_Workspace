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
