# CTU-G Workspace
## Dashboard Shell and Role-Based Navigation Design
**Document type:** UI/UX and Frontend Design Specification  
**Version:** 0.1 (Proposed; labels revised 17 November 2026)  
**Status:** Draft for design review; not workflow or access-policy approval  
**Date:** November 17, 2026  
**Recommended repository path:** `docs/design/CTU-G_Workspace_Dashboard_Shell_and_Role-Based_Navigation_Design_v0.1.md`

> **Core architectural decision:** CTU-G Workspace uses **one reusable dashboard shell**, not five separate dashboard applications. Role labels guide the proposed navigation; the final visible pages and available actions are calculated from effective permissions and enabled services.

## 1. Purpose, Scope, and Authority
This design defines a consistent authenticated dashboard shell, suggested navigation hierarchy for Student, Instructor, Treasurer, School Admin, and Super Admin, plus responsive, accessibility, security, and acceptance requirements. It covers interface architecture and navigation presentation, not creation of new backend privileges or approval of pending workflows.

**Authority and dependencies:** the current System Workflow Catalogue, SRS, approved ERD, access-control implementation, and any approved architecture decisions take precedence where they conflict with this proposal. Menu labels below are proposed information architecture, not evidence that routes/APIs already exist or that a user has permission.

## 2. Single Reusable Dashboard Shell
**Shell regions**

| Region | Purpose |
|---|---|
| Global header | CTU-G Workspace identity; active school year and semester context; search (if enabled); notifications; user menu. |
| Sidebar navigation | Permission-filtered groups and links; active state; collapsed/expanded behavior. |
| Breadcrumb / context row | Current module/page, academic period context, and important workflow notices. |
| Main content outlet | Shared layout area that renders each module page, cards, tables, forms and empty states. |
| Footer / utilities | Profile, Account settings, Logout; support and accessibility affordances as appropriate. |

**Desktop wireframe (conceptual)**
```text
┌────────────────────────────────────────────────────────────────────────┐
│ CTU-G Workspace  │ Academic period │ Search* │ Alerts │ Profile       │
├──────────────────┬─────────────────────────────────────────────────────┤
│ DASHBOARD SHELL  │ Breadcrumb / period / workflow notice              │
│                  ├─────────────────────────────────────────────────────┤
│ Dashboard        │ Page title + relevant quick action                  │
│ Role modules     │ ┌──────────────┐ ┌──────────────┐                  │
│ Grouped links    │ │ Summary card │ │ Summary card │                  │
│                  │ └──────────────┘ └──────────────┘                  │
│ Profile          │ Module table / form / activity / empty state        │
│ Settings         │                                                     │
│ Logout           │                                                     │
└──────────────────┴─────────────────────────────────────────────────────┘
```
* Search is optional and must respect data-access permissions.

### 2.1 Shared component model
- `DashboardShell`: authenticated page frame, responsive layout and focus handling.
- `DashboardHeader`: brand, academic-period display, notifications, user menu.
- `PermissionAwareSidebar`: filters proposed menu registry against the server-authorized effective capability set.
- `Breadcrumbs` and `PageHeader`: consistent hierarchy and context.
- `ModuleOutlet`: route rendering with server-backed authorization checks.
- `DashboardWidgetGrid`: renders only permitted data widgets and quick actions.
- `AccessDenied`, `ServiceUnavailable`, `NotFound`, `Loading`, and `EmptyState`: shared states.

All users share these components. The shell changes its menu and content by capabilities; it does **not** switch between five unrelated dashboard applications.

## 3. Role Navigation Proposals
The groups below indicate default organization, subject to workflow and permission reconciliation. Navigation labels use sentence case, as required by `docs/design/PATTERNS.md` §9 (for example "Account operations", "Applicant reviews"); proper names and established institutional terms (CTU-G Workspace, School Admin, Super Admin, Student, Instructor, Treasurer) keep their capitals. Global items (My profile, Account settings, Logout) appear for every authenticated user, with their actions still validated by the backend.

### 3.1 Student
**Purpose:** Help students monitor academic-period requirements, subjects used for clearance, organizational fees, and campus notices.

| Sidebar group | Suggested links |
|---|---|
| Overview | Dashboard |
| Academic | Academic period; My subjects; My clearance; Clearance history |
| Finance | Organizational fees; Payments & receipts |
| Campus | Announcements; Notifications |
| Support | Account concerns |

**Dashboard widgets:** Current academic period; Clearance progress; Outstanding organizational fees; Announcements.

**Conditions and boundaries:** For a newly active semester, the student may be required to confirm period-specific details and submit subjects for clearance before ordinary dashboard access. Actual enrollment remains authoritative in CTU’s main system; verification/integration or approved manual confirmation is required. Prior-semester clearance requirements and fee-eligibility rules must follow their approved workflows.

### 3.2 Instructor
**Purpose:** Provide teaching references and only the academic or clearance actions explicitly delegated to the instructor.

| Sidebar group | Suggested links |
|---|---|
| Overview | Dashboard |
| Teaching | Assigned subjects; Student lists |
| Clearance | Clearance reviews; Review history |
| Academic services | Group rating |
| Campus | Announcements; Notifications |
| Support | Account concerns |

**Dashboard widgets:** Assigned subjects; Pending clearance reviews; Student summaries; Announcements.

**Conditions and boundaries:** Clearance Reviews and Group Rating are conditional modules, not assumed powers of every instructor. Display only when the workflow is approved, service enabled, and effective permissions allow access. Teaching or enrollment references must come from authorized records/integration rather than independent enrollment administration.

### 3.3 Treasurer
**Purpose:** Support organizational-fee receivables, collections, expense tracking, receipts, financial clearance and reports.

| Sidebar group | Suggested links |
|---|---|
| Overview | Dashboard |
| Financial management | Fee obligations; Student fee records; Payments; Receipts; Expenses |
| Clearance | Financial clearance; Clearance history |
| Reports | Financial reports; Export reports |
| Campus | Notifications |

**Dashboard widgets:** Total collected; Outstanding receivables; Pending payments; Financial clearance queue.

**Conditions and boundaries:** Obligations are period-specific and created/resumed only under verified-enrollment and approved fee-eligibility rules. No institutional enrollment management or access-control administration is exposed to the Treasurer. Sensitive financial exports require their own authorization.

### 3.4 School Admin
**Purpose:** Manage ordinary school operations while remaining outside technical access-control governance.

| Sidebar group | Suggested links |
|---|---|
| Overview | Dashboard |
| Account operations | Applicant reviews; Account directory; Account concerns |
| Academic configuration | School years & semesters; Academic references |
| Campus management | Announcements; Notifications |
| Clearance oversight | Clearance monitoring |
| Reports | Operational reports |

**Dashboard widgets:** Pending applications; Active academic period; Clearance progress; Account concerns.

**Conditions and boundaries:** School Admin can perform approved account-review operations but cannot manage roles, role assignments, role permissions, account-specific overrides, or the permission/service catalogue. Rejected-applicant handling must follow the separately approved notification-and-deletion workflow; this navigation document does not redefine it.

### 3.5 Super Admin
**Purpose:** Inherit all authorized School Admin operational functions and additionally administer protected technical access governance.

| Sidebar group | Suggested links |
|---|---|
| Overview | Dashboard |
| School operations — inherited | Applicant reviews; Account directory; Account concerns; School years & semesters; Academic references; Announcements; Notifications; Clearance monitoring; Operational reports |
| Access control | Role management; Role assignments; Role permissions; Account overrides; Permission catalogue; Service management |
| Security & audit | Access audit logs; Access reviews |
| System operations | System health; Integration status |

**Dashboard widgets:** School operations summary; Access-control activity; Security audit alerts; System health.

**Conditions and boundaries:** Super Admin is the second application-level admin tier, not a separate third Technical Super Admin tier. Inheritance must be implemented through explicit grants/role assignments, never a hardcoded role-name bypass. The Django framework superuser is a separate concept. System-health and integration functions are proposed and remain permission-gated.

## 4. Effective Permission-Driven Navigation
1. The backend remains the authority for the authenticated account, account approval/active state, active services, and effective permissions. UI hiding is not security enforcement.
2. Effective access derives from assigned active roles, permitted role grants and account-level overrides. Active Deny overrides a Grant. A requested role is not an assigned role.
3. A menu link is visible only when its route/module is enabled and the account satisfies the required effective capability check. The server must independently authorize every read, write, download and export.
4. Hide an expandable parent when all its permitted child links are hidden. Do not display inaccessible widget counts, links, notifications or sensitive summaries.
5. Multiple roles produce one deduplicated navigation tree. The same module should not appear twice. No frontend role-name bypass for Admin or Super Admin.
6. A workspace switcher may offer navigation context for multi-role accounts, but changing the displayed context can never add authorization.
7. Permission changes, account deactivation and disabled services must be reflected after appropriate revalidation. Any stale navigation must fail closed at the API/route boundary.
8. Route, menu, widget and action definitions should share one capability mapping. Final permission codes and route paths must be derived from the implemented catalogue; this document deliberately does not invent them.

### 4.1 Menu lifecycle
```text
Authenticated session -> authorized capabilities -> menu registry filtering
                      -> service-state filtering -> deduplication
                      -> responsive sidebar + dashboard widgets
User opens a module -> frontend route guard -> backend permission check
```

## 5. Academic-Period and Business-Rule Boundaries
- Display the active School Year and Semester in the shared header or page context where useful, sourced from approved academic-period configuration.
- Students may be directed through semester-specific subject and clearance information collection before normal dashboard access, **only** under an approved workflow.
- CTU-G Workspace must not become the authoritative enrollment management system. CTU’s main system is the source for verified enrollment; use an approved integration or authorized verification where direct integration is unavailable.
- Organizational-fee obligations are evaluated per academic period according to approved enrollment/eligibility rules, including newcomers, transferees, paused students and returnees.
- A disabled or unfinished module should not be represented as an active, working feature in production navigation.

## 6. Responsive UI and Accessibility
| Viewport | Navigation treatment |
|---|---|
| Desktop (large) | Persistent sidebar (expand/collapse); full header, breadcrumbs and configurable content grid. |
| Tablet (medium) | Collapsible sidebar or rail; preserve active page and readable content widths. |
| Mobile (small) | Accessible menu drawer with focus trap and close behavior; clear page heading and essential shortcuts. |

Use a clean institutional appearance: forest-green accents, white/light-gray surfaces, legible typography, strong focus indicators, predictable hover/selected states, and no color-only status messages.

**Visual direction (implemented 17 November 2026, owner-approved):** the dashboard shares the public website's palette through dashboard-scoped `--db-*` tokens that alias the public tokens (`docs/design/TOKENS.md` §1.4). Three distinct appearances follow the existing theme preference: **Light** (public mint gradient, frosted light header and sidebar, forest-green accents), **System default on a dark OS** (the public forest-green gradient, green-glass header and sidebar) and **Dark** (black, black-glass header and sidebar). Data surfaces (tables, forms, financial and administrative screens) stay nearly solid; frosted glass is limited to the header, the desktop sidebar and overview cards. The welcome banner reuses the campus photo under a forest-green overlay that keeps text at AA over any crop. The mobile drawer is opaque and unblurred, and every blur falls back to a solid colour where unsupported. A colour-depth refinement (same day, owner-approved, colour only) layers each theme with understated gradients: a mint highlight and soft green corner in Light, deep-green to emerald tones in System-dark (header, deeper sidebar, emerald cards and deep panels as distinct layers), and a quiet black-to-charcoal lift in Dark, plus a soft shadow and 1px sheen on panels and cards. Layout, sizes, spacing, typography and text are unchanged. Ensure keyboard navigation, descriptive labels, contrast, screen-reader announcements, visible loading/empty/error states, and responsive tables/forms.

## 7. Navigation States and Error Handling
| Situation | Expected behavior |
|---|---|
| Pending, rejected, or inactive account | Authenticated shell unavailable unless an approved, specific limited-status experience exists; never imply approved access. |
| Module not permitted | Hide from sidebar; direct URL is blocked by route guard and backend, with a safe access-denied experience. |
| Service disabled | Remove or disable according to approved UX rule; backend rejects the operation. |
| Permission revoked during session | Refresh capabilities and remove affected links; backend continues to deny stale requests. |
| No authorized modules | Show an explanatory minimal dashboard/empty state and Support where authorized. |
| Academic-period setup outstanding | Show only approved setup/review steps and essential help, without bypassing server-side requirements. |
| Backend/network failure | Show recoverable status and retry without leaking protected records or stale sensitive widgets. |

## 8. Design Acceptance Checklist
- [ ] Exactly one shared dashboard shell is used for every application-level role.
- [ ] Role navigation groups match approved workflow catalogue entries and authorized capabilities.
- [ ] School Admin has no Access Control Management links or corresponding API access.
- [ ] Super Admin inherits School Admin operations and additionally has protected technical governance access through explicit permissions.
- [ ] No third application-level Technical Super Admin role is introduced.
- [ ] Multi-role users see deduplicated navigation; account-level Deny and inactive services are enforced.
- [ ] Direct URLs and API operations are denied when the corresponding capability is absent.
- [ ] Dashboard widgets, notifications, counts, exports and quick actions are separately permission-filtered.
- [ ] Student semester onboarding does not create independent institutional enrollment authority.
- [ ] All layouts work with keyboard, mobile, tablet and desktop; no horizontal overflow for core navigation.
- [ ] Empty, loading, access-denied, expired-session and service-disabled states are designed.
- [ ] A workflow marked only Proposed/Draft is not shown as a completed/available function.

## 9. Dependencies, Decisions Pending and Implementation Order
**Dependencies:** current System Workflow Catalogue and human approvals; approved use cases/SRS; permission catalogue and evaluator behavior; active service rules; academic-period and finance-clearance workflows; implemented frontend route map and backend endpoints.

**Open decisions:** exact route URLs and permission codes; which instructor-specific workflows are approved; what appears in production for disabled modules; semester onboarding details; notification scope; access-audit and system-health UI permissions; whether search and workspace switcher are needed initially.

**Suggested delivery sequence:** (1) shared DashboardShell, header and responsive sidebar; (2) capability-aware navigation registry and route guards; (3) School Admin and Student menus aligned to the active workflows; (4) Instructor and Treasurer modules; (5) Super Admin governance menus only after secure backend boundaries are approved; (6) end-to-end role/permission, responsive and accessibility testing.

## 10. Document Control
| Field | Value |
|---|---|
| Owner | CTU-G Workspace design/development team |
| Status | Proposal — requires human design/architecture approval |
| Version | v0.1 |
| Scope of approval | UI shell and navigation information architecture only, not new workflow privileges |
| Change policy | Revise after reconciliation; preserve the workflow catalogue and ERD as separate sources of truth |
| Revision | 17 November 2026: navigation and widget labels converted to sentence case to remove the conflict with PATTERNS.md §9 (owner instruction). No structural, permission or workflow change. |
| Revision | 17 November 2026: §6 visual direction added after the approved dashboard visual refinement (three themes aligned with the public site). No structural, permission or workflow change. |
| Revision | 17 November 2026: §6 colour-depth refinement (gradients, layered surfaces, shadow and sheen tokens). Colour only; no layout, structure, permission or workflow change. |

---
*End of design proposal.*
