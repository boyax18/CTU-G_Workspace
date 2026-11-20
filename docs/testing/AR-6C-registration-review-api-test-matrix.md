# CTU-G Workspace — AR-6C Registration Review API Test Matrix

**State:** DRAFT test plan; NOT a report of tests run.
**Prepared:** 2026-11-08
**Execution target:** isolated Django/MySQL test database, never production/dev data for destructive assertions.

## Acceptance cases

| ID | Setup / request | Expected result |
| --- | --- | --- |
| API-01 | Feature flag off; all three routes | Denied/unavailable; no data or audit write |
| API-02 | Anonymous GET list | No pending personal data exposed |
| API-03 | Anonymous POST with valid-looking payload | Denied; explicit CSRF/session rule applies; no write |
| API-04 | Authenticated Student/Instructor | No list or decision authority |
| API-05 | Approved active Admin role, **without** effective permission | Denied; role name alone insufficient |
| API-06 | Admin role Grant plus account-level Deny | Denied despite role grant |
| API-07 | Inactive Admin role / account / requisite service | Denied; no write |
| API-08 | Django Superuser session | No Workspace registration-review authority |
| API-09 | Authorized Admin with `read` only | Can see allowed minimal list, cannot approve/reject |
| API-10 | List includes pending Student/Instructor and unrelated/sensitive accounts | Only eligible request objects; only approved fields; pagination validated |
| API-11 | Valid approve with exact permission | Target Approved+active, **one requested** base role, one audit event |
| API-12 | Valid reject with exact permission and allowlisted code | Target Rejected+inactive, no assigned role, one audit event |
| API-13 | Target = actor or staff/superuser target | Denied; no write |
| API-14 | Target already reviewed, role-assigned or not Pending | Denied; no duplicate assignment/audit |
| API-15 | Requested role = Admin/Treasurer/protected/inactive | Denied; no write |
| API-16 | Missing CSRF or invalid Origin; malformed JSON | Rejected before mutation; no write |
| API-17 | Request uses unexpected fields or free-text reason | 4xx; no write; no secret reflected |
| API-18 | Oversize payload or throttle exceeded | Limited; no write; safe response |
| API-19 | Two simultaneous decisions to same target | Exactly one final decision and matching audit; competitor safely denied |
| API-20 | Audit writer intentionally fails | Decision and role assignment fully rolled back |
| API-21 | Granted permission revoked mid-session | Next protected request denied; no stale grant use |
| API-22 | Hand-crafted request despite hidden UI controls | Backend independently enforces effective permission |
| API-23 | Invalid/inaccessible account ID | No account-existence leakage; no write |
| API-24 | Regression: normal login, CSRF endpoint, logout, public registration | Existing behavior and tests remain passing |

## Execution log template — leave blank until real run

| Field | Entry |
| --- | --- |
| Test run date / executor | NOT RUN |
| Git commit/branch | NOT RECORDED |
| Catalogue digest / activation profile | NOT APPROVED |
| Django/MySQL versions | NOT RECORDED |
| Test runner command | NOT RUN |
| Passed / failed / skipped | NOT RUN |
| Defects and remediation | NOT RECORDED |
| Reviewer sign-off | NOT APPROVED |

## Baseline evidence (separate from this proposed API)

- AR-6A1 domain service: 17 isolated tests reportedly passed.
- AR-6A2 Admin bootstrap: 15 isolated tests passed.
- AR-5A session auth + registration: 44 regression tests reportedly passed.
- AR-5B frontend: 25 tests and build passed.
- AR-6B1 static manifest: passed, planning-only; no DB writes.

These baseline results **are not** evidence that API-01 through API-24 passed. Do not fill in outcomes until actual execution.
