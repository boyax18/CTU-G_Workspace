"""G1D-P3C1 pure syntax-based source scanner tests: NO Django or database."""

from tempfile import TemporaryDirectory
from pathlib import Path
from unittest import TestCase

from apps.access_control.tests_support.g1d_p3c1_writer_inventory_test_only import (
    Finding, scan_source, scan_sources, scan_backend_directory, summary,
)


class WriterInventorySourceContracts(TestCase):
    SRC = "apps/access_control/services.py"

    def scan(self, code, path=None):
        return scan_source(path or self.SRC, code)

    def test_direct_role_creation_detected(self):
        self.assertIn(Finding(self.SRC, 1, "orm_mutation", "Role", "create"),
                      self.scan("Role.objects.create(role_name='Technical Super Admin')"))

    def test_alias_role_creation_detected(self):
        self.assertTrue(any(f.subject == "Role" for f in self.scan(
            "from apps.access_control.models import Role as PrivRole\nPrivRole.objects.create(is_active=False)")))

    def test_get_or_create_detected(self):
        self.assertEqual(self.scan("Role.objects.get_or_create(role_name='Admin')")[0].operation, "get_or_create")

    def test_bulk_and_filtered_updates_detected(self):
        findings = self.scan("RolePermission.objects.filter(is_active=True).update(is_active=False)\n"
                             "AccountRole.objects.bulk_create([])")
        self.assertEqual({(f.subject, f.operation) for f in findings},
                         {("RolePermission", "update"), ("AccountRole", "bulk_create")})

    def test_queryset_delete_detected(self):
        self.assertEqual(self.scan("AccountPermission.objects.filter(pk=1).delete()")[0].operation, "delete")

    def test_readonly_orm_not_reported_as_mutation(self):
        self.assertEqual(self.scan("Role.objects.filter(is_active=True).count()"), ())

    def test_static_sql_insert_detected(self):
        result = self.scan('cursor.execute("INSERT INTO `roles` (role_name) VALUES (%s)", ["Admin"])')
        self.assertEqual(result[0].category, "sql_mutation")
        self.assertEqual(result[0].subject, "roles")

    def test_dynamic_sql_flagged_for_review_even_if_select(self):
        result = self.scan('cursor.execute(f"SELECT * FROM {table}")')
        self.assertEqual(result[0].category, "dynamic_sql")

    def test_static_sql_select_not_reported(self):
        self.assertEqual(self.scan('cursor.execute("SELECT * FROM roles")'), ())

    def test_malformed_python_returns_visible_error(self):
        result = self.scan('def broken(: pass')
        self.assertEqual(result[0].category, "parse_error")

    def test_unreadable_source_returns_visible_error(self):
        result = self.scan(b"\xff\xfe")
        self.assertEqual(result[0].category, "unreadable_source")

    def test_missing_argument_flags_dynamic_sql(self):
        self.assertEqual(self.scan("cursor.execute()")[0].category, "dynamic_sql")

    def test_excludes_test_and_migration_paths(self):
        paths = ["apps/access_control/tests_support/a.py", "apps/access_control/test_actor.py",
                 "apps/access_control/migrations/0001_initial.py", "apps/access_control/.venv/secrets.py"]
        for path in paths:
            self.assertEqual(self.scan("Role.objects.create()", path=path), ())

    def test_excludes_non_python_names(self):
        self.assertEqual(self.scan("Role.objects.create()", path="apps/access_control/.env"), ())

    def test_summary_never_claims_ready(self):
        self.assertEqual(summary(100, ())["release_status"], "BLOCKED")
        self.assertIn("Cannot prove a real MySQL", summary(100, ())["limitations"][2])

    def test_file_scanner_never_modifies_source(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            source = root / "apps" / "access_control" / "services.py"
            source.parent.mkdir(parents=True)
            data = b"Role.objects.create(role_name='Admin')\n"
            source.write_bytes(data)
            files, findings = scan_backend_directory(root)
            self.assertEqual(files, 1)
            self.assertEqual(source.read_bytes(), data)
            self.assertEqual(len(findings), 1)

    def test_directory_scanner_ignores_symlink_if_supported(self):
        with TemporaryDirectory() as d:
            root = Path(d)
            safe = root / "apps" / "access_control"
            safe.mkdir(parents=True)
            target = root / "external.py"
            target.write_text("Role.objects.create()")
            link = safe / "hidden.py"
            try:
                link.symlink_to(target)
            except (OSError, NotImplementedError):
                return
            files, findings = scan_backend_directory(root)
            self.assertEqual((files, findings), (0, ()))

    def test_duplicate_sources_sorted(self):
        count, findings = scan_sources({
            "apps/access_control/z.py": b"Role.objects.create()",
            "apps/access_control/a.py": b"Service.objects.create()",
        })
        self.assertEqual(count, 2)
        self.assertEqual([f.path for f in findings], ["apps/access_control/a.py", "apps/access_control/z.py"])

    def test_scan_reports_nonexistent_backend(self):
        with TemporaryDirectory() as root:
            with self.assertRaises(ValueError):
                scan_backend_directory(Path(root) / "missing")

    def test_does_not_inspect_environment_or_gitignore(self):
        count, results = scan_sources({
            "apps/access_control/.env": b"DO_NOT_READ",
            "apps/access_control/.gitignore": b"DO_NOT_READ",
            "apps/access_control/module.py": b"Role.objects.create()",
        })
        self.assertEqual((count, len(results)), (1, 1))
