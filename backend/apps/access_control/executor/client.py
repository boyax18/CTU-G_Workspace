"""mTLS client. This process never opens an executor database connection."""
from contextlib import contextmanager
from contextvars import ContextVar
import http.client
import ssl
from urllib.parse import urlsplit

from django.conf import settings
from apps.access_control.protected_requests import canonical, digest
from apps.access_control.writer_boundary import WriterBoundaryUnavailable
from .protocol import decode, fingerprint, request, sanitize_evidence
from .errors import AuthenticationDenied, ExecutionDenied

_proof = ContextVar("workspace_actor_proof", default=None)
LOCAL = object()


@contextmanager
def using_actor_proof(proof):
    token = _proof.set(proof)
    try:
        yield
    finally:
        _proof.reset(token)


def enabled():
    value = getattr(settings, "WORKSPACE_P3C6_REQUIRE_VERIFIED_WRITER", False)
    if type(value) is not bool:
        raise WriterBoundaryUnavailable("Invalid writer configuration.")
    return value


def transport(path, value, *, kind="ordinary"):
    try:
        c = settings.WORKSPACE_EXECUTOR_CLIENTS[kind]
        url = urlsplit(c["url"])
        if url.scheme != "https" or not url.hostname or url.username or url.password or url.path not in ("", "/"):
            raise ValueError()
        context = ssl.create_default_context(cafile=c["ca"])
        context.minimum_version = ssl.TLSVersion.TLSv1_3
        context.load_cert_chain(c["certificate"], c["private_key"])
        conn = http.client.HTTPSConnection(url.hostname, url.port or 443, context=context, timeout=10)
        try:
            conn.connect()
            if fingerprint(conn.sock.getpeercert(binary_form=True)) != c["server_fingerprint"]:
                raise ValueError()
            body = canonical(value)
            conn.request("POST", path, body, {"Content-Type": "application/json", "Content-Length": str(len(body))})
            response = conn.getresponse()
            result = decode(response.read(32769))
            if response.status == 401 and path == "/authenticate":
                raise AuthenticationDenied()
            if response.status == 403:
                raise ExecutionDenied()
            if response.status != 200 or type(result) is not dict or set(result) != {"result"}:
                raise WriterBoundaryUnavailable("Executor refused the request; reconcile uncertain outcomes before retry.")
            return result["result"]
        finally:
            conn.close()
    except (WriterBoundaryUnavailable, AuthenticationDenied, ExecutionDenied):
        raise
    except Exception:
        raise WriterBoundaryUnavailable("Executor unavailable; reconcile uncertain outcomes before retry.") from None


def remote_call(operation, payload):
    if not enabled():
        return LOCAL
    from .runtime import active_operation
    if active_operation() == operation:
        return LOCAL
    kind = "protected" if operation in {"technical_role.provision", "technical_admin.bootstrap", "bootstrap.initial_admin"} else "ordinary"
    envelope = request(operation, payload, _proof.get())
    try:
        return transport("/execute", envelope, kind=kind)["value"]
    except WriterBoundaryUnavailable as exc:
        # Trusted callers can retain these non-secret correlation values for
        # /receipt; API errors remain generic and never echo proofs/passwords.
        exc.request_id = envelope["request_id"]
        exc.request_hash = digest(sanitize_evidence(envelope))
        raise
    except ExecutionDenied:
        if operation in {"registration.approve", "registration.reject"}:
            from apps.accounts.registration_review import RegistrationReviewDenied
            raise RegistrationReviewDenied("Registration request is unavailable.") from None
        if operation == "registration.reapply":
            from apps.accounts.reapplication import ReapplicationDenied
            raise ReapplicationDenied() from None
        from apps.access_control.delegation import PermissionManagementDenied
        raise PermissionManagementDenied("Executor authorization refused.") from None


def authenticate_actor(school_id, password, *, kind="ordinary"):
    return transport("/authenticate", {"school_id": school_id, "password": password}, kind=kind)


class ExecutorProofMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        with using_actor_proof(request.session.get("workspace_executor_proof")):
            return self.get_response(request)
