# AR-3B2B1 — Catalogue v2 Manifest and Static Validator

Date: 7 November 2026, Asia/Manila. Status: implemented and verified for static
planning only. The current user instruction accepts AR-3B2A as the planning
baseline; it does not approve live grants, initialization or unresolved security
policies. Existing proposal documents retain their original status and bytes.

## Files created

| New file | Purpose |
| --- | --- |
| `backend/apps/access_control/catalogue/v2_0.json` | Independent `catalogue-v2.0` planning data with pinned provenance, exact definitions/defaults, retirement history, eligibility and blockers. |
| `backend/apps/access_control/catalogue/validation_v2.py` | Standard-library-only strict validator, source derivation, static model-limit inspection and deeply immutable result. |
| `backend/apps/access_control/test_catalogue_v2.py` | 46 focused static tests, including isolation, policy tampering, exact data and v1 preservation. |
| `backend/scripts/test_catalogue_static.py` | Runs new tests and existing v1 manifest tests with isolated settings, a dummy backend and a connection-refusal guard. |
| `docs/implementation/access-control/ar-3b2b1-catalogue-v2-manifest-static-validator.md` | This implementation, verification and next-phase report. |

No existing file was modified. The package initializer and existing planner do
not import or select v2, so the default v1 command and runtime application behavior
are unchanged. No v2 database-planning or mutation endpoint is added.

## Accepted source and versioning

The independent artifact uses:

- `schema_version`: `static-catalogue-v2.0`.
- `manifest_version`: `catalogue-v2.0`.
- `source_revision`: `v2.0-review-1`.
- `planning_only`: strictly Boolean `true`.
- Acceptance limited to the owner-accepted static planning baseline.

Its source is
`docs/architecture/AR-3B2A-permission-catalogue-v2-proposal.md`, pinned to:

`56CCD699A127AC7A734BD53A2CB7D4A30A1D3953413E4C423897B4A9C9398B78`

The manifest and validator also pin the repaired complete C1 JSON, original C1
proposal, SRS v0.3 Markdown and AR-2/AR-3A documents. Validation checks actual bytes
against all six expected hashes on each call. Unavailable or changed evidence
fails closed; caller-supplied provenance cannot redirect file reads. No fallback
document, source rewrite, hash refresh or fabricated owner-decision identity is used.

Version identifiers, provenance and all source-derived structures are immutable
baseline contracts. Any changed candidate requires a deliberate new reviewed
version/source pin, not editing counts or bypassing validation.

## Exact validated contents

| Item | Result |
| --- | ---: |
| Services | 10 |
| Selectable permission definitions | 95 |
| Proposed role definitions | 6 |
| Proposed default bindings | 106 |
| Unchanged C1 definition metadata | 79 |
| Revised name/description definitions | 2 |
| New definitions | 14 |
| Historical retirement tombstones | 1 |
| Blocked permission definitions | 14 |
| Internal contract readiness F | 9 |
| Planned readiness P | 72 |
| Scope descriptions | 16 |
| Open policy decisions | 10 |
| Unsupported delegation configurations, all BLOCKED | 8 |

The exact role totals are Student 18, Instructor 17, Treasurer 23, Admin 35,
Technical Super Admin 10 and SSG Advisor 3. These are **proposed pair counts**,
not effective authority, permission initialization or live role creation.

The two metadata revisions change only permission name and description for
`access_control.technical_accounts.provision` and
`access_control.technical_accounts.recover`; codes and other core metadata remain.
All 79 KEEP definitions preserve their seven core source fields exactly. All 96
C1 proposed pairs are retained, with ten additional proposed pairs.

`access_control.role_assignments.manage` is excluded from the selectable 95 and
stored as one historical tombstone containing its complete original C1 definition,
three replacement identifiers, no defaults, no automatic grant remapping and no
execution authority. Existing future database records must be preserved/reported;
this artifact does not delete or revoke them.

All 14 B definitions and all seven delegation authority codes have no default
grants. Governance role defaults contain no academic, finance, clearance, rating
or report permission. SSG Advisor has exactly:

- `finance.monitoring.overview.read`
- `reports.monitoring.financial.read`
- `finance.monitoring.transactions.read`

## Static validation and eligibility contracts

`read_manifest()` returns parsed mutable planning data for inspection; it rejects
duplicate JSON keys, non-finite constants, malformed/unreadable JSON.
`validate_manifest()` validates that data or the installed separate v2 artifact,
then returns `ValidatedCatalogueV2` containing deeply immutable data and counts.
It does not authorize an Account or execute any policy.

The validator:

- Derives the exact expected definition/delta/default/role/scope/decision data
  from pinned AR-3B2A tables and pinned C1 data, without generating files on failure.
- Checks canonical/global-unique codes, static Unicode-equivalent name collisions,
  service/role references, names/descriptions/modules/actions, readiness, exact
  pair totals and duplicate bindings. Field lengths are read with Python AST from
  current model declarations; the models are never imported by v2 validation.
- Rejects blocked/delegation defaults, selectable retired codes, Advisor write or
  missing-view defaults, G business defaults, altered retirements, numeric IDs,
  unexpected privilege fields and metadata/default changes even at unchanged totals.
- Enforces source-exact composition contracts: Normal Admin is Admin; full
  application Super Admin needs Admin+G, effective core codes, approved/active
  eligibility, service delegation, usable reviewed governance and object policy.
  G membership or management Grants alone are insufficient.
- Records Advisor eligibility as Instructor+SSG Advisor plus effective read codes,
  approved/active state, valid appointment/period and minimized read projections.
  Role membership or read Grants alone do not establish monitoring eligibility.
- Preserves explicit Deny precedence, requested-role non-authority, object ownership,
  finance self-interest, dependent-override review, self/assigned-role protections,
  effective-last-operator safeguards and no Django Superuser application bypass.
- Keeps delegation OFF, enabled scopes empty, Cartesian widening/wildcards/reserved
  ordinary mutation disabled. All V2-01 through V2-10 remain OPEN and operational
  gates remain BLOCKED. It rejects marking them approved or ready.

Those are validated planning contracts, not implemented runtime checks. Existing
evaluator and B2 behavior are untouched. A read-only Advisor role cannot suppress
write rights from another role automatically; the explicit coexistence/conflict
policy remains required. Static normalization does not replace future comparisons
against actual MySQL uniqueness/collation behavior.

## Tests executed and database isolation

From `backend`:

```powershell
& '.\.venv\Scripts\python.exe' -B scripts/test_catalogue_static.py
```

Actual result: **81 passed, 0 failed, 0 skipped**, in 1.737 seconds:

- **46 new v2 tests**, including subtests over all field limits, blocked codes,
  provenance sources and important eligibility/security flags.
- **35 existing v1 ManifestTests**, loaded unchanged. No v1 PlannerTests or other
  database-fixture tests were run.

The runner configures settings in memory and never loads development settings or
dotenv/database credentials. It uses Django's dummy backend and patches the base
connection entry point to raise on any attempt. The guard recorded **zero database
connection attempts**. No database was created, queried, migrated or written and
no test database cleanup was necessary.

A separate subprocess test forbids Django imports entirely and successfully
imports and validates v2 with only the Python standard library. Tests also cover
deep immutability, C1 exact preservation, missing/tampered source evidence, strict
Boolean types, disabled operational gates, all three Advisor reads, retirement,
revisions and same-count matrix tampering. No full regression suite was run.

## C1 and project preservation

The complete repaired v1 manifest remains byte-identical:

`86D72D82295CB358244145C6D24EBE8BA948F5211DE298EBF897B5D3D83ED447`

The original C1 source-content pin remains:

`02EB308DB5AFF1491EA2D024F5F7F1074125E3A7B9BB02DBD1409F6A6170A99E`

The v1 validator, planner, tests, package initialization, services, settings,
models, historical migrations, registration and frontend are unchanged. All 215
pre-existing paths, including untracked files and recorded deletions, were captured
before implementation and compared afterward. Only the five new files above are
added. There was no reset, clean, discard, commit or push.

Protected ERD SHA-256 values remain:

- Full: `E9235A87555FFCD50ECB6AB6C1A45F9C7C54E344FF8F269ECC890579F633E4B2`.
- Auth: `F050F7B910038532CA8E73B283F16A57DEDD6B738FDC74D293E64D539A4AFAC4`.

Database integrity is established here by **no connection or database operation**,
not by claiming a new live snapshot. Prior planner classifications and table
counts were not rerun or forced in this static-only phase.

## Remaining security/approval blockers

Static acceptance does not resolve the ten policy decisions: exact live-grant
adoption; role/promotion eligibility; monitoring privacy/appointment/coexistence;
governance/recovery intent boundaries; independent actor/shared-role review;
effective operator/quorum/locking/recovery; first real human attribution/serialization;
event/session/review evidence; Django framework integration; and activation/business
scope. Initialization, grants, activation, live mutations, administrator creation,
first-operator attribution, evidence, object checks, sessions/events and framework
changes remain explicit BLOCKED gates.

No fake audit actor or approval record is installed. The B1 actor FK, bounded audit
payload and absent first-init mutex remain real bootstrap dependencies. Any optional
flag, evidence or session schema change still needs independent approval. No role,
service, permission, account or Django Superuser was created or activated.

## Handoff: independently authorized read-only v2 database planning

The next task may consume the immutable v2 result for a version-aware read-only
planner, while preserving the v1 command's default behavior and historical pins.
It must adapt to v2 provenance/tombstone/composition fields rather than pass them
blindly into the current v1 comparison implementation.

Compare then-current Service/Permission/Role/default records using actual MySQL
collations and explicit CREATE/MATCH/CONFLICT/DEFER classifications. Handle both
revised metadata definitions and preserved retirement history; flag active retired
grants/overrides for review, never alias/remap/delete them. Preserve unknown/inactive
records and report unresolved blockers separately from metadata existence.

Require a READ ONLY snapshot/SELECT guard, no audit or timestamp writes, replay
and integrity evidence. Any disposable-MySQL fixture testing needs explicit next-
phase authorization; this phase did not create such fixtures. Derive live results
from inspected state, not from proposed totals or old v1 classifications. There
must be no apply/seed mode, activation, grant enablement or administrator provisioning.

AR-3B2B1 stops after the independently versioned artifact, static validation,
focused tests and this report.
