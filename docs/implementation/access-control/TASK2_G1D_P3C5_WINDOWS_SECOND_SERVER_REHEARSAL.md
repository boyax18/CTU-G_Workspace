# CTU-G Workspace — G1D-P3C5 Windows Second-Server Rehearsal

**Status:** Windows-specific local test candidate; **not executed against Windows/MySQL yet**. Production release is `BLOCKED`.
**Base checkpoint:** `ronald` / `9594a02` (13 November 2026).

## Why this exists

The P3C5 source-only draft passed 30 offline tests and 1,254 backend regression tests, but the Docker-only MySQL proof did not run. Docker is not part of the CTU-G Workspace application stack and is optional for this security rehearsal.

This adapter reuses the existing P3C5 test-only `DockerRehearsal.run` 21-check manifest while substituting a second isolated local Windows MySQL 8.4 server. It does not change or remove the original Docker test files.

## Strict isolation properties

- The adapter creates its own cryptographically named pipe and temporary database data directory beneath the operating system's temporary folder, using its own `mysqld.exe` subprocess.
- The temporary server has `--no-defaults`, `--standalone`, `--skip-networking`, `--mysqlx=OFF`, `--named-pipe=ON`, an exact unique `--socket`, a separate `--datadir` and separate logs. It does **not** stop, restart or modify the existing MySQL service.
- Every MySQL client command requires `--protocol=PIPE`, the random pipe name, `--no-defaults` and `--no-login-paths`; no TCP fallback. It removes ambient MySQL password/configuration variables.
- Before the first mutating SQL command, it verifies MySQL's reported data directory, Windows pipe name, TCP disabled, named pipes enabled, and server version `8.4.x` against the newly launched process. If any identity or isolation check fails, it stops.
- The newly initialized database has no production data. Synthetic `ctug_p3c5_disposable` tables and accounts exist only on that second instance. It runs 21 negative and positive privilege checks, terminates **only its own process**, and attempts to delete the temporary folder.
- Server initialization briefly creates a passwordless root account in the *isolated test instance* (`--initialize-insecure`), then changes its password before fixture creation. The random pipe and disabled TCP/X are the access boundary during this interval. Do not run on shared or untrusted workstations.

## Limitations and stop conditions

This Windows adapter has not been exercised on a Windows MySQL server within ChatGPT's Linux environment. Offline contract tests only verify the command structure and fail-closed branches; successful database proof requires owner-local execution. Named pipe access may be denied by Windows permissions. If it fails, **do not change the production MySQL service**, grant new rights on the real database, switch to TCP, edit `ctug_workspace`, or run fixtures against port 3306.

Even if all 21 SQL checks pass, this verifies only a disposable synthetic MySQL grant pattern. It does not prove the actual Django runtime or DBA credentials are separated, enforce dynamic role authorization, persist signatures or ledgers, verify backups, or enable protected-role provisioning. P4/P5 release remains **BLOCKED**.

## Owner-local verification

From the project root with backend virtual environment installed:

```powershell
python -B backend/manage.py test apps.access_control.test_task2_g1d_p3c5_windows_isolated --settings=config.test_settings --noinput
cd backend
python -B -m apps.access_control.tests_support.g1d_p3c5_windows_pipe_fence_test_only --ack P3C5_SECOND_SERVER_NO_PRODUCTION
```

The companion guarded installer runs the focused suite, the isolated Windows MySQL proof, existing backend regression, and migration check before committing exactly three new files. It verifies branch/checkpoint/package hash first. If a check fails, it does not commit; the newly added source may remain for review.

**Never execute the old Docker runner against a real local database. Do not call this demo stored procedure in production.**

## Windows MySQL 8.4 named-pipe authentication correction

The first user-local rehearsal passed 16 offline tests, then stopped immediately
after securing the disposable root credential. The precise MySQL client error
was not preserved. One likely cause is `caching_sha2_password`: on MySQL 8.4,
changing a password clears its authentication cache, and Windows named pipes
are *not* secure transport, so the client must support RSA public-key exchange.

This revision adds `--get-server-public-key` **only to the explicitly addressed
unique, disposable named-pipe client command**, with TCP and login-paths still
disabled, and adds an offline regression check for that option. Do not use the
option as a substitute for authenticating production hosts or for production
TLS/credential policy; this disposable fixture is not release evidence.

The Windows isolated MySQL rehearsal is still **NOT VERIFIED** until all
21 privilege checks succeed on the owner's machine. Any further failure must
stop without a commit or a change to the normal MySQL instance.
