> **RECOVERED / RECONSTRUCTED DOCUMENT — NOT THE ORIGINAL FILE**  
> Reconstructed on 2026-11-07 from previous CTU-G Workspace development reports, known milestones, and the original C1 proposal. Statements about tests and environment are **historical reports supplied by Codex**, not newly run or independently verified. Exact original wording, every test assertion, source line, and implementation nuance may differ. Treat current backend code and test results as authoritative when discrepancies occur.  
> **Status:** Historical implementation handoff; **not an authorization** to initialize or change roles, privileges, services, or database records. Current SRS v0.3 revises the administrator use cases; earlier access-governance assumptions need reconciliation.  

# Phase 1H-C2A — Permission Catalogue Validator and Read-Only Planner

## 1. Purpose and historical scope

Phase 1H-C2A implemented an immutable planning baseline and a **read-only** Django management command to compare the then-proposed permission catalogue with the existing database. It did **not** apply any changes, initialize services, assign privileges, or create a Technical Super Admin.

The historical handoff reported **286 backend tests passed** (58 more than 228), no failures or skips; eight new files; 10 services, 82 proposed permissions, and 96 proposed role bindings validated. This is a reconstruction of that report, not the original full implementation document.

## 2. Reported source and command

Known reported implementation paths:

- `backend/apps/access_control/catalogue/planner.py` — planning/comparison logic.
- `backend/apps/access_control/catalogue/validation.py` — manifest validator.
- `backend/apps/access_control/catalogue/__init__.py` — package.
- Other new source/test/command files existed; their exact paths and contents must be confirmed in the repository.

From `backend` on Windows PowerShell:

```powershell
.\.venv\Scripts\python.exe -B manage.py plan_permission_catalogue
.\.venv\Scripts\python.exe -B manage.py plan_permission_catalogue --format json
```

Both commands were reported to perform **read-only planning**. Use the current implementation to confirm accepted flags and query behavior.

## 3. C1 planning baseline

The historical manifest reflects C1 proposal v1:

| Category | Planned count |
| --- | ---: |
| Services | 10 |
| Permission definitions | 82 |
| Role-permission binding intentions | 96 |
| Existing initialized roles | 4 |
| Future Technical Super Admin role | 1, not initialized |

C1 readiness types: `F` for referenced framework contract, `P` for planned feature, `B` for blocked/reserved. These are **documentation-only readiness states**, not database columns, deployed features, or permission grants. Reserved permissions and delegation authority codes have no proposed default grants.

## 4. Planner classifications

| Classification | Meaning |
| --- | --- |
| `CREATE` | Exact proposed service/permission is absent; show planned creation only |
| `MATCH` | Existing database record matches the manifest definition |
| `CONFLICT` | Existing database record conflicts on identifier, metadata, relationship, collation, or protected state |
| `DEFER` | Missing role, unresolved approval, actor/bootstrap attribution, policy, or other prerequisite prevents application |

Repeated reads must not mutate any record or timestamp. Unknown existing records must be reported and preserved, not silently cleaned. Case/accent/trailing-space MySQL-equivalent identifiers must be treated conservatively to avoid uniqueness errors.

## 5. Historical local-development planner output

From the user-supplied Codex completion report:

| Classification | Count | Interpretation in the prior baseline |
| --- | ---: | --- |
| CREATE | 92 | 10 services + 82 permission metadata rows proposed |
| MATCH | 4 | The four initialized roles matched |
| CONFLICT | 0 | No conflicts detected in that reported run |
| DEFER | 97 | Technical Super Admin and all 96 proposed role binding operations deferred |

These categories summarize planned entities/operations rather than a single uniform set of existing database rows. They are **historical output**, not a guarantee that the current local database remains in that state.

## 6. Guardrails and historical verification

The implementation report said:

- Django checks and test suite completed with 286 passing, zero failed or skipped.
- The live planner performed only reads and did not create services/permissions or any audit record.
- Development schema/migrations/data, both ERD hashes, and pre-existing files remained unchanged.
- Disposable MySQL test databases were removed.

This recovery document did not rerun tests, inspect live MySQL, or validate Git state.

## 7. Blockers and handoff

The original C1 proposal identified 18 project-owner decisions (D01–D18), all open at that time. At minimum, live initialization needs explicit approval of a versioned manifest, safe actor attribution, initial operator bootstrap policy, protected default-grant governance, audit metadata event contracts, and separation of metadata application, grants, and activation.

**Revised use-case warning:** SRS v0.3 later changed the Admin and multi-role requirements. The historical 10/82/96 manifest and the associated command are a **comparison baseline**, not an approved current grant manifest. Reconcile and version it before any permission insert, role assignment, or delegation activation.

No `apply`, `seed`, `bootstrap`, or general mutation operation is authorized by this document.

