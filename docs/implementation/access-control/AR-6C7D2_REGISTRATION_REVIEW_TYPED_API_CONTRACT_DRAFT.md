# AR-6C7D.2 — Registration Review typed API contract (draft, inactive)

**Status:** Add-only offline frontend contract. No live URL wiring, activation, grants, database access or production requests.

## Source of truth (inspected 2026-11-12)

Existing Django modules:

- `backend/apps/accounts/registration_review_urls.py` — **not mounted** by `backend/config/urls.py`.
- `backend/apps/accounts/registration_review_api.py` — guarded `RegistrationReviewAPI` and endpoint handlers.
- `backend/apps/accounts/registration_review.py` — approval/rejection transaction and four allowed rejection reasons.
- `frontend/src/api/client.ts` — session cookie and CSRF-aware `postJSON`, used unchanged.

The review API requires both `WORKSPACE_REGISTRATION_REVIEW_API_ENABLED` and `WORKSPACE_REGISTRATION_APPROVAL_ENABLED`; the reviewer must be an eligible active application Admin with an exact effective permission and the `accounts` and `access_control` services must both be active. None of these gates is changed here.

## Reviewed draft protocol

The **URL root prefix is deliberately unspecified**, because the URLconf is detached. The child paths are below; do not assume or invent a mounted root.

| Operation | Method | Relative route | Request | Success response |
|---|---|---|---|---|
| List pending | GET | `''` with `?page=N&status=Pending` | None | `{"results":[{"account_id":1,"school_id":"...","requested_role":"Student","created_at":"..."}],"page":1,"page_size":20}` |
| Approve one | POST | `<account_id>/approve/` | `{}` | `{"account_id":1,"status":"Approved"}` |
| Reject one | POST | `<account_id>/reject/` | `{"rejection_code":"identity_mismatch"}` | `{"account_id":1,"status":"Rejected"}` |

Only Student/Instructor pending requests are eligible, and the read payload excludes email, personally identifying names, credential hashes and token fields. No `total_count` or `next_page` is currently specified; do not invent them.

Four rejection codes: `incomplete_submission`, `ineligible_registration`, `identity_mismatch`, `duplicate_request`.

Draft errors: `400 invalid_request`, `401 authentication_required`, `403 access_denied`, `404 request_unavailable`, `405 method_not_allowed`, `406 not_acceptable`, `415 unsupported_media_type`, `429 rate_limited`, `503 review_unavailable`. Stale and inaccessible requests both produce `request_unavailable` to prevent enumeration.

## Delivered files

- `frontend/src/features/admin/registrationReviewApiContract.ts`: typed request plans and strict response validation.
- `frontend/src/features/admin/registrationReviewApiGate.ts`: `REGISTRATION_REVIEW_LIVE_API_ENABLED = false` (not tied to mock UI gate).
- `frontend/src/features/admin/registrationReviewApi.ts`: optional future HTTP adapter; GET uses same-origin session and no-store; POST reuses existing CSRF-aware `postJSON`. All methods fail before network calls while disabled.
- `frontend/tests/registration-review-api-contract.test.mjs`: offline fake server payloads, contract/error cases, and assert no network when gated.

No existing source file is edited; the adapter is not imported into the app or dashboard. The existing fictional preview remains separate and hard-disabled.

## Verification and next governance gates

Run from `frontend/`:

```powershell
node --test tests/registration-review-api-contract.test.mjs tests/registration-review-preview.test.mjs tests/dashboard-navigation.test.mjs
npm run build
```

Before future use, separately approve protected permission initialization, inactive-to-active service and permission changes, review URL mount/prefix, review API gates, operational monitoring and audit attribution. Then revalidate the contract and perform real E2E tests in an authorized disposable environment. None of this document constitutes approval.
