"""Reviewable MySQL 8.4 security DDL. No production installer or ORM migration.

Execute only after schema/DBA approval. The disposable harness installs these
exact statements on the migrated application schema on its own second server.
"""
import re

from apps.access_control.protected_requests import require

VERSION = "wex-1"
TABLES = ("wex_control", "wex_requests", "wex_audits", "wex_recovery_events")
FENCED = ("accounts", "users", "roles", "services", "permissions", "account_roles",
          "role_permissions", "account_permissions", "access_audit_logs", "registration_notification_outbox")


def identifier(value):
    require(type(value) is str and re.fullmatch(r"[a-z][a-z0-9_]{0,63}", value) is not None)
    return "`" + value + "`"


def statements(ordinary="wex_ordinary", protected="wex_protected", notifications="wex_notifications"):
    identifier(ordinary)
    identifier(protected)
    identifier(notifications)
    result = [
        """CREATE TABLE wex_control (
          id INT PRIMARY KEY CHECK(id=1), epoch INT NOT NULL, incarnation CHAR(64) NOT NULL,
          roster_hash CHAR(64) NOT NULL, fence_hash CHAR(64) NOT NULL, recovery_hash CHAR(64) NOT NULL,
          release_hash CHAR(64) NOT NULL, halted BOOLEAN NOT NULL DEFAULT 1,
          schema_version VARCHAR(16) NOT NULL, definition_hash CHAR(64) NOT NULL,
          roster_expires BIGINT NOT NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin""",
        """CREATE TABLE wex_requests (
          request_id CHAR(64) PRIMARY KEY, nonce CHAR(64) NOT NULL UNIQUE, request_hash CHAR(64) NOT NULL,
          operation VARCHAR(64) NOT NULL, success_scope VARCHAR(64) UNIQUE,
          kind ENUM('ordinary','protected') NOT NULL, principal VARCHAR(128) NOT NULL,
          peer CHAR(64) NOT NULL, actor_id INT NULL, connection_id BIGINT NOT NULL,
          claim_hash CHAR(64) NOT NULL, epoch INT NOT NULL, incarnation CHAR(64) NOT NULL,
          evidence MEDIUMBLOB NOT NULL, status ENUM('CLAIMED','ATTEMPTED','APPLIED') NOT NULL,
          issued BIGINT NOT NULL, expires BIGINT NOT NULL, result JSON NULL,
          FOREIGN KEY(actor_id) REFERENCES accounts(account_id),
          CHECK((status='APPLIED' AND result IS NOT NULL) OR (status<>'APPLIED' AND result IS NULL))
        ) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin""",
        """CREATE TABLE wex_audits (
          request_id CHAR(64) NOT NULL, audit_id INT NOT NULL UNIQUE,
          PRIMARY KEY(request_id,audit_id), FOREIGN KEY(request_id) REFERENCES wex_requests(request_id),
          FOREIGN KEY(audit_id) REFERENCES access_audit_logs(access_audit_log_id)
        ) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin""",
        """CREATE FUNCTION wex_lease(protected_only BOOLEAN) RETURNS BOOLEAN
        READS SQL DATA SQL SECURITY DEFINER
        RETURN EXISTS(SELECT 1 FROM wex_requests r JOIN wex_control c ON c.id=1
          WHERE r.request_id=@wex_request AND r.status='ATTEMPTED'
          AND r.connection_id=CONNECTION_ID() AND c.halted=0
          AND r.epoch=c.epoch AND r.incarnation=c.incarnation
          AND UNIX_TIMESTAMP(UTC_TIMESTAMP()) < r.expires
          AND SUBSTRING_INDEX(r.principal,'@',1)=SUBSTRING_INDEX(USER(),'@',1)
          AND (protected_only=0 OR (r.kind='protected' AND BINARY SUBSTRING_INDEX(USER(),'@',1)='__PROTECTED_PRINCIPAL__')))""",
        """CREATE FUNCTION wex_reserved(n VARCHAR(100)) RETURNS BOOLEAN
        DETERMINISTIC NO SQL SQL SECURITY DEFINER
        RETURN LOWER(REGEXP_REPLACE(n,'[[:space:][:punct:]_]','')) COLLATE utf8mb4_unicode_ci
          IN ('admin','superadmin','technicalsuperadmin')""",
        """CREATE FUNCTION wex_governance(p INT) RETURNS BOOLEAN
        READS SQL DATA SQL SECURITY DEFINER
        RETURN EXISTS(SELECT 1 FROM permissions p JOIN services s ON p.service_id=s.service_id
          WHERE p.permission_id=p AND (s.service_code IN
          ('access_control','accounts','auth','authentication','authorization','security','governance','admin')
          OR p.module_name IN ('access_control','accounts','auth','authentication','authorization','security','governance','admin')
          OR SUBSTRING_INDEX(p.permission_code,'.',1) IN
          ('access_control','accounts','auth','authentication','authorization','security','governance','admin')))""",
    ]
    result = [sql.replace("__PROTECTED_PRINCIPAL__", protected) for sql in result]
    # Parameter name must differ from the table alias and column names.
    result[-1] = result[-1].replace("wex_governance(p INT)", "wex_governance(pid INT)").replace("p.permission_id=p AND", "p.permission_id=pid AND")
    result.append("""CREATE FUNCTION wex_rejected_registration(aid INT) RETURNS BOOLEAN
        READS SQL DATA SQL SECURITY DEFINER
        RETURN wex_lease(0) AND EXISTS(
          SELECT 1 FROM accounts a
          JOIN roles base_role ON base_role.role_id=a.requested_role_id
          JOIN wex_requests r ON r.request_id=@wex_request
          JOIN wex_audits link ON link.request_id=r.request_id
          JOIN access_audit_logs decision ON decision.access_audit_log_id=link.audit_id
          WHERE a.account_id=aid AND a.request_status='Rejected' AND a.is_active=0
            AND a.is_staff=0 AND a.is_superuser=0 AND a.reviewed_by=r.actor_id
            AND a.account_id<>r.actor_id AND a.reviewed_at IS NOT NULL
            AND base_role.is_active=1 AND BINARY base_role.role_name IN ('Student','Instructor')
            AND r.kind='ordinary' AND r.operation='registration.reject'
            AND decision.actor_account_id=r.actor_id AND decision.target_account_id IS NULL
            AND decision.action='account.registration.reject'
            AND JSON_UNQUOTE(JSON_EXTRACT(decision.old_value,'$.request_status'))='Pending'
            AND JSON_UNQUOTE(JSON_EXTRACT(decision.new_value,'$.request_status'))='Rejected'
            AND JSON_UNQUOTE(JSON_EXTRACT(decision.new_value,'$.account_deleted'))='true'
            AND CAST(JSON_UNQUOTE(JSON_EXTRACT(decision.old_value,'$.account_id')) AS UNSIGNED)=aid
            AND CAST(JSON_UNQUOTE(JSON_EXTRACT(decision.new_value,'$.account_id')) AS UNSIGNED)=aid
            AND JSON_UNQUOTE(JSON_EXTRACT(decision.new_value,'$.rejection_code'))=a.rejection_reason
            AND NOT EXISTS(SELECT 1 FROM account_roles ar WHERE ar.account_id=aid)
            AND NOT EXISTS(SELECT 1 FROM account_permissions ap WHERE ap.account_id=aid))""")
    result.insert(3, """CREATE TABLE wex_recovery_events (
        event_id BIGINT AUTO_INCREMENT PRIMARY KEY, action ENUM('HOLD','ROTATE','REFRESH') NOT NULL,
        previous_epoch INT NOT NULL, next_epoch INT NOT NULL, reason_hash CHAR(64) NOT NULL,
        evidence MEDIUMBLOB NOT NULL, occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin""")
    for table in FENCED:
        for event in ("INSERT", "UPDATE", "DELETE"):
            requirements = ["IF NOT wex_lease(0) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='verified writer lease required'; END IF;"]
            if table in {"roles", "services", "permissions"}:
                requirements.append("IF NOT wex_lease(1) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='protected writer required'; END IF;")
            for row in (("OLD",) if event == "DELETE" else ("NEW",) if event == "INSERT" else ("OLD", "NEW")):
                condition = None
                if table == "account_roles":
                    condition = f"NOT EXISTS(SELECT 1 FROM roles WHERE role_id={row}.role_id AND BINARY role_name IN ('Student','Instructor'))"
                    condition += f" OR EXISTS(SELECT 1 FROM account_roles a JOIN roles r ON r.role_id=a.role_id WHERE a.account_id={row}.account_id AND wex_reserved(r.role_name))"
                    if event != "INSERT":
                        condition = "TRUE"
                elif table == "role_permissions":
                    condition = f"wex_governance({row}.permission_id) OR EXISTS(SELECT 1 FROM roles WHERE role_id={row}.role_id AND wex_reserved(role_name))"
                elif table == "account_permissions":
                    condition = f"wex_governance({row}.permission_id) OR EXISTS(SELECT 1 FROM account_roles a JOIN roles r ON r.role_id=a.role_id WHERE a.account_id={row}.account_id AND wex_reserved(r.role_name))"
                elif table == "accounts":
                    # Ordinary review may approve only pending base registrations.
                    # Framework flags and credential changes of approved users are protected.
                    condition = f"{row}.is_staff=1 OR {row}.is_superuser=1"
                    if event == "DELETE":
                        condition = "NOT wex_rejected_registration(OLD.account_id)"
                    elif event == "UPDATE" and row == "NEW":
                        condition += " OR OLD.request_status='Approved'"
                elif table == "access_audit_logs":
                    if event != "INSERT":
                        requirements.append("SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='audit is append only';")
                    else:
                        requirements.append("IF NOT EXISTS(SELECT 1 FROM wex_requests WHERE request_id=@wex_request AND actor_id=NEW.actor_account_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='audit actor mismatch'; END IF;")
                elif table == "users" and event == "DELETE":
                    requirements.append("IF NOT wex_rejected_registration(OLD.account_id) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='verified registration rejection required'; END IF;")
                if condition:
                    requirements.append(f"IF NOT wex_lease(1) AND ({condition}) THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='protected state refused'; END IF;")
            body = " ".join(requirements)
            if table == "registration_notification_outbox" and event == "UPDATE":
                immutable = ("outbox_id", "decision_audit_log_id", "template_code", "template_version", "encrypted_recipient",
                             "recipient_nonce", "wrapped_data_key", "encryption_key_version", "recipient_erased_at", "created_at")
                body = (f"IF BINARY SUBSTRING_INDEX(USER(),'@',1)='{notifications}' THEN IF "
                        + " OR ".join(f"NOT(NEW.{field} <=> OLD.{field})" for field in immutable)
                        + " THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='immutable notification evidence'; END IF; ELSE " + body + " END IF;")
            result.append(f"CREATE TRIGGER wex_{table}_{event.lower()} BEFORE {event} ON {identifier(table)} FOR EACH ROW BEGIN " + body + " END")
    result.append("""CREATE TRIGGER wex_audit_link AFTER INSERT ON access_audit_logs FOR EACH ROW
      INSERT INTO wex_audits(request_id,audit_id) VALUES(@wex_request,NEW.access_audit_log_id)""")
    immutable = ("request_id", "nonce", "request_hash", "operation", "success_scope", "kind", "principal", "peer", "actor_id",
                 "connection_id", "claim_hash", "epoch", "incarnation", "evidence", "issued", "expires")
    result.append("CREATE TRIGGER wex_request_immutable BEFORE UPDATE ON wex_requests FOR EACH ROW BEGIN IF "
                  + " OR ".join(f"NOT(NEW.{field} <=> OLD.{field})" for field in immutable)
                  + " OR NOT((OLD.status='CLAIMED' AND NEW.status='ATTEMPTED' AND NEW.result IS NULL)"
                  " OR (OLD.status='ATTEMPTED' AND NEW.status='APPLIED' AND NEW.result IS NOT NULL))"
                  " THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='immutable evidence or invalid transition'; END IF; END")
    result.append(f"""CREATE TRIGGER wex_request_identity BEFORE INSERT ON wex_requests FOR EACH ROW
      BEGIN IF NEW.status<>'CLAIMED' OR NEW.connection_id<>CONNECTION_ID()
        OR BINARY SUBSTRING_INDEX(NEW.principal,'@',1)<>BINARY SUBSTRING_INDEX(USER(),'@',1)
        OR (NEW.kind='protected' AND BINARY SUBSTRING_INDEX(USER(),'@',1)<>'{protected}')
        OR (NEW.kind='ordinary' AND BINARY SUBSTRING_INDEX(USER(),'@',1)<>'{ordinary}')
        THEN SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT='executor identity mismatch'; END IF; END""")
    return result


def grants(schema, runtime, ordinary, protected, recovery, notifications="wex_notifications"):
    db = identifier(schema)
    for user in (runtime, ordinary, protected, recovery, notifications):
        identifier(user)
    result = []
    for user in (ordinary, protected):
        result.append(f"GRANT SELECT ON {db}.* TO '{user}'@'localhost'")
    for table in (*FENCED, "django_session"):
        result.append(f"GRANT SELECT ON {db}.{identifier(table)} TO '{runtime}'@'localhost'")
    result.append(f"GRANT INSERT,UPDATE,DELETE ON {db}.django_session TO '{runtime}'@'localhost'")
    for user in (ordinary, protected):
        result.append(f"GRANT LOCK TABLES ON {db}.* TO '{user}'@'localhost'")
        for table in FENCED:
            # UPDATE is needed for MySQL SELECT FOR UPDATE, including catalogue
            # locks. Triggers forbid actual ordinary catalogue/protected DML.
            if user == ordinary and table in {"roles", "services", "permissions"}:
                continue
            privileges = "INSERT" if table == "access_audit_logs" else "INSERT,UPDATE"
            if user == ordinary and table in {"accounts", "users"}:
                # DELETE is fenced by the exact rejection lease and immutable
                # decision receipt, never exposed to runtime or other handlers.
                privileges += ",DELETE"
            result.append(f"GRANT {privileges} ON {db}.{identifier(table)} TO '{user}'@'localhost'")
        result.append(f"GRANT INSERT,UPDATE ON {db}.wex_requests TO '{user}'@'localhost'")
    result.append(f"GRANT SELECT,UPDATE ON {db}.wex_control TO '{recovery}'@'localhost'")
    result.append(f"GRANT INSERT ON {db}.wex_recovery_events TO '{recovery}'@'localhost'")
    for table in ("registration_notification_outbox", "access_audit_logs"):
        result.append(f"GRANT SELECT ON {db}.{table} TO '{notifications}'@'localhost'")
    columns = "delivery_status,attempt_count,next_attempt_at,lease_expires_at,lease_token,last_failure_code,updated_at,delivered_at"
    result.append(f"GRANT UPDATE({columns}) ON {db}.registration_notification_outbox TO '{notifications}'@'localhost'")
    # No principal gets DDL, GRANT OPTION, ROLE_ADMIN, trigger/routine management,
    # audit deletion, evidence deletion or access to another schema.
    return result
