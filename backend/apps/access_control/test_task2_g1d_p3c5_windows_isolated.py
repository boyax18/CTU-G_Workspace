"""Offline tests for Windows-only disposable named-pipe MySQL driver."""

import os
import pathlib
import subprocess
import tempfile
import unittest
from unittest.mock import Mock, patch

from apps.access_control.tests_support import g1d_p3c5_windows_pipe_fence_test_only as m


class TestP3C5WindowsNamedPipeAdapter(unittest.TestCase):
    def setUp(self):
        # This constructor does not start any server, connect or write files.
        self.driver = m.WindowsNamedPipeRehearsal.__new__(m.WindowsNamedPipeRehearsal)
        self.driver.bin = pathlib.Path('X:/Synthetic/MySQL Server 8.4/bin')
        self.driver.pipe = 'ctug_p3c5_testing_unique'
        self.driver.data = pathlib.Path(os.getcwd()) / 'synthetic-data'
        self.driver.proc = None
        self.driver.work = None
        self.driver.root_password = 'a' * 48
        self.driver.web_password = 'b' * 48
        self.driver.executor_password = 'c' * 48
        self.driver._root_secured = False
        self.driver.container = 'synthetic-cleanup-id'

    def test_checkpoint_blocks_production(self):
        self.assertNotEqual(m.CHECKPOINT, 'PRODUCTION')
        self.assertNotIn('ctug_workspace', m.CHECKPOINT)
        self.assertEqual('P3C5_SECOND_SERVER_NO_PRODUCTION', m.ACKNOWLEDGEMENT)

    def test_server_options_require_unique_pipe_and_no_tcp(self):
        args = m._isolated_server_options(self.driver.bin, self.driver.data, self.driver.pipe,
                                          pathlib.Path('server.err'), pathlib.Path('p3c5.pid'))
        self.assertEqual('--no-defaults', args[1])
        self.assertIn('--skip-networking', args)
        self.assertIn('--mysqlx=OFF', args)
        self.assertIn('--named-pipe=ON', args)
        self.assertIn('--socket=' + self.driver.pipe, args)
        self.assertIn('--standalone', args)
        self.assertTrue(any(x.startswith('--datadir=') for x in args))
        self.assertTrue(all('--defaults-file=' not in x for x in args))

    def test_client_options_prevent_fallback_to_tcp_or_login_paths(self):
        for principal in ('root', 'ctug_p3c5_web', 'ctug_p3c5_executor'):
            args = m._client_options(self.driver.bin, self.driver.pipe, principal, True)
            self.assertEqual('--no-defaults', args[1])
            self.assertIn('--no-login-paths', args)
            self.assertIn('--protocol=PIPE', args)
            self.assertIn('--host=.', args)
            self.assertIn('--socket=' + self.driver.pipe, args)
            self.assertIn('--user=' + principal, args)
            self.assertIn('--database=ctug_p3c5_disposable', args)
            self.assertFalse(any(x.startswith('--port=') for x in args))

    def test_named_pipe_requests_rsa_key_for_first_post_rotation_login(self):
        # MySQL 8.4 caching_sha2_password clears cache after ALTER USER.
        # Windows named pipes are not considered secure transport.
        for principal in ('root', 'ctug_p3c5_web', 'ctug_p3c5_executor'):
            args = m._client_options(self.driver.bin, self.driver.pipe, principal, False)
            self.assertIn('--get-server-public-key', args)
            self.assertIn('--protocol=PIPE', args)
            self.assertNotIn('--protocol=TCP', args)

    def test_missing_pipe_or_schema_prevents_identity_verification(self):
        class Process:
            def poll(self): return None
        self.driver.proc = Process()
        self.assertFalse(self.driver._identity_verified(''))
        self.assertFalse(self.driver._identity_verified('x\t1\t1\tctug_p3c5_testing_unique\t8.4.13'))
        self.assertFalse(self.driver._identity_verified(str(self.driver.data) + '\t0\t1\t' + self.driver.pipe + '\t8.4.13'))
        self.assertFalse(self.driver._identity_verified(str(self.driver.data) + '\t1\t0\t' + self.driver.pipe + '\t8.4.13'))
        self.assertFalse(self.driver._identity_verified(str(self.driver.data) + '\t1\t1\totherpipe\t8.4.13'))
        self.assertFalse(self.driver._identity_verified(str(self.driver.data) + '\t1\t1\t' + self.driver.pipe + '\t8.0.40'))
        self.assertTrue(self.driver._identity_verified(str(self.driver.data) + '\t1\t1\t' + self.driver.pipe + '\t8.4.13'))

    def test_stopped_process_fails_identity(self):
        class Process:
            def poll(self): return 1
        self.driver.proc = Process()
        self.assertFalse(self.driver._identity_verified(str(self.driver.data) + '\t1\t1\t' + self.driver.pipe + '\t8.4.13'))

    def test_no_database_schema_for_root(self):
        self.assertFalse(any(x.startswith('--database') for x in m._client_options(self.driver.bin, self.driver.pipe, 'root', False)))

    def test_no_ambient_mysql_password_or_default_config(self):
        def run(args, **kw):
            self.assertNotIn('MYSQL_PWD', kw['env'])
            self.assertNotIn('MYSQL_HOME', kw['env'])
            self.assertNotIn('MYSQL_TEST_LOGIN_FILE', kw['env'])
            self.assertNotIn('MYSQL_TCP_PORT', kw['env'])
            return subprocess.CompletedProcess(args, 0, 'OK', '')
        with patch.dict(os.environ, {'MYSQL_PWD': 'actual-workspace-secret', 'MYSQL_TEST_LOGIN_FILE': 'local-file'}), patch.object(m.subprocess, 'run', side_effect=run):
            self.assertEqual('OK', self.driver._invoke(['mysql'], 'SELECT 1').stdout)

    def test_generated_password_not_in_process_arguments(self):
        def run(args, **kw):
            self.assertEqual('test-only', kw['env']['MYSQL_PWD'])
            self.assertNotIn('test-only', ' '.join(args))
            return subprocess.CompletedProcess(args, 0, 'OK', '')
        with patch.object(m.subprocess, 'run', side_effect=run):
            self.driver._invoke(['mysql'], 'SELECT 1', password='test-only')

    def test_root_unsecured_connection_has_no_password_prompt(self):
        with patch.object(self.driver, '_invoke', return_value=subprocess.CompletedProcess([], 0, '', '')) as inv:
            self.driver._mysql('root', 'SELECT 1;')
            self.assertIn('--skip-password', inv.call_args[0][0])
            self.assertIsNone(inv.call_args[0][2])

    def test_live_credentials_not_read_from_environment(self):
        with patch.object(self.driver, '_invoke', return_value=subprocess.CompletedProcess([], 0, '', '')) as inv:
            self.driver._mysql('web', 'SELECT 1;')
            self.assertEqual('b' * 48, inv.call_args[0][2])

    def test_unknown_principal_aborts(self):
        with self.assertRaises(m.RehearsalError):
            self.driver._mysql('actual-workspace-account', 'SELECT 1;')

    def test_unexpected_cleanup_command_aborts(self):
        with self.assertRaises(m.RehearsalError):
            self.driver._docker(['rm', '--force', 'wrong-container'])
        with self.assertRaises(m.RehearsalError):
            self.driver._docker(['run', 'anything'])

    def test_no_django_config_imports_or_existing_db_name(self):
        text = pathlib.Path(m.__file__).read_text(encoding='utf-8')
        self.assertNotIn('django.conf', text)
        self.assertNotIn('load_dotenv', text)
        self.assertNotIn('ctug_workspace', text)
        self.assertNotIn('stop-service', text.lower())

    def test_non_windows_main_stops_without_starting_db(self):
        with patch.object(m.platform, 'system', return_value='Linux'), patch.object(m.WindowsNamedPipeRehearsal, 'run') as run:
            self.assertEqual(1, m.main(['--ack', m.ACKNOWLEDGEMENT]))
            run.assert_not_called()

    def test_client_invocation_timeout_fails_closed(self):
        with patch.object(m.subprocess, 'run', side_effect=subprocess.TimeoutExpired(['mysql'], 1)):
            with self.assertRaises(m.RehearsalError):
                self.driver._invoke(['mysql'], 'SELECT 1;')

    def test_windows_init_does_not_touch_existing_mysql_service(self):
        text = pathlib.Path(m.__file__).read_text(encoding='utf-8')
        self.assertNotIn('net stop', text.lower())
        self.assertNotIn('sc stop', text.lower())
        self.assertNotIn('taskkill', text.lower())
        self.assertNotIn('DROP DATABASE ctug_workspace', text)
        self.assertNotIn('--install', text)

    def test_cleanup_verifies_identity_and_gracefully_stops_child_server(self):
        with tempfile.TemporaryDirectory(prefix="ctug-p3c5-separate-") as directory:
            self.driver.work = pathlib.Path(directory)
            self.driver.data = self.driver.work / "data"
            self.driver.proc = Mock()
            self.driver.proc.poll.return_value = None
            identity = str(self.driver.data) + '\t1\t1\t' + self.driver.pipe + '\t8.4.13'
            with patch.object(self.driver, '_mysql', side_effect=[
                subprocess.CompletedProcess([], 0, identity, ''),
                subprocess.CompletedProcess([], 0, '', ''),
            ]) as mysql, patch.object(m.shutil, 'rmtree') as remove:
                self.driver._cleanup()
                self.assertEqual(('root', 'SHUTDOWN;'), mysql.call_args_list[1].args)
                self.driver.proc.wait.assert_called_once_with(timeout=12)
                self.driver.proc.terminate.assert_not_called()
                remove.assert_called_once_with(self.driver.work.resolve())

    def test_cleanup_refuses_shutdown_and_delete_on_identity_mismatch(self):
        self.driver.proc = Mock()
        self.driver.proc.poll.return_value = None
        with patch.object(self.driver, '_mysql', return_value=subprocess.CompletedProcess([], 0, 'wrong-instance', '')) as mysql:
            with patch.object(m.shutil, 'rmtree') as remove:
                with self.assertRaises(m.RehearsalError):
                    self.driver._cleanup()
                self.assertEqual(1, mysql.call_count)
                remove.assert_not_called()

    def test_cleanup_refuses_unowned_directory(self):
        with tempfile.TemporaryDirectory(prefix="other-owner-") as directory:
            self.driver.work = pathlib.Path(directory)
            self.driver.data = self.driver.work / "data"
            with patch.object(m.shutil, 'rmtree') as remove:
                with self.assertRaises(m.RehearsalError):
                    self.driver._cleanup()
                remove.assert_not_called()

    def test_cleanup_failure_is_never_silently_reported_as_success(self):
        with tempfile.TemporaryDirectory(prefix="ctug-p3c5-separate-") as directory:
            self.driver.work = pathlib.Path(directory)
            self.driver.data = self.driver.work / "data"
            with patch.object(m.shutil, 'rmtree', side_effect=OSError):
                with self.assertRaises(m.RehearsalError):
                    self.driver._cleanup()


if __name__ == '__main__':
    unittest.main()
