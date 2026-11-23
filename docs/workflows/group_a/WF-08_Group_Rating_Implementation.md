# WF-08 — Group Peer Rating implementation record

Implemented 23 November 2026. This record documents the current foundation for the Group Peer Rating workflow. It is not a claim that the complete Professor, Group Leader, Student and Admin workflow is finished.

Parent: [Workflow catalogue](../CTU-G_Workspace_System_Workflow_Catalogue.md).

## Scope implemented

| Area | Implementation |
| --- | --- |
| Backend data model | Added rating sessions, rating groups, group members, private submissions, individual results and activity records. |
| Session states | Draft, Published, Closed and Released statuses are represented in the model. |
| Professor/Instructor session creation | Authorized Instructors can create a session with a title, deadline and criteria list. |
| Publishing | The session publisher can assign an account as the leader of each named group and publish the session. |
| Leader member management | An assigned leader can confirm group members using account School IDs. |
| Student submissions | Assigned students can submit ratings for their group before the deadline. A unique submission record locks that student's submission against further edits. |
| Individual result release | The session creator can calculate and release individual average criterion scores and final scores. |
| Activity log | Session creation, member confirmation, publication, submission and result release actions are recorded. |
| Dashboard integration | The existing permission-gated Group rating dashboard entry is now available when `group_rating.sheets.assigned.read` is effective. |

## Changed files

| File | Change |
| --- | --- |
| `backend/apps/group_rating/models.py` | Replaced the placeholder module with the rating-session data model. |
| `backend/apps/group_rating/migrations/0001_initial.py` | Added the initial Group Rating database migration. |
| `backend/apps/group_rating/views.py` | Replaced placeholder views with permission-checked session, member, publication, submission and release API actions. |
| `backend/config/urls.py` | Added the `/api/v1/group-rating/...` routes. |
| `frontend/src/features/groupRating/GroupRatingPage.tsx` | Added the initial Group Rating dashboard interface and session table. |
| `frontend/src/features/dashboard/navigation.ts` | Changed the Group rating dashboard entry from planned to shell/available. |
| `frontend/src/features/dashboard/SessionDashboardPage.tsx` | Mounted `GroupRatingPage` for the permission-visible Group rating view. |

## API routes

| Method | Path | Main purpose |
| --- | --- | --- |
| GET | `/api/v1/group-rating/` | Return only rating sessions visible to the current account by assignment or ownership. |
| POST | `/api/v1/group-rating/sessions/` | Create a Draft rating session. |
| POST | `/api/v1/group-rating/sessions/<session_id>/publish/` | Assign group leaders and publish a session. |
| POST | `/api/v1/group-rating/sessions/<session_id>/members/` | Confirm or replace the assigned leader's group member list. |
| POST | `/api/v1/group-rating/sessions/<session_id>/submit/` | Submit and lock private peer ratings for the current student. |
| POST | `/api/v1/group-rating/sessions/<session_id>/release/` | Calculate and release individual results. |

All mutation endpoints require the relevant effective permission code on every request. The existing session/permission system is authoritative; dashboard visibility does not grant API access.

## Workflow privacy and locking behavior

- A student submission is locked by a unique `RatingSubmission` database record and rejects a second submission.
- A submission response is private to the submitting student.
- The API currently does not expose one student's raw ratings to another student or to the group leader.
- Group members can only be changed for a Draft or Published session before the deadline.
- Individual results are stored separately and are only released when the professor/instructor release action sets `released_at`.
- The current implementation does not yet provide an email notification, export, PDF report or admin monitoring interface.

## Scoring behavior

The current release calculation:

1. Excludes the student being scored from incoming rater submissions.
2. Uses ratings submitted by the remaining group members.
3. Averages each criterion across incoming submissions.
4. Averages all criterion averages to produce a two-decimal final score.

The 1–5 submitted rating validation, missing-row validation and average calculation are initial implementation rules. They remain subject to policy approval and do not supersede the existing requirement for an approved scoring formula.

## Role coverage

| Workflow actor | Current coverage | Remaining work |
| --- | --- | --- |
| Student | Submits private ratings through an API and receives a separately stored result model. | Add the private rating-grid UI, submission lock UI and own-result-only view. |
| Group Leader | Backend member confirmation and assigned-session listing. | Add leader notification, member-entry grid and submission-progress UI without rating values. |
| Professor/Instructor | Session creation, publishing and result release APIs. | Add assigned-class controls, group/criteria editors, progress monitoring and Excel/PDF export UI. |
| Admin | Existing account/permission framework remains available. | Add active/completed session monitoring, issue checks, activity log UI and documented final-score adjustment process. |

## Current limitations

- The frontend currently provides session creation and a session table. It does not yet call the member, publish, submit or release role controls.
- The migration cannot be applied until the configured MySQL credentials and database are available.
- No focused automated tests have been added specifically for the Group Rating models, privacy boundaries or API endpoints.
- No Excel export or PDF report generation is implemented.
- No notification delivery for published sessions is implemented.
- No Student, Professor or Admin role assignment UI was added; those workflows continue to use the existing account-role system.

## Verification performed

- Django Python syntax compilation passed for the changed Group Rating and URL modules.
- Django `python manage.py check` reported no configuration issues.
- `python manage.py makemigrations group_rating --check --dry-run` reported no missing model migrations.
- Frontend `npm.cmd run build` passed.
- Database migration/history validation could not complete because MySQL returned `Access denied` for the configured `ctug_app` account.

These checks verify the foundation only. They do not certify database migration success, workflow privacy, role behavior, browser operation or policy approval.

## Approval boundary

No scoring policy, privacy-release policy, export policy or Human Approval was added or inferred by this implementation. The existing WF-08 requirement section remains Draft and policy decisions remain pending.
