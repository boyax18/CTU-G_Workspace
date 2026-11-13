# CTU-G Workspace — G1D-P3C6A Django Writer Boundary Seam

**Checkpoint:** `ronald` / `bbe393f4a6d99b2aa357d59494eb6034a5125665` source-only export.
**Status:** Guarded *development candidate*, not a verified database writer fence.
**Release status:** **BLOCKED**.

## Source observations

- `apps.accounts.registration_review` directly updates an account and creates an `AccountRole` on approval, followed by a transactional access-audit entry and possibly an encrypted outbox record.
- `apps.access_control.mutations` directly creates/updates `RolePermission` and `AccountPermission`, using existing service governance locks, reviewed scopes, and audits.
- `apps.accounts.admin_bootstrap` independently provisions an ordinary first `Admin` using an authenticated Django framework operator and direct database writes.
- The G1D-P3C5 disposable MySQL proof is *not* installed against the real Workspace schema or production principals. Its demonstration procedure does not validate the acting user.

## P3C6A change

The new `apps.access_control.writer_boundary.require_verified_writer()` is an explicit integration point invoked before the three existing write transactions. Its recognized intents are registration approval/rejection, role permission changes, per-account permission changes, and initial ordinary-Admin bootstrap.

`WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER` is **opt-in** in this initial compatibility increment:

- **Unset or exactly `False`**: preserve existing guarded local-development workflows. **Not evidence of database separation.**
- **Exactly `True`**: reject all covered writes until a separately designed and verified database executor exists; no fallback to direct ORM writes.
- **Any other value**: reject all covered writes as invalid configuration.
- **Unknown operation**: always reject, even if enforcement is disabled.

No setting is inserted into the project's real `.env` or Django settings by this package. Do **not** enable the flag on a live system until a coordinated rollout is planned: existing registration approvals, rejections, ordinary permission management and initial-Admin bootstrap will become unavailable. These exceptions are internal and must not be exposed as detailed error messages in an API.

## What this DOES NOT implement

This module is a Python fail-closed **guard when enabled**, not a MySQL security barrier. Privileged DB users, direct SQL, unmanaged Django ORM paths, management commands, raw queries, external workers and stored procedures remain outside its enforcement. A boolean flag cannot prove identity, role authority, ledger durability, service grants, or database isolation. Default `False` is deliberately not production-release eligible. Do not call this a completed P3C6 integration.

## Next verified integration scope

1. Approve per-operation authority and writer identities and confirm real MySQL privilege separation without exposing credentials.
2. Reconcile account approval, legacy direct permission updates, management commands, rollback/audit/outbox, and application runtime SQL requirements against *actual* tables and transactions.
3. Build an executor with real caller authentication, authorization, signing evidence, single-use ledger and role restrictions, and a database-level denial of direct protected writes.
4. Test both negative/positive operations and crash recovery on a schema-compatible separate MySQL instance before rollout; verify primary-environment backups, restoration and session-draining evidence.
5. Review role provisioning and bootstrap as independent release gates. `prepare_g1d_p1_protected_role --apply` must remain disabled.

## Tests and safeguards

A `SimpleTestCase` module verifies the opt-in gate, strict configuration parsing, unknown-operation refusal, and prevention of database transaction/preflight entry for all covered write paths. Tests do not access MySQL. Owner-local full regression and `makemigrations --check --dry-run` are mandatory before a bounded Git commit.

**Files changed:** two new Python files, three narrowly edited existing service files, this documentation file. No migrations, schema, new endpoints, database writes, Git push, `.env`, or official ERD changes.
