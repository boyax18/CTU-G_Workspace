# AR-6C5C — Bounded Bulk Registration Review (Development Draft)

**Project:** CTU-G Workspace

**Status:** Added as detached API and tests; disabled by default; not production approved.

## Scope

This patch adds a bounded immediate operation for **1–20 explicitly selected** pending registration IDs. It supports Approve Selected, Reject Selected (approved reason codes only), and Select All **on the current 20-record page** by submitting the IDs already shown to the authorized reviewer. It does **not** claim to process 200 registrations asynchronously; that is AR-6C5D and its separate, still-unapproved database proposal.

No new Django model, database migration, account enrollment table, or official ERD change is required by AR-6C5C.

## Feature gates and routing

`BulkRegistrationReviewView` inherits `RegistrationReviewAPI`'s server-side CSRF, session, JSON parser, rate limiting, service availability, admin assignment and effective-permission checks. It also checks three gates:

- `WORKSPACE_REGISTRATION_REVIEW_API_ENABLED`
- `WORKSPACE_REGISTRATION_APPROVAL_ENABLED`
- `WORKSPACE_BULK_REGISTRATION_REVIEW_ENABLED` (missing/unset is **False**)

The `registration_bulk_urls.py` URL configuration is **NOT** included in `backend/config/urls.py`; it exists solely for isolated tests and a future governed integration. Do not register or enable it before the approved permission catalogue and operator governance requirements are satisfied.

### Proposed API contract (not live)

`POST /bulk/` when `registration_bulk_urls.py` is used as the temporary test URLconf, JSON only:

```json
{"action":"approve","account_ids":[101,102,103]}
```

```json
{"action":"reject","account_ids":[101,102],"rejection_code":"duplicate_request"}
```

No `select_all` boolean, account role, admin identity or search filter can authorize a request. All IDs are integer primary keys, unique within the request and limited to 20. To select everything on the visible page, send the IDs from the existing pending-list response. Cross-page Select All Matching is reserved for AR-6C5D.

The response reports `requested`, `processed`, `remaining`, `interrupted`, aggregate `counts`, and a per-submitted-ID `results` array. Outcomes include `Approved`, `Rejected`, `Skipped`, and `Failed`. **Skipped** deliberately merges stale, nonexistent, ineligible and inaccessible targets; no sensitive reason is returned. If authorization is revoked or a service becomes unavailable partway through, no further decisions are started, `interrupted=true` and remaining items stay unprocessed. The client must reconcile current records before retrying.

## Transaction and authorization invariants

- Each account is processed through the existing `approve_registration` / `reject_registration` service, not via direct SQL or model bulk-update.
- Every decision still locks/rechecks governance services, active Admin role, exact effective permission, target eligibility and request status before modifying data.
- Per-account transactions include the account decision, audit entry, base-role assignment (approval only), and encrypted outbox insert when that feature is enabled.
- A rejected registration stays inactive and retained; no account deletion is introduced.
- Independent per-account transactions intentionally permit partial success. The whole batch is **not** one atomic transaction.
- Bulk requests are separately throttled to 3 requests/minute per remote address (in addition to existing API throttling). IP-based throttling does not replace stronger future authenticated-user or institutional policies.
- The response is **not** a durable job receipt; browser interruptions may obscure partially completed results. Repeated decisions on already-processed accounts are skipped without repeating their audit/notification records.

## Validation

Run only against the existing isolated MySQL test settings:

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend"
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py makemigrations accounts --check --dry-run
python manage.py test apps.accounts.test_registration_bulk --settings=config.test_settings --noinput
```

After the dedicated tests pass, rerun the existing suites, including `apps.accounts.test_registration_outbox_worker`.

## Next: AR-6C5D (200+ accounts)

The queue proposal at `docs/database/proposals/AR6C5D_BULK_QUEUE_PROPOSAL.dbml` is *not approved* and must not be merged into `full_schema.dbml` or migrated without explicit project-owner approval. It proposes jobs plus immutable target-ID snapshots. Worker must authenticate/recheck Admin permission for every decision, stop on revocation, provide progress and idempotency, and use the independent notification outbox for emails. Selection limits, retention, operator policies, and progress access need explicit review.
