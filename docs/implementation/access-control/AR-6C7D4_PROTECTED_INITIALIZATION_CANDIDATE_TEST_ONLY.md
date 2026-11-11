# AR-6C7D.4 — Protected Initialization Candidate (Disposable Tests Only)

**Status:** TEST-ONLY IMPLEMENTATION / GOVERNANCE NOT COMPLETE
**Branch target:** `ronald`
**Baseline commit before change:** `0d58f5f`
**Scope:** Registration Review Admin defaults only

## Owner scope decision

On 2026-11-12 the project owner expressed approval in the working conversation for these **three proposed defaults on the existing `Admin` role**:

- `accounts.registration_requests.read`
- `accounts.registration_requests.approve`
- `accounts.registration_requests.reject`

This establishes intended *scope*, not verified independent security review or authority to execute against `ctug_workspace`. This document does not authenticate a signer or substitute for the project's institutional approval process. There is no approval to activate a service or mount a route.

## Scope and runtime guarantees

The add-only integration fixture imports the existing AR-6C7C.6 and AR-6C7C.7 test support. It stages in **one outer transaction** exactly two inactive services, three definitions, and three inactive Admin bindings with eight exact audit receipts. A second run verifies the same receipts and creates nothing. Any failure in metadata, role binding, audit receipt verification or postcondition rolls back the whole first pass.

It must execute only under `--settings=config.test_settings`, with `IsolatedMySQLRunner` using a fresh `test_ctug_registration_<16 hex>` MySQL database. The existing pinned catalogue and blocked execution contract remain unchanged. Neither the fixture nor its tests creates an operational management command, Django URL, task, deployment toggle or live grant.

No effective permissions can result because both services and all three role bindings remain inactive. It does not alter `AccountRole`, create direct account overrides, or alter session, CSRF, registration, bulk review, or the official ERD.

## Local verification

In PowerShell from `backend/`:

```powershell
python -B manage.py test apps.access_control.test_registration_review_protected_candidate --settings=config.test_settings --noinput
```

If that passes:

```powershell
python -B manage.py test apps.access_control.test_audit apps.access_control.test_mutations apps.access_control.test_registration_review_metadata apps.access_control.test_registration_review_inactive_grants apps.access_control.test_registration_review_protected_candidate --settings=config.test_settings --noinput
```

The expected discovery count is **17 new tests** and **137 combined tests** based on the prior 120 passing tests. Actual local test outcomes must be recorded; these counts are not proof of success. Do not add `--keepdb` or `--parallel`.

## Gates still blocked

1. **Independent security-review evidence:** security reviewer identity and separate signoff not yet established.
2. **Operational executor and evidence:** ticket identifier, approval provenance, and execution identity not verified.
3. **Real database metadata and protected-grant writes:** not authorized. The existing draft execution contract must not be made writable by changing its flags.
4. **Service activation:** not approved for `accounts` or `access_control`.
5. **API/UI activation:** neither Django Registration Review URLs nor backend flags nor frontend flags may be enabled.
6. **Real end-to-end approval/rejection:** blocked until independent authorization, explicit release approval and successful authenticated security tests.

**Next step after tests and focused commit:** review genuine independent authorization evidence and write a separate operator runbook/implementation design before considering any live initializer. Do not infer that successful test fixtures grant operational permission.
