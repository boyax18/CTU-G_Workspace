# Academic Settings v2.3 candidate addendum

26 November 2026. **PROPOSED; independent review OPEN; provisioning NOT AUTHORIZED.**
This is review evidence, not a protected catalogue pin or institutional approval.
The v2.0/v2.1/v2.2 manifests, source pins and validators remain authoritative and unchanged.

Base: `catalogue-v2.2`, effective digest
`192ba955d1dae06bfbdf574e52ef454390b9fd41b803f63778d1d220b6cd8c6d`;
v2.2 addendum SHA-256 `4285837e51f5331bb54fab50246c25d4efb0bbd65905a567368ba7e6681f8fdd`.
The candidate retains the existing delta envelope (`base`, `addendum`, `result`,
`operations`, `independent_review`). Its strictly enumerated new operation types are
`add_permission`, `add_default_binding` and `restate_permission_definition`; existing
validators deliberately do not accept this candidate. Only the adjacent offline validator does.

| Candidate operation | Authorization interpretation |
| --- | --- |
| Move `finance.fee_schedule.manage`: Treasurer → Admin | Fee proposal option A. Same definition, service, scope and ORD protection. Keep genuine Admin-role grant enforcement. Treasurer retains collection, receipts and financial records. |
| Add `academic.enrollment_verifications.record` → Admin | In-person official Student+semester verification and evidenced gaps only; no self-verification or Student confirmation. |
| Add `academic.semester_onboarding.self.submit` → Student | Own Draft and own atomic finalization only. Keep `academic.profile.self.read` for reads and the old clearance-request binding for its original purpose. |
| Add `academic.historical_participation.correct` → Admin | One missing Closed/Archived participation, clearance and original-fee snapshot; never edit existing history or reopen the semester. |
| Clarify `academic.courses.manage` | Includes versioned curricula; published versions immutable. No new holder. |
| Clarify `academic.periods.manage` | Includes section subject offerings; instructor assignment still uses `clearance.teaching_assignments.manage`. No new holder. |

The historical code has **provisional ORD** metadata solely to express this candidate using the
existing ORD/GOV vocabulary. Whether stronger protected handling and a second, distinct School
Admin reviewer are required remains an owner/security decision. Do not infer GOV provisioning or
two-person enforcement from this file. Keep historical correction off until resolved.

No Admin `access_control.*` default, no Technical Super Admin business default, no Treasurer write
expansion, no new role, delegation, account override or service. Technical Super Admin business
authority still requires a genuine stored Admin assignment and valid context. All three new
permissions remain planned (`P`); inclusion in a static candidate confers no runtime authority.

## Deny transition contract

| New exact code | Any active account Deny on these old codes must still block it |
| --- | --- |
| `academic.enrollment_verifications.record` | `academic.profiles.manage` |
| `academic.semester_onboarding.self.submit` | `clearance.requests.self.submit` |
| `academic.historical_participation.correct` | `academic.periods.manage`, `academic.profiles.manage` |

The proposed runtime patch applies this narrowing in the effective resolver, including session
permission hints and locked operation rechecks. This is **Deny-only compatibility**, never an
Allow alias. Denies remain account-wide even if a Grant has a role scope, the old service is
inactive, or another role is selected. New-code Denies retain ordinary precedence too. Query
failure still returns no effective permissions. Existing Deny rows are never removed or changed.

After a separately authorized inventory, independently review each required additional new-code
Deny and any conflicting new-code Grant. An existing Grant cannot be overwritten blindly to
mirror a Deny because `(account, permission)` is unique. Keep the old Deny and compatibility
guard during rollout **and rollback**. No data migration is included here. Never copy broad old
account Grants automatically to replacement codes; review recipient, purpose, selected-role scope,
eligibility and separation of duties individually. A role-default addition itself expands authority
for role holders who previously had only direct Grants or lacked the broad default: inventory it.

## Approval gates

Review the consolidated governance proposal and fee proposal, the actual read-only impact report,
the complete patch and isolated results. Resolve fee-after-obligation policy, historical review and
protection, and FR-CLR-02 signatory evidence. Independent pin approval, reviewed provisioning,
database migration authorization and per-feature launcher-mode approval are separate steps.
Candidate checksums are integrity evidence authored by the implementer, **not** independent approval.

The patch does not add a v2.3 installer, invoke any protected executor, approve any launcher mode,
change any switch, or alter a pinned validator. Installation needs a separately reviewed v2.3
validator/provisioning contract; the current v2.2 planner must continue refusing these operations.
