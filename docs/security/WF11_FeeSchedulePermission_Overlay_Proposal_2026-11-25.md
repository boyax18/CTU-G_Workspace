# Proposal: post-v2.2 overlay for `finance.fee_schedule.manage` (semester organizational fee)

**Status:** PROPOSAL ONLY. Not installed, not reviewed and not provisioned. The pinned v2.0, v2.1 and
v2.2 manifests, validators, digests and default bindings are unchanged. Nothing in this document
grants any account or role a permission.

**Date:** 25 November 2026 · **Source decisions:** WF11 R-01 (`docs/workflows/WF11_Reconciliation_2026-11-25/WF11_Approved_Documentation_Reconciliation_Record.md`), security readiness review §1 (`WF11_PreImplementation_Security_Readiness_Review_2026-11-25.md`).

## 1. The conflict

| Item | Pinned state (v2.0 → v2.1 → v2.2) | Approved business rule (R-01) |
| --- | --- | --- |
| `finance.fee_schedule.manage` default role | **Treasurer** only (v2.1/v2.2 do not touch it) | **School Admin** configures and approves the full semester organizational fee |
| Definition | "Maintain period fee amounts under approved rules; do not rewrite amounts used by historical payments." Service `finance`, scope `FINANCE`, protection `ORD` | Treasurer keeps cash collection, receipts and payment records |

The v2.2 delta's `independent_review.status` is still `OPEN`.

## 2. How the code behaves today (no overlay)

`apps.finance.fees` authorizes every fee operation with the existing HDAC evaluator and one narrowing
rule (`services.authorize(..., admin_role_grant=True)`): the exact code must reach the account
**through an active grant of one of its genuine Admin roles**. It also requires the selected Admin
context, active academic and finance services, and account-specific Deny precedence.

Consequences under the pinned catalogue:
- School Admin is refused (no Admin binding exists).
- Treasurer is refused (no Admin assignment).
- A dual Treasurer+Admin account is refused even with role context off, because the code reaches it
  only through the Treasurer role.
- A direct account Grant alone is refused.

So **no account can configure or approve a semester fee at runtime until a reviewed overlay exists**,
and semester activation keeps failing closed on `approved_fee`. Isolated tests prove the success path
with an explicit, throwaway-database-only Admin binding.

## 3. Breadth review

- The `finance` service covers organization fee schedules, payments, receipts, funds, expenses and
  exemptions. Each of these, except the fee schedule, has its own separate code
  (`finance.payments.*`, `finance.receipts.issue`, `finance.funds.record`, `finance.expenses.record`,
  `finance.exemptions.manage`).
- `finance.fee_schedule.manage` maintains **period fee amounts**. The only period fee the system models
  is the semester organizational fee (`finance_semester_fee_*` tables), so its present meaning matches
  R-01.
- **Risk:** if a future slice adds other period fee types (for example, a separate event fee), this
  code would silently extend School Admin authority to them. The future slice must then introduce a
  narrower code rather than reuse this one.

## 4. Proposed overlay (to be reviewed; not executed)

**Option A (recommended, consistent with the readiness review).** A versioned `v2_3_delta.json`
containing only:
1. Remove the default binding `Treasurer → finance.fee_schedule.manage`.
2. Add the default binding `Admin → finance.fee_schedule.manage`.

Keep the exact code, its definition, service, scope and `ORD` protection. Keep every other binding.

**Option B (if reviewers judge the code too broad).** Add a narrow code such as
`finance.semester_fee.manage` bound to Admin, and leave `finance.fee_schedule.manage` unchanged. This
needs a one-line code change in `apps/finance/fees.py` (`PERMISSION_CODE`) plus its tests.

**Preserved in both options:**
- Every account-specific Grant and Deny row; a Deny still overrides.
- Selected-role context behaviour: Treasurer context never authorizes fee setting.
- Treasurer keeps `finance.fee_schedule.read` and all payment, receipt, fund, expense and ledger codes.
- Admin gains no `access_control.*` default.
- The v2.0, v2.1 and v2.2 files and digests.

## 5. Potentially affected holders

- **Static (catalogue):** the Treasurer role default binding (1 row).
- **Live `ctug_workspace`:** not inventoried. No connection was made. Before review, run a read-only
  inventory of:
  - `role_permissions` rows for the code: role, `is_active`, granted_by.
  - `account_permissions` Grant/Deny rows for the code: account, effect, `is_active`, and any role scope.
  - Accounts holding both Treasurer and Admin assignments.

  Report counts only; do not include personal data.
- **Runtime callers:** only `apps.finance.fees` checks this code. No other endpoint relies on the
  Treasurer binding.

## 6. Steps still required (none are authorized by this document)

1. Independent security and governance review of the breadth (§3) and of Option A vs B.
2. Read-only live inventory (§5) and an impact note.
3. Author the overlay JSON, extend the validator chain (v2.3), pin its digest and add tests.
4. Separately authorized provisioning on `ctug_workspace`, after the finance `0001` and `0002` migrations
   have been separately approved and applied.
5. Separate owner decisions to turn on `WORKSPACE_SEMESTER_FEE_CONFIGURATION_ENABLED` and
   `WORKSPACE_SEMESTER_FEE_APPROVAL_ENABLED` for a launcher mode.

## 7. Update, 26 November 2026 (no change to the recommendation)

- **Consolidated package:** this proposal is item A of
  `WF11_AcademicSettings_Permission_Governance_Proposal_2026-11-26.md`. That package also covers the
  verification, onboarding, curriculum/offering and historical-correction codes, so all of them can be
  reviewed in one `v2_3_delta.json`.
- **Obligations now exist:** `finance.0002_fee_obligation` adds the WF-07.02 obligation snapshot, created
  only by onboarding finalization or the evidenced WF11-D14 correction. The approval impact is now a real
  count. Once any Student obligation exists, approving a new rate is refused (`obligations_assessed`)
  until a separately approved financial adjustment workflow exists. Existing amounts are never
  rewritten, deleted or split between earlier and later Students. **This rule needs owner
  confirmation.**
- **Super Admin:** fee authority reaches a Technical Super Admin only through a genuine Admin assignment
  (`test_technical_super_admin_only_through_a_genuine_admin_assignment`). This is unchanged by Option A or B.

## 8. Authorized inventory connection preflight, 26 November 2026

Starting at `10e3fe8`, the owner approved read-only inspection, but no usable verified SELECT-only
connection was found in the available configurations/login profiles. Root was not used, no
database connection was attempted, and actual fee-code binding, Allow/Deny, holder and access-loss
counts remain **unknown**. See the [preflight evidence](WF11_Permission_Inventory_Preflight_2026-11-26.md)
and [unexecuted dedicated-reader proposal](WF11_Permission_Inventory_Reader_Setup_2026-11-26.md).
This records no fee overlay approval, provisioning, credential change or independent review.

The subsequent authorized reduced inventory found no `finance` service row and no
`finance.fee_schedule.manage` definition, stored role binding, Allow, Deny or holder. The
Treasurer default in the pinned catalogue has no live holder in this snapshot. There are
two potential Admin recipients after separate baseline and fee provisioning, including one
with a genuine Admin assignment alongside Technical Super Admin. Fee authority would still
require the Admin role grant and the workflow's runtime checks. Independent review remains open.
[Reduced inventory results](WF11_Permission_Inventory_Preflight_2026-11-26.md#catalogue-comparison-and-potential-impact).

