"""P3C5 disposable Windows MySQL named-pipe SQL proof. NEVER production.

This reuses the P3C5 21-check disposable privilege exercise, but launches a
SECOND server process with a fresh temporary data directory and a random,
private named pipe. It cannot import Django settings, secrets, or .env.

An isolated proof is NOT a production writer fence or an authorization to
create/assign protected roles. Fail closed on all environment uncertainty.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from .g1d_p3c5_docker_fence_test_only import (
    CHECKPOINT as PREVIOUS_CHECKPOINT,
    DockerRehearsal,
    RehearsalError,
    SCHEMA,
)

CHECKPOINT = "G1D-P3C5-WINDOWS-SEPARATE-NAMED-PIPE-ONLY"
ACKNOWLEDGEMENT = "P3C5_SECOND_SERVER_NO_PRODUCTION"


def _isolated_server_options(bin_dir: Path, datadir: Path, pipe: str, log: Path, pid: Path) -> list[str]:
    """Server must never inherit live config or expose a TCP listener."""
    return [
        str(bin_dir / "mysqld.exe"),
        "--no-defaults",
        f"--basedir={bin_dir.parent}",
        f"--datadir={datadir}",
        "--standalone",
        "--skip-networking",
        "--mysqlx=OFF",
        "--named-pipe=ON",
        f"--socket={pipe}",
        f"--log-error={log}",
        f"--pid-file={pid}",
        "--skip-log-bin",
        "--persisted-globals-load=OFF",
    ]


def _client_options(bin_dir: Path, pipe: str, user: str, schema: bool) -> list[str]:
    """Never allow default TCP, login paths or ambient config."""
    result = [
        str(bin_dir / "mysql.exe"),
        "--no-defaults", "--no-login-paths",
        "--protocol=PIPE", "--host=.", f"--socket={pipe}",
        # MySQL 8.4 named pipes are not secure transport for caching_sha2_password.
        # After ALTER USER clears the auth cache, the next login needs RSA exchange.
        # This is ONLY a locally isolated, disposable named-pipe test server.
        "--get-server-public-key",
        "--batch", "--skip-column-names", "--raw", "--skip-reconnect",
        f"--user={user}",
    ]
    if schema:
        result.append(f"--database={SCHEMA}")
    return result


def _is_own_datadir(reported: str, expected: Path) -> bool:
    # MySQL Windows paths often carry a trailing slash and mixed separators.
    return os.path.normcase(os.path.normpath(reported.replace("/", os.sep))) == os.path.normcase(
        os.path.normpath(str(expected))
    )


class WindowsNamedPipeRehearsal(DockerRehearsal):
    def __init__(self, binary_dir: Path):
        super().__init__()
        self.bin = binary_dir.resolve(strict=True)
        self.pipe = "ctug_p3c5_" + secrets.token_hex(16)
        self.work: Path | None = None
        self.data: Path | None = None
        self.proc: subprocess.Popen | None = None
        self._root_secured = False

    def _invoke(self, args: list[str], sql: str = "", password: str | None = None, timeout=30):
        env = os.environ.copy()
        for key in ("MYSQL_PWD", "MYSQL_TEST_LOGIN_FILE", "MYSQL_HOME", "MYSQL_TCP_PORT", "MYSQL_UNIX_PORT"):
            env.pop(key, None)
        if password is not None:
            env["MYSQL_PWD"] = password
        try:
            return subprocess.run(args, input=sql + "\n", text=True, capture_output=True,
                                  timeout=timeout, check=False, env=env, encoding="utf-8", errors="replace")
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RehearsalError("Isolated MySQL command unavailable or timed out") from exc

    def _mysql(self, who: str, sql: str):
        if who == "root":
            user = "root"
            password = self.root_password if self._root_secured else None
        elif who == "web":
            user, password = "ctug_p3c5_web", self.web_password
        elif who == "executor":
            user, password = "ctug_p3c5_executor", self.executor_password
        else:
            raise RehearsalError("Unknown disposable principal")
        args = _client_options(self.bin, self.pipe, user, who != "root")
        # --skip-password is explicit so no interactive credential prompt occurs.
        if password is None:
            args.append("--skip-password")
        return self._invoke(args, sql, password)

    def _identity_verified(self, output: str) -> bool:
        parts = output.strip().split("\t")
        if len(parts) != 5 or self.data is None:
            return False
        datadir, skip_net, named_pipe, pipe, version = parts
        return (
            _is_own_datadir(datadir, self.data)
            and skip_net in ("1", "ON")
            and named_pipe in ("1", "ON")
            and pipe.lower().endswith(self.pipe.lower())
            and version.startswith("8.4.")
            and self.proc is not None and self.proc.poll() is None
        )

    def _start(self):
        if platform.system() != "Windows":
            raise RehearsalError("Windows-only standalone second-server proof")
        for executable in (self.bin / "mysqld.exe", self.bin / "mysql.exe"):
            if not executable.is_file():
                raise RehearsalError("MySQL server and client executables not found together")
        version = self._invoke([str(self.bin / "mysqld.exe"), "--no-defaults", "--version"]).stdout
        if not re.search(r"\bVer\s+8\.4\.", version, flags=re.IGNORECASE):
            raise RehearsalError("Requires a MySQL 8.4 standalone binary installation")
        # Do not use any database directory supplied from Django settings or env.
        self.work = Path(tempfile.mkdtemp(prefix="ctug-p3c5-separate-"))
        self.data = self.work / "data"
        log, pid = self.work / "disposable-mysqld.err", self.work / "disposable-mysqld.pid"
        self.created = True  # Ensures parent.run() calls our cleanup even if startup fails.
        initialize = self._invoke([
            str(self.bin / "mysqld.exe"), "--no-defaults",
            f"--basedir={self.bin.parent}", f"--datadir={self.data}",
            "--initialize-insecure", "--console", "--persisted-globals-load=OFF",
        ], timeout=180)
        if initialize.returncode != 0:
            raise RehearsalError("Isolated MySQL data-directory initialization failed")
        # Initialized root starts passwordless; pipe is random, TCP and X are disabled.
        with (self.work / "startup.log").open("ab") as fp:
            try:
                self.proc = subprocess.Popen(
                    _isolated_server_options(self.bin, self.data, self.pipe, log, pid),
                    stdin=subprocess.DEVNULL, stdout=fp, stderr=subprocess.STDOUT,
                    cwd=str(self.work),
                )
            except OSError as exc:
                raise RehearsalError("Could not start isolated second MySQL process") from exc
        deadline = time.monotonic() + 75
        while time.monotonic() < deadline:
            if self.proc.poll() is not None:
                raise RehearsalError("Disposable MySQL exited before accepting its private pipe")
            # Identity is checked before issuing even the first ALTER USER.
            response = self._mysql("root", "SELECT @@global.datadir, @@global.skip_networking, @@global.named_pipe, @@global.socket, @@global.version;")
            if response.returncode == 0:
                if not self._identity_verified(response.stdout):
                    raise RehearsalError("Isolated MySQL identity or transport did not match; no SQL writes permitted")
                break
            time.sleep(0.5)
        else:
            raise RehearsalError("Private named-pipe MySQL did not start in time")
        # Generated hex password is not placed on any command line.
        password_change = self._mysql("root", "ALTER USER 'root'@'localhost' IDENTIFIED BY '" + self.root_password + "';")
        if password_change.returncode != 0:
            raise RehearsalError("Failed to secure disposable root after verifying isolation")
        self._root_secured = True
        validated = self._mysql("root", "SELECT @@global.datadir, @@global.skip_networking, @@global.named_pipe, @@global.socket, @@global.version;")
        if validated.returncode != 0 or not self._identity_verified(validated.stdout):
            raise RehearsalError("Disposable identity check failed after securing credentials")

    def _docker(self, args, *, input_text=None, timeout=30):
        # Parent.run() has only one Docker-specific cleanup call at the end.
        if len(args) != 3 or args[:2] != ["rm", "--force"] or args[2] != self.container:
            raise RehearsalError("Unexpected Docker operation; standalone proof stopped")
        self._cleanup()
        return subprocess.CompletedProcess(args, 0, "", "")

    def _cleanup(self):
        # On Windows mysqld may be a launcher with a child server. Terminating
        # only that handle can leave the child and its locked data files alive.
        # Authenticate and verify our private instance before graceful shutdown.
        if self.proc is not None and self.proc.poll() is None:
            response = self._mysql("root", "SELECT @@global.datadir, @@global.skip_networking, @@global.named_pipe, @@global.socket, @@global.version;")
            if response.returncode != 0 or not self._identity_verified(response.stdout):
                raise RehearsalError("Disposable cleanup identity unavailable; directory retained")
            shutdown = self._mysql("root", "SHUTDOWN;")
            if shutdown.returncode != 0:
                raise RehearsalError("Disposable graceful shutdown failed; directory retained")
            try:
                self.proc.wait(timeout=12)
            except (OSError, subprocess.TimeoutExpired):
                raise RehearsalError("Disposable server shutdown unresolved; directory retained") from None
        if self.work is None or not self.work.exists():
            return
        # Validate the resolved absolute target before ANY recursive removal.
        work = self.work.resolve(strict=True)
        if (self.work.is_symlink() or work != self.work.absolute()
                or work.parent != Path(tempfile.gettempdir()).resolve(strict=True)
                or not work.name.startswith("ctug-p3c5-separate-")
                or self.data != work / "data"):
            raise RehearsalError("Disposable cleanup path refused")
        try:
            shutil.rmtree(work)
        except OSError:
            raise RehearsalError("Disposable cleanup incomplete; directory retained") from None

    def run(self) -> dict:
        report = super().run()
        report["checkpoint"] = CHECKPOINT
        report["isolated_transport"] = "unique named pipe; TCP disabled; MySQL X disabled"
        report["previous_proof_manifest"] = PREVIOUS_CHECKPOINT
        report["production_release_status"] = "BLOCKED"
        report["production_writer_fence_verified"] = False
        return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Disposable second-server MySQL 8.4 Windows-only fencing demonstration")
    parser.add_argument("--ack", required=True, choices=[ACKNOWLEDGEMENT])
    parser.add_argument("--bin-dir", help="Folder containing stock MySQL Server 8.4 mysqld.exe and mysql.exe")
    options = parser.parse_args(argv)
    if platform.system() != "Windows":
        print(json.dumps({"checkpoint": CHECKPOINT, "rehearsal": "NOT_RUN", "reason": "Windows only", "production_release_status": "BLOCKED"}))
        return 1
    default_bin = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "MySQL" / "MySQL Server 8.4" / "bin"
    bin_dir = Path(options.bin_dir) if options.bin_dir else default_bin
    try:
        report = WindowsNamedPipeRehearsal(bin_dir).run()
        print(json.dumps(report, indent=2, sort_keys=True))
        return 0
    except (RehearsalError, OSError, ValueError) as exc:
        print(json.dumps({"checkpoint": CHECKPOINT, "rehearsal": "NOT_VERIFIED", "reason": str(exc), "production_release_status": "BLOCKED"}, indent=2))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
