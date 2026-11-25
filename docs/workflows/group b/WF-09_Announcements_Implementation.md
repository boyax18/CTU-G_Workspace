# WF-09 - Announcements implementation record

Implemented 25 November 2026. This record describes the current read-only campus Announcement feature.

Parent: [Workflow catalogue](./CTU-G_Workspace_System_Workflow_Catalogue.md).

## Scope implemented

| Area | Implementation |
| --- | --- |
| Backend model | Added `Announcement` records with title, body, author, and creation date. |
| Read access | Any authenticated Workspace account can read all announcements. |
| Admin posting | Admin users can create announcements in Django Admin. |
| Automatic notifications | The Notifications foundation provides a `create_notification` helper for future announcement posting. |
| Dashboard | Added an effective-permission-gated Announcements sidebar item. |
| Frontend | Added announcement cards with author, date, body, loading, error, and empty states. |

## Data model

`Announcement` fields:

| Field | Rule |
| --- | --- |
| `title` | CharField, maximum 200 characters. |
| `body` | TextField. |
| `author` | Optional foreign key to the account; related name `announcements`; deleting the author preserves the announcement and clears the author. |
| `created_at` | Automatically set at creation. |

Announcements are ordered newest first.

## Backend files

| File | Change |
| --- | --- |
| `backend/apps/announcements/models.py` | Defines `Announcement`. |
| `backend/apps/announcements/serializers.py` | Serializes title, body, author name, and creation date. |
| `backend/apps/announcements/views.py` | Provides the authenticated read-only list. |
| `backend/apps/announcements/urls.py` | Mounts the Announcements route. |
| `backend/apps/announcements/admin.py` | Registers search and list-display fields. |
| `backend/apps/announcements/migrations/0001_initial.py` | Creates the table and seeds the Student read grant. |
| `backend/config/urls.py` | Mounts `/api/v1/announcements/`. |

## API route

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/announcements/` | Any authenticated account | Return all announcements newest first. |

No announcement `POST`, `PUT`, `PATCH`, or `DELETE` API endpoint is mounted.

## Frontend files

| File | Change |
| --- | --- |
| `frontend/src/features/announcements/api.js` | Loads announcements. |
| `frontend/src/features/announcements/AnnouncementsPage.tsx` | Displays announcement cards and page states. |
| `frontend/src/features/dashboard/navigation.ts` | Makes the Announcements module permission-gated and working. |
| `frontend/src/features/dashboard/SessionDashboardPage.tsx` | Mounts the Announcements page. |
| `frontend/src/App.tsx` | Adds `/announcements`. |

## Author display

The API resolves an author's profile name when available and otherwise uses the account School ID. The frontend displays `Admin Office` when no author or author name is available.

## Permission behavior

The frontend reveals the module when the session contains:

- `announcements.read`

The backend endpoint requires authentication. It does not rely on dashboard permission hints for identity or access decisions.

## Manual test

1. Open Django Admin.
2. Create two announcements.
3. Give one announcement an author and leave one author blank.
4. Sign in as an approved active Student.
5. Open `/announcements`.
6. Confirm both cards are visible.
7. Confirm the blank-author card shows `Admin Office`.
8. Confirm the author name and date are visible on the other card.
9. Confirm each body preserves line breaks.

