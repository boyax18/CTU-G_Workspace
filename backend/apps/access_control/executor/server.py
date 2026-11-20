"""Small mTLS-only fixed-operation service; no Django URL or SQL proxy."""
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ssl
from threading import Lock
from threading import BoundedSemaphore
from time import monotonic

from django.db import connections
from apps.access_control.protected_requests import canonical, require
from .protocol import decode, fingerprint
from .errors import AuthenticationDenied, ExecutionDenied


def make_server(address, executor, *, ca, certificate, private_key):
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.minimum_version = ssl.TLSVersion.TLSv1_3
    context.verify_mode = ssl.CERT_REQUIRED
    context.load_verify_locations(cafile=ca)
    context.load_cert_chain(certificate, private_key)
    attempts, guard = {}, Lock()

    class Handler(BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.0"

        def log_message(self, *args):
            pass  # never log passwords, proofs, account identifiers or SQL errors

        def do_POST(self):
            self.connection.settimeout(10)
            try:
                require(not self.headers.get("Transfer-Encoding"))
                lengths = self.headers.get_all("Content-Length", [])
                require(len(lengths) == 1 and lengths[0].isdigit() and 0 < int(lengths[0]) <= 32768)
                peer = fingerprint(self.connection.getpeercert(binary_form=True))
                value = decode(self.rfile.read(int(lengths[0])))
                if self.path == "/authenticate":
                    from hashlib import sha256
                    require(type(value) is dict and type(value.get("school_id")) is str)
                    key = (peer, sha256(value["school_id"].encode()).hexdigest())
                    with guard:
                        # Bounded per-client/account authentication attempts.
                        for expired in [k for k, ts in attempts.items() if not ts or monotonic() - ts[-1] >= 60]:
                            del attempts[expired]
                        require(key in attempts or len(attempts) < 4096)
                        recent = [t for t in attempts.get(key, ()) if monotonic() - t < 60]
                        require(len(recent) < 8)
                        attempts[key] = [*recent, monotonic()]
                    result = executor.authenticate(value, peer)
                elif self.path == "/execute":
                    result = executor.execute(value, peer)
                elif self.path == "/receipt":
                    result = executor.receipt(value, peer)
                elif self.path == "/ready":
                    require(value == {})
                    result = executor.ready(peer)
                else:
                    require(False)
                body, status = canonical({"result": result}), 200
            except (AuthenticationDenied, ExecutionDenied) as exc:
                body = b'{"error":"denied"}'
                status = 401 if isinstance(exc, AuthenticationDenied) else 403
            except Exception:
                if executor.config.get("isolated_datadir"):
                    import traceback
                    traceback.print_exc()  # ephemeral fictional-fixture diagnostics only
                body, status = b'{"error":"executor_refused_or_outcome_unknown"}', 503
            finally:
                connections.close_all()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    class BoundedServer(ThreadingHTTPServer):
        daemon_threads = True
        request_queue_size = 32
        slots = BoundedSemaphore(32)

        def get_request(self):
            sock, remote = super().get_request()
            sock.settimeout(5)
            return context.wrap_socket(sock, server_side=True, do_handshake_on_connect=False), remote

        def process_request(self, sock, remote):
            if not self.slots.acquire(blocking=False):
                sock.close()
                return
            try:
                super().process_request(sock, remote)
            except BaseException:
                self.slots.release()
                raise

        def process_request_thread(self, sock, remote):
            try:
                super().process_request_thread(sock, remote)
            finally:
                self.slots.release()

        def handle_error(self, *args):
            pass  # malformed TLS/HTTP must never dump request contents

    server = BoundedServer(address, Handler)
    server.daemon_threads = True
    return server
