"""AR-6C7C: OFFLINE static contract validation only.

Reads exactly two JSON files. No Django imports, database connections,
permission writes, feature-flag edits, routing changes, or file writes.
This is NOT an approval, database diff, or activation procedure.
"""

from __future__ import annotations

import argparse
from hashlib import sha256
import json
from pathlib import Path
import sys

BACKEND = Path(__file__).resolve().parents[1]
CATALOGUE = BACKEND / 'apps' / 'access_control' / 'catalogue'
SOURCE_PATH = CATALOGUE / 'v2_0.json'
PROFILE_PATH = CATALOGUE / 'registration_review_profile_v0_1_draft.json'
SERVICES = ('accounts', 'access_control')
PERMISSIONS = (
    'accounts.registration_requests.read',
    'accounts.registration_requests.approve',
    'accounts.registration_requests.reject',
)
BINDINGS = tuple(('Admin', code) for code in PERMISSIONS)
GATE_NAMES = (
    'metadata_initialization', 'role_grants',
    'service_activation', 'api_activation',
)


class ProfileContractError(ValueError):
    """Profile is not an exact, safe review-only subset."""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ProfileContractError(message)


def load_local() -> tuple[dict, dict, str]:
    """Read only the explicitly named, versioned JSON files."""
    source_raw = SOURCE_PATH.read_bytes()
    profile_raw = PROFILE_PATH.read_bytes()
    return (json.loads(profile_raw), json.loads(source_raw),
            sha256(source_raw).hexdigest())


def verify(profile: dict, source: dict, source_digest: str) -> dict:
    """Strictly validate subset; never apply anything or query database."""
    require(isinstance(profile, dict), 'Profile must be an object')
    require(set(profile) == {
        'schema_version', 'profile_id', 'status', 'source',
        'allowlist', 'gates', 'approval',
    }, 'Unexpected/missing profile top-level fields')
    require(profile['schema_version'] == 'ctug-registration-review-activation-profile/v0.1',
            'Unrecognized profile schema')
    require(profile['profile_id'] == 'AR-6C7C-REGISTRATION-REVIEW-V0.1-DRAFT',
            'Unrecognized profile identity')
    require(profile['status'] == 'DRAFT_UNAPPROVED', 'Profile must remain unapproved')

    provenance = profile['source']
    require(isinstance(provenance, dict) and set(provenance) == {
        'manifest_version', 'source_revision', 'manifest_sha256',
    }, 'Invalid catalogue provenance')
    require(provenance['manifest_version'] == 'catalogue-v2.0', 'Wrong source manifest')
    require(provenance['source_revision'] == 'v2.0-review-1', 'Wrong source revision')
    require(provenance['manifest_sha256'] == source_digest, 'Source SHA-256 mismatch')
    require(source.get('manifest_version') == provenance['manifest_version'],
            'Catalogue version mismatch')
    require(source.get('source_revision') == provenance['source_revision'],
            'Catalogue revision mismatch')
    require(source.get('planning_only') is True, 'Catalogue no longer planning-only')

    allow = profile['allowlist']
    require(isinstance(allow, dict) and set(allow) == {
        'services', 'permissions', 'role_bindings',
    }, 'Unexpected/missing allowlist fields')
    require(allow['services'] == list(SERVICES), 'Service allowlist changed')
    require(allow['permissions'] == list(PERMISSIONS), 'Permission allowlist changed')
    require(allow['role_bindings'] == [
        {'role_name': 'Admin', 'permission_code': code} for code in PERMISSIONS
    ], 'Role binding allowlist changed')

    gates = profile['gates']
    require(isinstance(gates, dict) and set(gates) == set(GATE_NAMES),
            'Unexpected/missing activation gates')
    require(all(gates[k] == 'BLOCKED' for k in GATE_NAMES),
            'Every activation gate must remain BLOCKED')
    approval = profile['approval']
    require(isinstance(approval, dict) and set(approval) == {
        'system_owner', 'security_reviewer', 'change_ticket',
    } and all(v is None for v in approval.values()),
            'Draft is not allowed to claim approval')

    service_rows = source.get('services')
    permission_rows = source.get('permissions')
    source_bindings = source.get('default_bindings')
    require(isinstance(service_rows, list) and isinstance(permission_rows, list)
            and isinstance(source_bindings, list), 'Malformed source catalogue lists')
    require(len(service_rows) == 10 and len(permission_rows) == 95
            and len(source_bindings) == 106, 'Source catalogue counts changed')

    for code in SERVICES:
        matches = [row for row in service_rows if row.get('service_code') == code]
        require(len(matches) == 1, f'Missing/duplicate service: {code}')
    for code in PERMISSIONS:
        matches = [row for row in permission_rows if row.get('permission_code') == code]
        require(len(matches) == 1, f'Missing/duplicate permission: {code}')
        row = matches[0]
        require(row.get('service_code') == 'accounts', f'Wrong parent service: {code}')
        require(row.get('scope') == 'SCHOOL', f'Wrong scope: {code}')
        require(row.get('grant_protection') == 'GOV', f'Wrong grant protection: {code}')
        require(row.get('readiness') == 'P' and row.get('origin') == 'KEEP',
                f'Unexpected proposed status: {code}')
    for role, code in BINDINGS:
        matches = [row for row in source_bindings if
                   row.get('role_name') == role and row.get('permission_code') == code]
        require(len(matches) == 1, f'Missing/duplicate proposed binding: {role}/{code}')
    require(any(row.get('role_name') == 'Admin' for row in source.get('roles', [])),
            'Admin role missing in source')

    return {
        'mode': 'OFFLINE STATIC REVIEW ONLY',
        'profile': profile['profile_id'],
        'source_sha256': source_digest,
        'candidate_counts': {'services': len(SERVICES), 'permissions': len(PERMISSIONS),
                             'admin_role_bindings': len(BINDINGS)},
        'blocked_gates': list(GATE_NAMES),
        'database_checked': False,
        'database_changes': False,
        'runtime_approval': False,
        'notice': 'Static subset matches v2 proposal. NOT a DB diff; no writes or activation authorized.',
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--format', choices=('text', 'json'), default='text')
    args = parser.parse_args()
    try:
        report = verify(*load_local())
    except (ProfileContractError, OSError, ValueError, TypeError) as exc:
        print(f'STATIC REVIEW FAILED: {exc}', file=sys.stderr)
        return 1
    if args.format == 'json':
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(f"MODE: {report['mode']}")
        print(f"Profile: {report['profile']}")
        print(f"Candidate counts: {report['candidate_counts']}")
        print('Activation gates: all BLOCKED')
        print('Database accessed: NO')
        print('Database writes performed: NO')
        print(report['notice'])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
