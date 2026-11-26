# Controlled activation preparation — verification record

26 November 2026 · starting branch/HEAD `ronald` / `2a1bca1`.
Local corrections and preparation are committed together; the final SHA is reported in the delivery
message and available with `git log -1 --oneline`. No push/merge or actual operational acceptance.

| Verification | Observed result | Scope / evidence |
| --- | --- | --- |
| Existing backend boundary/onboarding/concurrency/HTTP/residual/fee suites | **91/91 passed**, 207.918 s | Guarded `config.test_settings` + `IsolatedMySQLRunner`; fresh `test_ctug_registration_*` database created/destroyed. Current runtime constants unchanged. |
| Candidate backend permission transition | **21/21 passed**, 33.128 s | Unapplied patch in separate source copy; disposable MySQL. Nine new transition tests plus all seven existing verification and five historical-correction assertions inherited unchanged. |
| Offline candidate/inventory contract tests | **12/12 passed** | Exact candidate envelope/operations, unchanged base-validator chain, altered candidate addendum, missing/injected operations, forged approval/type/JSON-key refusal, patch reproducibility, no default connection/driver import, no personal fields, SELECT-only query definitions, scoped-grant modes, Deny review, privileged/wrong-schema refusal. |
| Prepared schema and inventory SQL | **2/2 passed** | Disposable MySQL only. Full 24-table column/constraint inventory, generated orphan/duplicate/atomic consistency SQL and every inventory SELECT syntax checked. No actual database inspection. |
| Student dashboard boundary browser suite | **10/10 passed** in the final combined 30-test run (48.662 s) | Mocked APIs, fresh browser profiles and private loopback Vite. Selected Student with extra assignments, missing/denied read code, generic/refused/unavailable status responses, protected URLs/Back/refresh/cross-tab completion, held response after a role roundtrip, independent non-Student contexts and account access. |
| Related Student onboarding + dashboard shell browser suites | **20/20 passed** in that final combined run | Mocked APIs. Includes Regular/Irregular, verification/Pending, completion and contrast/layout probes at 360–1440px in Light/System-dark/Dark. |
| Current frontend unit suite | **285/286 passed** before and after correction | Same single `dashboard-navigation` / `appointment-evidence` assertion described below. No test weakened or removed. |
| Current frontend build | **Passed** | `tsc -b && vite build`; no runtime flags activated. |
| Candidate frontend build | **Passed** | Proposed exact constants/navigation/historical permission hint only in separate source copy; all registry frontend flags off; both TypeScript/Vite success and a built `dist/index.html` verified. |
| Current frontend lint | **3 existing errors** | `RoleContextSwitcher.tsx:16` and `:19`, `RolePermissionsPanel.tsx:52`, all `react-hooks/set-state-in-effect`. These files are unchanged from the starting commit. No new lint error in the modified provider. |
| Migration graph/model consistency | **Passed offline** | `MigrationLoader(None)`, complete nine-node ancestor closure (seven requested plus two baseline prerequisites), all DB connections forbidden; no model drift. Generated evidence contains 24 tables, 11 registry features, 14 backend and 14 frontend flags, no approved Academic Settings modes. |
| Existing catalogue source pins | **Unchanged; v2.2 validator passed** | v2.0 → v2.1 → v2.2 chain, effective digest `192ba955d1dae06bfbdf574e52ef454390b9fd41b803f63778d1d220b6cd8c6d`. Prior independent-review status remains OPEN. |

Commands are in the [acceptance checklist](WF11_Operational_Acceptance_2026-11-26.md).
Test-only launcher acknowledgments are cleared in Python **after** loading environment values;
PowerShell 5 removes an empty environment assignment and dotenv would reload it. The wrapper
also substitutes a random disposable DB name before importing base settings; the established test
runner independently verifies the database name before test creation. No `.env`, credential or
launcher mode is modified. Initial direct test attempts stopped in settings validation before
connecting; the guarded wrapper resolves that test-process initialization issue.

The candidate test first lacked an existing script dependency in its source copy; adding
`backend/scripts` fixed that. A repeated-finalization test initially misused the existing review
helper after completion (no Draft fields then); it now resubmits the actual original finalization
parameters and proves idempotence. These were test harness corrections, not application regressions.

## Regression identity and history

| Immutable Git revision tested with current installed Node/TypeScript | Result |
| --- | --- |
| `51d0904`, before Academic Settings | `dashboard-navigation.test.mjs`: `appointment-evidence: access_control.appointments.record` |
| `13da643`, onboarding frontend milestone | Same suite, test and assertion |
| `2a1bca1`, requested starting checkpoint | Same suite, test and assertion |

The first registry-integrity assertion reads pinned `v2_0.json`; the appointment recording code is
absent. `appointment-evidence` is the navigation-item ID printed in the assertion, not another test
suite. The older and latest reports use different levels of naming for the same pre-existing defect.
[Reproducer](../../review_only/academic_settings_v2_3/reproduce_frontend_baseline.mjs) extracts sources
from Git into fresh ignored directories and executes the unchanged tests; current files/pins are
never checked out over the workspace. Test code, dependencies and assertion are preserved.

## Remaining verification limits

No new full-backend regression was run: 91 existing targeted tests and 21 proposed-runtime tests
are the exact backend scope. The earlier full-backend four `apps.accounts` failures are historical
reports, not newly reproduced claims in this delivery. Not all existing browser suites were rerun;
the exact 30 current relevant browser tests above passed.

No actual database permission inventory, backup, restored-live-data migration rehearsal, live schema
or ledger verification, grant provisioning, phase/mode activation or operational acceptance occurred.
Independent governance approval, proof/retention decisions, fee-after-obligation policy, historical
review/protection and adviser/fixed-signatory reconciliation remain owner/security responsibilities.
The candidate checksum validates integrity only and is not independent approval or a protected pin.

Private execution logs are retained under ignored `.local/wf11-*`; no secrets or actual account
records are included in this report. The existing untracked reconciliation folder remains untouched.

## Follow-up: authorized inventory preflight, starting at `10e3fe8`

The owner approved the prepared read-only inventory and later requested local connection/profile
inspection plus unexecuted reader-creation steps if needed. Metadata inspection found the expected
configured local target, root application credentials, no saved MySQL login paths and no usable
verified reader. No database connection or SQL statement was executed. Live counts and comparison
against the governance proposal remain unknown; the database operation is stopped under the
owner's explicit condition. See [preflight findings](../security/WF11_Permission_Inventory_Preflight_2026-11-26.md)
and the [separate-approval reader setup](../security/WF11_Permission_Inventory_Reader_Setup_2026-11-26.md).
This follow-up changes documentation only; prior implementation tests were not rerun, and no
independent review, Human Approval, credential change, migration or activation is claimed.
