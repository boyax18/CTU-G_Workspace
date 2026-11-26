# Authorized permission inventory and preflight

26 November 2026 (Asia/Manila) · branch `ronald`.

**The full eight-table inventory completed at 20:19:41 Manila time**, following the authorized
live `access_control.0004`/`0005` migrations and scope-table SELECT grant. Persisted role-scope
evidence is now available; both scoped-Grant evaluation states are modeled. Independent
governance review remains OPEN. Earlier checkpoint records below retain their historical limits.

## Full inventory after authorized maintenance from `7d9624f`

Named operator Ronald used the owner-confirmed current-session maintenance window. The existing
reader authenticated to the verified local MySQL 8.4.13 target over TLS. Positive preflight
verified USAGE plus SELECT on exactly the eight approved tables, no other privilege or grant
option, `CURRENT_ROLE() = NONE`, and no mandatory roles. The existing reader credential and
owner-held pseudonym key were unchanged. The existing full-mode command ran its fixed queries
in a read-only consistent snapshot and rolled back; it did not use application credentials.

| Measure | Verified full-inventory result |
| --- | --- |
| Exact codes reviewed / stored definitions | 13 / 0 |
| Required services (`academic`, `clearance`, `finance`) | 0 of 3 |
| Role bindings, active / inactive | 0 / 0 |
| Account Allows (`Grant`), active / inactive | 0 / 0 |
| Account Denies, active / inactive | 0 / 0 |
| Source holders / accounts with modeled access changes | 0 / 0 |
| Potential expansions / losses | 0 / 0 |
| Legacy Deny pairs / new-Grant conflicts | 0 / 0 |
| Persisted role scope | **Available**; the new table is empty; both scoped-Grant scenarios modeled |

The reviewed codes/default comparison and conditional cohorts in the reduced snapshot below
remain unchanged: all 17 original application tables match their pre-migration schema and row
hashes. The missing base services, definitions and role bindings remain provisioning blockers;
zero modeled change is not authorization or evidence that catalogue defaults are live.
The inventory does not attest an authenticated selected-role request or appointment eligibility.

The detailed report is encrypted with CurrentUser DPAPI in the existing owner-protected vault:
`.local/wf11-inventory-private/wf11-activation-20261126-200645-ec7ff448.inventory.dpapi`.
Ciphertext SHA-256 `6296ac94c9df5cea7d95a9f0b5200fad4bacbb3269522a7a533a06aa9d2372fa`.
The seven Academic Settings migrations remain pending on the actual database; v2.3 is inactive,
all switches are OFF, and no HDAC provisioning or independent approval occurred.
[Migration, backup and rehearsal evidence](../operations/WF11_Migration_and_Activation_Runbook_2026-11-26.md#authorized-local-maintenance-execution-26-november-2026).

## Reduced inventory from `f63f8ac`

On 26 November 2026 at `14:15:38+08:00`, the operator verified the same `ctug_workspace` instance
at `127.0.0.1:3306` on MySQL 8.4.13. The reader username had no matching MySQL account. The operator
created `'ctug_wf11_inventory_ro'@'127.0.0.1'` with a server-generated 48-character password and
granted table-level SELECT on `accounts`, `account_roles`, `roles`, `permissions`,
`role_permissions`, `account_permissions` and `services`.

The reader authenticated over TLS. `CURRENT_USER()` matched the approved identity.
`SHOW GRANTS` returned USAGE plus the seven expected SELECT grants, with no grant option.
`CURRENT_ROLE()` returned `NONE` and the mandatory-role configuration was empty. The reader
then ran the fixed SELECTs in a repeatable-read, read-only snapshot and rolled it back.
Privileged access was used for metadata verification and the approved MySQL account setup.
The application permission query ran entirely as the reader.

The reader secret, pseudonym key and detailed report were encrypted with Windows DPAPI under
the owner's Windows profile in `.local/wf11-inventory-private/`. The directory's access rules
were verified for the owner and the encrypted files were decrypted in memory to check readback.
Git evidence contains aggregate counts. [Reader setup and verification](WF11_Permission_Inventory_Reader_Setup_2026-11-26.md).

The encrypted report is `permission-inventory-20261126T141538706050.dpapi` in that directory.
Ciphertext SHA-256 `d07bf2d82dd53cb310fd1778bc105f1e4be54e7203812ee4afa8ea86d5e3b24b`.

### Observed snapshot

| Measure | Count or status |
| --- | --- |
| Exact permission codes reviewed / stored definitions found | 13 / 0 |
| Required services found (`academic`, `clearance`, `finance`) | 0 of 3 |
| Role-to-permission bindings, active / inactive | 0 / 0 |
| Account Allows (`Grant`), active / inactive | 0 / 0 |
| Account Denies, active / inactive | 0 / 0 |
| Distinct source holders in scope | 0 |
| Distinct accounts with a potential modeled change under observed definitions and services | 0 |
| Legacy Deny account/replacement pairs to review, existing new Denies, new-Grant conflicts | 0, 0, 0 |
| `account_permission_role_scopes` | **Unavailable**. The table is absent and no scope rows were queried. |

The account query identified four active, Approved, non-framework accounts in the relevant
role cohorts. Two have Student assignments. One has Admin alone and one has Admin, Instructor
and Technical Super Admin assignments. None of these four has an active Treasurer assignment.
These are observed assignments. Source holders for the reviewed codes are zero.

### Catalogue comparison and potential impact

The source-pinned v2.2 catalogue and the v2.3 candidate were validated offline. Each exact code
below has zero live definitions, role bindings, direct overrides and holders in this snapshot.

| Reviewed code | v2.2 default | Candidate v2.3 default |
| --- | --- | --- |
| `academic.catalogue.read` | Admin, Instructor, Student, Treasurer | Same |
| `academic.courses.manage` | Admin | Same, clarified curriculum definition |
| `academic.enrollment_verifications.record` | Absent | Admin |
| `academic.historical_participation.correct` | Absent | Admin |
| `academic.periods.manage` | Admin | Same, clarified offering definition |
| `academic.profile.self.read` | Student | Same |
| `academic.profiles.manage` | Admin | Same |
| `academic.sections.manage` | Admin | Same |
| `academic.semester_onboarding.self.submit` | Absent | Student |
| `clearance.requests.self.submit` | Student | Same |
| `clearance.subjects.manage` | Admin | Same |
| `clearance.teaching_assignments.manage` | Admin | Same |
| `finance.fee_schedule.manage` | Treasurer | Admin |

The reduced model found **zero expansions and zero losses** under the observed service and
permission baseline. The catalogue defaults have not been provisioned for this scope. If an
independently approved change later provisions the services, definitions, role bindings and
applicable runtime prerequisites, the observed Admin cohort has two potential recipients for
fee management, verification and historical correction. One of those two separately holds
Technical Super Admin. Authority would come through its genuine Admin assignment. The two
Student accounts are the potential recipients for the new own-onboarding code. The fee move
would remove no observed Treasurer holder in this snapshot. These are counts of potential
recipients conditional on provisioning, eligibility and the applicable role context.

The inventory found no active legacy Deny to mirror for these transitions and no new-code
Grant conflict. The Deny-only predecessor mapping still applies to any future cutover review.
Existing Denies elsewhere are outside the reviewed codes. Review a fresh snapshot before
provisioning and preserve the Deny precedence and genuine Admin fee grant requirements.

### Governance limits and next decision

The missing table leaves persisted role scope unavailable. The inventory did not model the
scope-enabled resolver. Its conditional comparison covers only scoped Grant evaluation off.
Live role-selection context, ordinary appointments, switches and workflow conditions were
outside this snapshot. Any scope-enabled use needs the normal schema and authorization review.
The resolver remains fail closed on database errors. Independent review stays OPEN.

Request authorization for a separate read-only migration ledger and schema reconciliation for
`access_control.0005_account_permission_role_scopes` and its ancestors. Use the result for a
backup and restore rehearsal and a reviewed migration decision. In parallel, scope the base
service and exact-role provisioning for the first School Admin phase. The empty base is a
separate blocker from the v2.3 delta. [Pending migration dependencies](../operations/WF11_Migration_and_Activation_Runbook_2026-11-26.md#pending-role-scope-inventory-dependency).

## Reader setup preflight from `f9cf56b`

The owner approved the dedicated reader and the eight documented table-level SELECT grants.
The administrative preflight authenticated over loopback TCP and confirmed MySQL 8.4.13 at
`127.0.0.1:3306` with `ctug_workspace` selected. It read server and table metadata and checked
the proposed username in `mysql.user`.

| Check | Verified result |
| --- | --- |
| Existing InnoDB base tables | 7 of 8. `services`, `permissions`, `roles`, `role_permissions`, `account_permissions`, `account_roles`, `accounts` |
| Missing table | `account_permission_role_scopes` |
| Reader account | `ctug_wf11_inventory_ro` has no matching MySQL account at any host |
| Server mandatory roles | None configured when checked |
| Account creation and grants | No `CREATE USER` or `GRANT` statements issued |
| Reader login and effective privileges | Pending account creation |
| Permission inventory | No application records queried. Definition, binding, holder, Allow, Deny and potential access-change counts are unknown |

The repository defines the absent table in `access_control.0005_account_permission_role_scopes`.
The preflight checked table presence. The migration ledger was outside this check. MySQL requires
`CREATE` in a grant on a table that does not exist, so the eighth SELECT grant cannot be issued
under the approved procedure. The prepared inventory also requires the table.
[Migration source](../../backend/apps/access_control/migrations/0005_account_permission_role_scopes.py) ·
[MySQL GRANT documentation](https://dev.mysql.com/doc/refman/8.4/en/grant.html).

The approved procedure still specifies all eight tables. The proposed decision for the current
schema is to approve a reader with seven table-level SELECT grants and an inventory that reports
per-Grant role scope as unavailable. The potential access comparison would be limited to the
resolver configuration with scoped Grant evaluation off. Independent review remains open.
[Reader setup procedure](WF11_Permission_Inventory_Reader_Setup_2026-11-26.md).

## Initial configuration preflight from `10e3fe8`

This earlier pass ended before a database connection. The findings below describe that pass.

The owner authorized the prepared SELECT-only inventory and local documentation commits, while
requiring an existing suitable SELECT-only account and positive target/privilege verification.
The owner subsequently confirmed `backend/.env` as the connection configuration and that no
separate reader had intentionally been configured. Inspecting local configurations/login profiles
and preparing account-creation instructions were authorized; creating an account was not.

### Observed configuration findings

| Check | Actual observation |
| --- | --- |
| Repository checkpoint | `ronald`, HEAD `10e3fe8`; existing untracked reconciliation folder preserved |
| Configured application target | `127.0.0.1:3306`, database `ctug_workspace` in `backend/.env` |
| Application database identity | Configured as `root`; not used for connection, account enumeration or inventory |
| Inventory configuration | No `WF11_INVENTORY_DB_*` or `WF11_INVENTORY_HMAC_KEY` available in the process or application configuration |
| Standard client option files | No reader found in checked user, drive-root, Windows or MySQL installation option-file locations; the ProgramData server option file's client groups contain no identity/password |
| MySQL saved login paths | `mysql_config_editor.exe print --all` returned success with no profiles/output; standard `.mylogin.cnf` location absent |
| Workbench connection profiles | Three root profiles and one unverified non-root profile; the non-root profile has no password available in the inspected configuration, no selected schema, no read-only naming indication and no privilege proof |
| Actual server/database identity | **Unverified**: configuration metadata is not evidence of a connected server |
| Actual SELECT-only privileges | **Unverified**: no suitable authenticated reader was available for `SHOW GRANTS` |
| Database connections / SQL statements executed | **0 / 0** |

Only nonsecret connection metadata and key presence/classification were displayed. No password,
credential value, non-root username, application-account identity or personal record is included.
No credential vault was enumerated, no password guessed, and no root/application fallback used.

**Conclusion:** no usable verified SELECT-only connection was found in the accessible local
configurations/login profiles. This does **not** prove that the server contains no read-only account:
server-wide account enumeration was not performed through the prohibited root fallback.
Per the owner's stop condition, the database operation stopped before connection.

### Inventory status before reader creation

The prepared scope names **13 permission codes**. That is a source-code scope count, not a count
of permission rows actually present in `ctug_workspace`.

| Requested live metric | Result |
| --- | --- |
| Affected permission definitions / active services | Unknown — not inspected |
| Affected active/inactive role bindings | Unknown — not inspected |
| Account-level Allows (`Grant`), active/inactive and role scopes | Unknown — not inspected |
| Account-level Denies, active/inactive | Unknown — not inspected |
| Existing old-code holders / affected accounts / multi-role combinations | Unknown — not inspected |
| Potential privilege expansion or access loss | Unknown — no live source data |
| Required new-code Deny additions / conflicts with existing Grants | Unknown — no live source data |

None of these unknowns is zero. No pseudonymous account report was generated, and no old approval,
isolated test fixture, catalogue default or backup count was substituted for a live finding.
Validation of actual grants/holders against the [governance proposal](WF11_AcademicSettings_Permission_Governance_Proposal_2026-11-26.md)
and candidate v2.3 therefore remains outstanding.

The source-derived Deny requirements remain:

| Candidate operation | Denies that must retain effect |
| --- | --- |
| Official verification: `academic.enrollment_verifications.record` | Old `academic.profiles.manage` Deny and any new-code Deny |
| Own onboarding: `academic.semester_onboarding.self.submit` | Old `clearance.requests.self.submit` Deny and any new-code Deny |
| Historical correction: `academic.historical_participation.correct` | Either old `academic.periods.manage` / `academic.profiles.manage` Deny and any new-code Deny |
| Fee binding move: `finance.fee_schedule.manage` | Existing Deny on the unchanged code |

Keep every old Deny and its history; review new-code Deny additions/Grant conflicts after actual
inspection. Never infer replacement Allows from broad old Allows. The uninstalled candidate's
Deny-only compatibility remains a proposal, not effective runtime behavior or an approved migration.

## Authorization history

The first pass required either an existing verified reader or separate authorization to create
the documented reader. The owner supplied that authorization for the eight-table setup. The
schema check above is now the blocker. The existing read-only inventory authorization remains
on record.
