# CTU-G Workspace — WF-11 Approved Documentation Reconciliation Record

**Date:** 25 November 2026 (Asia/Manila)  
**Source:** Uploaded project Workflow Catalogue v0.3.50 + SRS v0.4; Stage 1 draft v0.3.51; Stage 2 review v0.3.52 + SRS amendment proposal; Stage 3 approval memo.  
**Owner authorization:** The project owner expressly approved **R-01, R-02, R-03 as documentation targets only** in this conversation.  
**Change scope:** Documentation-only. No project repository, HDAC permission manifests, DB schema or app code changed.

## Reconciled documentation targets

| Decision | Approved target | Remaining separate gate |
| --- | --- | --- |
| R-01 | School Admin configures full semester organizational-fee amount; Treasurer collects cash and performs permitted financial operations | Existing `finance.fee_schedule.manage` Treasurer default in pinned v2.2 **not** changed. Independent scope/impact review and separately approved versioned catalogue overlay, with explicit Deny/selected-role/object checks |
| R-02 | Verified, current Student+semester-specific official CTU enrollment/subject evidence permits immediate completion after Student confirmation; otherwise Pending Verification and in-person School Admin evidence review, then Student final confirmation | Official accepted proof types/source, permission, evidence freshness, privacy/retention and secure audit still require institutional/technical authorization |
| R-03 | WF-05.05 — Complete Student Semester Onboarding — Semester Academic Information Setup; WF-05 category count 4 → 5 | Individual WF-05.05 Human Approval remains **unchecked**, and implementation/security/schema gates still apply |

## Documents consolidated

1. **Full Workflow Catalogue v0.3.53**: Based on Stage 2 v0.3.52, aligned header/version/document-control/changelog, WF-05 category and register; registered full existing-style WF-05.05 detailed specification; updated specific WF-05/06/07/11 references and the R-01/R-02/R-03 boundary.
2. **Full proposed SRS v0.4 consolidated copy**: Preserved existing requirement IDs, incorporated WF-05.05 nomenclature and count, updated approval disposition, clarified what stays pending under open decisions OD-15–18. **Formal SRS review signature remains Pending**.
3. **Review-only diff patches**: Show precisely what changed relative to the earlier Stage 2 documents. **Do not blindly apply to original project v0.3.50 files**.

## Approved workflow behavior preserved

- WF11-D01–D25 stakeholder planning baseline; D20/D21 explicitly skipped.
- Manually activated/closed periods, one Active campus semester, warned closures/archives, audited historical corrections without reopening.
- Continuing Students with uncleared previous adjacent semester are blocked from new Student onboarding; verified returning-Student non-enrollment gaps permit new onboarding without clearing old signatures. Old status remains **Uncleared** and debts remain recorded.
- Student onboarding: Regular/Irregular → subjects → course/year → explicit final confirmation. In-person School Admin missing-subject correction, no online correction request and no post-completion subject-edit feature.
- Onboarding creates one Student+semester participation, subject links, clearance/signatories and full snapshotted fee obligation **atomically and idempotently** only after adequate CTU-specific verification.
- HDAC: real selected Admin-role permission, active service, account-specific Deny precedence, record scope, auditable privileged writes; no School Admin Access Control Management authority and no blanket Super Admin bypass.

## No accidental approval or implementation

- Planning/R-01–03 documentation approvals are **not** individual `Human Approval` sign-offs.
- Protected HDAC v2/v2.1/v2.2 pins remain unchanged; no effective default role grants, account permissions or overrides changed.
- Pending institutional proof/retention and any fee-schedule code scope ambiguity must be addressed in separate approval processes.
- Other workflow titles/IDs and the Group Rating unassigned subflows were not redefined.
- No code compilation, integration tests, migrations or database access were carried out by this documentation-only change.

## Review points for downstream work

1. Confirm official CTU evidence acceptance, authorized verifier, minimal retained reference and proof validity/freshness/revocation.
2. Independently review `finance.fee_schedule.manage` breadth and affected grants/Denies before even proposing the exact future pinned overlay; consider a narrower new permission if necessary.
3. Inspect the future actual schema/constraints and backend source for period + participation + clearance/signatories + fee snapshot atomic/unique creation.
4. Seek the individual Human Approval for WF-05.05, WF-05.04, WF-11.01, WF-06/07 affected subflows, and separately required specification/security sign-offs; do not infer approval from this consolidation.

### Source hygiene observation

The Stage 2 source catalogue's **historical Appendix C Workflow ID mapping** contains several apparently malformed older rows (for example, `WF-05.04` mapping displays a register-style row, rather than a three-column historical ID mapping). This predates this consolidation and is intentionally **left unchanged** to avoid an unrelated historical rewrite. Schedule a separate minimal source-integrity correction with its own evidence if desired.
