# WF-06 - Clearance implementation record

Implemented 25 November 2026. This record documents the current Student Clearance foundation for the CTU-G Workspace. It does not claim that the complete clearance request or assigned-review workflow is implemented.

Parent: [Workflow catalogue](./CTU-G_Workspace_System_Workflow_Catalogue.md).

## Scope implemented

| Area | Implementation |
| --- | --- |
| Backend data model | Added `ClearanceItem` records for one student's office requirements. |
| Statuses | Supports `cleared`, `pending`, and `for_review`. |
| Student read access | A student can read only their own clearance items. |
| Write protection | Students cannot create, update, or delete clearance items through the API. |
| Admin management | The Django Admin Office can create and update clearance items. |
| Dashboard integration | Added an effective-permission-gated **My clearance** dashboard entry. |
| Frontend page | Shows cleared-office count, overall status, and the office status table. |

## Data model

`ClearanceItem` fields:

| Field | Rule |
| --- | --- |
| `student` | Foreign key to the authenticated account; related name is `clearance_items`. |
| `office` | Maximum 100 characters. |
| `status` | `cleared`, `pending`, or `for_review`; defaults to `pending`. |
| `remarks` | Optional text with a maximum length of 255 characters. |
| `updated_at` | Automatically updated when the item changes. |

The database enforces one record per student and office through `unique_together = ("student", "office")`.

## Backend files

| File | Change |
| --- | --- |
| `backend/apps/clearance/models.py` | Defines `ClearanceItem`. |
| `backend/apps/clearance/serializers.py` | Defines the read-only API representation. |
| `backend/apps/clearance/views.py` | Provides the authenticated read-only student list. |
| `backend/apps/clearance/permissions.py` | Restricts access to eligible Student accounts with the self-read permission. |
| `backend/apps/clearance/urls.py` | Defines the Clearance route. |
| `backend/apps/clearance/admin.py` | Registers Clearance items with office/status filters and account search. |
| `backend/apps/clearance/migrations/0001_initial.py` | Creates the table and seeds the Student self-read permission grant. |
| `backend/config/urls.py` | Mounts `/api/v1/clearance/`. |

## API route

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/clearance/` | Authenticated Student with `clearance.requests.self.read` | Return only the current student's clearance items. |

No Clearance `POST`, `PUT`, `PATCH`, or `DELETE` routes are mounted for students.

## Frontend files

| File | Change |
| --- | --- |
| `frontend/src/features/clearance/api.js` | Loads the signed-in student's clearance items. |
| `frontend/src/features/clearance/ClearancePage.tsx` | Displays summary and office status table. |
| `frontend/src/features/dashboard/navigation.ts` | Makes **My clearance** a working permission-gated shell. |
| `frontend/src/features/dashboard/SessionDashboardPage.tsx` | Mounts the Clearance page. |
| `frontend/src/App.tsx` | Adds the `/clearance` route. |

## Page behavior

The summary shows:

- `X / Y offices cleared`
- `Complete` when every office is cleared and at least one item exists
- `Incomplete` for any other state

The office table shows Office, Status, Remarks, and Last updated.

Status presentation:

| Status | Presentation |
| --- | --- |
| `cleared` | Green pill |
| `pending` | Amber pill |
| `for_review` | Red pill |

Loading, error, and empty states are handled separately.

## Permission behavior

The effective Student permission is:

- `clearance.requests.self.read`

The frontend only reveals the link when the session contains that permission. Django independently rechecks the account, active Student role, service state, role grant, and effective permission on every API request.

## Migration and run commands

```powershell
cd backend
python manage.py makemigrations clearance
python manage.py migrate
python manage.py check
```

## Manual test

1. Open Django Admin.
2. Add four `ClearanceItem` records for the target approved Student.
3. Set two items to `Cleared`, one to `Pending`, and one to `For Review`.
4. Sign in as that Student.
5. Open `/clearance` or select **My clearance**.
6. Confirm the summary says `2 / 4 offices cleared`.
7. Confirm the overall status says `Incomplete`.

## Current limitations

- Clearance creation and status changes are Admin-only.
- No Student clearance request submission endpoint is implemented.
- No assigned-office review or decision endpoint is implemented.
- No clearance notification or export feature is implemented.

