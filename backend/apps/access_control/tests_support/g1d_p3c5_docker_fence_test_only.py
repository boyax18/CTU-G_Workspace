"""G1D-P3C5 disposable MySQL writer-privilege rehearsal, NEVER production.

Runs only inside a newly created, network-isolated, disposable Docker MySQL
container. No Django settings or workspace DB credentials are read. This is a
negative-test *demonstration* of per-table privileges plus a narrow stored
operation. It is NOT a production authorization, real signer trust, session
fence, ledger, backup verification, or protected-role provisioning workflow.
"""

from __future__ import annotations

import argparse
import json
import re
import secrets
import shutil
import subprocess
import time
from dataclasses import dataclass
from uuid import uuid4


CHECKPOINT = "G1D-P3C5-DISPOSABLE-DB-PROOF-ONLY"
SCHEMA = "ctug_p3c5_disposable"
IMAGE = "mysql:8.4"
RELEASE_STATUS = "BLOCKED"
# Static fixture identities have no rights outside the isolated container.
WEB = "ctug_p3c5_web"
EXECUTOR = "ctug_p3c5_executor"
# Expected MySQL server denial codes, not arbitrary errors such as SQL syntax.
PRIVILEGE_ERRORS = frozenset({1142, 1143, 1370, 1227, 1044})
ROLE_REFUSED_ERROR = 1644
DUPLICATE_ERROR = 1062
MYSQL_ERROR = re.compile(r"\bERROR\s+(\d+)\s*\(", re.IGNORECASE)


class RehearsalError(RuntimeError):
    pass


@dataclass(frozen=True)
class Proof:
    name: str
    result: str


def sql_setup(web_password: str, executor_password: str) -> str:
    """Construct disposable-only schema; passwords must be hex-generated.

    The demo procedure accepts arbitrary target IDs: it does not authenticate
    the app actor. It must NEVER be installed in CTU-G Workspace's real DB.
    """
    if not all(re.fullmatch(r"[0-9a-f]{48}", value) for value in (web_password, executor_password)):
        raise RehearsalError("Only generated test credential format permitted")
    return f"""
CREATE DATABASE `{SCHEMA}`;
USE `{SCHEMA}`;
CREATE TABLE roles (
  role_id INT PRIMARY KEY,
  role_name VARCHAR(50) NOT NULL UNIQUE,
  is_active BOOLEAN NOT NULL
) ENGINE=InnoDB;
CREATE TABLE accounts (
  account_id INT PRIMARY KEY,
  school_id VARCHAR(50) NOT NULL UNIQUE
) ENGINE=InnoDB;
CREATE TABLE account_roles (
  account_role_id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  role_id INT NOT NULL,
  assigned_by INT NOT NULL,
  UNIQUE KEY account_role_unique(account_id, role_id),
  FOREIGN KEY (account_id) REFERENCES accounts(account_id),
  FOREIGN KEY (role_id) REFERENCES roles(role_id),
  FOREIGN KEY (assigned_by) REFERENCES accounts(account_id)
) ENGINE=InnoDB;
CREATE TABLE role_permissions (
  role_permission_id INT AUTO_INCREMENT PRIMARY KEY,
  role_id INT NOT NULL,
  permission_id INT NOT NULL
) ENGINE=InnoDB;
CREATE TABLE account_permissions (
  account_permission_id INT AUTO_INCREMENT PRIMARY KEY,
  account_id INT NOT NULL,
  permission_id INT NOT NULL
) ENGINE=InnoDB;
CREATE TABLE access_audit_logs (
  access_audit_log_id INT AUTO_INCREMENT PRIMARY KEY,
  actor_account_id INT NOT NULL,
  target_account_id INT NOT NULL,
  action VARCHAR(50) NOT NULL,
  FOREIGN KEY (actor_account_id) REFERENCES accounts(account_id),
  FOREIGN KEY (target_account_id) REFERENCES accounts(account_id)
) ENGINE=InnoDB;
INSERT INTO roles VALUES
 (1, 'Student', 1), (2, 'Instructor', 1), (3, 'Admin', 1),
 (4, 'Technical Super Admin', 0);
INSERT INTO accounts VALUES
 (900, 'synthetic-operator'), (101, 'synthetic-student'), (102, 'synthetic-instructor');
CREATE USER '{WEB}'@'localhost' IDENTIFIED BY '{web_password}';
CREATE USER '{EXECUTOR}'@'localhost' IDENTIFIED BY '{executor_password}';
-- Runtime is deliberately NOT granted direct INSERT/UPDATE/DELETE on role tables.
GRANT SELECT ON `{SCHEMA}`.roles TO '{WEB}'@'localhost';
GRANT SELECT ON `{SCHEMA}`.account_roles TO '{WEB}'@'localhost';
-- Read-only executor connection for a real permission-denial test.
GRANT SELECT ON `{SCHEMA}`.roles TO '{EXECUTOR}'@'localhost';
DELIMITER //
CREATE PROCEDURE p3c5_assign_base_demo(IN p_target INT, IN p_role VARCHAR(50))
SQL SECURITY DEFINER
BEGIN
  DECLARE EXIT HANDLER FOR SQLEXCEPTION
  BEGIN
    ROLLBACK;
    RESIGNAL;
  END;
  -- Only a demonstrative role allowlist; not complete actor authorization.
  IF p_target IS NULL OR p_role IS NULL OR p_role NOT IN ('Student', 'Instructor') THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'not an allowed base role';
  END IF;
  START TRANSACTION;
  INSERT INTO account_roles (account_id, role_id, assigned_by)
    SELECT p_target, role_id, 900 FROM roles
    WHERE role_name = p_role AND is_active = 1
      AND EXISTS (SELECT 1 FROM accounts WHERE account_id = p_target);
  IF ROW_COUNT() != 1 THEN
    SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'target or role not eligible';
  END IF;
  INSERT INTO access_audit_logs (actor_account_id, target_account_id, action)
    VALUES (900, p_target, 'p3c5.base_role_demo');
  COMMIT;
END//
DELIMITER ;
GRANT EXECUTE ON PROCEDURE `{SCHEMA}`.p3c5_assign_base_demo
  TO '{WEB}'@'localhost';
"""


def expected_checks() -> tuple[str, ...]:
    return (
        "runtime_login", "executor_login", "runtime_role_insert_denied",
        "runtime_protected_reactivation_denied", "runtime_protected_assignment_denied",
        "runtime_role_permission_denied", "runtime_account_permission_denied",
        "runtime_audit_forgery_denied", "runtime_assignment_delete_denied",
        "runtime_role_drop_denied", "runtime_admin_via_routine_refused",
        "runtime_protected_via_routine_refused", "runtime_null_role_refused",
        "runtime_student_assignment_works", "runtime_instructor_assignment_works",
        "runtime_duplicate_rolls_back", "executor_role_insert_denied",
        "executor_routine_execution_denied", "postconditions_role_protected",
        "postconditions_assignments", "postconditions_audit",
    )


class DockerRehearsal:
    def __init__(self):
        self.container = "ctug-p3c5-" + uuid4().hex[:12]
        self.root_password = secrets.token_hex(24)
        self.web_password = secrets.token_hex(24)
        self.executor_password = secrets.token_hex(24)
        self.proofs: list[Proof] = []
        self.created = False

    @staticmethod
    def _docker(args: list[str], *, input_text: str | None = None, timeout: int = 30):
        try:
            return subprocess.run(
                ["docker", *args], input=input_text, text=True,
                capture_output=True, timeout=timeout, check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError) as exc:
            raise RehearsalError("Disposable Docker operation unavailable or timed out") from exc

    def _mysql(self, who: str, sql: str):
        if who == "root":
            user, password = "root", self.root_password
        elif who == "web":
            user, password = WEB, self.web_password
        elif who == "executor":
            user, password = EXECUTOR, self.executor_password
        else:
            raise RehearsalError("Unexpected disposable principal")
        command = [
            "exec", "-i", "-e", "MYSQL_PWD=" + password, self.container,
            "mysql", "--protocol=socket", "--batch", "--skip-column-names",
            "--raw", "--user=" + user,
        ]
        if who != "root":
            command.extend(["--database", SCHEMA])
        return self._docker(command, input_text=sql + "\n", timeout=30)

    def _good(self, name: str, who: str, sql: str, *, expected: str | None = None):
        result = self._mysql(who, sql)
        if result.returncode != 0:
            raise RehearsalError("Rehearsal positive check failed: " + name)
        if expected is not None and result.stdout.strip() != expected:
            raise RehearsalError("Rehearsal postcondition mismatch: " + name)
        self.proofs.append(Proof(name, "PASS"))

    def _denied(self, name: str, who: str, sql: str, allowed_errors=PRIVILEGE_ERRORS):
        result = self._mysql(who, sql)
        codes = {int(x) for x in MYSQL_ERROR.findall(result.stderr)}
        if result.returncode == 0 or not codes.intersection(allowed_errors):
            raise RehearsalError("Expected MySQL rejection missing: " + name)
        self.proofs.append(Proof(name, "DENIED_AS_EXPECTED"))

    def _start(self):
        if shutil.which("docker") is None:
            raise RehearsalError("Docker CLI unavailable: isolated MySQL rehearsal NOT RUN")
        # No host port, volume or network access; only docker exec via local socket.
        result = self._docker([
            "run", "--detach", "--rm", "--network", "none", "--name", self.container,
            "--label", "ctug.p3c5=disposable-only",
            "--env", "MYSQL_ROOT_PASSWORD=" + self.root_password,
            IMAGE,
        ], timeout=150)
        if result.returncode != 0:
            raise RehearsalError("Could not start disposable MySQL Docker container")
        self.created = True
        # Verify the actual container network mode, not just our requested flag.
        mode = self._docker(["inspect", "--format", "{{.HostConfig.NetworkMode}}", self.container])
        if mode.returncode != 0 or mode.stdout.strip() != "none":
            raise RehearsalError("Disposable container network isolation not verified")
        # Explicitly verify no host-facing published ports.
        ports = self._docker(["port", self.container])
        if ports.returncode != 0 or ports.stdout.strip():
            raise RehearsalError("Disposable container exposed published ports")
        for _ in range(90):
            auth = self._mysql("root", "SELECT 'ready';")
            if auth.returncode == 0 and auth.stdout.strip() == "ready":
                return
            time.sleep(1)
        raise RehearsalError("Disposable MySQL not ready")

    def run(self) -> dict:
        try:
            self._start()
            setup = self._mysql("root", sql_setup(self.web_password, self.executor_password))
            if setup.returncode != 0:
                raise RehearsalError("Disposable schema and privilege initialization failed")
            self._good("runtime_login", "web", "SELECT 1;", expected="1")
            self._good("executor_login", "executor", "SELECT 1;", expected="1")
            self._denied("runtime_role_insert_denied", "web", "INSERT INTO roles (role_id, role_name, is_active) VALUES (99,'Other',1);")
            self._denied("runtime_protected_reactivation_denied", "web", "UPDATE roles SET is_active=1 WHERE role_id=4;")
            self._denied("runtime_protected_assignment_denied", "web", "INSERT INTO account_roles (account_id, role_id, assigned_by) VALUES (101,4,900);")
            self._denied("runtime_role_permission_denied", "web", "INSERT INTO role_permissions (role_id, permission_id) VALUES (4,1);")
            self._denied("runtime_account_permission_denied", "web", "INSERT INTO account_permissions (account_id, permission_id) VALUES (101,1);")
            self._denied("runtime_audit_forgery_denied", "web", "INSERT INTO access_audit_logs (actor_account_id,target_account_id,action) VALUES (900,101,'forged');")
            self._denied("runtime_assignment_delete_denied", "web", "DELETE FROM account_roles WHERE account_id=101;")
            self._denied("runtime_role_drop_denied", "web", "DROP TABLE roles;")
            self._denied("runtime_admin_via_routine_refused", "web", "CALL p3c5_assign_base_demo(101, 'Admin');", {ROLE_REFUSED_ERROR})
            self._denied("runtime_protected_via_routine_refused", "web", "CALL p3c5_assign_base_demo(101, 'Technical Super Admin');", {ROLE_REFUSED_ERROR})
            self._denied("runtime_null_role_refused", "web", "CALL p3c5_assign_base_demo(101, NULL);", {ROLE_REFUSED_ERROR})
            self._good("runtime_student_assignment_works", "web", "CALL p3c5_assign_base_demo(101, 'Student');")
            self._good("runtime_instructor_assignment_works", "web", "CALL p3c5_assign_base_demo(102, 'Instructor');")
            self._denied("runtime_duplicate_rolls_back", "web", "CALL p3c5_assign_base_demo(101, 'Student');", {DUPLICATE_ERROR})
            self._denied("executor_role_insert_denied", "executor", "INSERT INTO roles (role_id, role_name, is_active) VALUES (98,'Bad',1);")
            self._denied("executor_routine_execution_denied", "executor", "CALL p3c5_assign_base_demo(102, 'Student');", {1370})
            self._good("postconditions_role_protected", "root", f"SELECT CONCAT(is_active,':', (SELECT COUNT(*) FROM `{SCHEMA}`.account_roles WHERE role_id=4)) FROM `{SCHEMA}`.roles WHERE role_id=4;", expected="0:0")
            self._good("postconditions_assignments", "root", f"SELECT COUNT(*) FROM `{SCHEMA}`.account_roles WHERE (account_id=101 AND role_id=1) OR (account_id=102 AND role_id=2);", expected="2")
            self._good("postconditions_audit", "root", f"SELECT COUNT(*) FROM `{SCHEMA}`.access_audit_logs;", expected="2")
            if tuple(p.name for p in self.proofs) != expected_checks():
                raise RehearsalError("Proof manifest incomplete")
            return {
                "checkpoint": CHECKPOINT,
                "disposable_tests_passed": len(self.proofs),
                "proofs": [{"name": p.name, "result": p.result} for p in self.proofs],
                "production_release_status": RELEASE_STATUS,
                "production_writer_fence_verified": False,
                "limitations": [
                    "Disposable schema and grant simulation, not the CTU-G Workspace production schema",
                    "Normal registration approval and dynamic permission mutations still require production integration design",
                    "Demo procedure only checks a base-role allowlist, not caller identity or policy eligibility",
                    "Synthetic Docker credentials, not DBA-attested production principals or real protected executor",
                    "No signature trust, persistent signed ledger, session drain, independent backup restoration, or live migration",
                ],
            }
        finally:
            if self.created:
                # Always discard throwaway users, tables and secrets; no volumes.
                self._docker(["rm", "--force", self.container], timeout=35)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run disposable Docker MySQL privilege negative tests ONLY")
    parser.add_argument("--ack", required=True, choices=["P3C5_ISOLATED_DOCKER_ONLY"])
    opts = parser.parse_args(argv)
    if opts.ack != "P3C5_ISOLATED_DOCKER_ONLY":
        return 2
    try:
        report = DockerRehearsal().run()
    except RehearsalError as exc:
        print(json.dumps({
            "checkpoint": CHECKPOINT, "rehearsal": "NOT_VERIFIED",
            "production_release_status": RELEASE_STATUS, "error": str(exc),
        }, indent=2, sort_keys=True))
        return 1
    print(json.dumps(report, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
