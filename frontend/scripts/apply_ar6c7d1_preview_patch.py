"""AR-6C7D.1 opt-in, single-file frontend integration. NO backend or DB access.

Run from anywhere:
    python -B frontend/scripts/apply_ar6c7d1_preview_patch.py --check
    python -B frontend/scripts/apply_ar6c7d1_preview_patch.py --apply

Requires the exact previously reviewed dashboard file; refuses changed local source.
"""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path

# Updated by package author after canonical snapshot inspection.
EXPECTED_BASE_SHA256 = 'a3519f3fb578b212ed57da981f2718053251b5df969dff54dc70274cf933ef07'
IMPORT_ANCHOR = "import DashboardIcon from '../../components/dashboard/DashboardIcon';"
BRANCH_ANCHOR = "  if (view !== 'overview') {"
IMPORT_INSERT = """import RegistrationReviewPreview from '../admin/RegistrationReviewPreview';
import { REGISTRATION_REVIEW_UI_PREVIEW_ENABLED } from '../admin/registrationReviewPreviewGate';"""
BRANCH_INSERT = """  // AR-6C7D.1: fictional mock UI only; hard-disabled pending separate approval.
  if (view === 'registration-review' && REGISTRATION_REVIEW_UI_PREVIEW_ENABLED) {
    return <RegistrationReviewPreview permissions={permissions} />;
  }

"""


def main() -> None:
    parser = argparse.ArgumentParser(description='Safely review or install the disabled AR-6C7D.1 UI branch.')
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--check', action='store_true', help='Check all preconditions; do not change files')
    mode.add_argument('--apply', action='store_true', help='Patch only SessionDashboardPage.tsx after validation')
    args = parser.parse_args()

    frontend = Path(__file__).resolve().parents[1]
    target = frontend / 'src/features/dashboard/SessionDashboardPage.tsx'
    gate = frontend / 'src/features/admin/registrationReviewPreviewGate.ts'
    panel = frontend / 'src/features/admin/RegistrationReviewPreview.tsx'
    if not (target.is_file() and gate.is_file() and panel.is_file()):
        raise SystemExit('STOP: required frontend files are missing.')
    if 'REGISTRATION_REVIEW_UI_PREVIEW_ENABLED: boolean = false;' not in gate.read_text(encoding='utf-8'):
        raise SystemExit('STOP: preview gate must remain explicitly false.')

    original = target.read_bytes()
    raw = original.decode('utf-8-sig')
    newline = '\r\n' if '\r\n' in raw else '\n'
    canonical = raw.replace('\r\n', '\n')
    digest = hashlib.sha256(canonical.encode('utf-8')).hexdigest()
    if digest != EXPECTED_BASE_SHA256:
        raise SystemExit('STOP: local SessionDashboardPage.tsx differs from inspected baseline; do not overwrite. Share this result before editing.')
    if canonical.count(IMPORT_ANCHOR) != 1 or canonical.count(BRANCH_ANCHOR) != 1:
        raise SystemExit('STOP: expected insertion anchors were not found exactly once.')
    patched = canonical.replace(IMPORT_ANCHOR, IMPORT_ANCHOR + '\n' + IMPORT_INSERT, 1)
    patched = patched.replace(BRANCH_ANCHOR, BRANCH_INSERT + BRANCH_ANCHOR, 1)
    if args.check:
        print('PREVIEW PATCH CHECK PASSED — no files changed.')
        print('Will edit only frontend/src/features/dashboard/SessionDashboardPage.tsx.')
        print('Mock UI gate remains FALSE; no live routes or API calls will be added.')
        return

    backup = Path.home() / 'Downloads' / 'CTUG_AR6C7D1_SessionDashboardPage_before_patch.tsx'
    if backup.exists():
        raise SystemExit('STOP: existing backup must be reviewed first; not overwriting it.')
    if not backup.parent.is_dir():
        raise SystemExit('STOP: Downloads folder not found; no file changes.')
    backup.write_bytes(original)
    # Preserve Windows/Unix newline convention; keep existing BOM if any.
    encoded = patched.replace('\n', newline).encode('utf-8')
    if original.startswith(b'\xef\xbb\xbf'):
        encoded = b'\xef\xbb\xbf' + encoded
    target.write_bytes(encoded)
    print('Patched only:', target)
    print('Original backup:', backup)
    print('REGISTRATION_REVIEW_UI_PREVIEW_ENABLED stays FALSE. No APIs connected.')


if __name__ == '__main__':
    main()
