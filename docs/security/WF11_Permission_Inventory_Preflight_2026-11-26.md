# Authorized permission inventory — connection preflight blocked

26 November 2026 (Asia/Manila) · branch `ronald` · starting commit `10e3fe8`.
**Owner-authorized read-only inventory; NOT EXECUTED. No database connection attempted.**

The owner authorized the prepared SELECT-only inventory and local documentation commits, while
requiring an existing suitable SELECT-only account and positive target/privilege verification.
The owner subsequently confirmed `backend/.env` as the connection configuration and that no
separate reader had intentionally been configured. Inspecting local configurations/login profiles
and preparing account-creation instructions were authorized; creating an account was not.

## Observed configuration findings

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

## Inventory results and governance implications

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

## Blocker and next permitted step

Inventory authorization is already granted and does not need to be requested again. Resume the
same guarded inventory only after an existing authenticated SELECT-only connection is supplied
and its target/privileges are positively verified. Supply a secure local configuration location,
not a password in chat; keep the owner-held pseudonym key/report outside Git.

If no existing suitable reader can be supplied, the exact [dedicated reader setup proposal](WF11_Permission_Inventory_Reader_Setup_2026-11-26.md)
is ready for **separate** owner/DBA authorization. It creates one new local database identity and
grants SELECT on eight named existing tables only. No such SQL was executed. Existing credentials,
HDAC rows, migrations, protected pins, feature switches, launcher modes and approval fields remain
unchanged. Independent governance review and the pending policy decisions remain OPEN.
