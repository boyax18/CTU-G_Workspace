# AR-6B1 — Permission Catalogue Governance Review

**Project:** CTU-G Workspace  
**Prepared:** 2026-11-08 (Asia/Manila)  
**Status:** DRAFT FOR REVIEW — **NOT APPROVED; NO DATABASE OR AUTHORIZATION CHANGES**  
**Scope:** Registration-review release slice; preserve the pinned full V2 catalogue.

## 1. Purpose and evidence

AR-6B1 evaluates what must be approved and tested before enabling a *minimum, bounded* Workspace Admin registration-review workflow. It does **not** authorize catalogue initialization, grants, service activation, or API exposure.

Evidence available from shared terminal output and project documents:

| Evidence | Observed | Limitation |
| --- | --- | --- |
| First Admin bootstrap post-check | 1 Admin role assignment, 1 bootstrap audit event, 1 framework operator | Verifies initial local account provisioning, **not** V2 governance/activation approval |
| `plan_permission_catalogue_v2` | 10 services, 95 permission definitions, 106 proposed bindings; 6 proposed roles; 1 retirement tombstone | Read-only; cannot grant or activate |
| Planner classifications | `CREATE=105`, `MATCH=4`, `DEFER=108`, `CONFLICT=0` | Four roles match; two optional roles and 106 bindings are deferred |
| Proposed catalogue pin | `catalogue-v2.0`, `v2.0-review-1`, SHA-256 `56ccd699a127ac7a734bd53a2cb7d4a30a1d3953413e4c423897b4a9c9398b78` | Source identifier for review only |
| AR-6A1 isolated tests | 17/17 reported passing | Does not mean service switch or API route is live |
| AR-6A2 isolated tests | 15/15 passed | One-time account bootstrap is distinct from catalogue first-operator initialization |
| Frontend session tests/build | 25/25 tests and production build passed | Browser end-to-end authorization not yet demonstrated |

Sources to reconcile against actual repository before accepting this draft:

- `docs/architecture/AR-3B2A-permission-catalogue-v2-proposal.md`
- `backend/apps/access_control/catalogue/v2_0.json` (pinned actual manifest)
- `backend/apps/access_control/catalogue/planner_v2.py`
- `backend/apps/accounts/registration_review.py`
- `docs/security/ACCESS_CONTROL_GATES.md`
- `docs/decisions/ADR-001-admin-identity-separation.md`

## 2. Proposed smallest usable permission scope — **NOT ACTIVE**

| Exact permission code | Role candidate | Required resource policy | Intended backend use |
| --- | --- | --- | --- |
| `accounts.registration_requests.read` | `Admin` | Only eligible pending school registrations; redact data and exclude framework/governance accounts | Authorized list/details endpoint; paginate, minimize returned fields |
| `accounts.registration_requests.approve` | `Admin` | Existing eligible Pending inactive Student/Instructor; target distinct from actor; no assigned roles; atomic audit | Approve request and assign **only** requested base role |
| `accounts.registration_requests.reject` | `Admin` | Same target restrictions, with allowlisted non-sensitive rejection code | Reject request with atomic audit; no role assignment |

`accounts.profile.self.read` is a separate proposed general profile permission, **not a prerequisite to approve/reject**. It should be evaluated on its own scoped merits rather than bundled into a minimum release automatically.

### Precondition chain

1. Reviewer is a real active, Approved Workspace account, **not** a Django staff/superuser account.
2. Reviewer holds an active `Admin` application role assignment; role alone is **not sufficient**.
3. Exact requested permission is effectively allowed via the protected, approved grant path; individual `Deny` overrides any role `Grant`.
4. Required `accounts` **and** `access_control` services are active as required by the tested AR-6A1 service, with correct catalogue definitions.
5. Target object passes current Pending/active/role/review-history rules and school/identity eligibility, not merely a matching ID.
6. Server-side operation and target authorization, CSRF session protection, request limits, and atomic audit are enforced. UI visibility is never an authorization boundary.
7. Feature switch `WORKSPACE_REGISTRATION_APPROVAL_ENABLED` remains **False** until the preconditions have been independently verified and approved for activation.

### Observed AR-6A1 implementation boundary

`registration_review.py` already defines `approve_registration` and `reject_registration`, checks the distinct actor and target, validates exact effective permission, serializes related rows under MySQL `READ COMMITTED`, updates the target status, attaches only the selected base role upon approval, and writes an audit record in the transaction. It explicitly warns that a future API must *independently* enforce CSRF, session, object scope, payload validation, and rate limits. No registration-review API has been verified live.

## 3. V2 governance decision register — ALL OPEN for operational activation

| ID | Required determination | Review recommendation | Current disposition |
| --- | --- | --- | --- |
| V2-01 | Exact 95 definitions, 1 tombstone, 2 metadata revisions, 6 roles, 106 pairs | Keep pinned V2 unchanged until signed exact-source approval; if scope shrinks, issue a **new version**, recompute totals and rerun planner | **OPEN** |
| V2-02 | Eligibility, ordinary additional role allowlist, protected Admin/G elevation, Advisor appointment | Student/Instructor base role only via registration review; keep Treasurer, SSG Advisor, Admin and G promotions outside this release | **OPEN / out of pilot** |
| V2-03 | Three minimized SSG Advisor monitoring projections, V/T coexistence | No finance monitoring enabled by registration pilot | **OPEN / deferred** |
| V2-04 | Separation of identity creation, ordinary role assignment, Admin/G promotion, templates, grants and recovery | Registration approval grants only requested Student/Instructor base role; bootstrap and recovery stay separate | **OPEN** |
| V2-05 | Independent reviewer/executor, exact reviewed delta, expiry, replay, self-benefit | Enforce reviewer != target for registration; independent governance review is still required for grants/activation | **OPEN** |
| V2-06 | Effective last operator, common lock order, quorum and recoverability | Do not enable Admin/G membership or governance grants in pilot; review service/grant activation effect on K | **OPEN** |
| V2-07 | First real operator/independent institutional evidence, initialization audit/serialization | First Admin creation is audited, but separate catalogue initializer provenance and institutional authorization remain unresolved | **OPEN** |
| V2-08 | Auth event sources, privacy/retention, failed-subject logging, session revocation and step-up | Require denial and revoked-role tests; do not claim session revocation is implemented until proven | **OPEN** |
| V2-09 | Django framework privileges, admin site and management boundaries | Persisted framework flags and separate bootstrap exist; still review restricted admin surfaces, recovery and cross-domain bypasses | **PARTIALLY IMPLEMENTED; decision OPEN** |
| V2-10 | Service readiness, activation, finance/signature/rating/messages/report/privacy rules | Limit first business release to registration review; all other services/grants remain off, readiness must be independently evidenced | **OPEN** |

The prior planner additionally marked `initialization`, `grants`, `service_activation`, `live_mutations`, `administrator_provisioning` (for catalogue governance), `first_operator_attribution`, `independent_review_evidence`, `effective_last_operator`, `object_authorization`, `session_revocation`, `authentication_events`, and `django_superuser_changes` as blocked. **This review does not clear them.**

## 4. Why we must not seed just three rows today

The V2 digest covers an exact full proposal. Silently cherry-picking three permissions/bindings would not be an approved V2 application. Also, the AR-6A1 service requires both `access_control` and `accounts` to be active, and the evaluator must honor effective grants and Deny precedence. Therefore, a limited release needs a formally reviewed *versioned subset/activation profile*, compatible metadata, controlled init/grant workflow, and authorization tests. The existence of the first Admin account is not an authorization to bypass these steps.

**Recommended path:** Keep full V2 as the candidate, approve its exact metadata separately when ready, and develop a **distinctly versioned registration-review activation profile** with an explicit allowlist of services, three effective Admin permissions, blocked defaults, and reversible audit-backed operations. Do not change the pinned V2 manifest in place.

## 5. Proposed acceptance criteria for a future AR-6B2 (not implemented)

- [ ] Named institutional/system owner approves exact catalogue/proposal digest, permitted activation profile and rationale; separate review/execution identities where required.
- [ ] Confirm database schema and actual Django models, index/uniqueness constraints, enum states, roles, service/permission metadata and audit contract.
- [ ] Review activation procedure with dry-run SQL/plan and explicit diff, including only needed metadata, grant edges and service activation; never give all 95 permissions to Admin.
- [ ] Audit every write with a real attributable operator, ticket/approval evidence, before/after value and rollback plan, in a consistent transaction/lock order.
- [ ] Test role union, explicit `Deny` precedence, inactive services/roles/accounts, pending/rejected accounts, ordinary and Django framework accounts, reserved targets, self-review, and wrong/missing permission.
- [ ] Test object-level eligibility and redacted list fields, CSRF/cookies, pagination, rate limits, concurrent double-approval/rejection, replay and audit rollback.
- [ ] Test role or permission revocation against existing sessions; no stale authorization from frontend or cached role labels.
- [ ] Verify post-activation state with read-only queries and a regression suite using isolated MySQL; separately test browser end-to-end in the actual development environment.
- [ ] Update `docs/DEVELOPMENT_STATUS.md`, `docs/CHANGELOG.md`, `docs/testing/TEST_RESULTS.md`, `docs/security/ACCESS_CONTROL_GATES.md` and relevant SRS/ERD/API docs on actual implementation and approval changes.

### Initial negative test matrix (proposed)

| Scenario | Expected result |
| --- | --- |
| Pending/disabled reviewer | 403/denial, no write |
| Reviewer has active Admin role but lacks exact permission | 403/denial, no write |
| Reviewer has matching role Grant and direct Deny | 403/denial, no write |
| Django Superuser without Workspace assignment | Workspace reviewer denied |
| Student/Instructor tries approve/reject | 403/denial, no write |
| Reviewer targets own account | Denied, no write |
| Target not Pending or already assigned a role | Denied; no second assignment |
| Requested role is Admin/Treasurer/G/unknown/inactive | Denied; no write |
| Two reviewers decide same pending request concurrently | Exactly one final decision/audit; other denied |
| Audit fails during a valid decision | Entire decision and role assignment rolled back |
| Missing/disabled `accounts` or `access_control` service | Decision unavailable |
| User sees hidden UI button or hand-crafted request | Server independently denies without permission |

## 6. Next scoped handoff

**Next bounded development task: AR-6B1A (documentation and specification verification only)**. Review this draft against `v2_0.json`, actual model schema and authorization tests; record owners, explicit yes/no amendments to scope and V2-01..V2-10. No grants or live endpoints until the relevant gates are demonstrably closed. After approval, prepare a **read-only activation-profile planner** and isolated test plan before any one-time write.

## 7. Sign-off block — deliberately unsigned

| Field | Value |
| --- | --- |
| System owner | **NOT RECORDED** |
| Security/technical reviewer | **NOT RECORDED** |
| Exact accepted manifest/profile digest | **NOT APPROVED** |
| Scope and object policy accepted | **NOT APPROVED** |
| Catalogue metadata initialization | **NOT AUTHORIZED** |
| Role grants | **NOT AUTHORIZED** |
| Service activation | **NOT AUTHORIZED** |
| Decision date | — |

**Preservation:** No DB write, migration, setting, runtime manifest, code, or permission grant is included with this review artifact.
