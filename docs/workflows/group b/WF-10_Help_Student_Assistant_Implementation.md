# WF-10 - Help and Student Assistant implementation record

Implemented 25 November 2026. This record describes the published Help Article and Student-to-Admin message foundation.

Parent: [Workflow catalogue](./CTU-G_Workspace_System_Workflow_Catalogue.md).

## Scope implemented

| Area | Implementation |
| --- | --- |
| Help Article model | Added ordered FAQ-style articles with categories and publish state. |
| Published article list | Logged-in users can read only published articles. |
| Optional category filter | The article list accepts `?category=`. |
| Student contact | Approved active Students can submit a subject and message. |
| Help requests | Messages are stored in `HelpRequest` with open/closed status. |
| Admin review | Articles and requests are registered in Django Admin. |
| Dashboard | Added a bottom Help / Student Assistant utility link. |
| Settings | Added a profile/settings read-update page for the existing profile update permission. |

## Help Article model

`HelpArticle` fields:

| Field | Rule |
| --- | --- |
| `question` | CharField, maximum 255 characters. |
| `answer` | TextField. |
| `category` | Optional CharField, maximum 50 characters. |
| `order` | PositiveIntegerField, default zero. |
| `is_published` | Boolean, default true. |

The model orders by `order`, then `id`.

## Help Request model

`HelpRequest` fields:

| Field | Rule |
| --- | --- |
| `student` | Foreign key to the authenticated account; related name `help_requests`. |
| `subject` | CharField, maximum 150 characters. |
| `message` | CharField, maximum 2000 characters. |
| `status` | `open` or `closed`; defaults to `open`. |
| `created_at` | Automatically set at creation. |

## Backend files

| File | Change |
| --- | --- |
| `backend/apps/helpcenter/models.py` | Defines `HelpArticle` and `HelpRequest`. |
| `backend/apps/helpcenter/serializers.py` | Validates contact subject and message. |
| `backend/apps/helpcenter/views.py` | Provides article list and contact submission. |
| `backend/apps/helpcenter/permissions.py` | Restricts contact submission to eligible Student accounts. |
| `backend/apps/helpcenter/urls.py` | Mounts Help routes. |
| `backend/apps/helpcenter/admin.py` | Registers editable ordered articles and reviewable requests. |
| `backend/apps/helpcenter/migrations/0001_initial.py` | Creates Help Article and Help Request tables. |
| `backend/apps/accounts/settings_api.py` | Provides profile settings read and update. |
| `backend/apps/accounts/urls.py` | Mounts `/api/v1/auth/settings/`. |
| `backend/apps/accounts/migrations/0007_profile_settings_permission.py` | Seeds the Student profile update grant. |
| `backend/config/settings.py` | Registers `apps.helpcenter`. |
| `backend/config/urls.py` | Mounts `/api/v1/help/...`. |

## API routes

| Method | Path | Access | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/help/articles/` | Authenticated | Return published articles. |
| GET | `/api/v1/help/articles/?category=Finance` | Authenticated | Return published articles in a category. |
| POST | `/api/v1/help/contact/` | Eligible Student | Create an open Help Request. |
| GET | `/api/v1/auth/settings/` | Profile-update permission | Return the signed-in profile settings. |
| POST/PATCH | `/api/v1/auth/settings/` | Profile-update permission | Update names, suffix, and email. |

Contact validation rejects missing or whitespace-only subject and message values.

## Frontend files

| File | Change |
| --- | --- |
| `frontend/src/features/help/api.js` | Loads filtered articles and submits Help Requests. |
| `frontend/src/features/help/HelpPage.tsx` | Displays published FAQ articles and contact form. |
| `frontend/src/features/settings/api.js` | Loads and updates account settings. |
| `frontend/src/features/settings/SettingsPage.tsx` | Displays editable profile fields and save feedback. |
| `frontend/src/features/dashboard/navigation.ts` | Adds utility routes for Help and Account settings. |
| `frontend/src/features/dashboard/SessionDashboardPage.tsx` | Mounts the Help and Settings pages. |
| `frontend/src/components/dashboard/DashboardIcon.tsx` | Adds the help icon. |
| `frontend/src/App.tsx` | Adds `/help` and `/settings`. |
| `frontend/src/layouts/DashboardLayout.tsx` | Maps direct utility routes to their dashboard views. |

## Admin starter articles

The Admin Office should add starter articles in Django Admin, for example:

1. Question: `How do I check my clearance?`
2. Question: `Why is my payment still pending?`
3. Categories: `Clearance` and `Finance`.
4. Set `is_published` to true.
5. Set `order` values to control FAQ display order.

The migration intentionally does not invent campus-specific article content.

## Settings behavior

The page reads and updates:

- First name
- Middle name
- Last name
- Suffix
- Email

The effective permission is:

- `accounts.profile.self.update`

The backend rechecks the permission for every settings GET and update.

## Manual test

1. Open Django Admin.
2. Create a published `Clearance` Help Article for “How do I check my clearance?”
3. Create a published `Finance` Help Article for “Why is my payment still pending?”
4. Sign in as an approved active Student.
5. Open `/help`.
6. Confirm both articles appear.
7. Filter by `Finance` and confirm only Finance articles remain.
8. Submit a contact subject and message.
9. Confirm the open `HelpRequest` appears in Django Admin.
10. Open `/settings`.
11. Confirm profile fields appear and can be saved.
