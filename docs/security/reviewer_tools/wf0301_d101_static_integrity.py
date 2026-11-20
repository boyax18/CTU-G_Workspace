#!/usr/bin/env python3
"""Read-only D-101 source-integrity preflight (NOT independent approval).

Checks section 19.4 of WF-03.01_D-89_CATALOGUE_V2_1_INTEGRITY_REVIEW_PACKAGE.md.
Does not run Django, open a database, execute tests, or change files/roles.
The reviewer MUST check source pins and approval requirements independently.
"""
import argparse
import hashlib
from pathlib import Path
import subprocess
import sys

PINNED = [
  {
    "path": "docs/architecture/AR-3B2A-permission-catalogue-v2-proposal.md",
    "sha256": "56ccd699a127ac7a734bd53a2cb7d4a30a1d3953413e4c423897b4a9c9398b78",
    "source_commit": "14125f9",
    "git_blob": "5b3d1c38f9bbbf81835dd431cb376e7a0d125cc0"
  },
  {
    "path": "backend/apps/access_control/catalogue/c1_v1.json",
    "sha256": "86d72d82295cb358244145c6d24ebe8ba948f5211de298ebf897b5d3d83ed447",
    "source_commit": "14125f9",
    "git_blob": "1e55fa9e3fd7ce398c7295d3244c4c637eba3b32"
  },
  {
    "path": "docs/implementation/access-control/phase1h-c1-permission-catalogue-governance-proposal.md",
    "sha256": "02eb308db5aff1491ea2d024f5f7f1074125e3a7b9bb02dbd1409f6a6170a99e",
    "source_commit": "14125f9",
    "git_blob": "f90e7bf2a71aa34f193d336a59bef0658a2d9129"
  },
  {
    "path": "docs/SRS/CTU-G_Workspace_SRS_v1.md",
    "sha256": "af4ead4f88bdb0877ab6c3b8965bec5caf0f058d74ab0d878ec690379210346f",
    "source_commit": "14125f9",
    "git_blob": "a9eadf80d99ea88084723da6695d3f2f9110104e"
  },
  {
    "path": "docs/architecture/AR-2-revised-administrator-access-control.md",
    "sha256": "b36c0dac6d18badc435cce242725d2d6424db9d7e12d6d4943f20c7eaaf8ce36",
    "source_commit": "14125f9",
    "git_blob": "27c7953db0cd6170a722c4401481fe11513b52b9"
  },
  {
    "path": "docs/architecture/AR-3A-administrator-architecture-finalization.md",
    "sha256": "464c0fec172ef5ba887dbc22ec5b09c3396ca1be53087d999bbf763966edded1",
    "source_commit": "14125f9",
    "git_blob": "3df6249e79e2379df52d2f3581574c7384ddc213"
  },
  {
    "path": "backend/apps/access_control/catalogue/v2_0.json",
    "sha256": "a7e2705236a37522b77468fd4154113d19e7e64bc479cfa420c41d7744a2548b",
    "source_commit": "14125f9",
    "git_blob": "5a1ca44bb6dd2e3b5876956924c24febdb3d38fb"
  },
  {
    "path": "backend/apps/access_control/catalogue/validation_v2.py",
    "sha256": "f6b83305db567dcafc57eba97011554587be4b65d6d3c7116dc6a80b9a756aa4",
    "source_commit": "14125f9",
    "git_blob": "5ade73984cf0e53f3083e961e205593047076905"
  },
  {
    "path": "docs/architecture/AR-3B2A-ADDENDUM-v2.1.md",
    "sha256": "78a3c7e2e0afd07a7c4c052e13f3503378076dc7f487d9ecf3bf1dc940e1afb7",
    "source_commit": "14125f9",
    "git_blob": "d6e37c9425b681e084ce96b7b2e862694e46261c"
  },
  {
    "path": "backend/apps/access_control/catalogue/v2_1_delta.json",
    "sha256": "b028a419bdc66a19a782f6a968464ffb2f4cec7e10630ec4c169e6cda549d3d8",
    "source_commit": "14125f9",
    "git_blob": "9069c3b8a3bdd06c5d029953d9eaf5dd79c8b685"
  },
  {
    "path": "backend/apps/access_control/catalogue/validation_v2_1.py",
    "sha256": "e176f9267b69baae7546d060064254d26a3e7df7a106b6505e941cb5b83d98b3",
    "source_commit": "9e259e7",
    "git_blob": "38ba7c9069e14f1905b6439627123af4546a9847"
  },
  {
    "path": "backend/apps/access_control/test_catalogue_v2_1.py",
    "sha256": "f171e002c11b2aba118bd83ff486b2b8089bbf63e51ca462a20abd44841051c8",
    "source_commit": "9e259e7",
    "git_blob": "abd275810677155471f5fa0561d6c7b7e71cd46f"
  },
  {
    "path": "backend/apps/access_control/test_wf0301_d89_catalogue_v21_runtime.py",
    "sha256": "6b4f90c6cbff9fd47bce1df628cd14dbedf027d472282215191777ef5ec40ff3",
    "source_commit": "14125f9",
    "git_blob": "117f25d21e62163634e4b76fed5e0d6586aed9eb"
  },
  {
    "path": "docs/architecture/AR-3B2A-ADDENDUM-v2.2.md",
    "sha256": "4285837e51f5331bb54fab50246c25d4efb0bbd65905a567368ba7e6681f8fdd",
    "source_commit": "28d46e1",
    "git_blob": "746d669a4d289600924914d7af1c9bbc123fafd0"
  },
  {
    "path": "backend/apps/access_control/catalogue/v2_2_delta.json",
    "sha256": "3b92b83139bd766990697d999ff8b2c2d4a9faace37ca7391cb66721b8f2b0d2",
    "source_commit": "28d46e1",
    "git_blob": "adf7a2d461f85ccf33af3c58ab9d998c2cd87529"
  },
  {
    "path": "backend/apps/access_control/catalogue/validation_v2_2.py",
    "sha256": "d03aab4841514d02493f572dcd179441aea11ea1c33f89d965d2c007813803c0",
    "source_commit": "28d46e1",
    "git_blob": "f4fb1d71d99f8c4c59ba65bc3c7473858c44fc66"
  },
  {
    "path": "backend/apps/access_control/test_catalogue_v2_2.py",
    "sha256": "cf50cdfefa637c63a6913729742e06750044eac9d2dbedc96203484d1ff7cc10",
    "source_commit": "9e259e7",
    "git_blob": "ac0a2ba1794ed457859ab22e22c9da4759be6ab0"
  },
  {
    "path": "backend/apps/access_control/test_wf0301_d103_catalogue_v22_runtime.py",
    "sha256": "c35aa4cf4a7bd342d273893268e551f181992273d896adcafe29d70118f33d33",
    "source_commit": "28d46e1",
    "git_blob": "3be56086e41343f473d5a3f6c486d27ca235f16c"
  },
  {
    "path": ".gitattributes",
    "sha256": "16b13fcbf7111184b8d76ea773db020b18da82ed7cd076bef366636cdccb10f9",
    "source_commit": "28d46e1",
    "git_blob": "4fc4e67eeb8b95ac12d93883aff766c339c52e39"
  }
]


def git(repo, *args, binary=False):
    result = subprocess.run(
        ['git', '-C', str(repo), *args], capture_output=True, check=False
    )
    if result.returncode:
        raise RuntimeError('git ' + ' '.join(args) + ': ' + result.stderr.decode('utf-8', 'replace').strip())
    return result.stdout if binary else result.stdout.decode('utf-8', 'replace').strip()


def main():
    ap = argparse.ArgumentParser(description='Read-only, author-provided D-101 static pin preflight')
    ap.add_argument('--repo', required=True, help='CTU-G Workspace Git root')
    args = ap.parse_args()
    repo = Path(args.repo).resolve()
    if not (repo / '.git').exists():
        print('FAIL: expected Git repository root', file=sys.stderr)
        return 2
    try:
        head = git(repo, 'rev-parse', 'HEAD')
        print('Current HEAD:', head)
        print('Scope: 19 pinned artifacts, Git blob bytes only; no tests, no database')
        failures = 0
        for item in PINNED:
            rel=item['path']
            ref=item['source_commit']
            try:
                scoped=git(repo, 'show', f'{ref}:{rel}', binary=True)
                current=git(repo, 'show', f'HEAD:{rel}', binary=True)
                sha_ref=hashlib.sha256(scoped).hexdigest()
                sha_head=hashlib.sha256(current).hexdigest()
                blob_ref=git(repo, 'rev-parse', f'{ref}:{rel}')
                ok=(sha_ref == item['sha256'] and sha_head == item['sha256'] and blob_ref == item['git_blob'])
                if not ok:
                    failures += 1
                print(('MATCH' if ok else 'MISMATCH') + ': ' + rel + ' [' + ref + ']')
                if not ok:
                    print('    scope SHA:',sha_ref, 'HEAD SHA:',sha_head,'scope Git blob:',blob_ref)
            except Exception as exc:
                failures+=1
                print('ERROR:',rel, str(exc))
        print(f'\nStatic preflight: {len(PINNED)-failures}/{len(PINNED)} files match')
        print('D-101 remains OPEN until an independent qualified reviewer performs the required full review, runs evidence tests, and signs v2.1 then v2.2.')
        print('D-102 implementation/authorization and S0-to-S1 extension remain BLOCKED.')
        return 1 if failures else 0
    except Exception as exc:
        print('FAIL:',exc,file=sys.stderr)
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
