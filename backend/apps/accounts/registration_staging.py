"""Shared protected Student/Instructor staging; legacy Student behavior retained."""
import base64
import hashlib
import hmac
import json
import logging
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.throttling import SimpleRateThrottle

from apps.access_control.models import Role
from .models import Account, StudentRegistrationStage, UserProfile
from .services import RegistrationUnavailable
from .api_errors import ERRORS

CONFLICT = ERRORS["conflict"][1]
logger = logging.getLogger(__name__)


def policy():
    values = {
        "otp_seconds": getattr(settings, "STUDENT_REGISTRATION_OTP_SECONDS", 600),
        "resend_seconds": getattr(settings, "STUDENT_REGISTRATION_RESEND_SECONDS", 60),
        "max_resends": getattr(settings, "STUDENT_REGISTRATION_MAX_RESENDS", 3),
        "max_attempts": getattr(settings, "STUDENT_REGISTRATION_MAX_ATTEMPTS", 5),
        "stage_seconds": getattr(settings, "STUDENT_REGISTRATION_STAGE_SECONDS", 1800),
    }
    if any(type(v) is not int or not 1 <= v <= (100 if key in {"max_resends", "max_attempts"} else 86400)
           for key, v in values.items()):
        raise RegistrationUnavailable()
    return values


def _local_writer():
    # Never introduce a local DB writer into a fenced executor deployment.
    # Its separate credential/trigger contract must be extended before rollout.
    from apps.access_control.executor.client import enabled
    if enabled():
        raise RegistrationUnavailable()


def _digest(purpose, value):
    key = getattr(settings, "STUDENT_REGISTRATION_STAGING_KEY", settings.SECRET_KEY)
    if not isinstance(key, str) or len(key) < 32:
        raise RegistrationUnavailable()
    return hmac.new(key.encode(), ("ctug:student-registration:v1:" + purpose + ":" + value).encode(), hashlib.sha256).hexdigest()


def _encrypt(data, token_hash):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    nonce = secrets.token_bytes(12)
    key = bytes.fromhex(_digest("encryption", "aes-gcm"))
    ciphertext = AESGCM(key).encrypt(nonce, json.dumps(data).encode(), token_hash.encode())
    return base64.b64encode(nonce + ciphertext).decode()


def _decrypt(stage):
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    raw = base64.b64decode(stage.encrypted_payload, validate=True)
    key = bytes.fromhex(_digest("encryption", "aes-gcm"))
    return json.loads(AESGCM(key).decrypt(raw[:12], raw[12:], stage.token_hash.encode()))


def _token_hash(token):
    if not isinstance(token, str) or len(token) != 43:
        return None
    return _digest("browser-token", token)


def _stage_role(stage):
    # Existing encrypted Student payloads have no role key. Never reinterpret them.
    role = _decrypt(stage).get("requested_role", "Student")
    if role not in {"Student", "Instructor"}:
        raise RegistrationUnavailable()
    return role


def _role_result(result, role):
    if role == "Instructor":
        result["requested_role"] = role
    return result


class _IdentityThrottle(SimpleRateThrottle):
    def __init__(self, digest, scope, rate):
        self.identity_key = "ctug:registration-identity:" + scope + ":" + digest
        self.rate = rate
        super().__init__()

    def get_cache_key(self, request, view):
        return self.identity_key


def _identity_limits(digests, *, otp=False):
    # Applies to Student and Instructor alike (WF-01.01 R-03, owner-approved
    # 16 Nov 2026). Reuse DRF's configured cache/rate semantics. Keys never
    # contain raw IDs/email. Same budgets as existing IP controls; identity
    # reservations additionally cap live stages at one per ID and one per email,
    # across both registration roles, so the budget is shared across roles.
    rates = ("30/min", "200/day") if otp else ("5/min", "30/day")
    for purpose, digest in digests.items():
        for period, rate in enumerate(rates):
            throttle = _IdentityThrottle(digest, f"{'otp' if otp else 'begin'}:{purpose}:{period}", rate)
            if not throttle.allow_request(None, None):
                raise exceptions.Throttled(wait=throttle.wait())


def _conflict(*, preserve_cookie=False, role="Student"):
    result = _role_result({"status": "conflict", "message": CONFLICT}, role)
    if preserve_cookie:
        result["preserve_verification_cookie"] = True
    return result


def _identity_conflicts(payload):
    # The same normalized identities and actual DB collation apply before mail
    # delivery, when continuing a saved attempt, and at permanent creation.
    return Account.objects.filter(Q(school_id=payload["school_id"]) | Q(email=payload["email"])).exists()


def _summary(stage, now, *, status="verification_required"):
    p = policy()
    result = {
        "status": status,
        "delivery_sent": bool(stage.otp_digest),
        "expires_in": max(0, int((stage.expires_at - now).total_seconds())),
        "retry_after": max(0, p["resend_seconds"] - int((now - stage.last_sent_at).total_seconds())),
        "resends_remaining": max(0, p["max_resends"] - stage.resend_count),
        "attempts_remaining": max(0, p["max_attempts"] - stage.attempt_count),
        # Configured code lifetime (D-01) for applicant guidance; not a secret.
        "code_valid_seconds": p["otp_seconds"],
    }
    if _stage_role(stage) == "Instructor":
        result["requested_role"] = "Instructor"
    return result


class _PendingDelivery:
    """A code whose digest is stored; it is mailed only after that write commits."""

    def __init__(self, stage, code, digest, recipient, role, now):
        self.stage, self.code, self.digest = stage, code, digest
        self.recipient, self.role, self.now = recipient, role, now


def _prepare_code(stage, now):
    """Inside the locked transaction: store a fresh code digest. Never sends mail.

    Returns (_PendingDelivery, None), or (None, conflict result) after deleting a
    stage whose identity is no longer available.
    """
    payload = _decrypt(stage)
    role = payload.get("requested_role", "Student")
    if _identity_conflicts(payload):
        stage.delete()
        return None, _conflict(role=role)
    previous_digest = stage.otp_digest
    for _ in range(8):
        code = f"{secrets.randbelow(1_000_000):06d}"
        digest = _digest("otp", stage.token_hash + ":" + code)
        if digest != previous_digest:
            break
    else:
        raise RegistrationUnavailable()
    stage.otp_digest = digest
    stage.otp_expires_at = min(stage.expires_at, now + timedelta(seconds=policy()["otp_seconds"]))
    stage.last_sent_at = now
    stage.save()
    return _PendingDelivery(stage, code, digest, payload["email"], role, now), None


def _deliver_code(delivery):
    """After commit: send the code; on failure invalidate only this same code.

    Sending outside the transaction means no row/index lock or DB connection is
    held during SMTP, and no code is mailed for a stage write that later rolls
    back (WF-01 R-02, owner-approved 16 Nov 2026).
    """
    stage, now = delivery.stage, delivery.now
    try:
        delivered = send_mail(
            "CTU-G Workspace registration verification code",
            f"Your {delivery.role} registration verification code is: {delivery.code}\n\n"
            f"This code expires in {policy()['otp_seconds'] // 60} minutes. "
            "It does not approve or activate your account.\n"
            "If you did not request this registration, ignore this email.",
            settings.DEFAULT_FROM_EMAIL, [delivery.recipient], fail_silently=False,
        )
        if delivered != 1:
            raise RuntimeError("Mail backend did not accept the message.")
    except Exception:
        # Retain encrypted stage for bounded resend; the uncertain code is invalid.
        # The digest guard never clears a newer code issued by a concurrent resend.
        # Never log the exception/message/recipient/code or claim delivery succeeded.
        try:
            with transaction.atomic():
                StudentRegistrationStage.objects.filter(
                    pk=stage.pk, otp_digest=delivery.digest,
                ).update(otp_digest="", otp_expires_at=None)
        except DatabaseError:
            # The undelivered code is known only to the server; it still expires.
            logger.warning("Registration code invalidation after delivery failure did not complete.")
        stage.otp_digest = ""
        stage.otp_expires_at = None
        return _summary(stage, now, status="delivery_failed")
    return _summary(stage, now)


def purge_expired_stages():
    _local_writer()
    count, _ = StudentRegistrationStage.objects.filter(expires_at__lte=timezone.now()).delete()
    return count


def begin_student_registration(data, token=None):
    return _begin_registration(data, token, role="Student")


def begin_instructor_registration(data, token=None):
    return _begin_registration(data, token, role="Instructor")


def _begin_registration(data, token, *, role):
    _local_writer()
    from .serializers import RegistrationSerializer
    serializer = RegistrationSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    if data.get("requested_role") != role:
        raise RegistrationUnavailable()
    p, now = policy(), timezone.now()
    # Even failed duplicate paths hash; plaintext/confirmation are never staged.
    payload = {k: v for k, v in data.items() if k not in {"password", "password_confirmation", "requested_role"}}
    payload["password_hash"] = make_password(data["password"])
    payload["email"] = Account.objects.normalize_email(data["email"])
    if role == "Instructor":
        payload["requested_role"] = role
    _identity_limits({"id": _digest("school-id", payload["school_id"]), "email": _digest("email", payload["email"])})
    try:
        purge_expired_stages()
        with transaction.atomic():
            owned = StudentRegistrationStage.objects.select_for_update().filter(token_hash=_token_hash(token)).first()
            if owned:
                owned_role = _stage_role(owned)
                if _identity_conflicts(_decrypt(owned)):
                    owned.delete()
                    return _conflict(role=role)
                if _identity_conflicts(payload):
                    # Reject changed conflicting input, but preserve possession
                    # of the original, immutable and still-eligible attempt.
                    return _conflict(preserve_cookie=True, role=role)
                # The existing attempt remains immutable; cookie possession resumes it.
                result = _summary(owned, now, status="existing_verification")
                if role == "Instructor" and owned_role == "Student":
                    result["requested_role"] = "Student"
                return result
            if not Role.objects.filter(role_name=role, is_active=True).exists():
                raise RegistrationUnavailable()
            if _identity_conflicts(payload):
                return _conflict(role=role)
            browser_token = secrets.token_urlsafe(32)
            token_hash = _token_hash(browser_token)
            stage = StudentRegistrationStage.objects.create(
                token_hash=token_hash,
                school_id_digest=_digest("school-id", payload["school_id"]),
                email_digest=_digest("email", payload["email"]),
                encrypted_payload=_encrypt(payload, token_hash),
                created_at=now, expires_at=now + timedelta(seconds=p["stage_seconds"]), last_sent_at=now,
            )
            delivery, conflict = _prepare_code(stage, now)
            if conflict:
                return conflict
    except IntegrityError as exc:
        if exc.args and exc.args[0] == 1062:
            if not (
                _identity_conflicts(payload) or StudentRegistrationStage.objects.filter(
                    Q(school_id_digest=_digest("school-id", payload["school_id"]))
                    | Q(email_digest=_digest("email", payload["email"]))
                ).exists()
            ):
                raise RegistrationUnavailable() from None
            return _conflict(role=role)
        raise RegistrationUnavailable() from None
    except (DatabaseError, ValueError, TypeError):
        raise RegistrationUnavailable() from None
    # The stage reservation and code digest have committed; only now send mail.
    # Delivery failure still sets the ownership cookie for bounded recovery.
    result = _deliver_code(delivery)
    result["browser_token"] = browser_token  # API consumes into HttpOnly cookie only.
    return result


def student_verification_status(token):
    _local_writer()
    try:
        stage = StudentRegistrationStage.objects.filter(token_hash=_token_hash(token)).first()
        if not stage or stage.expires_at <= timezone.now():
            return {"status": "expired"}
        if _identity_conflicts(_decrypt(stage)):
            return _conflict(role=_stage_role(stage))
        _identity_limits({"id": stage.school_id_digest, "email": stage.email_digest}, otp=True)
        return _summary(stage, timezone.now())
    except DatabaseError:
        raise RegistrationUnavailable() from None


def student_verification_action(token, action, code=""):
    _local_writer()
    p = policy()
    role_name = "Student"
    payload = None
    delivery = None
    try:
        with transaction.atomic():
            stage = StudentRegistrationStage.objects.select_for_update().filter(token_hash=_token_hash(token)).first()
            # A contender may wait on resend/verify locks. Evaluate deadlines
            # after acquiring the row, never against an earlier request timestamp.
            now = timezone.now()
            if not stage:
                return {"status": "expired"}
            if stage.expires_at <= now:
                stage.delete()
                return {"status": "expired"}
            role_name = _stage_role(stage)
            _identity_limits({"id": stage.school_id_digest, "email": stage.email_digest}, otp=True)
            if action == "cancel":
                stage.delete()
                return _role_result({"status": "cancelled"}, role_name)
            if stage.attempt_count >= p["max_attempts"]:
                return _summary(stage, now, status="attempts_exhausted")
            if action == "resend":
                if stage.resend_count >= p["max_resends"]:
                    return _summary(stage, now, status="resends_exhausted")
                if (now - stage.last_sent_at).total_seconds() < p["resend_seconds"]:
                    return _summary(stage, now, status="resend_cooldown")
                # Counters/cooldown commit before mail, so a failed send still
                # consumes the resend budget (D-02/D-08 unchanged).
                stage.resend_count += 1
                delivery, conflict = _prepare_code(stage, now)
                if conflict:
                    return conflict
            elif action != "verify":
                raise RegistrationUnavailable()
            else:
                if not stage.otp_expires_at or stage.otp_expires_at <= now or not stage.otp_digest:
                    return _summary(stage, now, status="otp_expired")
                if not hmac.compare_digest(stage.otp_digest, _digest("otp", stage.token_hash + ":" + code)):
                    stage.attempt_count += 1
                    if stage.attempt_count >= p["max_attempts"]:
                        stage.otp_digest = ""
                    stage.save(update_fields=["attempt_count", "otp_digest"])
                    return _summary(stage, now, status="attempts_exhausted" if not stage.otp_digest else "otp_invalid")
                # The stage lock serializes verification/resend/cancel and code replay.
                # Verification proof and permanent creation share the SAME transaction.
                payload = _decrypt(stage)
                stage.email_verified_at = now
                stage.save(update_fields=["email_verified_at"])
                role = Role.objects.select_for_update().get(role_name=role_name, is_active=True)
                if _identity_conflicts(payload):
                    stage.delete()
                    return _conflict(role=role_name)
                account = Account.objects.create(
                    school_id=payload["school_id"], email=payload["email"],
                    password=payload["password_hash"], requested_role=role,
                    request_status="Pending", is_active=False,
                    email_verified_at=now, email_verified_address=payload["email"],
                )
                UserProfile.objects.create(account=account, **{
                    key: payload.get(key) or None for key in ("first_name", "middle_name", "last_name", "suffix")
                })
                stage.delete()
                return _role_result({"status": "completed", "message": "Registration submitted. Your verified account is pending administrative review."}, role_name)
    except IntegrityError as exc:
        # Exit the failed transaction first. A collision can't leave a partial account.
        if exc.args and exc.args[0] == 1062:
            if payload is None or not _identity_conflicts(payload):
                raise RegistrationUnavailable() from None
            return _conflict(role=role_name)
        raise RegistrationUnavailable() from None
    except (DatabaseError, Role.DoesNotExist, ValueError, TypeError):
        raise RegistrationUnavailable() from None
    # Only a resend reaches this point, after its new code digest has committed.
    return _deliver_code(delivery)
