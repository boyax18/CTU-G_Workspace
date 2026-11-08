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
| `api/AUTH_ENDPOINT_INVENTORY.md` | Initial authentication API inventory to validate against route code | When auth endpoints/contracts change |
| `templates/PHASE_COMPLETION_CHECKLIST.md` | Standard closure checklist for future phases | Every new phase |

## Existing documentation to retain

Keep your existing SRS, architecture diagrams, Figma/FigJam sources, and `docs/database/*.dbml` files. **Do not overwrite them with this pack.** Audit the DBML against migrations (in particular, Django account `is_staff` and `is_superuser` columns). Add cross-links here once the actual filenames are verified.

## Documentation rules

1. **Code + tests + docs** are the phase-completion gate. A passing unit test is not proof that a live permission is activated.
2. Record test counts as *observed*, including the command and relevant database/settings context; distinguish code implementation from live deployment.
3. Record security decisions as approved, proposed, or blocked. Do not silently convert a read-only catalogue plan into grants.
4. Never commit `.env`, passwords, recovery tokens, real account emails/IDs, raw personal records, or database dumps containing personal information.
5. If facts become stale, mark them **needs re-verification** instead of assuming they remain true.

## Installation

This pack is additive. Extract its `docs/` folder into the repository root. Preview diffs if any matching files already exist. A developer must perform the final review and commit; this pack cannot edit your local Windows repository directly.
