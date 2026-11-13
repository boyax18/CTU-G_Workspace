# CTU-G Workspace — Task 2 G1D-P3A: root-signed registry contract (test-only)

**Status:** Candidate for owner local verification. Based on source snapshot `ronald` at `c2d501c`, November 13, 2026. Not installed in the user's Windows repository by this delivery. No live role creation approved.

## Scope and result

This small, **add-only and test-only** candidate tests whether an independent public-root pin set can authenticate a synthetic, domain-separated Ed25519 signer roster before the existing fictional approval-bundle verifier accepts signer public keys.

It adds a bounded and canonical synthetic roster hash and an exact 2-root signature check; verified scope is a disposable-schema name and database incarnation. The registry verification fails closed for missing/duplicate/invalid roots, tampered roster, substituted persons or keys, epoch rollback (given an independently supplied epoch floor), expired/revoked root, missing active duty, and unexpected manifest changes. Existing `g1d_p1_authorization_design_test_only.verify_bundle()` remains the downstream signer/bundle verifier and is NOT changed. No production imports are added.

These tests **do not** establish a trusted human identity, appointment, real-world independent device custody, a secure hardware key, current revocation service, approved production key store, or real signer authorization. The test caller supplies pinned synthetic root keys; the source of their authenticity is an unimplemented operational control. The epoch floor must be independently and durably held; caller-supplied floors cannot defeat rollback by themselves. The restricted ASCII canonicalization is NOT RFC 8785 JCS. Production must review crypto library/dependency and canonicalization choices.

## Approved versus blocked

- Already approved: D1–D6 for **disposable test-only** development. D7 is withheld.
- Not approved: modifying `docs/database/full_schema.dbml`, production models/migrations, main database, new permissions, `Technical Super Admin` role, live `--apply`, credentials, trust enrollment or promotions.
- The prototype's `simulate_fenced_writers=True` **does not implement maintenance fencing**. A real privileged writer may bypass its control-row lock; the existing tests already demonstrate this.
- Only two application Admin levels exist: Normal Admin and Technical Super Admin. Django framework superuser is separate and not a governance bypass.

## Add-only file map

1. `backend/apps/access_control/tests_support/g1d_p3a_root_endorsed_registry_test_only.py`
2. `backend/apps/access_control/test_task2_g1d_p3a_root_endorsed_registry.py`
3. `docs/implementation/access-control/TASK2_G1D_P3A_ROOT_SIGNED_TRUST_REGISTRY_TEST_ONLY.md`

No other repository paths need modification.

## Verification performed on this source snapshot

- **32/32 cryptographic contract tests passed** on an isolated Python runtime by importing the existing snapshot’s synthetic Ed25519 contract and the three-file candidate; no Django/MySQL connection was used.
- Python compilation passed for the new Python files.
- **Not verified here:** Django test runner, disposable MySQL test creation/destruction, full 1,033+ suite, migration check, `ctug_workspace` read-only state and Windows Git staging. These require owner-local checks.

## Local verification discipline

Before installation: inspect branch/HEAD; ensure the three target paths do not already exist; preserve pre-existing untracked and modified files, including the official ERD. Never stage or replace anything unrelated.

1. Run focused suite using disposable MySQL settings:
   `python -B manage.py test apps.access_control.test_task2_g1d_p3a_root_endorsed_registry --settings=config.test_settings --noinput`
2. Run the existing G1D-P1 authorization tests and new suite together under `config.test_settings`.
3. Run full Accounts + Access Control regression using established test enumeration; baseline was 1,033 tests across 44 modules, so expect baseline + newly discovered tests, subject to current repository status.
4. Check migrations: `python -B manage.py makemigrations --check --dry-run --settings=config.settings` (never `migrate`).
5. Verify `prepare_g1d_p1_protected_role --apply` remains unavailable; run read-only P0/P1 preflight if required.
6. Document actual results, review exact-file staged diff, and commit only after local security regression passes. **Do not push.**

## Next security blockers

Production trust-root enrollment and pin custody, live identity proof, ledger/retention/schema approval, least-privilege credential isolation, mandatory fenced privileged writers, independent audit custody, and operational crash/backup restore validation. The four-table ledger remains only proposed. The real `ctug_workspace` state is **not inspected or modified in this delivery**.
