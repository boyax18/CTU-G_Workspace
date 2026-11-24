"""Create the git-ignored synthetic LAN secrets file once (stdlib only; never prints values).

    python backend/scripts/ctug_lan_local_secrets.py

Writes <repo>/.local/ctug-lan/synthetic.env with a dedicated Django secret key and a
dedicated 256-bit outbox wrapping key for the synthetic database. An existing file is
never overwritten (rotating the outbox key would make queued synthetic rows unreadable).
"""

import base64
import secrets
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
TARGET = REPO_ROOT / ".local" / "ctug-lan" / "synthetic.env"


def main():
    if TARGET.exists():
        print(f"Synthetic LAN secrets: existing ({TARGET})")
        return 0
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    content = (
        "# CTU-G Workspace synthetic LAN profile secrets. Development only; git-ignored.\n"
        "# Never copy these into backend/.env or any real environment.\n"
        f"DJANGO_SECRET_KEY={secrets.token_urlsafe(50)}\n"
        f"WORKSPACE_OUTBOX_KEK_V1_B64={base64.b64encode(secrets.token_bytes(32)).decode('ascii')}\n"
    )
    with open(TARGET, "x", encoding="utf-8") as handle:  # "x": fail rather than overwrite
        handle.write(content)
    print(f"Synthetic LAN secrets: created ({TARGET})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
