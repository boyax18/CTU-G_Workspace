"""Compile proposed frontend sources in a fresh ignored copy; never modify active app files."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from prepare_runtime_patch import ROOT, proposed_files


if __name__ == "__main__":
    destination = Path(tempfile.mkdtemp(prefix="wf11-v23-frontend-", dir=ROOT / ".local")).resolve()
    if not destination.is_relative_to((ROOT / ".local").resolve()):
        raise RuntimeError("Invalid candidate frontend destination.")
    frontend = destination / "frontend"
    shutil.copytree(ROOT / "frontend", frontend, ignore=shutil.ignore_patterns(
        "node_modules", "dist", ".env", ".env.*", "*.tsbuildinfo"))
    for relative, content in proposed_files().items():
        if relative.startswith("frontend/"):
            (destination / relative).write_text(content, encoding="utf-8", newline="\n")
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    subprocess.run(["node", "-e", "require('fs').symlinkSync(process.argv[1],process.argv[2],'junction')",
                    str(ROOT / "frontend/node_modules"), str(frontend / "node_modules")],
                   check=True, creationflags=flags)
    env = dict(os.environ)
    import sys
    sys.path.insert(0, str(ROOT / "backend"))
    from config.dev_features import FEATURES
    for feature in FEATURES:
        for name in feature.frontend_flags:
            env[name] = "0"
    print("Compiling proposed frontend with feature flags off in:", frontend, flush=True)
    # Direct Node entry points avoid Windows batch-shim ambiguity and run package.json's exact
    # two build stages. A zero exit code alone is insufficient: require the output artifact too.
    for args in (["node", str(frontend / "node_modules/typescript/bin/tsc"), "-b"],
                 ["node", str(frontend / "node_modules/vite/bin/vite.js"), "build"]):
        subprocess.run(args, cwd=frontend, env=env, creationflags=flags, check=True)
    if not (frontend / "dist/index.html").is_file():
        raise RuntimeError("Candidate build produced no output artifact.")
    print("Proposed TypeScript and Vite build verified; active frontend unchanged.", flush=True)
