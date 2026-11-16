# Public registration API error contract

16 November 2026 (Asia/Manila). Scope: existing PublicJSONView registration/CSRF and WF-01.01 OTP endpoints, plus their existing shared React client. This extends the existing error envelope; it does not install a second HTTP client or a global DRF exception policy.

## Inspection, reconciliation and approval basis

Inspected the workflow catalogue WF-01.01, PublicJSONView/RegistrationView, registration serializers/service/staging/OTP responses, the separate session/review handlers, shared client/ApiError, registration components and existing tests before editing. Existing session/review exception contracts remain outside the backend rollout. The user authorized this scoped implementation and inclusion of the earlier uncommitted OTP implementation in the final commit. No new migration, official ERD edit, workflow-policy approval or security-boundary change is authorized by this task.

Approved task requirements are the implementation authority: retain existing status/code semantics (including generic 409 and missing/expired 410), add safe request correlation, remove duplicate OTP response construction, and expose accessible correction/retry/status/restart actions without automatically retrying mutations. Policy/Human Approval in the workflow catalogue remains unchanged.

## Compatible wire format

```json
{
  "error": {
    "code": "conflict",
    "message": "We could not complete this registration. Please check your information or contact support.",
    "request_id": "32_lowercase_hex_characters"
  }
}
```

Validation errors may include a bounded `error.fields` map of public field names to fixed safe messages. Retryable throttles may include integer `error.retry_after`, matching `Retry-After`. Existing bounded OTP state metadata is retained on failure for recovery; it never contains a bearer token, recipient, submitted identifier or password. Every scoped API response has a server-generated `X-Request-ID`; errors repeat it in `error.request_id`. Caller-supplied correlation IDs are not reflected. Network/client-generated failures may have no server reference because no response was received; absence of optional headers never masks an existing HTTP error.

| HTTP | Existing stable code | Meaning / UI recovery |
| --- | --- | --- |
| 400 | validation_error | Correct public input fields; retain nonsensitive form values. |
| 400 | otp_invalid | Clear code, announce error, focus code entry. |
| 400 | otp_expired | Clear code; explicitly resend within server limits. |
| 400 | attempts_exhausted | Clear code; cancellation/restart remains explicit. |
| 403 | csrf_failed | Refresh the security token explicitly; do not repeat the failed POST automatically. |
| 405 / 406 / 415 | method_not_allowed / not_acceptable / unsupported_media_type | Safe protocol error; no technical/raw response text. |
| 409 | conflict | Same Student generic message for both roles before/after OTP; never identify the conflicting field. |
| 410 | expired | No usable verification session; clear code and show restart. A 410 alone cannot prove whether an earlier uncertain verification committed. |
| 429 | throttled / resend_cooldown / resends_exhausted | Respect bounded retry hints and existing per-stage limits; no automatic POST retry. |
| 503 | delivery_failed | Encrypted stage retained by existing workflow; show bounded resend recovery, never delivery success. |
| 503 | registration_unavailable | Dependency/writer refusal or existing unexpected-failure contract; safe logging and correlation, no boundary details. |
| 500 | server_error | Safe mapping if an existing API exception explicitly carries 500; never return 200 for failure. |

Unexpected public registration exceptions retain the existing HTTP 503 contract. Field error values are selected from fixed public messages, not exception strings or submitted input. Error normalization preserves security/Retry-After/cookie headers and removes unknown error-body data. The separate protected executor, audit, CSRF and rate-limit mechanisms remain authoritative.

## Logging and frontend rules

Application failure logs are JSON events with the same structured LogRecord fields: event, server request ID, fixed error code, HTTP status, static operation name and failure classification (expected/dependency/writer_boundary/unexpected). Expected 4xx use INFO; 5xx use ERROR. Collection of INFO events depends on the deployment logging level. No request body, cookies, headers, query strings, submitted identity, exception message, stack trace, password, OTP or cryptographic material is logged. Expected failures are represented explicitly and logged by the existing response boundary; unexpected exceptions are mapped there rather than swallowed. Existing Django/proxy access logging remains separate; registration secrets are never put in URLs by the client.

React extends ApiError/readResponse/postJSON/getJSON. Known messages and recovery actions are chosen by stable code/status; malformed/HTML/unrecognized errors cannot display raw server details, even through unknown error codes or validation values. Request IDs and retry hints are validated before use. Non-idempotent operations are issued once. Network/invalid-success responses after a write are marked uncertain and require an explicit status check; an error response is never treated as a success. A later 410 does not prove whether the earlier uncertain write committed, and the UI does not claim otherwise. Passwords clear on conflict, invalid session/security, mail failure or uncertain submission; OTP input clears on failed verification. Safe registration fields remain in memory for correction, without browser persistence.

ApiErrorNotice uses a focused `role=alert`, `aria-live=assertive`, `aria-atomic=true` summary and validated request reference. Field errors keep the existing Input component's label/aria-invalid/aria-describedby semantics. Keyboard-accessible native controls provide correction, security refresh, status read, resend, cancellation or restart. Countdown text is outside the live alert to avoid repeated screen-reader announcements. No separate Resume email verification control is added; Student primary action remains Proceed Email Verification. A reported mail-send failure retains staged ownership and offers that action to reach the resend screen without resubmitting credentials.

16 November UX follow-up: removed the unhelpful “Review registration details” button. Registration conflicts now provide plain guidance to check both School ID and email, wait for review if already applied, or use the supported Sign in link for an approved account. Safe input retention, password clearing, request references and generic HTTP 409 behavior remain unchanged. Field-specific identity disclosure still requires explicit owner authorization under the existing privacy contract. The follow-up passed 47 focused frontend checks, nine headless UI checks, build and scoped lint; no backend/schema/workflow change was made for this UX adjustment.

16 November email-availability follow-up: the owner confirmed keeping generic errors and requested that used email be rejected before email verification. Initial submissions already checked permanent accounts; saved-attempt continuation and resend had gaps. One shared identity check now covers normalized email/School ID before new staging, immediately before OTP generation/delivery, saved-attempt continuation/status and final permanent creation. An email on any existing Pending/Approved/Rejected account is unavailable; another active staged reservation also blocks a second email send. No standalone field-availability endpoint or field-specific conflict detail is exposed.

An owned stage whose original identity has been claimed cannot continue or resend. A different, conflicting submission in the same browser is rejected while preserving the still-valid original stage and its ownership cookie; its encrypted data is never overwritten. The internal cookie-preservation flag is consumed before response serialization. Existing fixed expiry, attempt/resend limits, generic 409 response, database uniqueness and final all-or-nothing transaction remain authoritative. The extra pre-delivery check handles a conflict arising between initial validation and code issuance; final database constraints still resolve concurrent permanent inserts.

Validation for this follow-up: 119 backend checks passed in 34.048 seconds in the guarded disposable database (destroyed afterward), including seven new regression tests for account states, normalization, saved-cookie paths, status/resend refusal, a simulated pre-send race and other staged email reservations. Sender mocks verify no mail is sent on these conflicts. The isolated browser conflict test passed and explicitly verifies remaining on /register without navigating to verification. Changed files: registration_staging.py, student_registration_api.py, test_student_registration_otp.py, the browser conflict test and this contract. No ERD, migration, approved workflow definition or privacy policy was changed.

Catalogue recheck after the interrupted turn: WF-01.01 main step 5 requires checking both School ID and email before staging (step 6), OTP delivery (step 7) and the verification screen (step 8). The shared identity checks and continuation/resend safeguards implement that existing requirement; step 12 still rechecks identities and relies on database uniqueness in the atomic creation transaction. The catalogue's conflict error row requires the same generic message, which is preserved. Alternative B's original-attempt ownership and no-overwrite rule are preserved. The current catalogue and its owner's approval name/date were read only; Human Approval is still unchecked and WF-01.02 was not started. The earlier reload was refused when automatic approval review hit its usage limit. Following the user's continue instruction, normal approval review permitted the retry: the local backend was reloaded, and the real proxy returned the expected safe 410 for a cookie-less verification request with matching request references. No approval check was bypassed, migration applied or real OTP email sent by this continuation.

## Verification, changed files and commit

| Check | Result |
| --- | --- |
| Focused backend suite | 136 passed in 35.041 s: new error/privacy/correlation/concurrency checks plus Student OTP, public registration, email uniqueness and account tests. Fresh guarded disposable MySQL DB created/destroyed. |
| Backend regressions | 75 passed in 38.325 s: session/login, recovery, review/rejection, API and framework-admin checks. Disposable DB destroyed. |
| Full frontend suite | 136 tests: 135 passed, one previously existing unrelated failure in registration-review-api-contract.test.mjs:210, “mock UI and dashboard are not modified or coupled to real client.” Unchanged SessionDashboardPage already imports the guarded review API gate; this task does not edit it or the activation gates. |
| Headless UI | 9 passed in 12.701 s against fresh headless Edge profiles and a temporary localhost-only Vite instance. All API responses mocked; non-local traffic blocked; no real applicant, mail or DB used. |
| UI coverage | Real keyboard Enter/Tab/focus, assertive atomic error announcement semantics, code clearing/field associations, generic 409 with safe input retention/password clearing, expired restart, CSRF refresh without POST retry, bounded resend cooldown, exhaustion/cancel availability, mail failure, lost response followed by 410, and safe HTML server failure. |
| Build/lint | npm run build and scoped ESLint checks passed. |
| Local HTTP smoke check | Reloaded local backend; cookie-less verification GET through the real Vite proxy returned 410 expired with a matching validated body/header request reference and no-store. No account creation or mail send involved. |
| Protected files | Official ERDs and every existing account migration match task-start SHA-256; no new migration generated/applied during this task. Existing 0005 is included unchanged only because the user explicitly requested the prior OTP prerequisites be committed too. |

Automated ARIA/live-region and focus behavior was tested in a real headless browser. A human screen-reader listening session and actual recipient inbox delivery were not performed or claimed. The backend rollout remains scoped to PublicJSONView; session/review authentication, permissions, auditing, writer fencing, rate limits, database uniqueness and OTP policy values are unchanged. Tests preserve the protected writer refusal before DB access.

An owner edit to the catalogue approval name/date occurred after the task-start fingerprint. The agent did not edit that catalogue or tick Human Approval; that externally edited file is excluded from this commit. Other pre-existing unrelated access-control, rejection/outbox, configuration and ERD work is also left unstaged.

### Files in this change

Error-handling implementation:

- backend/apps/accounts/api_errors.py — safe code/message registry, validation translation, scoped exception mapping, response normalization and correlation.
- backend/apps/accounts/views.py — reuse PublicJSONView for request IDs, normalization and structured logs; remove duplicated inline mapping.
- backend/apps/accounts/student_registration_api.py — reuse registry/finalizer for OTP failures; unknown service state fails safely.
- backend/apps/accounts/registration_staging.py — reuse generic conflict message; keep decryption failures out of the mail-delivery catch.
- frontend/src/api/client.ts — extend the existing ApiError/response reader/CSRF/POST/GET path with safe metadata, messages and uncertain-write handling.
- frontend/src/components/common/ApiErrorNotice.tsx — shared accessible error summary.
- frontend/src/features/auth/registrationFeedback.ts — scoped recovery/secret-retention policy.
- frontend/src/features/auth/registration.ts — validate positive workflow responses; malformed success cannot create a false confirmation.
- frontend/src/features/auth/RegisterPage.tsx and VerifyEmailPage.tsx — accessible errors, explicit recovery, secret clearing and safe input retention.
- backend/apps/accounts/test_public_api_errors.py; frontend/tests/api-errors.test.mjs; frontend/tests/browser/registration-errors.test.mjs — contract/privacy/concurrency and UI coverage.
- frontend/tests/registration.test.mjs and reapplication.test.mjs — update fixtures to the actual OTP response contract; existing invariants retained.
- frontend/package.json and package-lock.json — official playwright-core dev dependency and node:test UI script; existing installed Edge reused, no browser download or new test runner.
- docs/api/REGISTRATION_ERROR_CONTRACT.md — contract, verification, boundaries and commit receipt.

Previously implemented OTP prerequisites included under the user's explicit clarification:

- .gitignore; backend/apps/accounts/models.py, services.py, urls.py; backend/config/settings.py.
- backend/apps/accounts/migrations/0005_student_registration_otp.py (pre-existing, unchanged); backend/requirements-registration.txt; backend/scripts/apply_student_registration_otp_local.py (pre-existing release helper, not executed by this task).
- backend/apps/accounts/management/commands/purge_student_registration_staging.py; backend/apps/accounts/test_student_registration_otp.py, test_registration.py, test_email_uniqueness.py.
- frontend/src/App.tsx; frontend/tests/registration-layout.test.mjs.
- docs/workflows/group_a/WF-01.01_Student_Registration_Review.md and WF-01.01_Student_Registration_Implementation.md — historical prerequisite records; current error evidence is this contract. Their catalogue reference remains a separate owner-controlled workspace artifact.

Tests were run in the shared working tree, which also contains pre-existing unrelated changes. Those unrelated changes were not staged; this is not a clean production release certification.

## Shared Student/Instructor feedback — 16 November 2026

The owner's latest instruction adopts Student error feedback/response for Instructor, superseding the earlier Instructor-only sentence, action panel and configuration/recipient metadata. Both roles use the existing registry, scoped backend mapper, ApiError client and accessible notice.

All initial/final identity conflicts return HTTP 409, code conflict and exactly:
"We could not complete this registration. Please check your information or contact support."
The error envelope contains code/message/request_id and optional safe field errors/retry metadata; OTP errors share the existing status/expiry/attempt/resend/delivery counters. Instructor errors no longer expose requested_role, support_contact, password_reset_enabled, can_continue, email or otp_expires_in. Successful owned-stage replies retain role context only where required to preserve the original role. Staff ID validation and forbidden Instructor school fields retain role-appropriate safe field text.

Both registration forms show the same check-details/wait-for-review guidance and Sign in link to /. Instructor substitutes Staff ID for School ID. There is no separate reset/unavailable, Continue or contact-action panel. Both OTP screens share generic saved-registration email wording, attempts, expiry error with Resend code, resend countdown, Cancel registration, explicit security refresh/status/restart and no automatic POST retry. Passwords/OTP clear under the same existing conditions.

Matching/nonconflicting original-browser attempts resume without overwriting details or sending new mail. Changed conflicting submitted identities return shared 409 while preserving the valid original stage/cookie; correction permits continuation. Cross-browser identity knowledge still cannot resume/cancel. Unrelated duplicate-key storage failures now produce genuine safe 503 with rollback for both roles, correcting the legacy Student false-conflict classification to its existing workflow transaction-error contract. Real identity/reservation collisions remain 409.

Core Instructor staging/OTP, Staff ID, no Student-only fields, atomic Pending/profile/proof, rate/expiry/writer boundaries and later School Admin review remain. Password-recovery implementation/flag is untouched; official support contact remains owner input, with Student's generic support wording on the registration form. No public configuration endpoint or new schema was added.

Verification: 165 focused backend checks, 93 related regressions, 51 focused frontend checks, 29 browser checks and one real OTP/browser/CSRF/MySQL/protected-read acceptance passed; build/lint passed. Full frontend: 139/140 passed, one known unrelated dashboard/mock-isolation failure. Disposable databases were destroyed; no real email/inbox or production acceptance was claimed. See the [current feedback consistency report](../workflows/group_a/WF-01.02_Feedback_Consistency.md). No new commit/push or agent policy/Human Approval; the receipt below describes earlier work.

## Commit receipt

Implementation and authorized OTP prerequisites: `70ccf553a61b802bc8816687e69ac72fcadd2052` — `feat(auth): centralize registration errors and OTP recovery` (34 reviewed files).

This receipt is a documentation-only follow-up so the implementation hash can be recorded without a self-referential commit. The official ERD, externally edited workflow catalogue and unrelated access-control/rejection/outbox work are excluded. No push was performed. The existing migration 0005 was committed unchanged as explicitly authorized; this task generated/applied no new migration to the development database.

References: [DRF exceptions and direct-response scope](https://www.django-rest-framework.org/api-guide/exceptions/), [DRF view lifecycle](https://www.django-rest-framework.org/api-guide/views/), [Playwright installed Edge channel](https://playwright.dev/docs/browsers).

## WF-01 audit corrections — 16 November 2026

Owner-approved (OD-1(a), OD-2, OD-3, packages P1-P4). The error envelope, codes, HTTP statuses and messages above are unchanged. Record: [WF-01 audit corrections](../workflows/group_a/WF-01_Audit_Corrections_2026-11-16.md).

| Area | Contract change |
| --- | --- |
| Success summaries | verification_required / existing_verification bodies (register, status, resend) add code_valid_seconds: the configured code lifetime (D-01), an integer 1-86400. It is guidance only and never appears in error envelopes. Clients treat it as optional. |
| Mail ordering | The staging row and code digest commit before mail is sent. delivery_failed semantics are unchanged; invalidation clears only the code that failed, never a newer code from a concurrent resend. |
| Rate limits | GET /register/verification/ applies the 30/min and 200/day IP budgets to both roles before any lookup (HTTP 429 throttled). Per-identity budgets (keyed ID and email, shared across roles) now apply to Student as well as Instructor: admission 5/min and 30/day; owned OTP/status 30/min and 200/day. |
| Client wording | A 410 on the first load of the code screen shows neutral text (no saved registration in this browser; it may have expired, been cancelled or already been submitted) instead of claiming expiry. A submission answered with existing_verification shows that the newly entered details were not used. The Resend button's accessible name is always Resend code; its countdown is a linked description. |
