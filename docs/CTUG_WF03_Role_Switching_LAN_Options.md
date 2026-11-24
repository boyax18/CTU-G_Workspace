# CTU-G Workspace — WF-03.01 Role Switching over LAN

**Document type:** Development decision and implementation guidance  
**Scope:** Active-role switching for authorized multi-role accounts  
**Current decision:** **Option A — Controlled LAN development testing (recommended now)**  
**Future target:** **Option B — Secure LAN deployment**  
**Status:** Option A implemented (fail-closed gate) and started by `Start-CTUG-LAN.ps1` (24 Nov 2026); this document does not authorize protected governance activation

## 1. Background and current issue

WF-03.01's **Active Role** selector was verified on localhost: the selector appeared; Admin ↔ Instructor navigation changed correctly; School Admin did not obtain Technical Super Admin governance access; and protected permission mutations stayed unavailable (4/4 local browser acceptance checks passed).

The existing development activation requires:

```text
CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK=LOCAL_ONLY_WF0301_D116
```

That acknowledgment is intentionally coupled to a **localhost-only** `ALLOWED_HOSTS` policy. Adding LAN IPs (for example `192.168.100.46`) violates that policy when the acknowledgment is set. Removing the acknowledgment allows ordinary LAN hosting to be configured, but disables the role-context feature, so the selector disappears. The user's role assignments are not deleted.

**Important:** Django's `ALLOWED_HOSTS` and the role-context activation gate are separate checks. Adding an IP to `WORKSPACE_ALLOWED_HOSTS` may fix a `DisallowedHost` error, but it **does not** enable LAN role switching.

## 2. Decision summary

| Area | Option A — Controlled LAN development | Option B — Secure LAN deployment |
|---|---|---|
| Purpose | Finish internal WF-03 demonstration and test on trusted local devices | Support real institutional users on a managed campus network |
| Transport | HTTP permitted **only for isolated test data and test accounts** | HTTPS required end to end from browser to controlled proxy |
| Role context | New explicit **development-only trusted-LAN** gate | Separate hardened deployment activation policy |
| Django debug | Development mode only | `DEBUG=False` |
| Credentials and data | Synthetic accounts; do not enter real student/staff credentials or applicant personal information | Real data only after security, privacy, and operational approval |
| Permissions | Existing role eligibility and effective-permission checks retained | Same, with deployment security validation |
| Protected governance writes | Disabled; no bypass | Remain disabled until separately authorized and verified |
| Network exposure | Specific trusted private LAN, firewall-restricted | Managed network, trusted proxy, firewall segmentation |
| Status | **Recommended next step; not yet implemented** | Deferred; required before real deployment |

## 3. Option A — Controlled LAN development (recommended now)

### 3.1 Goal

Allow a signed-in, **test** account with multiple eligible roles to switch between its assigned roles from the development PC or another explicitly approved device on the same trusted LAN, **without** opening the protected WF-03 management executor or relaxing authorization.

### 3.2 Required implementation

1. **Introduce a distinct LAN test opt-in.** Keep `LOCAL_ONLY_WF0301_D116` as-is. Add a separate, clearly named, default-off development-only role-context activation path. Do not reinterpret the localhost acknowledgment to mean LAN access.
2. **Restrict the scope.** Require development settings, an approved local database, an explicit allowlist of private LAN hosts, and a narrowly defined firewall/network policy. Reject wildcard/public hosts and unexpected configuration combinations. `ALLOWED_HOSTS` is not itself an authentication or network-isolation control.
3. **Preserve the role/context authorization model.** Continue to require authenticated, approved, active accounts; validate active account-role assignments on each relevant request; enforce the selected role's effective permissions server-side; reject revoked or unauthorized roles.
4. **Preserve CSRF/session protection.** Keep CSRF checks and session cookies. Configure permitted origins and cookie behavior for the chosen LAN URL; validate this in a real browser. Do **not** disable CSRF or weaken cookie flags merely to make the UI appear.
5. **Maintain protected-operation isolation.** Keep Technical Super Admin governance mutations and protected executor endpoints closed in the normal LAN development profile. Do not migrate, provision S0, grant privileges, or activate fences just for the demonstration.
6. **Use the existing frontend.** The Active Role selector should appear only when the backend confirms enabled role context and returns more than one eligible role; navigation must be derived from the selected role's server-authorized permissions.
7. **Add focused automated tests.** Cover default-off behavior; allowed versus disallowed LAN host; invalid opt-in; unauthorized roles; revoked roles; CSRF failures; disabled governance endpoints; and preservation of the existing localhost mode.

### 3.3 Required safety rules

- Use **only synthetic test accounts, test passwords, and non-sensitive test applications** while HTTP is in use. LAN HTTP can expose passwords, sessions, and personal data to others able to observe the network; a trusted Wi-Fi label does not provide encryption.
- Do not enroll real applicants, use production credentials, or process actual student/staff records over HTTP LAN. If real users or genuine personal information are needed, **stop and implement Option B first**.
- Restrict access to explicitly trusted devices on an isolated private network; do not expose Vite/Django through router port forwarding, public DNS, or an internet tunnel.
- Keep the Django backend on loopback behind the frontend's local API proxy where feasible. Apply narrow firewall rules to the frontend and ensure the PC's LAN IP is current.
- Do not change protected executor authorization, migration status, or database privilege boundaries as part of this work.

### 3.4 Acceptance criteria (must all pass)

- [ ] Same trusted LAN device can open the development frontend and log in with a **test** account.
- [ ] Backend reports enabled role context only when the explicit LAN test gate is valid.
- [ ] Multi-role test account sees the **Active Role** selector; single-role account does not.
- [ ] Admin ↔ Instructor switching changes navigation and available actions as authorized.
- [ ] Selected role cannot access permissions belonging exclusively to another role.
- [ ] Revoked/inactive role, inactive/unapproved account, and unauthenticated requests are rejected.
- [ ] Forged requests or invalid CSRF tokens are rejected.
- [ ] School Admin cannot access Technical Super Admin governance operations.
- [ ] Protected executor / protected permission mutations remain disabled and inaccessible.
- [ ] Localhost-only mode still works and all affected regression tests pass.
- [ ] No real credentials, student records, or applicant personal data used in HTTP LAN tests.

### 3.5 Completion and rollback

Once the above tests pass, **record Option A as a development-testing success only**, not a production-security approval. Make only reviewed, scoped source/test commits. To roll back, turn off the LAN opt-in, stop LAN-bound development listeners, and return to the existing localhost-only configuration. No database migration is necessary for the feature gate itself.

## 4. Option B — Secure LAN deployment (deferred)

### 4.1 Goal

Make role switching and other approved CTU-G Workspace operations available to authorized users on a managed campus network, including real accounts and personal information, without dependence on a debug-only/local-only acknowledgment.

### 4.2 Required implementation

1. Establish a named LAN deployment environment using a maintained web/app server and **HTTPS with a certificate trusted by every supported device**. Do not treat the Vite development server as a production server.
2. Run Django with `DEBUG=False`, managed secrets, explicit `ALLOWED_HOSTS`, approved `CSRF_TRUSTED_ORIGINS`, Secure/HttpOnly session cookies, and correctly configured proxy HTTPS headers only if requests truly pass through a trusted proxy.
3. Use a reverse proxy, narrow firewall rules, network segmentation, operational logs, security monitoring, backups, and a documented update/recovery procedure.
4. Add a separate **default-off deployment role-context gate** with fail-closed checks. Do not reuse `CTUG_ROLE_CONTEXT_NORMAL_DEV_ACK` or disable its localhost-only restrictions.
5. Verify the authentication/session lifecycle, role revocation behavior, effective-permission scoping, CSRF, session expiry, error handling, and authorized frontend navigation across supported devices.
6. Review service activation, pending database migrations, executor boundaries, and protected role/permission governance **separately**. No protected mutation is enabled solely because LAN/HTTPS role switching passes.
7. Complete privacy/security review, stakeholder approvals, operational runbooks, realistic acceptance tests, and a controlled launch plan before onboarding real applicants.

### 4.3 Acceptance criteria

- [ ] All supported devices establish valid HTTPS connections without certificate-warning bypasses.
- [ ] Secure cookies and trusted-origin/CSRF settings work as intended.
- [ ] Authorized multi-role accounts can switch roles from PC and mobile browsers.
- [ ] Role permission boundaries remain enforced on the server, including after revocation and logout.
- [ ] Unauthorized and forged requests fail closed; protected executor remains gated.
- [ ] Deployment environment meets agreed privacy, operations, backup, and access controls.
- [ ] Required independent approvals for privileged activation are recorded before any such activation.

## 5. Explicitly out of scope for Option A

- Public internet deployment or production rollout
- Real applicant intake or collection of genuine credentials over HTTP
- Reworking already accepted WF-03.01 user interactions
- Enabling protected Access Control Management writes or S0 provisioning
- Applying pending `access_control` migrations merely to make the role selector visible
- Changing organization fee, clearance, or unrelated workflows

## 6. Decision and next action

**Recommendation: choose Option A now** to unblock a narrow, internal, synthetic-data LAN demonstration while preserving existing WF-03 safeguards. It is the smaller development task and is appropriate **only** if the environment and data stay strictly test-only.

**Choose Option B before** inviting real students, instructors, or administrators to log in over LAN, or before accepting genuine applicant data. Option A is **not** a substitute for HTTPS.

**Implementation status (24 November 2026):** Option A is implemented as a fail-closed gate on the local `ctug_workspace` database and is configured automatically for the detected address by `Start-CTUG-LAN.ps1` (`operations/LOCAL_SETUP_RELEASE_RUNBOOK_DRAFT.md` §2A). The owner chose to use the existing development database; §3.3's caution about real credentials over plain HTTP still applies, so use only a trusted network. A same-day variant bound to a separate synthetic database was removed. Option B (HTTPS) remains deferred and unactivated.

**Earlier status:** Neither option was activated by this document. The earlier experimental HTTPS/LAN patch was removed; the current working tree was reported clean at checkpoint `42640b9` before subsequent Git reconciliation. Confirm the latest Git state before editing.

**Next scoped engineering task:** Inspect the current WF-03 role-context settings and test harness; implement and test the **separate, default-off Option A gate** without removing the existing localhost policy; verify LAN browser acceptance with synthetic accounts; then record results. Preserve all approval gates.
