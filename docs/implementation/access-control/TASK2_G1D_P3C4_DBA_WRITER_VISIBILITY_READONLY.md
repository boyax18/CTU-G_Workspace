# CTU-G Workspace — G1D-P3C4: DBA writer visibility (read-only)

**Source checkpoint:** `ronald` / `4d80170`, November 13, 2026.
**Status:** Development candidate, exact local verification pending. Read-only, add-only, cannot authorize protected role creation.

## What this adds

The P3C1 source scan found 14 direct ORM writer sites, and P3C2 found privileged capabilities in the **current** MySQL credential. P3C3 handles uncertain synthetic recovery evidence but cannot authenticate operational facts. P3C4 adds a broader **read-only, anonymized MySQL system-catalogue visibility diagnostic**. It counts rows visible to the current credential in `mysql.user`, global and schema/table/column/routine grant sources, role assignments, default roles, process-list metadata, and workspace routines/triggers/events.

The optional P3C4 local command uses `SELECT COUNT(*)` and `SELECT DATABASE()` only, and prints aggregated counts, source coverage, and `release_status: BLOCKED`. No user names, hostnames, grant statements, session SQL, secrets or private keys should appear in its output. A failed/denied metadata query becomes `UNAVAILABLE` without echoing the underlying SQL error. A successfully returned metadata count **does not mean the view is complete**, especially for process lists and INFORMATION_SCHEMA objects.

## Add-only source files

1. `backend/apps/access_control/tests_support/g1d_p3c4_dba_visibility_test_only.py` — exact static query inventory, anonymized count summaries, fail-closed release status.
2. `backend/apps/access_control/management/commands/report_g1d_p3c4_dba_visibility.py` — guarded SELECT-only local MySQL command. It never makes security changes or claims writer isolation.
3. `backend/apps/access_control/test_task2_g1d_p3c4_dba_visibility.py` — offline contract tests including invalid shapes, partial catalogue visibility and release hold.
4. `docs/implementation/access-control/TASK2_G1D_P3C4_DBA_WRITER_VISIBILITY_READONLY.md` — documentation.

## Safety boundary

- **Not a production fence.** `mysql.user` / grant-table row counts cannot enumerate effective privileges across roles and definer processes. Metadata access may be partial and `PROCESSLIST` is only a point-in-time view.
- A high-privilege development credential is **not** a production release identity. Do not create new MySQL users, change their privileges, kill sessions, start a maintenance window, or use privileged Django role writes as part of this step.
- `prepare_g1d_p1_protected_role --apply` remains disabled. D7 remains withheld. The official `docs/database/full_schema.dbml` remains untouched by this deliverable, and its pre-existing local modification must be preserved.
- No signed institutional identity proof or independent DBA attestation is supplied by this code. Existing Role/Permission models, synthetic ledger, P3C3 recovery classifier and feature gates remain unchanged.

## Local command (read-only development database)

After the focused tests and before full regression, an owner on local MySQL 8.4 may run:

```powershell
cd "C:\Users\ronal\IdeaProjects\Nadd\CTU-G Workspace\backend"
python -B manage.py report_g1d_p3c4_dba_visibility --settings=config.settings --expected-db ctug_workspace --ack P3C4_SELECT_ONLY_VISIBILITY
```

If the current MySQL credential cannot SELECT system metadata, expect `UNAVAILABLE` for those sources. That is **not an error to fix by granting broad DB privileges**. The output must always state `release_status: BLOCKED`. Review the output before sharing it; aggregate information may still be institution-sensitive.

Run the full Accounts and Access Control regression under `config.test_settings` and `makemigrations --check --dry-run --settings=config.settings`. Only then stage the four exact new files and commit without pushing.

## Next actual operational step (not another code-only proof)

An independently authorized MySQL DBA must review the **effective** grants of every database user/role and every external/scripted writer, including accounts with global control privileges, active roles and routine DEFINERs. Record the scoped identities and grants in **private** evidence, not chat or Git; issue narrower credentials for application/read-only/release use, and attest maintenance/admission controls against competing connections. The credential separation and session fence require operations outside this script. Also obtain separately authenticated institutional signers, final ledger schema/retention approval and a fresh restore rehearsal before any D7 live privileged mutation.
