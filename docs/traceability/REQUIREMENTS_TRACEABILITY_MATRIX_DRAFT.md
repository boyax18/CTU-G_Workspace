# CTU-G Workspace — Requirements Traceability Matrix (Review Draft)

**Document ID:** CTUG-RTM-001 | **Date:** November 11, 2026  
**Source:** SRS v0.4 **review draft**. The companion's new `FR-FIN-09..14`/`AT-25..31` are **proposed only**.  
**Evidence convention:** P = planned requirement; I = implementation observed in reviewed snapshot; T = automated test checkpoint reported (not rerun here); D = feature detached/disabled; G = release/governance gate pending; U = UAT pending. Status labels may coexist.

| SRS ID / area | Acceptance ID | Current observed development evidence | Live/release status | Follow-up verification |
|---|---|---|---|---|
| FR-REG-01..03 public registration | AT-01 | Student/Instructor backend route and tests described | I,T,U | Verify full browser/validation, field/privacy negative tests |
| FR-REG-04..08 approvals and provisioning | AT-02 | Trusted approval service + inactive review API described | I,T,D,G,U | Authorize reviewer scope, exact code, negative/atomic audit API tests |
| FR-AUTH-01..06 session, CSRF, lifecycle | AT-01,02,23 | Django sessions/CSRF and React shell reported | I,T,U | Cross-browser session expiry, role revocation, cookie/origin tests |
| FR-AUTH-07 rate-limit/auth events | AT-12 | Storage and event contract not approved | P,G | Design and privacy review, rate-limit tests |
| FR-ACL-01..03,11 deny and object scope | AT-11,16,23 | Evaluator implementation/tested; no active catalogue | I,T,G,U | Service gating + module-specific ownership tests |
| FR-ACL-04..10,12..14 protected governance | AT-03,06,07,08,09,10,14,15 | Historical C1/C2A planning, no approved grants | P,G | Role composition, catalogue manifest, impact/mutation/rollback |
| FR-ADM-01..09 role assignment profiles | AT-03,05,08,09,10 | Admin role/default policy proposed; bootstrap separate | P,G | Target allowlist, conflicts, audit and no self-escalation |
| FR-ACA-01..04 academic | AT-16 | ERD and intended use cases | P,G,U | Module workflow, CTU-owned data source, record/class scopes |
| FR-FIN-01..08 SSG Finance | AT-04,05,24 | ERD and desired finance flows | P,G,U | Ledger/fee policy, conflict controls, monitor read-only exports |
| Proposed FR-FIN-09..14 | Proposed AT-25..31 | Companion only; no approved code evidence | P,G | Approve external enrollment status/fee recurrence/returning rules |
| FR-CLR-01..05 clearance | (not individually numbered in v0.4) | ERD and intended behavior | P,G,U | Add signed test cases for signatory/period/ownership/print |
| FR-RAT-01..04 group rating | (not individually numbered in v0.4) | ERD and intended behavior | P,G,U | Tests for group membership, duplicate/self-rating and privacy |
| FR-COM-01..04 announcements/reports | (not individually numbered in v0.4) | ERD/intended behavior | P,G,U | Audience, read-state, report finalization/export tests |
| FR-AUD-01..05 security events/audit | AT-12,15 | Mutation audit implemented; auth-event store pending | I,T,G | Scope, PII redaction, retention, rollback and real role grant |
| FR-DJA-01..07, FR-ADMRO-01 | AT-13,22 | Read-only `/admin/` reviewed and 121/121 backend suite reported | I,T,U | Test current candidate, model allowlist and bypass negatives |
| FR-REC-01..02 password recovery | AT-17 | Recovery code/tests documented | I,T,D,G | E2E email/sender flow, anti-enumeration and secure rollout |
| FR-NOT-01..02 notification outbox | AT-18,19 | Encrypted writer + worker code, historical 93/93 checkpoint | I,T,D,G | Sender, worker/queue recovery, key rotation and privacy |
| FR-BULK-01..02 immediate selected review | AT-20 | Detached service/API; historical 115/115 checkpoint | I,T,D,G | Each-item authorization/replay/concurrency and live-routing gate |
| FR-BULK-03 durable bulk queue | AT-21 | Two official ERD **text-only** tables | P,G | Models, approved migration, worker, operational recovery and load |
| FR-UI-01..08 shared dashboard | AT-23 | Shell, 38/38 frontend, successful build/browser render | I,T,G,U | Exact session permissions, accessible navigation and module API E2E |
| FR-DOC-01 documentation/change control | AT-14 (partial) | November 11 v0.4 SRS + 12-file refresh prepared | I,G | Integrate/approve package, keep evidence versioned |
| NFR-SEC-01..03 security | AT-07,09..16,22,23 | Selected negative tests reported | T,G | Full release-candidate security matrix, threat model |
| NFR-PRV/AUD/REL/PER/USA/OPS | All applicable | Proposed standards, limited technical checkpoints | P,G,U | Privacy officer review, performance/restore/accessibility evidence |

## Missing acceptance-test ID coverage

The parent v0.4 contains detailed functional requirements for **academic, clearance, group rating, announcements and reports** but no dedicated `AT` IDs for many module-level workflows. After those modules and policies are approved, add unique tests (do not reuse another feature's ID) and complete a two-way mapping: each P0 requirement -> at least one positive and one negative test where applicable; each test -> versioned requirement. The companion `AT-25..31` are **not adopted** automatically.

## Evidence register template

| Evidence ID | Test ID | Source commit and environment | Observed result | Reviewer/date | Notes |
|---|---|---|---|---|---|
| EV-____ | TC-____ / AT-____ | ____ | Pass/Fail/Blocked/Not run | ____ | Redacted log or screenshot reference |

**Policy:** Never mark a requirement "complete" solely because it exists in a DBML, UX shell, documentation draft, disabled service, or a historical test count. A completed release needs implemented+verified+approved gates.
