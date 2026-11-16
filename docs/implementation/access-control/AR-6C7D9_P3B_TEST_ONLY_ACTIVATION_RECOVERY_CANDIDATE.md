# AR-6C7D.9 — Phase 3B Test-Only Activation/Recovery Candidate

**Project:** CTU-G Workspace
**Classification:** implementation candidate for disposable MySQL tests; **NOT** authorized operational activation
**Prior live state:** AR-6C7D.7 Phase 1 and AR-6C7D.8 Phase 2 independently verified; two inactive services; three definitions; three inactive Admin bindings; eight historic receipts; no effective review permissions
**Latest Phase 3A checkpoint provided by the owner:** commit `2a602b7` on branch `ronald`, 182 combined security tests passed, local read-only readiness reported one eligible Admin and zero effective permissions

## 1. Scope and explicit non-goals

This package adds exactly two files of executable Python (one Django management command and one test module) and this design document. It deliberately does **not** enable or provide an operational activation command for the local development database `ctug_workspace`, nor for production. It includes no migrations, ERD changes, account status changes, configuration overrides, URL mounts, grant overrides, notifications, or UI changes.

The command **refuses** `config.settings` even when passed an explicit confirmation. It only accepts `config.test_settings` with the unique, disposable MySQL test database name, test runner, connection pinning, READ COMMITTED isolation, frozen catalogue digest, disabled registration flags, and detached route already required by the earlier P1/P2 guards. Running `python manage.py test` with the provided test module exercises activation and compensation **inside a disposable database created and destroyed by the existing isolated test runner**. It never runs against `ctug_workspace`.

## 2. Transition design exercised in disposable MySQL

| Step | Initial state | Transactional change | Audit event count | Result |
|---|---|---|---:|---|
| P3B activation exercise | Services false; bindings false; P1/P2 receipts exactly valid | Set exactly `accounts` and `access_control` services true and the three Admin bindings true | 2 service activation + 3 binding activation | Three codes become effective for the exact approved set of application Admin accounts, **only inside the disposable DB** |
| P3B compensation exercise | Services true; bindings true; all five activation receipts verifiable | Set all three Admin bindings false and the two services false | 3 binding deactivation + 2 service deactivation | Zero effective review permissions; preserve all 18 historic receipts |

Both transitions use the existing append-only `record_access_audit_receipt`, the existing P1/P2 pinned source contracts, one durable atomic transaction and the same MySQL advisory lock as the P1/P2 initializers. Before commit, each operation verifies all scoped row values, all transition receipts, the exact expected Admin identity set, enabled/disabled permission outcomes, and still-disabled backend URL/feature gates. Failed assertions or audit writes roll back the entire transition.

**Important:** Grant activation applies to **all eligible Admin role assignees**, not merely the audit actor. The command requires explicit exact Admin account IDs rather than only an expected count. It rejects any approved, active Django staff/superuser that also carries the Admin role, because the generic permission evaluator itself does not use Django staff flags as a deny. It evaluates each of up to 100 test accounts after the change to catch unexpected grants. Neither the P3A Admin count nor the operator's provided ID is accepted as a substitute for an exact impact scope.

## 3. Test instructions — no live initialization

From Windows PowerShell, after extracting the package into the **root** of CTU-G Workspace:

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend"

python -B manage.py test apps.access_control.test_registration_review_activation_recovery_test_only --settings=config.test_settings --noinput

if ($LASTEXITCODE -ne 0) { throw "Phase 3B test-only exercise failed. Stop." }
```

Run the combined Phase 1–3B regression next, only after the isolated suite passes:

```powershell
$tests = @(
  "apps.access_control.test_audit"
  "apps.access_control.test_mutations"
  "apps.access_control.test_registration_review_metadata"
  "apps.access_control.test_registration_review_inactive_grants"
  "apps.access_control.test_registration_review_protected_candidate"
  "apps.access_control.test_registration_review_metadata_local_dev"
  "apps.access_control.test_registration_review_inactive_bindings_local_dev"
  "apps.access_control.test_registration_review_activation_readiness"
  "apps.access_control.test_registration_review_activation_recovery_test_only"
)
python -B manage.py test $tests --settings=config.test_settings --noinput
if ($LASTEXITCODE -ne 0) { throw "Combined regression failed. Stop." }
```

The candidate adds 37 tests to the existing 182 checked during P3A; an unchanged broader suite would discover **219 tests**. That number is an *expectation*, not a local test result. Tests must actually pass on the owner's Windows/MySQL setup before acceptance. Any test failure is a stop condition, not a reason to disable safeguards.

## 4. Negative tests and limits

The tests cover correct activation and compensation, the five receipts per transition, disabled API/route gates, Student and Instructor denial, framework superuser not granted unless assigned Admin (and refusal if assigned), exact multiple-Admin scope, pending role-request exclusion, wrong actor/scope/confirmation, default no-run, unexpected metadata, partial activation, account overrides, P1/P2 provenance tampering, feature flags enabled, failed first and mid-operation audit writes, lock refusal, duplicate activation/compensation, post-compensation reactivation refusal and mid-compensation rollback.

This is **not a validated production concurrency test**. Actual multi-connection lock contention, database restore drill, deployment configuration, authenticated HTTP security (CSRF/session/401/403/429), rate limits, approvals, notification outbox, and kill-switch rehearsal still need separate testing before operational activation. Mocking a lock refusal verifies fail-closed handling but is not equivalent to a live contention test.

## 5. Mandatory gates before any future operational activation

1. Export the full development MySQL schema **and data** outside Git; validate the dump cannot redirect restoration into the live schema, restore into a *separate* temporary database, and verify restored data and tables. A Git commit is not a database backup.
2. Approve an **exact account-ID impact set**, including what should happen if the Admin assignments change between review and execution. The Phase 3A count was one in the most recent inspection, but is not permanently pinned by count.
3. Independently review code and tests; design a separate local-only activation command with a named local target guard, backup/restoration checkpoint evidence **without secrets in logs**, one-time confirmation, operator/change authorization, exact audit provenance and a tested compensation pathway. Do not change the disposable-only command to accept `config.settings` by toggling one line.
4. Test both sides of the hybrid evaluator, inactive service gating, direct Deny precedence, governance locks, account approval, framework staff/superuser separation and authenticated API handling. Detaching the API route is **not** a substitute for inactive permissions.
5. Keep `WORKSPACE_REGISTRATION_APPROVAL_ENABLED`, `WORKSPACE_REGISTRATION_REVIEW_API_ENABLED`, frontend live gates and `registration-review-pending` URL unmounted through this stage. API/UI rollout is a separately authorized phase after integration security tests.
6. Verify the actual post-transition database state and exact audit receipts before declaring success. Compensation changes current state but intentionally **does not erase audit history**. Database restore and permission compensation are different recovery operations.

## 6. Git and ERD boundaries

Stage only:

- `backend/apps/access_control/management/commands/exercise_registration_review_activation_recovery_test_only.py`
- `backend/apps/access_control/test_registration_review_activation_recovery_test_only.py`
- `docs/implementation/access-control/AR-6C7D9_P3B_TEST_ONLY_ACTIVATION_RECOVERY_CANDIDATE.md`

Do not stage `docs/database/full_schema.dbml`, `backend/.env`, unrelated status entries or generated test artifacts. Do not use `git add .`. Do not push or activate on the strength of static syntax checks alone.
