"""Review-first, append-only AR-6C5D official ERD updater (no DB access).

Run from repository root:
  python scripts/ar6c5d/apply_approved_bulk_schema.py
  python scripts/ar6c5d/apply_approved_bulk_schema.py --apply

The sha256 precondition is the exact official ERD hash supplied by the owner
on November 10, 2026. Fail closed on drift or missing prerequisites.
"""
from __future__ import annotations

import argparse
import difflib
import hashlib
import os
from pathlib import Path
import re
import shutil
import sys
import tempfile

EXPECTED_SHA256 = '0CDE2A267BBC18F702701CA63D606F39AE0320D0D51FF23E91CCAE3CA4DB1FF6'
MARKER = '// ===== AR-6C5D: APPROVED BULK REGISTRATION QUEUE SCHEMA (REVIEW ONLY) ====='
REQUIRED = ('accounts', 'access_audit_logs', 'registration_notification_outbox')
ADDITIONS = ('registration_bulk_jobs', 'registration_bulk_job_items')


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest().upper()


def tables_of(text: str) -> list[str]:
    return re.findall(r'^\s*Table\s+([a-zA-Z_][a-zA-Z_0-9]*)\s*\{', text, re.M | re.I)


def body_of(text: str, table: str) -> str:
    m = re.search(r'^Table\s+' + re.escape(table) + r'\s*\{\s*\n(.*?)^\}', text, re.M | re.S)
    if not m:
        raise ValueError(f'Cannot find well-formed {table} block')
    return m.group(1)


def validate_target(text: str) -> None:
    names = tables_of(text)
    for name in REQUIRED:
        if names.count(name) != 1:
            raise ValueError(f'Official ERD must contain exactly one {name} table')
    for name in ADDITIONS:
        if name in names:
            raise ValueError(f'{name} is already present; refusing to append a duplicate')
    if MARKER in text:
        raise ValueError('AR-6C5D amendment marker already exists')
    for table, pk in [('accounts', 'account_id'), ('access_audit_logs', 'access_audit_log_id')]:
        body = body_of(text, table)
        if not re.search(r'^\s*' + re.escape(pk) + r'\s+int\s+\[pk\s*,\s*increment\]', body, re.M):
            raise ValueError(f'{table}.{pk} is not the approved int primary key')
    if not re.search(r'^\s*outbox_id\s+bigint\s+\[pk\s*,\s*increment\]', body_of(text, 'registration_notification_outbox'), re.M):
        raise ValueError('Unexpected notification outbox key type; manual review required')


def validate_fragment(text: str) -> None:
    names = tables_of(text)
    if names != list(ADDITIONS):
        raise ValueError(f'Expected only {ADDITIONS}; got {names}')
    for fragment in (
        'Ref: registration_bulk_jobs.requested_by_account_id > accounts.account_id',
        'Ref: registration_bulk_job_items.bulk_job_id > registration_bulk_jobs.bulk_job_id',
        'Ref: registration_bulk_job_items.target_account_id > accounts.account_id',
        'Ref: registration_bulk_job_items.decision_audit_log_id > access_audit_logs.access_audit_log_id',
        'request_fingerprint binary(32)',
        'next_attempt_at datetime',
        'decision_audit_log_id int [unique',
    ):
        if fragment not in text:
            raise ValueError(f'Fragment missing required design element: {fragment}')


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Modify the official DBML after validation and backup')
    args = parser.parse_args()
    repo = Path(__file__).resolve().parents[2]
    target = repo / 'docs/database/full_schema.dbml'
    fragment_file = repo / 'docs/database/proposals/AR6C5D_BULK_QUEUE_APPROVED_FOR_REVIEW.dbml'
    if not target.is_file() or not fragment_file.is_file():
        print('Missing official ERD or approved fragment; copy patch folders to repository root.', file=sys.stderr)
        return 2
    old = target.read_bytes()
    digest = sha(old)
    print(f'Official ERD: {target}')
    print(f'Current SHA-256: {digest}')
    if digest != EXPECTED_SHA256:
        print('BLOCKED: official ERD SHA-256 does not match owner-verified source. Do not overwrite; inspect changes.', file=sys.stderr)
        return 2
    try:
        source = old.decode('utf-8-sig')
        fragment = fragment_file.read_text(encoding='utf-8')
        validate_target(source)
        validate_fragment(fragment)
    except (UnicodeError, ValueError) as exc:
        print(f'BLOCKED: {exc}', file=sys.stderr)
        return 2

    newline = '\r\n' if b'\r\n' in old else '\n'
    addition = (MARKER + '\n' + fragment.strip() + '\n').replace('\n', newline).encode('utf-8')
    prefix = b'' if old.endswith((b'\r\n', b'\n')) else newline.encode('utf-8')
    updated = old + prefix + newline.encode('utf-8') + addition
    # Byte-for-byte preserve old content; only append.
    assert updated.startswith(old)
    print(f'New official ERD SHA-256 (proposed): {sha(updated)}')
    print('Tables added: registration_bulk_jobs, registration_bulk_job_items')
    if not args.apply:
        print('\nDRY RUN ONLY. No file was changed. Review the proposed appended DBML:')
        preview = '\n'.join(difflib.unified_diff(
            source.splitlines(), updated.decode('utf-8-sig').splitlines(),
            fromfile='full_schema.dbml (current)', tofile='full_schema.dbml (proposed)', lineterm=''
        ))
        print(preview)
        print('\nTo apply after review, rerun with --apply.')
        return 0

    backup_dir = Path.home() / 'Documents' / 'CTUG-Private-Backups'
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup = backup_dir / f'full_schema.before_AR6C5D_{digest[:12]}.dbml'
    if backup.exists() and backup.read_bytes() != old:
        print(f'BLOCKED: existing backup differs from current file: {backup}', file=sys.stderr)
        return 2
    if not backup.exists():
        # Create backup with exclusive creation; never overwrite.
        with backup.open('xb') as f:
            f.write(old)
    print(f'Backup: {backup}')
    # Recheck immediately before replace, preventing an accidental stale write.
    if target.read_bytes() != old:
        print('BLOCKED: ERD changed during review; no replacement made.', file=sys.stderr)
        return 2
    fd, temp_path = tempfile.mkstemp(prefix='.full_schema_ar6c5d_', suffix='.tmp', dir=target.parent)
    try:
        with os.fdopen(fd, 'wb') as tmp:
            tmp.write(updated)
            tmp.flush()
            os.fsync(tmp.fileno())
        shutil.copymode(target, temp_path)
        os.replace(temp_path, target)
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)
    print(f'APPLIED: official ERD updated by append-only amendment. New SHA-256: {sha(target.read_bytes())}')
    print('No Django model imported; no migration created or executed; no database modified.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
