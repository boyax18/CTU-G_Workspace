# Academic Settings v2.3 review package

**PROPOSED, NOT ACTIVE. Independent review OPEN. No provisioning or operational acceptance.**
Start with the [controlled activation handoff](../../docs/operations/WF11_Controlled_Activation_Preparation_2026-11-26.md),
[migration/activation runbook](../../docs/operations/WF11_Migration_and_Activation_Runbook_2026-11-26.md),
[acceptance checklist](../../docs/operations/WF11_Operational_Acceptance_2026-11-26.md) and
[observed verification results](../../docs/operations/WF11_Activation_Verification_2026-11-26.md).

| Artifact | Purpose |
| --- | --- |
| `v2_3_delta.json`, `ADDENDUM_PROPOSED.md` | Established delta envelope; fee binding move, three narrow permissions/defaults, two definition clarifications. Self-authored candidate integrity only; old catalogue pins unchanged. |
| `proposal.py`, `test_preparation.py` | Offline base-chain/candidate validation and inventory guards. No Django setup or DB connection. |
| `runtime_changes_PROPOSED.patch` | **Unapplied** exact backend/frontend changes, including effective-resolver Deny-only compatibility. No active v2.3 validator/installer or launcher change. |
| `prepare_runtime_patch.py`, `proposed/permission_transitions.py` | Reproducible patch text and proposed helper; never replace active source files. |
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
approval. Keep historical correction off until its protection/second-reviewer policy is resolved.
