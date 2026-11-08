# CTU-G Workspace — Development Changelog

Document meaningful changes after they are verified. Avoid copying secrets or identifying data from consoles.

## 2026-11-08 — Local development checkpoint

### Confirmed

- Frontend production build completed successfully using `npm run build`.
- Frontend `npm test` completed: 25 passed, 0 failed.
- AR-6A1 registration review tests: 17 reported passing; backend authentication/registration regression tests: 44 reported passing.
- AR-6A2 first Admin bootstrap tests: 15 passed, 0 failed (isolated MySQL test database created, migrated, and destroyed).
- Initial Workspace application Admin was provisioned through authenticated one-time bootstrap; bootstrap audit event verified via read-only preflight; temporary enabling settings module deleted.
- Read-only `plan_permission_catalogue_v2` executed. Report: 105 proposed creates, 4 matches, 108 deferred, 0 conflicts.

### Not changed / not authorized

- No permission catalogue activation, permission grants, role-default bindings, optional protected roles, or service activation from the planner.
- No live registration approval API or fully functional Admin dashboard established by this checkpoint.

### Open

- AR-6B1 governance review and documented approval boundaries.
- Database ERD/DBML reconciliation and full browser end-to-end testing.

## Changelog template

### YYYY-MM-DD — Phase/code reference

- **Changed:** 
- **Verified:** exact test commands and results
- **Data/migrations:** 
- **Security/authorization:** 
- **Documentation updated:** 
- **Blocked/follow-up:** 
