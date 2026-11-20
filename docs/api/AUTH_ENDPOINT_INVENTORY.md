# Authentication API Inventory — Draft

**Status:** Inventory transcribed from prior implementation work; verify against actual `backend/apps/accounts/urls.py`, view code, and tests before treating as a formal API contract. Endpoint request/response schemas are not fully specified here.

| Method | Path | Purpose | Security/contract notes |
| --- | --- | --- | --- |
| GET | `/api/v1/auth/csrf/` | CSRF initialization for browser client | Session/cookie configuration must match frontend origin |
| POST | `/api/v1/auth/register/` | Public Student/Instructor registration request | Server-side validation; no self-assigned active role |
| POST | `/api/v1/auth/login/` | Workspace session login | Reject pending/inactive or no eligible role; CSRF protected |
| GET | `/api/v1/auth/session/` | Current server-validated session/role state | Do not trust browser local role values |
| POST | `/api/v1/auth/logout/` | Terminate current session | CSRF protected; server confirmation required |

## Follow-up documentation

- Add exact serializers, HTTP response examples, error codes, and validation schemas from source-controlled code.
- Record session cookie attributes, CSRF policy, origin configuration, rate limiting, and role permission checks from the actual settings and views.
- Registration approval endpoints are **not** listed as implemented; AR-6C remains pending.
