# Permission Catalogue v2.1 → v2.2 → v2.3: sequential independent review handoff

**Prepared:** 27 November 2026 on `ronald` by the implementing agent (Claude Opus 5.5, Claude Code). It
co-authored the v2.3 candidate and the WF-11 work, so it **cannot approve** any of the three catalogues.
Nothing here is a review decision.

**Status:** v2.1, v2.2 and v2.3 independent review are all **OPEN**. Nothing from v2.3 is installed or
provisioned, and every v2.3-dependent switch is off.

This handoff reuses the existing review evidence; it does not restart any review. Approve strictly in
order. A rejection stops the later steps.

## 1. Order and existing evidence

| Step | Candidate | Existing evidence to use | Requires |
| --- | --- | --- | --- |
| 1 | v2.1 pin chain: `14125f9` (D-89) and the F-1 validator correction `9e259e7` | [D-89 review package](WF-03.01_D-89_CATALOGUE_V2_1_INTEGRITY_REVIEW_PACKAGE.md) §§1–7, 14 and the §19 handoff; [D-101 technical pre-review](WF-03.01_D-101_TECHNICAL_PRE_REVIEW.md) F-1 to F-7; [D-101 handoff](WF0301_D101_D102_INDEPENDENT_HANDOFF_2026-11-20.md) §§2–3 | — |
| 2 | v2.2: `28d46e1` (D-103) | The same package, §§8–15 and §19 | v2.1 approved |
| 3 | v2.3 candidate: [review package](../../review_only/academic_settings_v2_3/README.md) | §3 below, the [governance proposal](WF11_AcademicSettings_Permission_Governance_Proposal_2026-11-26.md), the [fee overlay proposal](WF11_FeeSchedulePermission_Overlay_Proposal_2026-11-25.md) and the [inventory preflight](WF11_Permission_Inventory_Preflight_2026-11-26.md) | v2.2 approved |

The reviewer must be independent of the implementation and hold no stake in the change (package §14,
item 1). No proxy or author-side signatures.

## 2. v2.1 and v2.2: currency of the existing evidence

- **Pinned bytes are unchanged.** The existing static helper reports 19/19 artifacts byte-identical to
  their scoped commits at the current HEAD:
  `backend\.venv\Scripts\python.exe docs\security\reviewer_tools\wf0301_d101_static_integrity.py --repo .`.
  The §19 scope therefore applies without change.
- **The evaluator changed since the §19 handoff.** The runtime tests run through it, so rerun them at
  the reviewed commit rather than relying on old counts. The relevant commits are `2549e01`, `cb8b56a`,
  `e3334f5`, `5428c08` and `6749218`; none changes a pinned file.
- **Reviewer tasks are unchanged:** package §19.5 and D-101 handoff §3. Complete §7 for v2.1, then §15
  for v2.2, using the §14 checklist.

## 3. v2.3: what you are asked to approve

| Item | Value |
| --- | --- |
| Delta `review_only/academic_settings_v2_3/v2_3_delta.json` | SHA-256 `4aef40877a90c7e9b6ec8b2560402be0acf3435ff524881260100ecf98204640` |
| Addendum `review_only/academic_settings_v2_3/ADDENDUM_PROPOSED.md` | SHA-256 `e9c3d4f094a465cf946c7ab89167b84a367a9d122957c71a7f130914a315e552` |
| Runtime patch `review_only/academic_settings_v2_3/runtime_changes_PROPOSED.patch` | SHA-256 `13782a2588187f703d9e080f2cd29e52b0c249d860623b8b660eb644e26b54f2` |
| Base | catalogue v2.2, effective digest `192ba955d1dae06bfbdf574e52ef454390b9fd41b803f63778d1d220b6cd8c6d` |

The three files above are `-text`, so their bytes survive a Windows checkout.

**Operations** (addendum table):
- move `finance.fee_schedule.manage` from Treasurer to Admin;
- add `academic.enrollment_verifications.record` → Admin, `academic.semester_onboarding.self.submit` →
  Student and `academic.historical_participation.correct` → Admin;
- restate the `academic.courses.manage` and `academic.periods.manage` definitions.

**How the 26 November pre-review blockers (non-independent) were addressed:**

| Pre-review item | Resolution |
| --- | --- |
| Historical correction lacked dual control and a decided protection level | **Owner decision, 27 Nov 2026:** two different School Admins are required. Runtime enforcement is active source code in `a60e048` (switch still off), with tests. The addendum proposes **`ORD`**: in this catalogue `GOV` is namespace protection for `accounts` and `access_control` only. |
| Base v2.1/v2.2 not independently approved | This handoff. The installable validator also requires one sign-off record approving all three (§4). |
| Six candidate-copy test errors (outdated fixtures and the pre-activation guard) | Corrected in the patch: the fixtures bind the v2.3 codes, and the guard is inverted (the old broad codes authorize nothing). No assertion was removed or weakened. |
| No v2.3 installer, no `finance` service, Phase 1 verifier incompatible | The patch adds `catalogue/validation_v2_3.py` and `provision_academic_settings_v2_3_local_dev` with tests. Phase 1 accepts a restated definition only with its exact v2.3 receipt. |

The patched command provisions:
- the `finance` service;
- the two pinned v2.2 definitions `finance.fee_schedule.manage` and `academic.profile.self.read`
  (Student, for onboarding reads), alongside the v2.3 operations.

It never creates a Treasurer fee binding or an account Grant, and it preserves every Deny.

**Signatories:** they follow the existing approved decisions (owner instruction, 26 November 2026).
Onboarding finalization creates only the WF-06.02 step 4 Pending requirements, and adviser or
fixed-signatory signing stays outside this delivery.

**Reproduce from the repository root** (disposable databases only; never `ctug_workspace`):

```powershell
backend\.venv\Scripts\python.exe review_only\academic_settings_v2_3\proposal.py
backend\.venv\Scripts\python.exe -m unittest discover -s review_only/academic_settings_v2_3 -p test_preparation.py -v
git apply --check review_only\academic_settings_v2_3\runtime_changes_PROPOSED.patch
cd review_only\academic_settings_v2_3
..\..\backend\.venv\Scripts\python.exe run_isolated_tests.py --candidate candidate_runtime_tests apps.access_control.test_academic_v2_3_provisioning apps.access_control.test_academic_phase1_provisioning apps.access_control.test_academic_phase2_provisioning apps.academic.test_student_dashboard_boundary apps.academic.test_wf1101_residual
..\..\backend\.venv\Scripts\python.exe run_isolated_tests.py --candidate -t . apps/access_control apps/academic apps/finance apps/clearance
..\..\backend\.venv\Scripts\python.exe verify_candidate_frontend.py
```

**Checklist:**

| # | Check | v2.3 |
| --- | --- | --- |
| 1 | Reviewer is not the implementation author and holds no stake in the change | ☐ |
| 2 | v2.1 and then v2.2 were approved first (§2) | ☐ |
| 3 | The three SHA-256 values above recomputed at the reviewed commit; the delta and addendum equal the `validation_v2_3.py` pins inside the patch | ☐ |
| 4 | Addendum read in full; it states only the operations above | ☐ |
| 5 | Offline validator and preparation tests reproduce | ☐ |
| 6 | Full patch reviewed, in particular: <br>• the Deny-only transition guard at the resolver's single return point; <br>• the narrow codes; <br>• the approval gate; <br>• the provisioning scope (no Treasurer fee binding, no Grants, Denies preserved, restatements receipted) | ☐ |
| 7 | Candidate and patched-copy regression tests reproduce on disposable MySQL | ☐ |
| 8 | The historical dual control in `a60e048` refuses the recording Admin, including under the evidence lock | ☐ |
| 9 | No live database, launcher mode or switch change is implied by approval | ☐ |

## 4. Sign-off record (created by the reviewer, never by the author)

`validation_v2_3.require_independent_approval()` reads this record. It must:
- be a new Markdown file under `docs/security/`;
- contain both v2.3 SHA-256 values above;
- contain these three exact lines: `v2.1 decision: APPROVED`, `v2.2 decision: APPROVED` and
  `v2.3 decision: APPROVED`.

The template below uses placeholders, so it cannot satisfy that check.

```text
Reviewer name and role:
Independence from the implementation confirmed (yes/no):
Commit reviewed:
v2.1 decision: <APPROVED or REJECTED>   date:   findings:
v2.2 decision: <APPROVED or REJECTED>   date:   findings:
v2.3 delta SHA-256: 4aef40877a90c7e9b6ec8b2560402be0acf3435ff524881260100ecf98204640
v2.3 addendum SHA-256: e9c3d4f094a465cf946c7ab89167b84a367a9d122957c71a7f130914a315e552
v2.3 decision: <APPROVED or REJECTED>   date:   findings:
Evidence reproduced (commands and results):
```

## 5. After a genuine approval (not before)

1. **Record the decisions.** The owner reconciles D-101 in the decision register and records the v2.3
   decision.
2. **Apply the patch.** A separately authorized commit applies it and sets
   `validation_v2_3.INDEPENDENT_APPROVAL` to the record's path and the two pins. Then rerun the §3
   tests.
3. **Provision (previously authorized), with the established backup and restore-verification
   safeguard.** Run `provision_academic_settings_v2_3_local_dev` phases `metadata` → `restate` →
   `bindings` → `activate` → `verify`, each with its exact `ctug_workspace:WF-11.01:V2.3:<PHASE>`
   confirmation and actor account 3. Then verify phases 1 and 2.
   - Expected post-check changes: `services` +1, `permissions` +5 (plus the two restated
     descriptions), `role_permissions` +5 and `access_audit_logs` +19. Nothing else may change.
4. **Activate locally.** Use per-feature `local` launcher-mode approvals for semester lifecycle, fee
   configuration and approval, verification, onboarding with finalization, and historical correction.
   The owner then runs the interactive acceptance cases.
