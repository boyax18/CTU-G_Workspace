# CTU-G Workspace — Security, Privacy and Operations Gates (Draft)

**Document ID:** CTUG-SEC-001 | **Date:** November 11, 2026  
**Status:** Review checklist; not a threat-model signoff, official campus privacy policy, role grant or permission activation.

## 1. Security invariants

| Boundary | Required safeguard | Evidence needed before activation |
|---|---|---|
| Account lifecycle | Pending/rejected/inactive cannot access; requested role does not grant | Registration + approval negative tests |
| Permission evaluator | Active role union + direct Grants, active Deny precedence, inactive account/role/service deny | Tests for all combinations, including mixed roles |
| Object-level access | Ownership/period/assigned class/action context checked **server side** | Cross-account/class/period API tests |
| Admin governance | Normal Admin cannot edit role defaults; Super Admin follows protected workflow | Allowlist, impact preview, independent review, audit rollback |
| Django framework Admin | Reviewed read-only maintenance models; `is_superuser` != Workspace grant | Django Admin negative tests, no custom API bypass |
| Audit | Attributable bounded event; security mutation atomic with its audit; receipts not modifiable or deletable by the application account; revocation not reversible by deleting a receipt (R-2, SR-1) | Forced-failure/rollback tests, privacy review; least-privilege and checkpoint tests on disposable databases (test_wf0301_r2_audit_integrity); OPEN until D-105 is decided and applied |
| Session and CSRF | HttpOnly cookie, secure origin, protection on state change, timely session invalidation; revocation not reversible by audit tampering | Browser integration + stale-session cases; SR-1 Stage A tests (test_wf0301_sr1_session_revocation, disposable databases). Source corrected and migration 0006 applied locally with all sessions cleared (D-106, Stage B Gate 2; owner login Test A pending, TC-042); trigger installation, restricted accounts and the SR-1a middleware fix OPEN |
| SMTP/password recovery | Feature-gated off unless separately approved; no token/log exposure | Safe reset tests, key rotation and sender/worker plan |
| Notification outbox | Encrypted recipient, bounded retries/leases, redacted logs, at-least-once backend acceptance semantics | Outbox isolation, retries, duplicate/rollback tests |
| Bulk review | 1–20 per immediate request and independent per-item authorization; large queue not auto-enabled | Replay, partial result, concurrency/revocation tests |
| Finance enrollment source | Verify official CTU enrollment externally; no CTU-G enrollment authority | Data contract, no-charge gap-period cases |
| Deployment | Production configuration and operational acceptance distinct from code/tests | Signed release checklist |

## 2. Threat/abuse scenarios to test

1. Student requests `Admin` / `Technical Super Admin` through registration payload; server rejects.
2. Normal Admin changes role defaults or promotes themselves using crafted requests; server denies, no side effects.
3. Valid role holder accesses another student's finances, other instructor's class, or another period; server denies.
4. A second role grants a permission but a direct Deny exists; Deny wins across all UI and API paths.
5. Django Superuser attempts Workspace business API without active custom grant; no automatic bypass.
6. Pending user uses a valid old session or password reset while inactive; protected access denied.
7. Approver's authority revoked between selection and bulk execution; target rechecked at transaction time.
8. Audit insert or outbox creation fails during a decision; protected transaction behaves exactly as documented.
9. Worker retries after provider timeout; duplicate email possibility is recognized; no false exactly-once guarantee.
10. User with Student+Treasurer duties tries to forgive or approve their own organizational fee; prohibited by approved conflict policy.
11. Missing or stale CTU main-system enrollment proof incorrectly treated as enrolled; assessment must not silently proceed.
12. Import of a second institutional data snapshot attempts to create duplicate fees for a previously assessed period.

## 3. Privacy and data minimization review items

- Identify a data steward for school ID, user profile, role history, fee transactions, receipts, rating records, authentication events and any enrollment verification evidence.
- Determine lawful purpose, user notices, accessible/inspectable data, export limits, retention and secure deletion rules with campus privacy officers; this checklist is not legal advice or an approved retention schedule.
- Never put plaintext passwords, hashes, reset tokens, real student records, unredacted security events, outbox recipients or secrets in tests, issue trackers, artifacts, README or examples.
- Auth activity log access by Normal Admin is a **proposed** redacted capability; event source/retention and user scope must be approved separately.
- Finance Monitor / SSG Advisor (same responsibility) may see only explicitly approved read-only financial overview, reports and scoped transaction history; not the raw full ledger or writes.
- Screen hiding is a usability layer, never proof of authorization. Exports, downloads and reports require their own server-side checks.

## 4. Governance and role defaults

The **proposed** profiles are `Normal Admin = Admin` and `Super Admin = Admin + protected technical governance role`, with first-operator provisioning and last-operator recovery. Additional role semantics (Instructor + SSG Advisor; Student + Treasurer; Instructor + Admin) require conflict checks. The V2 permission catalogue (10 services, 95 definitions, 106 candidate bindings) is a **proposal**, not a granted baseline. Protected role name, grantable-target allowlist, self-approval exception policy and governance approval chain are open decisions.

## 5. Feature-by-feature activation gates

| Feature | Existing evidence | Must remain blocked until |
|---|---|---|
| Registration-review live routes | Service/API tested, routes detached | Exact permission/service catalogue, object scope, API contract, negative tests and owner sign-off |
| Password recovery SMTP | Code/tests documented; feature disabled by default | Verified sender/secret handling, reset contract, abuse controls, owner approval |
| Notification outbox worker | Code/test checkpoint; worker disabled | Operations runbook, encrypted-key rotation, retention/alerting, sandbox test |
| 1–20 bulk review | Detached API; tests reported | Same individual approval controls plus per-item idempotency/race tests |
| 200-account persistent bulk | Official ERD text amended only | Approved schema+CHECK model, isolated migration, worker, failure recovery and explicit execution decision |
| Permission definitions/default grants | Read-only catalogue planner | Signed manifest, guarded grant initialization and separate activation decision |
| Protected campus modules | ERD and SRS describe future services | Module-specific API/data policy, privacy, record-scope tests and UAT |

## 6. Release gate owner checklist

| Gate | Owner (to assign) | Evidence reference | Decision/date |
|---|---|---|---|
| SRS and finance/enrollment policy | Campus system sponsor + finance office | ____ | Pending |
| Identity/role/permission governance | Technical & security reviewers | ____ | Pending |
| ERD/schema/migrations/rollback | DB and technical maintainers | ____ | Pending |
| Privacy/data retention | Campus privacy officer | ____ | Pending |
| CSRF/session/API/object authorization | Backend security reviewer | ____ | Pending |
| SMTP/worker operations | Operations/email owner | ____ | Pending |
| UAT/accessibility/performance | Student, instructor, finance, Admin representatives | ____ | Pending |
| Backup/restore and incident response | Deployment operations owner | ____ | Pending |
| Production go/no-go | Named authorized decision-makers | ____ | Pending |

**No checks in this document have been attested.** Record actual execution logs, source digests, date and accountable approver before changing a gate to complete.
