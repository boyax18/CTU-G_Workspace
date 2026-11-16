# CTU-G Workspace — Master Test Specification and UAT Plan (Draft)

**Document ID:** CTUG-TEST-001 | **Date:** November 11, 2026  
**Status:** Planning document; no new tests executed or release certified.  
**Requirements source:** SRS v0.4 review draft, `AT-01..AT-24`. Proposed SRS companion scenarios `AT-25..AT-31` remain outside the accepted baseline until approved.

## 1. Test policy

The SRS defines **what must happen**. This test specification defines **how to verify it**. Keep one stable master SRS plus an associated versioned test specification and execution record; never rewrite requirements merely to match code. Each result must identify environment, source revision, date, executor, setup, evidence and whether the feature was enabled. Development tests do not equal production approval.

Use a disposable isolated MySQL database for data-writing backend tests, and non-production identities. No real student information or live payments should be used. Mock or sandbox third-party enrollment/SMTP services unless their owners authorize end-to-end testing. Record cleanup and capture redacted evidence.

## 2. Planned layers

| Level | Purpose | Completion criteria |
|---|---|---|
| Static/configuration | Check docs, env defaults, route isolation, migrations, secrets and code analysis | No unapproved flags, drift, hidden credentials or accidentally connected protected routes |
| Unit/service | Validate business rules, evaluator, audit, idempotency and negative cases | Key invariants tested, deterministic runs |
| API/integration | Verify auth, CSRF, effective permissions, object scope, rate limits, transaction rollback | Auth/permission matrix passes in isolated DB |
| Frontend | Confirm components, navigation, empty states, keyboard behavior and errors | Build and tests pass; no hidden-button-only security |
| Browser end-to-end | Registration -> review -> login -> dashboard -> logout using approved sandbox gates | Evidenced full path in isolated environment |
| UAT | Stakeholders perform real-role scenarios on synthetic data | Signed acceptance with open defects documented |
| Nonfunctional/release | Performance, recovery, secure cookies, SMTP reliability, backup/restore | Agreed thresholds and tested runbooks, not just stated intentions |

## 3. Case inventory — planned acceptance

| Case ID | Related SRS scenario and requirement | Setup / action | Expected evidence | Current classification |
|---|---|---|---|---|
| TC-001 | AT-01; FR-REG-01..03 | Register Student or Instructor and attempt restricted fields | Pending inactive account, linked profile, no assigned role; invalid requests rejected | Related automated coverage reported; not independent UAT |
| TC-002 | AT-02; FR-REG-04..06 | School reviewer approves eligible pending request | Atomic role assignment, active status, bounded audit, login eligibility | Service tests reported; live review API detached |
| TC-003 | AT-02, AT-15; FR-AUD-01 | Force audit failure during approval | No partial account/role mutation | Related service tests reported; verify exact proof |
| TC-004 | AT-07, AT-09, AT-10 | Ordinary Admin tries protected role/default/self promotion | Explicit denial; zero state change | Gate/proposal; cannot claim live feature |
| TC-005 | AT-11; FR-ACL-01..02 | Multi-role grants plus direct Deny | Deny wins; active service/role rules apply | Evaluator tests reported; live grants not approved |
| TC-006 | AT-16; FR-ACL-11 | Fetch another student's finance or other class | Server denies/filters even if button is visible | Needed per module; not complete |
| TC-007 | AT-03..04; FR-FIN-03..07 | Instructor with SSG Advisor responsibility reads 3 approved views and attempts finance write | Scoped read allowed only with grants; all writes denied | Proposed role/catalogue unactivated |
| TC-008 | AT-05; FR-ADM-08 | Student+Treasurer attempts self-payment/exemption processing | Self-benefit action denied; independent authorized case allowed | Needs policy and implementation |
| TC-009 | AT-13, AT-22; FR-DJA-01..07 | Django superuser enters restricted `/admin/` | Reviewed read-only models only; no Workspace grant/bypass | 121/121 backend checkpoint reported; confirm exact suite |
| TC-010 | AT-17; FR-REC-01..02 | Request/reset password, replay/expire token, wrong CSRF | Enumeration-resistant and secure reset; no token disclosure | Feature-gated off; related tests reported |
| TC-011 | AT-18..19; FR-NOT-01..02 | Commit approval+audit+encrypted outbox; simulate worker retry/failure | Atomic result, bounded retry, no plaintext PII; no exactly-once claim | Outbox code/test snapshot, disabled by default |
| TC-012 | AT-20; FR-BULK-01..02 | Select 1–20 identities, mix eligible/revoked/missing | Per-item decisions, partial status, audit; no bulk bypass | Detached routes; 115/115 checkpoint reported |
| TC-013 | AT-21; FR-BULK-03 | Attempt durable 200-target queue in approved test sandbox | Correct freeze/idempotency/cancel/retry/recover and audit | ERD text only; **not executable yet** |
| TC-014 | AT-23; FR-UI-01,07,08 | One session, multi-role shell; Deny and inactive service | Correct links/absence; protected API independently denies | 38/38 frontend + build reported; browser acceptance pending |
| TC-015 | AT-24; FR-FIN-01..08 | Freshman, transferee, gap, returning fee case set | Uses verified external official status; no local enrollment authority | Policy approval and module tests pending |
| TC-016 | AT-06, AT-14; FR-ACL-03..13 | Planner vs approved future catalogue; role-default impact preview | No unapproved grant, accurate impact/rollback | Planning-only, no catalogue activation |
| TC-017 | AT-12; FR-AUD-02..05 | Normal Admin reads redacted auth events | Only approved scoped metadata, no secrets | Auth-event storage/view not finalized |
| TC-018 | AT-08..10; FR-ADM-02..04 | Protected bootstrap/promotion/removal | Independent attribution, last-operator safeguards | Governance decisions pending |
| TC-019 | AT-25..31 (proposed) | Detailed enrollment-derived fee obligation matrix | Proposed cases in SRS companion | **Not approved/not run** |

Case inventory is not a claim that each SRS AT has a unique automated test. Reviewer must trace actual test names and latest Git revision to these cases.

## 4. Mandatory negative security matrix

For each protected API/service, run at least: unauthenticated; CSRF absent/invalid (state changes); pending/rejected/inactive; no effective permission; active direct Deny; inactive service; incorrect record owner/class/period; mixed-role conflict; privilege escalation from payload fields; replay/duplicate; audit insertion failure; revoked session/role before request; and Django staff/superuser without custom grant. Mark *Not applicable* with reason, not silently skip.

## 5. UAT scripts (with synthetic accounts)

**UAT-A Student:** register -> remain pending -> approved by authorized reviewer -> log in -> see own dashboard -> attempt another student's records (denied) -> logout.  
**UAT-B Instructor:** register -> approval -> assigned teaching records -> no other class -> no finance-monitor view without approved responsibility.  
**UAT-C School Admin:** review requests -> test rejection reason privacy -> attempt protected role grant/template change (denied).  
**UAT-D Technical governance:** attempt reviewed role template preview, audit, change and rollback **only after separately activated test contract**.  
**UAT-E Finance owner:** simulate newcomer/inactive/return with verified external enrollment fixtures; reconcile gaps and outstanding debt (after policy approval).  
**UAT-F Technical operator:** inspect restricted Django Admin; cannot mutate Workspace permissions from Django UI.

## 6. Test evidence ledger template

| Field | Required content |
|---|---|
| Test/case ID | `TC-xxx`, `AT-xx` and requirement IDs |
| Build/source revision | Commit SHA, branch and migration list |
| Environment | OS, MySQL test database, browser/build version, fixture version |
| Flag/route state | Disabled/enabled in isolated sandbox, catalogue manifest digest |
| Steps and expected | Repeatable actions; redacted inputs |
| Actual result | Pass/Fail/Blocked/Not Run with reason |
| Evidence | Test log name, screenshot ID, CI run ID, date and reviewer |
| Security impact | Deny/object-scope/audit/rollback findings |
| Defect | Ticket, severity, owner, retest evidence |

## 7. Known historical evidence (not rerun here)

- November 10–11 source review references **121/121 backend**, **38/38 frontend**, and successful frontend build, with committed shared dashboard shell (reported `32675e5`).
- Earlier 93/93 and 115/115 backend checkpoint counts are **overlapping historical runs**, not additional test totals.
- The existing docs test record from November 8 is older; reconcile logs against source and CI before marking any row accepted.
- No end-to-end campus UAT, production SMTP, large-queue migration or production readiness can be inferred from these counts.

## 8. Release exit criteria

Every required P0 test passes on the **release candidate**, no unresolved critical security defects, all target roles and DENY/cross-object negatives covered, reviewed ERD/migrations and rollback evidence, verified secret management and recoverable backups, feature gates approved separately, campus UAT signed with an explicit exception list. Record the signed decision; automated pass counts alone are insufficient.
