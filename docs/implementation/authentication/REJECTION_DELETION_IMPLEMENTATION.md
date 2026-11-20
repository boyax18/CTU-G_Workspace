# Rejection deletion and standard registration

Implemented in source on 2026-11-15 (Asia/Manila), at the owner's request to
remove rejected accounts and the additional reapplication credentials on the
registration page. This changes future authorized rejection actions. It does
not run a cleanup of existing development accounts or change feature gates.

## Result

`RegisterPage.tsx` renders one standard registration form. Previous School ID,
previous email, verification-link requests, token-driven headings and token-based
submission are removed. The registration client always submits the full ordinary
registration payload to `/api/v1/auth/register/`, without a reapplication token.
School ID remains the login identifier, and unique-email normalization is retained.

The existing authorized rejection service locks and validates the Pending,
inactive Student/Instructor applicant and the reviewer exactly as before. It
refuses applicants with assigned roles, framework flags or permission history.
Within the same transaction, it records the rejection decision and configured
notification intent, then deletes only the applicant's `users` profile and
`accounts` row. Approval behavior is retained. Single and bulk rejection use the
same service; the existing HTTP response shape (`account_id`, `status`) is retained
as the decision receipt, even though that rejected account no longer exists.

The rejected account's old ID, status and bounded reason remain in immutable
audit JSON with `account_deleted: true`; the audit target foreign key is NULL
from insertion. The reviewer reference and audit/outbox rows remain intact.
Queued rejection email uses the encrypted recipient and decision snapshot,
independently of the deleted account. Its CTA is **Register Again**, without a
verification-link requirement. The admin confirmation explains account/profile
removal before rejection is submitted.

After a successful rejection the same School ID and email can be used in an
ordinary new registration. A new Pending/inactive account ID and password hash
are created; the old rejection decision continues to identify the removed ID.
Pending/Approved accounts still reserve their School ID and non-null email.

## History and transaction protection

No old audit is detached or edited. Existing protected foreign keys, including
legacy reapplication history and Django admin history, block deletion. The
service returns its existing generic unavailable-request result for those
applicants, and rolls back the new rejection, profile deletion, audit and outbox.
These historical accounts require a separate reviewed retention/cleanup path.

The delete uses two fixed, bound MySQL statements inside the existing trusted
transaction. This avoids Django's CASCADE collector issuing DELETEs on unrelated
admin-history tables, including when they contain no matching rows. Database
foreign keys remain enabled and authoritative. An error in either delete rolls
back the entire business transaction; no successful rejection is returned and
no new notification is retained for a failed deletion.

The backend reapplication endpoints/services remain gated for historical
compatibility. They are no longer used by the registration UI. This work does
not enable these gates, SMTP or new public routes, and adds no Django model migration.

## Trusted executor

The reviewable `executor/schema.py` contract now includes
`wex_rejected_registration(aid)`. It permits ordinary deletion of account/profile
rows only under a valid `registration.reject` lease for the same connection,
reviewer, applicant, and immutable audit receipt in that request. It checks the
Rejected/inactive/non-framework state, eligible active base role, matching
rejection reason and account ID, and absence of assigned roles/permissions.

The generated grant contract adds DELETE only on `accounts` and `users` for the
ordinary executor; row triggers fence it to that rejection. Runtime, notification
and recovery identities gain no deletion rights. Audit and security evidence
remain append-only; deleting Approved accounts or deleting from another operation
is denied. This contract was installed and verified only on a fresh, physically
isolated second MySQL server, with TCP disabled and a private named pipe.

No live MySQL accounts, grants, triggers or records were changed. Existing
protected deployments retain their old deny behavior until a DBA installs the
reviewed function/trigger/grant delta and coordinates the corresponding trusted
release/fence evidence. Application code must not fall back to direct runtime
writes if that deployment update is absent. This source change does not authorize
production installation or bypass the executor boundary.

## Verification

- Final focused backend lifecycle/notification/authorization suite: 169 tests
  passed in 86.806 seconds, including supplemental rollback/binding checks.
- Full backend regression: 1,473 tests passed in 210.385 seconds, using the
  existing guarded disposable MySQL runner.
- Actual-schema second-server harness: 65 checks passed, including successful
  rejection account/profile deletion, audit/outbox preservation, normal new
  registration with the freed credentials, runtime deletion denial, denial
  without a lease, denial from an unrelated operation, and Approved-account
  deletion denial. Recovery, replay and notification-worker boundaries also pass.
- Final focused frontend registration/layout/client/review tests: 32 passed.
- Frontend production TypeScript/Vite build: passed.
- Full frontend suite: 105 passed, one existing failure in the unchanged
  `registration-review-api-contract.test.mjs` assertion that the existing
  dashboard must not reference the review API gate. The prior extra-form layout
  failure is resolved by removing the reapplication form.
- Django migration drift check: no changes detected. System check: no issues.

Supplemental tests cover rollback after account-delete failure (including
restoring an already-deleted profile and discarding audit/outbox), protected
history preservation, exact two-table DELETE scope and immutable outbox binding.
The legacy reapplication service tests remain to protect historical compatibility.

The official ERD and unrelated existing workspace edits are preserved. ERD
SHA-256 remains `BEFB42DF64A6D10B1AA0828A8E2A0A62FF3167B2B35DADCFA973FECF6D54C6D1`.
Read-only fingerprints matched the earlier development snapshot for `accounts`
(3 rows), `users` (1), `account_roles` (1), `access_audit_logs` (15) and
`registration_notification_outbox` (0). No existing local applicant was removed.
The separate email migration-history reconciliation remains outside this change.
