# AR-3B2A Addendum v2.1 - Permission Catalogue v2.1 Overlay (WF-03.01, D-89)

Status: owner-authorized for local development on 18 November 2026 (WF-03.01 Stage D, decision D-89).
Independent review or signing of this addendum: OPEN (not performed).

This addendum is a versioned overlay on the accepted Permission Catalogue v2.0. It does not
edit, regenerate or replace `backend/apps/access_control/catalogue/v2_0.json`, the AR-3B2A
proposal, the SRS v1, AR-2, AR-3A or C1 sources, or any of their pins. It authorizes a static,
validated planning specification only: no database provisioning, no role or permission
change in any database, no API activation, no operational gate change and no production use.

## 1. Base catalogue

| Field | Value |
| --- | --- |
| base_manifest_version | catalogue-v2.0 |
| base_manifest_path | backend/apps/access_control/catalogue/v2_0.json |
| base_manifest_sha256 | a7e2705236a37522b77468fd4154113d19e7e64bc479cfa420c41d7744a2548b |
| base_manifest_digest_rule | SHA-256 of the content with CRLF normalized to LF (equal to the committed Git blob) |
| base_validator | backend/apps/access_control/catalogue/validation_v2.py (unchanged; must pass first) |

## 2. Reason

The owner-directed administrator model (ADR-004) makes the Technical Super Admin
(Instructor + Admin + Technical Super Admin) the only application role that manages
Access Control Management operations. School Admin (Instructor + Admin) handles school
operations and must not inherit any role-management authority. Catalogue v2.0 still binds
the ordinary-role management permission to Admin; this overlay moves that single default
binding and restates the two affected eligibility rules. The Django Superuser keeps its
protected framework procedures and receives no application bypass.

## 3. Exact delta

### 3.1 Default-binding moves

| Permission code | From role | To role |
| --- | --- | --- |
| access_control.role_assignments.ordinary.manage | Admin | Technical Super Admin |

### 3.2 Role eligibility restatements

| Role name | Requirement |
| --- | --- |
| Admin | Approved active Instructor promoted through a protected role procedure; retains Instructor. |
| Technical Super Admin | Granted or revoked only by the Django Superuser through the protected procedure; requires approved active Instructor and Admin; retains both. |

### 3.3 Result version identifiers

| Field | Value |
| --- | --- |
| schema_version | static-catalogue-v2.1 |
| manifest_version | catalogue-v2.1 |
| source_revision | v2.1-review-1 |

## 4. Preserved guarantees (no change)

- All 10 services, 95 permission definitions, 6 roles, retirement tombstone, v2 delta record
  and scope definitions are identical to v2.0. No permission code is added or removed.
- 106 default bindings: every v2.0 binding except the one moved in 3.1 is identical and in
  the same position. Admin keeps its other 34 defaults, including every WF-01 and WF-02
  registration-review and school-account binding; Technical Super Admin gains exactly one.
- composition (normal_admin, application_super_admin with its six governance codes bound only
  to Technical Super Admin, ssg_advisor, required multi-role combinations, authorization
  contract with explicit Deny precedence and no role-name or Django Superuser bypass),
  delegation OFF, every policy blocker OPEN, every blocked permission without defaults and
  every operational gate BLOCKED.
- Technical Super Admin defaults stay limited to the accounts and access_control services;
  access_control.governance_assignments.manage stays blocked and unbound.
- planning_only remains true. Runtime enforcement is not implemented by the manifest.

## 5. Integrity-pin procedure

1. The SHA-256 of this file's exact bytes (UTF-8, LF line endings, protected from line-ending
   conversion by `.gitattributes`) is recorded as `ADDENDUM_SHA256` in
   `backend/apps/access_control/catalogue/validation_v2_1.py` and repeated, for the record only,
   in `backend/apps/access_control/catalogue/v2_1_delta.json` and the WF-03.01 decision record.
2. The validator trusts only its own reviewed constant; the copy in the delta file must equal
   it and is never used as an authority. This file does not contain its own digest.
3. Any change to this file, the delta, the base manifest or a v2.0 pin makes validation fail;
   a revision requires a new reviewed addendum version and a new pin.
4. Independent approval or signing of the pinned digest is OPEN until it is actually
   performed and recorded by a reviewer other than the author.

## 6. Not authorized by this addendum

Database provisioning of any permission, binding or role; assigning Technical Super Admin or
any role to a real account; API routes or feature switches; executor storage; changes to the
official ERD or migrations; production use; ordinary-role (Treasurer, SSG Advisor) assignment
paths, which remain subject to their own eligibility decisions (D-100).
