# CTU-G Workspace — AR-6C7E.2

## Frontend/Backend Registration Review Contract Tests (Draft)

**Scope:** add-only integration/contract tests. No production route mounts, no migrations, no role/permission grants, no review decisions in the development database, no ERD edits.

**Baseline:** `ronald` branch; previous UI integration commit `08b4a10`; existing disabled frontend live gate and `REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT = null` must remain unchanged. The actual current Git state must be verified on the operator's computer.

## Contract under test

The Django candidate URLconf is `backend/apps/accounts/registration_review_urls.py`. It remains unmounted in `backend/config/urls.py`. During isolated Django tests, `ROOT_URLCONF` is temporarily set to that candidate URLconf and review flags are enabled **only inside disposable test settings**.

| Frontend expectation | Backend candidate behavior |
| --- | --- |
| `GET <approved-root>?page=N&status=Pending` | Returns only pending eligible Student/Instructor registrations, max 20 items/page |
| Pending list JSON | Exactly `results`, `page`, `page_size` at top level; `account_id`, `school_id`, `requested_role`, `created_at` per item |
| Approve | `POST <approved-root><id>/approve/` with `{}` JSON |
| Reject | `POST <approved-root><id>/reject/` with `{"rejection_code":"<approved-code>"}` JSON |
| Approved codes | `incomplete_submission`, `ineligible_registration`, `identity_mismatch`, `duplicate_request` |
| Decision JSON | Exactly `{"account_id":<id>,"status":"Approved"}` or `Rejected` |
| Session protection | Same-origin Django session; CSRF bootstrap at `/api/v1/auth/csrf/` before a decision POST |
| Denial | 400 validation; 401 anonymous; 403 denied/CSRF; 503 disabled gates; no raw sensitive error data in UI |
| Live wiring | No backend review route, approved frontend root is `null`, live API gate is `false` |

The prospective `/api/v1/registration-requests/` prefix is used **only in offline browser tests** to construct example paths. It is not a proposed or approved live route mount.

## New tests

1. `backend/apps/accounts/test_registration_review_p4_http_contract.py` — **12 Django tests** (one normal-route lock + eleven isolated HTTP contract tests), covering JSON shape, 20-row pagination, invalid query parameters, server eligibility filtering, approval/rejection receipts, invalid bodies, CSRF/origin restrictions, account Deny precedence and disabled gates.
2. `frontend/tests/registration-review-p4-integration-contract.test.mjs` — **10 Node tests**, verifying browser parsing against the backend shape, both decision payloads, error codes, mocked CSRF bootstrap and same-origin cookie credentials, no ambiguous POST retry, no browser fetch while disabled, and absence of live Django URL mounting.

All test account identifiers are fictional and only created inside disposable Django MySQL tests. The mocked browser fetch uses in-memory fake responses, not a running Django server. These are **contract and isolated HTTP tests**, not live browser end-to-end testing.

## Execution procedure (Windows PowerShell)

From the repository root (`C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace`):

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend"
python -B manage.py test apps.accounts.test_registration_review_p4_http_contract --settings=config.test_settings --noinput
if ($LASTEXITCODE -ne 0) { throw "AR-6C7E.2 backend contract failed. Stop." }

cd ..\frontend
node --test tests/registration-review-p4-integration-contract.test.mjs
if ($LASTEXITCODE -ne 0) { throw "AR-6C7E.2 frontend contract failed. Stop." }

node --test tests/registration-review-live-ready.test.mjs
if ($LASTEXITCODE -ne 0) { throw "Existing UI regression failed. Stop." }

npm run build
if ($LASTEXITCODE -ne 0) { throw "Frontend build failed. Stop." }
```

### Existing cross-module security regression

The established 289-test backend selection from AR-6C7D.9 Phase 3E remains the baseline. After the 12 new tests pass, rerun the same 13 baseline test modules **plus** `apps.accounts.test_registration_review_p4_http_contract`, expecting 301 tests if none were added/removed. Do not assume tests passed until terminal confirms `OK`.

## Release constraints and exit criteria

- No automatic editing of `config.urls`, `settings.py`, official `docs/database/full_schema.dbml`, permission metadata, migrations, sessions or records.
- The real API is still not mounted. UI and API gates remain disabled.
- Release requires a separate controlled activation and recovery decision. Skipping a recoverable database backup remains a known risk; test results do not supply database restore capability.
- Only after local test output and scoped source review should the two new test files and this documentation draft be committed (three files total).

**Not addressed in this add-only package:** actual network calls from a running browser to a mounted Django review API; feature flags, admin grant activation, email delivery or production deployment. Those require a separate rollout with appropriate safeguards.
