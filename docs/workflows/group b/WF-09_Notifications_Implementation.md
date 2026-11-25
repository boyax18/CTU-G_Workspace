# WF-09 - Notifications implementation record

Implemented 25 November 2026. This record describes the current student notification list, read state, unread badge, and notification helper.

Parent: [Workflow catalogue](./CTU-G_Workspace_System_Workflow_Catalogue.md).

## Scope implemented

| Area | Implementation |
| --- | --- |
| Backend model | Added recipient-specific notifications with title, body, optional announcement link, read state, and creation date. |
| Own-notification list | Students can list only their own notifications. |
| Read item | A notification can be marked read once. |
| Read all | All unread notifications for the current account can be marked read. |
| Unread badge | The dashboard sidebar shows the current unread count. |
| Creation helper | Added `create_notification` for future announcement and system integrations. |

## Data model

`Notification` fields:

| Field | Rule |
| --- | --- |
| `recipient` | Foreign key to the account; cascade delete. |
| `title` | Maximum 200 characters. |
| `body` | Optional text body. |
| `announcement` | Optional foreign key to `Announcement`; cascade delete. |
| `is_read` | Boolean; defaults to false. |
| `created_at` | Automatically set at creation. |

Notifications are ordered newest first.

## Backend files

| File | Change |
| --- | --- |
| `backend/apps/notifications/models.py` | Defines `Notification`. |
| `backend/apps/notifications/views.py` | Provides list, mark-one-read, and mark-all-read endpoints. |
| `backend/apps/notifications/urls.py` | Mounts Notification routes. |
| `backend/apps/notifications/admin.py` | Allows Admin Office staff to create, search, filter, and inspect notifications. |
| `backend/apps/notifications/service.py` | Provides `create_notification(...)`. |
| `backend/apps/notifications/migrations/0001_initial.py` | Creates the table and seeds the Student read-state grant. |
| `backend/config/urls.py` | Mounts `/api/v1/notifications/...`. |

## API routes

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/v1/notifications/` | Return the signed-in user's notifications and unread count. |
| POST | `/api/v1/notifications/<notification_id>/read/` | Mark one owned notification as read. |
| POST | `/api/v1/notifications/read-all/` | Mark every unread owned notification as read. |

The API filters every notification query by `recipient=request.user`. It does not return or mutate another Student's notifications.

## Creation helper

```python
create_notification(
    recipient=user,
    title="Campus announcement",
    body="A new announcement was posted.",
    announcement=announcement,
)
```

The helper creates a database notification and is available for future Admin announcement-posting logic.

## Frontend files

| File | Change |
| --- | --- |
| `frontend/src/features/notifications/NotificationsPage.tsx` | Displays unread count, notification cards, Mark-all control, and read state. |
| `frontend/src/features/dashboard/navigation.ts` | Makes Notifications a working permission-gated module. |
| `frontend/src/components/dashboard/DashboardNavigation.tsx` | Displays the unread badge beside Notifications. |
| `frontend/src/components/dashboard/DashboardShell.tsx` | Loads and refreshes the unread count. |
| `frontend/src/features/dashboard/SessionDashboardPage.tsx` | Mounts the Notifications page. |
| `frontend/src/App.tsx` | Adds `/notifications`. |

## Badge behavior

- Starts with the backend unread count.
- Drops immediately after the dashboard receives a mark-read event.
- Disappears when the unread count reaches zero.
- A read notification is presented with muted styling.

## Permission behavior

The module and API require:

- `notifications.read_state.self.read`

The frontend badge and module visibility are hints. The backend rechecks effective permissions and ownership for every endpoint.

## Manual test

1. Open Django Admin.
2. Add two `Notification` records for the target Student account.
3. Leave both notifications unread.
4. Sign in as that Student.
5. Confirm the Notifications sidebar badge shows `2`.
6. Open Notifications.
7. Click one notification.
8. Confirm the badge shows `1`.
9. Confirm the clicked item appears muted/read.
10. Click **Mark all as read**.
11. Confirm the badge disappears.

