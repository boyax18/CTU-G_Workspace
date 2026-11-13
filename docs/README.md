# CTU-G Workspace — Documentation Index

_Last reviewed: 2026-11-08 (local development; based on project terminal results shared in chat)_

This folder holds the project's **living documentation**. The SRS describes **what** the system should do; architecture, database, API, security, and implementation records describe **how**, **what has actually been built**, and **what remains blocked**.

## Core records

| Document | Purpose | Update trigger |
| --- | --- | --- |
| `DEVELOPMENT_STATUS.md` | Current verified work, unresolved items, next phase | Every phase or material change |
| `CHANGELOG.md` | Chronological project changes, including tests | Every tested phase |
| `testing/TEST_RESULTS.md` | Reproducible test commands and observed outcomes | Every test run accepted as evidence |
| `security/ACCESS_CONTROL_GATES.md` | Access-control restrictions and activation blockers | Before any change to roles, grants, approvals, or governance |
| `decisions/ADR-001-admin-identity-separation.md` | Rationale for Django Superuser vs Workspace roles | When the decision changes |
| `decisions/ADR-003-django-framework-account-flags.md` | Approved Option A for `is_staff` / `is_superuser` and ERD pins | When framework-account schema or its approval changes |
| `implementation/access-control/erd-fingerprint-provenance-2026-11-08.md` | Explains the historical and approved DBML fingerprints | When protected ERD provenance is reviewed |
| `implementation/authentication/ar-6c3-integration-readiness-assessment.md` | Remaining gates before live Admin registration-review integration | On verification or governance decisions |
| `implementation/authentication/ar-6c2-routing-safety-verification.md` | Routing isolation and prior 25/25 test evidence | If routing or feature gates change |
| `api/AUTH_ENDPOINT_INVENTORY.md` | Initial authentication API inventory to validate against route code | When auth endpoints/contracts change |
| `templates/PHASE_COMPLETION_CHECKLIST.md` | Standard closure checklist for future phases | Every new phase |

## Existing documentation to retain

Keep the existing SRS, architecture diagrams, Figma/FigJam sources, and `docs/database/*.dbml` files. The two Django framework account fields (`is_staff` and `is_superuser`) are now formally accepted by **ADR-003**; do not modify the DBML or replay migrations as part of this documentation update. Verify the approved raw DBML fingerprints in the local workspace before relying on the revised integrity verifier.

## Documentation rules

1. **Code + tests + docs** are the phase-completion gate. A passing unit test is not proof that a live permission is activated.
2. Record test counts as *observed*, including the command and relevant database/settings context; distinguish code implementation from live deployment.
3. Record security decisions as approved, proposed, or blocked. Do not silently convert a read-only catalogue plan into grants.
4. Never commit `.env`, passwords, recovery tokens, real account emails/IDs, raw personal records, or database dumps containing personal information.
5. If facts become stale, mark them **needs re-verification** instead of assuming they remain true.

## Installation

This index is maintained in the project repository. When applying documentation patches, compare their files with your local versions, merge newer changes, and verify Git diffs before committing; the patches do not edit your local Windows repository automatically.
