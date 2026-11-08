# ADR-001 — Separate Django Framework Superuser from Workspace Administration

**Status:** Adopted in local implementation; revisit if security architecture changes  
**Recorded:** 2026-11-08

## Context

CTU-G Workspace uses Django for framework operations and application roles for campus workflows. Those two authority domains must not be conflated.

## Decision

- **Django Superuser:** restricted framework administration, with framework `is_staff` and `is_superuser` flags; not automatically a Workspace role holder.
- **Workspace Admin:** an approved, active application account assigned the `Admin` role through the Workspace role table. Effective permissions are evaluated using the application's access-control policy.
- **Technical Super Admin:** a separately governed, optional protected application role for advanced access-control operations. Not created by first Admin bootstrap.
- **First Admin bootstrap:** one-time, audited provisioning, requiring an eligible authenticated framework operator and explicit confirmation; default command mode is read-only. The operator is not promoted into Workspace administration by using the command.

## Consequences

- Bootstrap created the first Workspace Admin **without** enabling services, role defaults, or permissions.
- Admin application endpoints must enforce backend permissions and object scope; a frontend Admin label or menu is never enough.
- Treat future governance elevation, recovery, and Admin replacement as separately approved workflows with independent audit evidence.
- Prohibit routine use or deployment of the temporary bootstrap settings module.

## Evidence

- Isolated AR-6A2 suite: 15/15 passed.
- Read-only post-bootstrap preflight: Admin assignments 1, bootstrap events 1, framework operators 1.

## Review triggers

Any change to framework admin exposure, operator identity, account recovery, protected roles, permission evaluator, bootstrap process, or governance authority must revise this ADR and related tests before deployment.
