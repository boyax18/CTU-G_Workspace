"""G1D-P3C1: read-only, partial privileged-writer source inventory (TEST ONLY).

This scanner is a *triage aid*, NOT a complete privileged-writer inventory,
DBA attestment, write fence, or authorization to create a protected role.
It does not connect to MySQL or execute scanned Python modules.
"""

from dataclasses import dataclass
from pathlib import Path
import argparse
import ast
import json
import re


WATCHED_MODELS = frozenset({
    "Role", "AccountRole", "RolePermission", "AccountPermission",
    "Permission", "Service",
})
MUTATIONS = frozenset({
    "create", "get_or_create", "update_or_create", "bulk_create",
    "bulk_update", "update", "delete",
})
TABLES = (
    "roles", "account_roles", "role_permissions", "account_permissions",
    "permissions", "services",
)
SQL_MUTATION = re.compile(
    r"\b(?:INSERT\s+INTO|UPDATE|DELETE\s+FROM|ALTER\s+TABLE|DROP\s+TABLE|CREATE\s+TABLE)"
    r"\s+[`\"]?(" + "|".join(TABLES) + r")\b", re.IGNORECASE,
)
SKIP_PARTS = frozenset({
    ".git", ".venv", "venv", "node_modules", "__pycache__", "tests_support",
    "migrations", ".pytest_cache", "build", "dist",
})


@dataclass(frozen=True, order=True)
class Finding:
    path: str
    line: int
    category: str
    subject: str
    operation: str


def _skip(path):
    parts = Path(path.replace("\\", "/")).parts
    name = parts[-1] if parts else ""
    return (not name.endswith(".py") or name.startswith("test_") or
            name == "tests.py" or any(x in SKIP_PARTS or x.startswith(".") for x in parts))


def _model_aliases(tree):
    aliases = {x: x for x in WATCHED_MODELS}
    module_aliases = set()
    for item in ast.walk(tree):
        if isinstance(item, ast.ImportFrom):
            # Import alias can rename the model. This is still intentionally a
            # conservative *partial* heuristic, not a data-flow analysis.
            if item.module in {"apps.access_control.models", "models"}:
                for alias in item.names:
                    if alias.name in WATCHED_MODELS:
                        aliases[alias.asname or alias.name] = alias.name
        elif isinstance(item, ast.Import):
            for alias in item.names:
                if alias.name == "apps.access_control.models":
                    module_aliases.add(alias.asname or "models")
    return aliases, module_aliases


def _orm_model(base, aliases, module_aliases):
    # Recursively unwind queryset.filter(...).order_by(...).update(...).
    if isinstance(base, ast.Call):
        return _orm_model(base.func, aliases, module_aliases)
    if isinstance(base, ast.Attribute):
        if base.attr == "objects":
            model = base.value
            if isinstance(model, ast.Name):
                return aliases.get(model.id)
            if (isinstance(model, ast.Attribute) and
                isinstance(model.value, ast.Name) and model.value.id in module_aliases):
                return model.attr if model.attr in WATCHED_MODELS else None
        return _orm_model(base.value, aliases, module_aliases)
    return None


def scan_source(relative_path, source):
    """Inspect a caller-supplied .py text or bytes sample without executing it."""
    if _skip(relative_path):
        return ()
    if not isinstance(source, (bytes, str)):
        return (Finding(relative_path, 0, "unreadable_source", "?", "wrong type"),)
    if isinstance(source, bytes):
        try:
            source = source.decode("utf-8-sig")
        except UnicodeDecodeError:
            return (Finding(relative_path, 0, "unreadable_source", "?", "decode error"),)
    try:
        tree = ast.parse(source, filename=relative_path)
    except SyntaxError as exc:
        return (Finding(relative_path, exc.lineno or 0, "parse_error", "?", "manual review"),)
    aliases, module_aliases = _model_aliases(tree)
    findings = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        method = node.func.attr
        if method in MUTATIONS:
            model = _orm_model(node.func.value, aliases, module_aliases)
            if model is not None:
                findings.add(Finding(relative_path, node.lineno, "orm_mutation", model, method))
        if method not in {"execute", "executemany"}:
            continue
        if not node.args:
            findings.add(Finding(relative_path, node.lineno, "dynamic_sql", "?", "no query argument"))
            continue
        arg = node.args[0]
        if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
            matches = SQL_MUTATION.findall(arg.value)
            for name in matches:
                findings.add(Finding(relative_path, node.lineno, "sql_mutation", name.lower(), method))
        else:
            # Dynamic SQL cannot be proved SELECT-only by a syntax scan.
            findings.add(Finding(relative_path, node.lineno, "dynamic_sql", "?", method))
    return tuple(sorted(findings))


def scan_sources(sources):
    """Return (files_scanned, findings) from a dict of safe relative names."""
    found = []
    count = 0
    for name, content in sorted(sources.items()):
        if _skip(name):
            continue
        count += 1
        found.extend(scan_source(name, content))
    return count, tuple(sorted(found))


def scan_backend_directory(backend):
    """Read only *.py below backend/apps and backend/config, never follow symlinks."""
    backend = Path(backend)
    if not backend.is_dir():
        raise ValueError("Backend directory not found")
    sources = {}
    for parent in (backend / "apps", backend / "config"):
        if not parent.is_dir():
            continue
        for path in parent.rglob("*.py"):
            if path.is_symlink() or not path.is_file():
                continue
            rel = path.relative_to(backend).as_posix()
            if _skip(rel):
                continue
            try:
                sources[rel] = path.read_bytes()
            except OSError:
                sources[rel] = None  # unreadable_source -> manual review
    return scan_sources(sources)


def summary(files_scanned, findings):
    """ALWAYS returns BLOCKED: a static scan cannot prove exclusive MySQL writes."""
    return {
        "checkpoint": "G1D-P3C1-STATIC-TRIAGE-ONLY",
        "files_scanned": files_scanned,
        "findings": [f.__dict__ for f in findings],
        "release_status": "BLOCKED",
        "limitations": [
            "Cannot detect dynamic model aliases, instance.save(), indirect service writers or stored procedures",
            "Cannot enumerate DB accounts, external scripts, active sessions or production writers",
            "Cannot prove a real MySQL privilege fence, trust custody, backup/restore or release authorization",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description="READ-ONLY G1D-P3C1 source triage. NEVER authorizes live writes.")
    parser.add_argument("--backend-root", type=Path, required=True)
    args = parser.parse_args()
    count, findings = scan_backend_directory(args.backend_root)
    if count == 0:
        parser.error("No readable Python source files found; refuse empty inventory")
    print(json.dumps(summary(count, findings), indent=2))


if __name__ == "__main__":
    main()
