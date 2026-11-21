"""Task 2: real loopback mTLS integration, without executor DB or privilege changes.

The *actual* executor HTTPS server and web client's transport are exercised with
short-lived fictional certificates.  A fake, read-only executor provides /ready.
No profile is activated; no MySQL service, account, table, or role is touched.
"""
from datetime import datetime, timedelta, timezone
import hashlib
import http.client
import ipaddress
from pathlib import Path
import ssl
import tempfile
from threading import Thread

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
from django.test import SimpleTestCase, override_settings

from apps.access_control.executor.client import transport
from apps.access_control.executor.server import make_server
from apps.access_control.writer_boundary import WriterBoundaryUnavailable


def _key():
    return ec.generate_private_key(ec.SECP256R1())


def _write_key(path, key):
    path.write_bytes(key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ))


def _identity(ca_key, ca_cert, common_name, usage):
    key = _key()
    now = datetime.now(timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, common_name)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(ca_cert.subject)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.ExtendedKeyUsage([usage]), critical=False)
    )
    if usage == ExtendedKeyUsageOID.SERVER_AUTH:
        builder = builder.add_extension(
            x509.SubjectAlternativeName([x509.IPAddress(ipaddress.ip_address('127.0.0.1'))]),
            critical=False,
        )
    return key, builder.sign(ca_key, hashes.SHA256())


def _ca():
    key = _key()
    now = datetime.now(timezone.utc)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, 'CTUG loopback test CA')])
    cert = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=5))
        .not_valid_after(now + timedelta(days=1))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.KeyUsage(
            digital_signature=True, content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False, key_cert_sign=True,
            crl_sign=True, encipher_only=False, decipher_only=False,
        ), critical=True)
        .sign(key, hashes.SHA256())
    )
    return key, cert


class _ReadOnlyExecutor:
    config = {}  # no isolated_datadir; no secrets or traceback in request responses

    def __init__(self):
        self.ready_peers = []
        self.other_calls = []

    def ready(self, peer):
        self.ready_peers.append(peer)
        return {'kind': 'ordinary', 'schema': 'fictional_loopback', 'isolated': True}

    def execute(self, value, peer):
        self.other_calls.append('execute')
        raise RuntimeError('Loopback harness refuses writes')

    def authenticate(self, value, peer):
        self.other_calls.append('authenticate')
        raise RuntimeError('Loopback harness refuses authentication')

    def receipt(self, value, peer):
        self.other_calls.append('receipt')
        raise RuntimeError('Loopback harness refuses receipts')


class WF03LoopbackMTLSTests(SimpleTestCase):
    """Real TLS 1.3 socket handshakes on loopback, no database access."""

    def setUp(self):
        directory = tempfile.TemporaryDirectory(prefix='ctug-mtls-test-')
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        ca_key, ca_cert = _ca()
        server_key, server_cert = _identity(ca_key, ca_cert, 'test-executor', ExtendedKeyUsageOID.SERVER_AUTH)
        client_key, client_cert = _identity(ca_key, ca_cert, 'test-runtime', ExtendedKeyUsageOID.CLIENT_AUTH)
        other_ca_key, other_ca_cert = _ca()
        outsider_key, outsider_cert = _identity(other_ca_key, other_ca_cert, 'untrusted-runtime', ExtendedKeyUsageOID.CLIENT_AUTH)
        ca_path = root / 'ca.pem'
        ca_path.write_bytes(ca_cert.public_bytes(serialization.Encoding.PEM))
        server_cert_path, server_key_path = root / 'server.pem', root / 'server.key'
        server_cert_path.write_bytes(server_cert.public_bytes(serialization.Encoding.PEM))
        _write_key(server_key_path, server_key)
        client_cert_path, client_key_path = root / 'client.pem', root / 'client.key'
        client_cert_path.write_bytes(client_cert.public_bytes(serialization.Encoding.PEM))
        _write_key(client_key_path, client_key)
        outsider_cert_path, outsider_key_path = root / 'outsider.pem', root / 'outsider.key'
        outsider_cert_path.write_bytes(outsider_cert.public_bytes(serialization.Encoding.PEM))
        _write_key(outsider_key_path, outsider_key)

        self.fake_executor = _ReadOnlyExecutor()
        self.server = make_server(
            ('127.0.0.1', 0), self.fake_executor,
            ca=str(ca_path), certificate=str(server_cert_path), private_key=str(server_key_path),
        )
        self.thread = Thread(target=self.server.serve_forever, kwargs={'poll_interval': 0.01}, daemon=True)
        self.thread.start()
        self.addCleanup(self._stop_server)

        self.port = self.server.server_address[1]
        self.client = {
            'url': f'https://127.0.0.1:{self.port}', 'ca': str(ca_path),
            'certificate': str(client_cert_path), 'private_key': str(client_key_path),
            'server_fingerprint': hashlib.sha256(
                server_cert.public_bytes(serialization.Encoding.DER)
            ).hexdigest(),
        }
        self.client_fingerprint = hashlib.sha256(
            client_cert.public_bytes(serialization.Encoding.DER)
        ).hexdigest()
        self.outsider = {'certificate': str(outsider_cert_path), 'private_key': str(outsider_key_path)}

    def _stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)

    def _call(self, path='/ready', value=None, config=None):
        with override_settings(WORKSPACE_EXECUTOR_CLIENTS={'ordinary': config or self.client}):
            return transport(path, {} if value is None else value)

    def test_real_tls13_mutual_auth_ready_and_peer_identity(self):
        self.assertEqual(
            self._call(),
            {'kind': 'ordinary', 'schema': 'fictional_loopback', 'isolated': True},
        )
        self.assertEqual(self.fake_executor.ready_peers, [self.client_fingerprint])
        self.assertFalse(self.fake_executor.other_calls)

    def test_server_certificate_fingerprint_mismatch_fails_before_post(self):
        config = {**self.client, 'server_fingerprint': '0' * 64}
        with self.assertRaises(WriterBoundaryUnavailable):
            self._call(config=config)
        self.assertFalse(self.fake_executor.ready_peers)

    def test_untrusted_client_certificate_cannot_call_ready(self):
        config = {**self.client, **self.outsider}
        with self.assertRaises(WriterBoundaryUnavailable):
            self._call(config=config)
        self.assertFalse(self.fake_executor.ready_peers)

    def test_client_without_certificate_cannot_call_ready(self):
        context = ssl.create_default_context(cafile=self.client['ca'])
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        conn = http.client.HTTPSConnection('127.0.0.1', self.port, context=context, timeout=3)
        try:
            with self.assertRaises((ssl.SSLError, OSError, http.client.HTTPException)):
                conn.request('POST', '/ready', b'{}', {'Content-Length': '2'})
                conn.getresponse().read()
        finally:
            conn.close()
        self.assertFalse(self.fake_executor.ready_peers)

    def test_tls12_is_rejected_before_http_request(self):
        context = ssl.create_default_context(cafile=self.client['ca'])
        context.maximum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(self.client['certificate'], self.client['private_key'])
        conn = http.client.HTTPSConnection('127.0.0.1', self.port, context=context, timeout=3)
        try:
            with self.assertRaises((ssl.SSLError, OSError)):
                conn.connect()
        finally:
            conn.close()
        self.assertFalse(self.fake_executor.ready_peers)

    def test_plain_http_url_refused_before_connecting(self):
        with self.assertRaises(WriterBoundaryUnavailable):
            self._call(config={**self.client, 'url': f'http://127.0.0.1:{self.port}'})
        self.assertFalse(self.fake_executor.ready_peers)

    def test_unknown_executor_path_fails_closed(self):
        with self.assertRaises(WriterBoundaryUnavailable):
            self._call(path='/raw-sql')
        self.assertFalse(self.fake_executor.ready_peers)
        self.assertFalse(self.fake_executor.other_calls)

    def test_ready_requires_empty_json_object(self):
        with self.assertRaises(WriterBoundaryUnavailable):
            self._call(value={'unexpected': True})
        self.assertFalse(self.fake_executor.ready_peers)
        self.assertFalse(self.fake_executor.other_calls)
