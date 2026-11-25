# CTU-G Workspace — WF-11 pre-implementation security readiness review

**Date:** 25 November 2026 (Asia/Manila)  
**Disposition:** **READY FOR RESTRICTED DEVELOPMENT of WF-11.01 academic-period foundation; NOT approved for activation or production release.**  
**Evidence base:** User-supplied `CTU-G Workspace - Copy(3).zip` (archived source code and v0.3.50 catalogue), consolidated catalogue v0.3.53 and proposed SRS v0.4 from the approved reconciliation package, and the user's report of documentation-only Git commit `18d4b01`. No live branch/database/deployment connection was available for direct inspection.  
**Authority boundary:** R-01/R-02/R-03 were approved **as documentation targets only**. All individual workflow Human Approval fields stay unchecked. This review neither replaces an independent security review nor grants institutional permission to process CTU records.

## 1. HDAC technical impact review — finding and disposition

**Static validation:** The original `backend/apps/access_control/catalogue/validation_v2_2.py` validator was run on the archived, unchanged pinned v2.0 → v2.1 → v2.2 chain. **PASS**, effective digest `192ba955d1dae06bfbdf574e52ef454390b9fd41b803f63778d1d220b6cd8c6d`. It returned 95 permissions, 106 default bindings, 32 Admin defaults, 13 Technical Super Admin defaults, and zero Admin `access_control.*` defaults. This is **static specification validation**, not evidence of the current database's provisioned permissions.

| Permission | Actual effective v2.2 default | Decision |
| --- | --- | --- |
| `academic.periods.manage` | `Admin` | Retain; require effective permission, genuine selected Admin context, authorized school scope and audit. |
| `academic.profiles.manage` | `Admin` | Existing possible operational basis for academic-record management; **do not assume** this alone authorizes CTU enrollment proof verification until action/object policy is formally accepted. |
| `finance.fee_schedule.manage` | `Treasurer` | **Mismatch.** Owner-approved target is School Admin for the full semester organization fee amount. Do not enable the fee-amount write endpoint with today's default binding. |

**Proposed future change (not executed):** A separately reviewed and pinned post-v2.2 overlay moving only the `finance.fee_schedule.manage` default from Treasurer to Admin is supported by the v2.0 definition, which describes the **organization fee schedule**. Preserve the exact permission code, protection (`ORD`), finance service and all unrelated role bindings. If a future implementation expands that code to broader fee types, stop and seek a more narrowly scoped permission instead.

**Mandatory authorization conditions for fee writes:** approved/active account, real eligible Admin role assignment, selected Admin role context, active Finance service, exact effective permission, account-specific **Deny precedence**, scoped semester/campus, safe fee-edit status and prior-obligation impact checks, transactionally reliable audit of actor/reason/old/new values. No `is_superuser`, UI visibility, account-Grant, or Super Admin label bypass. A dual-role Treasurer/Admin must explicitly act in authorized Admin context. Treasurer keeps independent cash payment/receipt abilities.

**Security constraints of the existing implementation:** `backend/apps/access_control/services.py` implements a fail-closed permission query with effective direct Deny precedence and selected-role restrictions **when configured**, plus ordinary-appointment checks behind a separate runtime gate. `backend/config/settings.py` confirms active-role context depends on explicit settings. Consequently, test both enabled and disabled configurations and do not treat the static manifest as proof of operational readiness. Current account-level overrides, existing direct Grants/Denies and live role permissions were **not inventoried** because no connection to `ctug_workspace` was made.

**Separate outstanding governance:** The original v2.2 delta itself has `independent_review.status = OPEN`. A new fee-binding overlay needs owner/reviewer approval, read-only live-grant impact inventory, validator/pins, and separately authorized provisioning/migration. Neither existing pinned metadata nor account Denies may be rewritten as part of WF-11 development.

## 2. CTU verification and privacy impact review

**Accepted requirements-level design:**

- CTU's official enrollment system remains authoritative. A Student's self-confirmed subjects or a configured curriculum are **not** institutional enrollment proof.
- **Verified lane:** a current, student-specific and semester-specific CTU enrollment/subject verification already exists, matches course/year/subjects and assigned classes, and is still valid. Following explicit final Student confirmation, WF-05.05 may finalize immediately without routine School Admin approval.
- **Manual lane:** with no sufficient proof, retain Draft/Pending Verification. Student personally shows the appropriate official academic record to School Admin; a legitimately authorized School Admin verifies and records an auditable determination. The Student returns to final confirmation; no clearance/fee/participation is created beforehand.
- A returning student's non-enrollment gap needs its **own verified historical determination**. Permitting onboarding does not complete old signatures, mark historical clearance Cleared, or erase outstanding fee balances. Missing Workspace records are not evidence of non-enrollment.
- Account approval evidence alone (such as an attestation made at original registration) is **not automatically evidence** for a later semester's subject enrollment.

**Minimum evidence-record contract:** student/account identity + CTU-G ID match; school/campus, school year and semester; enrollment finding; verified subject identifiers/course/year/sections/instructor matches; official source/type and controlled reference; verifier identity or approved integration attribution; checked-at and source-as-of timestamps; reason/outcome; audit reference; restricted read scope; status invalidation on contradiction or revoked evidence. Do not put private documents or unrestricted scans in general logs, audit text, or student/treasurer lists.

**Not yet evidenced/authorized:** a campus-approved evidence source or direct CTU data feed; official acceptance/freshness/revocation policy; retention and privacy authorization; exact School Admin operational verifier permission and object policy. The uploaded repository alone cannot certify these institutional decisions. A test-only synthetic evidence adapter is acceptable for inactive local development; it must fail closed outside explicitly isolated tests and never be represented as real CTU verification.

## 3. Additional dependent-workflow security consequences

- The v2.0 catalogue still includes Student default `clearance.requests.self.submit`, while the approved WF-05.05→WF-06 flow now creates clearance **automatically once**, at verified onboarding completion. Existing manual request paths must not create duplicates or bypass prerequisite verification. Treat this as an explicit endpoint-contract review, not permission deletion by assumption.
- No current `backend/apps/academic`, `backend/apps/finance`, or `backend/apps/clearance` model implementation was found beyond Django stubs in this uploaded snapshot. The semester-participation, evidence, subject, clearance, signatory, fee-snapshot and audit schema must be separately designed, approved and tested.
- The consolidated catalogue retains individual WF-11.01 and WF-05.05 **Human Approval unchecked**, and their workflow checklists still mark Reconcile unchecked even though the *documents* were reconciled. Do not silently mark these workflow steps approved/tested.
- The consolidated SRS is still **proposed**; full formal stakeholder/security/institution sign-off is not established by the WF-11 document-target approval.

## 4. Concrete next implementation slice — WF-11.01 foundation

**Can start once the owner explicitly authorizes that individual implementation scope:**

1. Inspect current `ronald` branch, status and database migrations. Avoid overwriting uncommitted work; do not create a deployment folder.
2. Implement `SchoolYear` and `Semester` data entities with unique period identifiers, exactly two Draft semesters when a School Year is created, derived School Year status, validated chronological dates, and appropriate history-safe foreign keys.
3. Implement permission-gated School Admin read/create/update of Draft periods in the **existing academic service**, with genuine selected Admin context, Deny precedence, school/campus scope and transactional audit. Keep newly introduced HTTP/UI functionality disabled by default pending review and approval.
4. Design safe one-Active-semester enforcement using database-backed concurrency guards/locks and an atomic transition. Implement and exercise it in isolated tests, but do not activate the live transition flow until approved fee/offerings preconditions can be enforced.
5. Preserve Closed/Archived history and Draft-only deletion restrictions; prevent period activation from automatically creating Student participation, clearance or fee records.
6. Add model/API/HDAC/concurrency tests on **isolated databases** and focused frontend tests. Do not change `ctug_workspace`, pinned v2.0/v2.1/v2.2, provision live role grants, turn on gates or push commits without the appropriate separate authorization.
7. Complete the workflow's own Inspect → Reconcile → Approve → Implement → Test → Commit record using real outcomes, without borrowing approval from planning R-01/R-02/R-03.

**Defer activation/use of these dependent capabilities:** School Admin semester fee write pending HDAC governance, Student enrollment evidence verification pending campus source/privacy policy, WF-05.05 atomic onboarding pending schema and workflow approvals, and dependent clearance/fee endpoints pending testable idempotence and audit contracts.

## 5. Go / no-go disposition

| Activity | Disposition |
| --- | --- |
| Read-only static HDAC impact review | **COMPLETE** — pinned v2.2 validator passes and fee-owner mismatch is specifically identified |
| Requirements-level CTU evidence contract review | **COMPLETE** — two-lane verification rules and missing authorizations clearly identified |
| Begin development of inactive WF-11.01 academic-period foundation | **CONDITIONALLY READY** — after owner scope approval; tests on isolated DB only |
| Assign fee-manage default to Admin in live HDAC | **NOT AUTHORIZED** — independent review, inventory, versioned overlay, provisioning approval needed |
| Treat enrollment evidence as campus-approved/live | **NOT AUTHORIZED** — institution/privacy and evidence source contract needed |
| Enable WF-11.01 activation or WF-05.05 onboarding in live system | **NOT READY** — individual Human Approval, verified preconditions, authorization, database and regression evidence needed |

**Changes performed by this review:** None to the user's repository, database, permissions, records or original documents. Only this standalone evidence-based review report was generated in the assistant's workspace.
