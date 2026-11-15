"""WF-01.01 encrypted, expiring Student registration; no account before OTP."""
import base64
import hashlib
import hmac
import json
import secrets
from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import send_mail
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.access_control.models import Role
from .models import Account, StudentRegistrationStage, UserProfile
from .services import RegistrationUnavailable
from .api_errors import ERRORS

CONFLICT = ERRORS["conflict"][1]


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


def _conflict(*, preserve_cookie=False):
    result = {"status": "conflict", "message": CONFLICT}
    if preserve_cookie:
        result["preserve_verification_cookie"] = True
    return result


def _identity_conflicts(payload):
    # The same normalized identities and actual DB collation apply before mail
    # delivery, when continuing a saved attempt, and at permanent creation.
    return Account.objects.filter(Q(school_id=payload["school_id"]) | Q(email=payload["email"])).exists()


def _summary(stage, now, *, status="verification_required"):
    p = policy()
    return {
        "status": status,
        "delivery_sent": bool(stage.otp_digest),
        "expires_in": max(0, int((stage.expires_at - now).total_seconds())),
        "retry_after": max(0, p["resend_seconds"] - int((now - stage.last_sent_at).total_seconds())),
        "resends_remaining": max(0, p["max_resends"] - stage.resend_count),
        "attempts_remaining": max(0, p["max_attempts"] - stage.attempt_count),
    }


def _issue_code(stage, now):
    payload = _decrypt(stage)
    if _identity_conflicts(payload):
        stage.delete()
        return _conflict()
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
    recipient = payload["email"]
    try:
        delivered = send_mail(
            "CTU-G Workspace registration verification code",
            f"Your Student registration verification code is: {code}\n\n"
            f"This code expires in {policy()['otp_seconds'] // 60} minutes. "
            "It does not approve or activate your account.\n"
            "If you did not request this registration, ignore this email.",
            settings.DEFAULT_FROM_EMAIL, [recipient], fail_silently=False,
        )
        if delivered != 1:
            raise RuntimeError("Mail backend did not accept the message.")
    except Exception:
        # Retain encrypted stage for bounded resend; any uncertain code is invalid.
        # Never log the exception/message/recipient/code or claim delivery succeeded.
        stage.otp_digest = ""
        stage.otp_expires_at = None
        stage.save(update_fields=["otp_digest", "otp_expires_at"])
        return _summary(stage, now, status="delivery_failed")
    return _summary(stage, now)


def purge_expired_stages():
    _local_writer()
    count, _ = StudentRegistrationStage.objects.filter(expires_at__lte=timezone.now()).delete()
    return count


def begin_student_registration(data, token=None):
    _local_writer()
    from .serializers import RegistrationSerializer
    serializer = RegistrationSerializer(data=data)
    serializer.is_valid(raise_exception=True)
    data = serializer.validated_data
    if data.get("requested_role") != "Student":
        raise RegistrationUnavailable()
    p, now = policy(), timezone.now()
    # Even failed duplicate paths hash; plaintext/confirmation are never staged.
    payload = {k: v for k, v in data.items() if k not in {"password", "password_confirmation", "requested_role"}}
    payload["password_hash"] = make_password(data["password"])
    payload["email"] = Account.objects.normalize_email(data["email"])
    try:
        purge_expired_stages()
        with transaction.atomic():
            owned = StudentRegistrationStage.objects.select_for_update().filter(token_hash=_token_hash(token)).first()
            if owned:
                if _identity_conflicts(_decrypt(owned)):
                    owned.delete()
                    return _conflict()
                if _identity_conflicts(payload):
                    # Reject changed conflicting input, but preserve possession
                    # of the original, immutable and still-eligible attempt.
                    return _conflict(preserve_cookie=True)
                # The existing attempt remains immutable; cookie possession resumes it.
                return _summary(owned, now, status="existing_verification")
            if not Role.objects.filter(role_name="Student", is_active=True).exists():
                raise RegistrationUnavailable()
            if _identity_conflicts(payload):
                return _conflict()
            browser_token = secrets.token_urlsafe(32)
            token_hash = _token_hash(browser_token)
            stage = StudentRegistrationStage.objects.create(
                token_hash=token_hash,
                school_id_digest=_digest("school-id", payload["school_id"]),
                email_digest=_digest("email", payload["email"]),
                encrypted_payload=_encrypt(payload, token_hash),
                created_at=now, expires_at=now + timedelta(seconds=p["stage_seconds"]), last_sent_at=now,
            )
            result = _issue_code(stage, now)
            result["browser_token"] = browser_token  # API consumes into HttpOnly cookie only.
            return result
    except IntegrityError as exc:
        if exc.args and exc.args[0] == 1062:
            return _conflict()
        raise RegistrationUnavailable() from None
    except (DatabaseError, ValueError, TypeError):
        raise RegistrationUnavailable() from None


def student_verification_status(token):
    _local_writer()
    try:
        stage = StudentRegistrationStage.objects.filter(token_hash=_token_hash(token)).first()
        if not stage or stage.expires_at <= timezone.now():
            return {"status": "expired"}
        if _identity_conflicts(_decrypt(stage)):
            return _conflict()
        return _summary(stage, timezone.now())
    except DatabaseError:
        raise RegistrationUnavailable() from None


def student_verification_action(token, action, code=""):
    _local_writer()
    p = policy()
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
            if action == "cancel":
                stage.delete()
                return {"status": "cancelled"}
            if stage.attempt_count >= p["max_attempts"]:
                return _summary(stage, now, status="attempts_exhausted")
            if action == "resend":
                if stage.resend_count >= p["max_resends"]:
                    return _summary(stage, now, status="resends_exhausted")
                if (now - stage.last_sent_at).total_seconds() < p["resend_seconds"]:
                    return _summary(stage, now, status="resend_cooldown")
                stage.resend_count += 1
                return _issue_code(stage, now)
            if action != "verify":
                raise RegistrationUnavailable()
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
            role = Role.objects.select_for_update().get(role_name="Student", is_active=True)
            if _identity_conflicts(payload):
                stage.delete()
                return _conflict()
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
            return {"status": "completed", "message": "Registration submitted. Your verified account is pending administrative review."}
    except IntegrityError as exc:
        # Exit the failed transaction first. A collision can't leave a partial account.
        if exc.args and exc.args[0] == 1062:
            return _conflict()
        raise RegistrationUnavailable() from None
    except (DatabaseError, Role.DoesNotExist, ValueError, TypeError):
        raise RegistrationUnavailable() from None
