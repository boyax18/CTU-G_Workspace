"""Opt-in, narrowly scoped dashboard mounting for AR-6C7E.1.

Run from project root:
    python -B frontend/scripts/apply_registration_review_live_panel_safe.py --check
    python -B frontend/scripts/apply_registration_review_live_panel_safe.py --apply

The target remains visually unchanged while the independently hardened API gate is FALSE.
No backend routes, permission flags or service states are changed.
"""
from __future__ import annotations

import argparse
import pathlib

IMPORT_ANCHOR = "import DashboardIcon from '../../components/dashboard/DashboardIcon';"
BRANCH_ANCHOR = "  if (view !== 'overview') {"
READ_HINT_GUARD = "  if (!canOpenDashboardView(view, permissions)) {"
INSERT_IMPORT = """import RegistrationReviewLivePanel from '../admin/RegistrationReviewLivePanel';
import { REGISTRATION_REVIEW_LIVE_API_ENABLED } from '../admin/registrationReviewApiGate';"""
INSERT_BRANCH = """  // AR-6C7E.1: only visible after independently approved frontend/backend activation.
  if (view === 'registration-review' && REGISTRATION_REVIEW_LIVE_API_ENABLED) {
    return <RegistrationReviewLivePanel roles={account.roles} permissions={permissions} />;
  }

"""


def main():
    parser = argparse.ArgumentParser()
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument('--check', action='store_true')
    choice.add_argument('--apply', action='store_true')
    args = parser.parse_args()

    project = pathlib.Path(__file__).resolve().parents[1]
    target = project / 'src/features/dashboard/SessionDashboardPage.tsx'
    gate = project / 'src/features/admin/registrationReviewApiGate.ts'
    root = project / 'src/features/admin/registrationReviewLiveConfig.ts'
    panel = project / 'src/features/admin/RegistrationReviewLivePanel.tsx'
    if not all(path.is_file() for path in (target, gate, root, panel)):
        raise SystemExit('STOP: Required frontend file missing.')
    if 'REGISTRATION_REVIEW_LIVE_API_ENABLED: boolean = false;' not in gate.read_text(encoding='utf-8'):
        raise SystemExit('STOP: Live API gate must remain explicitly FALSE.')
    if 'REGISTRATION_REVIEW_APPROVED_ROUTE_ROOT: string | null = null;' not in root.read_text(encoding='utf-8'):
        raise SystemExit('STOP: Approved route root must remain NULL.')

    original = target.read_bytes()
    data = original.decode('utf-8-sig')
    normalized = data.replace('\r\n', '\n')
    if INSERT_IMPORT in normalized or 'RegistrationReviewLivePanel' in normalized:
        raise SystemExit('STOP: Already patched or unexpected live panel reference.')
    for anchor in (IMPORT_ANCHOR, BRANCH_ANCHOR, READ_HINT_GUARD):
        if normalized.count(anchor) != 1:
            raise SystemExit('STOP: Expected dashboard anchor absent/duplicated; review local changes.')
    if normalized.index(READ_HINT_GUARD) > normalized.index(BRANCH_ANCHOR):
        raise SystemExit('STOP: Permission-hint guard no longer precedes live module routing.')
    patched = normalized.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + '\n' + INSERT_IMPORT, 1)
    patched = patched.replace(BRANCH_ANCHOR, INSERT_BRANCH + BRANCH_ANCHOR, 1)
    if args.check:
        print('CHECK PASSED: Dashboard integration is compatible; NO FILES CHANGED.')
        print('Live API gate remains FALSE, approved root NULL, Django URLconf untouched.')
        return
    formatted = patched.replace('\n', '\r\n' if '\r\n' in data else '\n')
    target.write_bytes((b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'') + formatted.encode('utf-8'))
    print('APPLIED: Only frontend/src/features/dashboard/SessionDashboardPage.tsx changed.')
    print('Live UI and API remain disabled, approved root NULL. Review git diff before commit.')


if __name__ == '__main__':
    main()
