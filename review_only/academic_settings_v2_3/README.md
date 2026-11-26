# Academic Settings v2.3 review package

**APPLIED for LOCAL DEVELOPMENT ONLY under the owner's [local-development authorization](../../docs/security/WF11_Owner_Local_Development_Authorization_2026-11-27.md)
(27 Nov 2026). Independent review OPEN and mandatory for production release.** The patch bytes are
unchanged; `--candidate` source copies are no longer used.
Revision of 27 November 2026: historical dual control, completed patch (fixtures, inverted guard,
installable validator, provisioning command, Phase 1 compatibility) and regenerated pins. Reviewers
start from the [sequential v2.1 → v2.2 → v2.3 handoff](../../docs/security/WF11_Catalogue_Sequential_Independent_Review_Handoff_2026-11-27.md).
Start with the [controlled activation handoff](../../docs/operations/WF11_Controlled_Activation_Preparation_2026-11-26.md),
[migration/activation runbook](../../docs/operations/WF11_Migration_and_Activation_Runbook_2026-11-26.md),
[acceptance checklist](../../docs/operations/WF11_Operational_Acceptance_2026-11-26.md) and
[observed verification results](../../docs/operations/WF11_Activation_Verification_2026-11-26.md).

| Artifact | Purpose |
| --- | --- |
| `v2_3_delta.json`, `ADDENDUM_PROPOSED.md` | Established delta envelope; fee binding move, three narrow permissions/defaults (historical correction `ORD` with runtime dual control), two definition clarifications. Self-authored candidate integrity only; old catalogue pins unchanged. |
| `proposal.py`, `test_preparation.py` | Offline base-chain/candidate validation and inventory guards. No Django setup or DB connection. |
| `runtime_changes_PROPOSED.patch` | **Unapplied** exact backend/frontend changes: effective-resolver Deny-only compatibility, the narrow codes, corrected test fixtures and the inverted pre-activation guard, the installable `validation_v2_3.py`, the `provision_academic_settings_v2_3_local_dev` command with its tests, and Phase 1 acceptance of exactly receipted restatements. Both v2.3 modules refuse until `INDEPENDENT_APPROVAL` records the genuine sign-off. No launcher change. |
| `prepare_runtime_patch.py`, `proposed/*.py` | Reproducible patch text and the proposed new files (transition guard, v2.3 validator, provisioning command and tests); never replace active source files. |
| `permission_inventory.py` | Default prints a query plan without connecting. Actual `ctug_workspace` SELECT-only operation needs the owner's specific authorization and an existing reader; no application credentials loaded. |
| `inspect_offline.py`, `offline_repository_evidence.json` | Complete migration closure, expected 24-table schema and exact 14 backend/14 frontend switch inventory; every DB connection prohibited during generation. |
| `schema_and_integrity_checks.sql` | Prepared read-only actual-environment schema/ledger/integrity checks; not executed there. |
| `run_isolated_tests.py`, `candidate_runtime_tests.py`, `schema_validation_tests.py` | Fresh disposable MySQL only. `--candidate` copies source and applies proposed text **only in that ignored copy**. No `.env`/credentials copied or changed. |
| `verify_candidate_frontend.py` | Builds proposed frontend in an ignored copy with registry flags off; checks real output artifact. |
| `reproduce_frontend_baseline.mjs` | Runs immutable historical navigation tests in fresh ignored source snapshots; proves the identical pre-existing failure. |

Safe offline validation from the repository root:

```powershell
backend\.venv\Scripts\python.exe review_only\academic_settings_v2_3\proposal.py
backend\.venv\Scripts\python.exe -m unittest discover -s review_only/academic_settings_v2_3 -p test_preparation.py -v
backend\.venv\Scripts\python.exe review_only\academic_settings_v2_3\inspect_offline.py --write
```

No default command here inspects the actual database. The isolated runner uses the repository's
guarded `config.test_settings` / `IsolatedMySQLRunner`; it never selects `ctug_workspace`. Source
copies and logs remain under ignored `.local/`. Candidate hashes are not independent security
approval. Historical correction stays off until operational acceptance; its two-Admin rule is active
source code (`a60e048`).
