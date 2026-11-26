# Dedicated permission-inventory reader — proposed operator steps

26 November 2026 · **PROPOSED ONLY; account creation/privilege changes NOT AUTHORIZED or executed.**
Prepared at the owner's request after the [connection preflight](WF11_Permission_Inventory_Preflight_2026-11-26.md)
found no usable verified reader in the available local configurations/login profiles. The original
read-only inventory approval remains valid; it does not authorize database account creation.

## 1. Operator and target preconditions

After separate authorization, the DBA uses an existing approved local administrative session and
privately verifies the intended local server, `ctug_workspace` and port 3306. The DBA confirms the
eight tables below already exist as InnoDB tables. Missing tables are an inventory prerequisite
blocker: do not apply migrations, create placeholder tables or broaden grants to compensate.

In that separately authorized DBA session, select `ctug_workspace` and perform these metadata
checks before creating anything. Confirm the intended MySQL server/version; require eight matching
InnoDB tables and no existing row for the proposed account name:

```sql
SELECT DATABASE(), @@hostname, @@port, VERSION();
SELECT TABLE_NAME, ENGINE
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'ctug_workspace'
  AND TABLE_NAME IN ('services', 'permissions', 'roles', 'role_permissions',
                    'account_permissions', 'account_roles', 'accounts',
                    'account_permission_role_scopes')
ORDER BY TABLE_NAME;
SELECT User, Host FROM mysql.user
WHERE User = 'ctug_wf11_inventory_ro';
```

Check whether the proposed account name is already present. If it exists, stop for a review of
that existing identity; do not change its password or append permissions blindly. Use `CREATE USER`
without `IF NOT EXISTS`, so a collision fails. MySQL documents this collision behavior in
[CREATE USER](https://dev.mysql.com/doc/refman/8.4/en/create-user.html).

Use a new owner-generated random secret held in an approved local secret store. The placeholder
below is not a password to use. Substitute it only in the DBA's private execution channel with
secret/history handling configured; never put the real value in chat, this file, shell arguments,
source control or captured output. Do not change `backend/.env` or reuse its application secret.

## 2. Exact proposed account and table grants

Execute only after explicit approval of **one new** account,
`'ctug_wf11_inventory_ro'@'127.0.0.1'`, and these eight table-level SELECT grants:

```sql
-- PROPOSAL ONLY. Stop on any error. Do not run with this literal placeholder.
CREATE USER 'ctug_wf11_inventory_ro'@'127.0.0.1'
  IDENTIFIED BY '<OWNER_GENERATED_NEW_SECRET>';

GRANT SELECT ON `ctug_workspace`.`services`
  TO 'ctug_wf11_inventory_ro'@'127.0.0.1';
GRANT SELECT ON `ctug_workspace`.`permissions`
  TO 'ctug_wf11_inventory_ro'@'127.0.0.1';
GRANT SELECT ON `ctug_workspace`.`roles`
  TO 'ctug_wf11_inventory_ro'@'127.0.0.1';
GRANT SELECT ON `ctug_workspace`.`role_permissions`
  TO 'ctug_wf11_inventory_ro'@'127.0.0.1';
GRANT SELECT ON `ctug_workspace`.`account_permissions`
  TO 'ctug_wf11_inventory_ro'@'127.0.0.1';
GRANT SELECT ON `ctug_workspace`.`account_roles`
  TO 'ctug_wf11_inventory_ro'@'127.0.0.1';
GRANT SELECT ON `ctug_workspace`.`accounts`
  TO 'ctug_wf11_inventory_ro'@'127.0.0.1';
GRANT SELECT ON `ctug_workspace`.`account_permission_role_scopes`
  TO 'ctug_wf11_inventory_ro'@'127.0.0.1';
```

These are SELECT privileges on the named tables, including all their columns; the existing
inventory query set selects minimized fields only. The setup grants no schema-wide/global SELECT,
write/DDL/administration privilege, GRANT OPTION, proxy authority or role membership. There is no
grant on `mysql.*`, other business tables or future tables. Table-level privilege syntax and scope
are described in [MySQL GRANT](https://dev.mysql.com/doc/refman/8.4/en/grant.html).

If an intermediate grant fails, stop and record which steps succeeded; do not run blanket
`GRANT ALL`, alter an existing account, edit system privilege tables or improvise a retry/cleanup.
These account-management statements change MySQL authorization metadata, so this proposal requires
separate approval even though it does not modify application records in `ctug_workspace`.

## 3. Positively verify the reader before inventory

Connect **as the new reader** using TCP `127.0.0.1:3306`, selecting `ctug_workspace`. For a private
operator console, the installed client's separate password prompt avoids a command-line secret:

```powershell
& 'C:\Program Files\MySQL\MySQL Server 8.4\bin\mysql.exe' --protocol=TCP --host=127.0.0.1 --port=3306 --user=ctug_wf11_inventory_ro --password --database=ctug_workspace
```

Run these read-only metadata checks in that reader session; keep output restricted and redact
identities/hostnames before sharing:

```sql
SELECT DATABASE(), CURRENT_USER(), USER(), @@hostname, @@port;
SHOW GRANTS;
SELECT CURRENT_ROLE(), @@GLOBAL.mandatory_roles;
```

Require the intended server/schema/port and matched reader account. Grants must be only USAGE
and SELECT on exactly the eight listed tables. Require no assigned/inherited/mandatory role and
no other privilege or GRANT OPTION. Stop on any mismatch or inability to prove this; do not probe
writes, disable global roles or modify credentials as a test.

Use **`SHOW GRANTS` without `FOR`** in this positive preflight: MySQL includes mandatory roles
there, while `SHOW GRANTS FOR CURRENT_USER()` omits them. The prepared inventory uses the latter,
so its explicit-grant guard alone is not a complete mandatory-role attestation. Checking this
before inventory is required; no guard/source change is included in this documentation delivery.
Self-inspection of grants needs no `mysql.*` grant, as explained in
[MySQL SHOW GRANTS](https://dev.mysql.com/doc/refman/8.4/en/show-grants.html).

## 4. Resume only the already-authorized inventory

Make the reader connection available to the inventory process through secure, process-local
`WF11_INVENTORY_DB_HOST=127.0.0.1`, `WF11_INVENTORY_DB_PORT=3306`,
`WF11_INVENTORY_DB_USER`, `WF11_INVENTORY_DB_PASSWORD` and an owner-held random
`WF11_INVENTORY_HMAC_KEY` of at least 32 bytes. Retain the key and full pseudonymous report in
owner-restricted storage outside Git. Do not put the database password in a command argument.

After the positive preflight above, use the existing guarded command from the repository root:

```powershell
backend\.venv\Scripts\python.exe review_only\academic_settings_v2_3\permission_inventory.py --authorize-read-only OWNER_AUTHORIZED_CTUG_WORKSPACE_PERMISSION_SELECT_ONLY
```

The script checks explicit privileges, starts a read-only consistent transaction, verifies the
selected database/read-only state and expected InnoDB schema, performs fixed SELECTs and rolls
back/closes. Missing scope tables or any refusal remains a blocker, not permission to migrate or
fall back to root. No v2.3 provisioning, business write or feature activation is included.

## 5. Exact separate authorization needed if no existing reader is supplied

> I authorize creation of the new local MySQL account
> `'ctug_wf11_inventory_ro'@'127.0.0.1'` with a new owner-held secret, granting only SELECT on
> the eight tables named in this reviewed setup document, and read-only verification of its
> target/grants/role inheritance. Do not alter existing accounts, credentials, application records,
> migrations, HDAC grants, catalogue pins, feature switches or launcher modes.

This authorization has **not** been granted. Supplying an existing verified reader is an alternative
that does not require authorizing a new account. Independent security review and Human Approval
remain OPEN.
