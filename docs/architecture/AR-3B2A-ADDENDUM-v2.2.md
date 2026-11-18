# AR-3B2A Addendum v2.2 - Permission Catalogue v2.2 Overlay (WF-03.01, D-103 Option A)

Status: owner-approved for policy on 19 November 2026 (D-103 Option A) and authorized for local
development implementation the same day. Independent review or signing of this addendum: OPEN
(not performed; tracked with the v2.1 review under D-101).

This addendum is a versioned overlay on the effective Permission Catalogue v2.1, which is itself an
overlay on the accepted v2.0. It does not edit, regenerate or replace any v2.0 or v2.1 file or pin.
It authorizes a static, validated planning specification only: no database provisioning, no role or
permission change in any database, no API, navigation or audit screen, no operational gate change and
no production use.

## 1. Base catalogue

| Field | Value |
| --- | --- |
| base_manifest_version | catalogue-v2.1 |
| base_effective_digest | 1adb16465e9d32712f890a95ee13dd5f21f4441790715aeaf91aa10c53183362 |
| base_effective_digest_rule | SHA-256 of the canonical JSON of the effective v2.1 catalogue (sorted keys, no whitespace) |
| base_addendum_sha256 | 78a3c7e2e0afd07a7c4c052e13f3503378076dc7f487d9ecf3bf1dc940e1afb7 |
| base_validator | backend/apps/access_control/catalogue/validation_v2_1.py (unchanged; must pass first, and it validates v2.0 first) |

## 2. Reason

The SRS gives the School Admin (Normal Administrator) no Access Control Management. Catalogue v2.1
still binds two read-only access_control defaults to Admin: inspecting ordinary accounts' roles and
capability summaries, and reading the school access-control audit projection. Both belong to the
Technical Super Admin. School Admin keeps its school operations through the accounts service:
account list, status and history (accounts.school_accounts.*), registration review, and the
school-scoped authentication activity code accounts.authentication_events.school.read.

## 3. Exact delta

### 3.1 Default-binding moves

| Permission code | From role | To role |
| --- | --- | --- |
| access_control.school_access.inspect | Admin | Technical Super Admin |
| access_control.audit.school.read | Admin | Technical Super Admin |

### 3.2 Result version identifiers

| Field | Value |
| --- | --- |
| schema_version | static-catalogue-v2.2 |
| manifest_version | catalogue-v2.2 |
| source_revision | v2.2-review-1 |

## 4. Preserved guarantees (no change)

- All 10 services, 95 permission definitions, 6 roles, role eligibility, retirement tombstone, v2
  delta record and scope definitions are identical to v2.1. No permission code is added or removed.
- 106 default bindings: every v2.1 binding except the two moved in 3.1 is identical and in the same
  position; both moves happen in place. Admin keeps 32 defaults and holds no access_control.*
  default; Technical Super Admin holds 13, all on the accounts and access_control services. Every
  accounts.* binding (WF-01 and WF-02) is unchanged.
- composition, delegation OFF, every policy blocker OPEN, every blocked permission without defaults,
  every operational gate BLOCKED, explicit Deny precedence, no role-name or Django Superuser bypass.
  The six governance codes stay bound only to Technical Super Admin, and
  access_control.governance_assignments.manage stays blocked and unbound.
- planning_only remains true. A default binding never creates a route, navigation item or audit
  screen; WF-12 must define any audit view separately.

## 5. Integrity-pin procedure

1. The SHA-256 of this file's exact bytes (UTF-8, LF line endings, protected from line-ending
   conversion by `.gitattributes`) is recorded as `ADDENDUM_SHA256` in
   `backend/apps/access_control/catalogue/validation_v2_2.py` and repeated, for the record only, in
   `backend/apps/access_control/catalogue/v2_2_delta.json` and the WF-03.01 decision record.
2. The validator trusts only its own reviewed constants (this addendum's digest, the effective v2.1
   digest and the v2.1 addendum digest). Copies elsewhere are never used as an authority. This file
   does not contain its own digest.
3. Any change to this file, the delta, v2.1, v2.0 or a v2.0 pin makes validation fail; a revision
   requires a new reviewed addendum version and a new pin.
4. Independent approval or signing of the pinned digest is OPEN until it is actually performed and
   recorded by a reviewer other than the author (D-101).

## 6. Not authorized by this addendum

Database provisioning of any permission, binding or role; assigning any role to a real account; API
routes, navigation items, feature switches or audit screens; P3B/P4 changes (D-102); executor storage;
changes to the official ERD or migrations; production use.
