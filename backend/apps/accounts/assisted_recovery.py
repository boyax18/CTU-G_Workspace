"""Assisted email verification and recovery for legacy accounts that cannot sign in (25 Nov 2026).

Legacy accounts approved before OTP registration have no email proof, so password recovery
refuses them (D-21, unchanged). An owner who can still sign in verifies on My profile
(email_verification). This module covers the owner who CANNOT sign in:

1. An authorized operator confirms the person's identity out of band and starts recovery:
   POST /api/v1/admin/school-accounts/<id>/assisted-recovery/  {"identity_confirmed": true}
   Exact permission ``accounts.school_accounts.assist_recovery`` (re-checked under lock), never
   the operator's own account, never an administrator / Technical Super Admin / framework
   account (D-71 precedent: privileged recovery needs a separately approved policy, so this
   stops at that authorization boundary). One audit event; the operator never sees the code.
2. A 6-digit code (existing challenge table, purpose "assisted") is sealed in the durable
   security-mail outbox and mailed to the account's CURRENT address.
3. The holder enters email + code on the public Forgot Password page:
   POST /api/v1/auth/account-recovery/verify/  {"email", "code"}
   Same neutral "incorrect or expired" error for every failure (no enumeration), the
   password-recovery throttles and identity budget. Only a correct code for the unchanged
   address records email_verified_at/address (audited) and then issues the EXISTING single-use
   password-reset ticket, so step 4 is the normal reset-password call under D-21.

Never creates a session, never impersonates, never stores or shows the code, and changes no
password, role, permission, approval or active status. Off unless WORKSPACE_ASSISTED_RECOVERY_ENABLED
and password recovery are both on; inert until the permission is provisioned and granted.
"""

import hmac
import logging
import secrets

from django.conf import settings
from django.db import DEFAULT_DB_ALIAS, DatabaseError, transaction
from django.utils import timezone
from rest_framework import exceptions
from rest_framework.response import Response

from apps.access_control.audit import record_access_audit
from apps.access_control.models import AccountPermission, AccountRole, Permission, Role, RolePermission, Service
from apps.access_control.services import has_permission
from apps.access_control.writer_boundary import WriterBoundaryUnavailable, writer_atomic

from . import email_verification as ev, password_reset, recovery_mail
from .account_status import AccountStatusDenied, AccountStatusUnavailable, is_reserved_role
from .email_trace import new_correlation_id, trace
from .models import Account
from .registration_review_api import MAX_ACCOUNT_ID, RegistrationReviewAPI, ReviewBurstThrottle
from .security_mail_models import AccountEmailVerification, SecurityMailOutbox
from .session_auth import WorkspaceSessionAPI

logger = logging.getLogger(__name__)

ASSIST_CODE = "accounts.school_accounts.assist_recovery"
AUTHORIZE_ACTION = "account.assisted_recovery.authorize"
VERIFIED_ACTION = "account.assisted_recovery.verified"
GATE_SETTING = "WORKSPACE_ASSISTED_RECOVERY_ENABLED"
ASSISTED = AccountEmailVerification.PURPOSE_ASSISTED


class AssistedRecoveryConflict(Exception):
    """Fixed reason for an account the operator may read; never account data."""

    REASONS = frozenset({
        "own_account", "privileged_account", "inactive_account", "no_operational_role",
        "email_missing", "already_verified", "recovery_wait",
    })

    def __init__(self, reason, retry_after=None):
        self.reason = reason if reason in self.REASONS else "recovery_wait"
        self.retry_after = retry_after
        super().__init__("Assisted recovery could not be started.")


def gate_open():
    return (getattr(settings, GATE_SETTING, False) is True
            and getattr(settings, "WORKSPACE_PASSWORD_RESET_ENABLED", False) is True)


def start_assisted_recovery(*, actor, target_id):
    """Operator step. Returns {"account_id", "status": "code_queued", "code_valid_seconds"}."""
    if not gate_open():
        raise AccountStatusUnavailable("Assisted recovery is not activated.")
    from apps.access_control.executor.client import enabled as executor_enabled
    if executor_enabled():
        # Like D-69: the protected executor has no such operation; refuse rather than bypass it.
        raise WriterBoundaryUnavailable("Assisted recovery is not supported by the protected writer.")
    if (not isinstance(actor, Account) or actor._state.adding or actor._state.db != DEFAULT_DB_ALIAS
            or type(actor.pk) is not int):
        raise AccountStatusDenied("An existing Workspace actor is required.")
    if type(target_id) is not int or not 1 <= target_id <= MAX_ACCOUNT_ID:
        raise AccountStatusDenied("An existing account is required.")
    if actor.pk == target_id:
        raise AssistedRecoveryConflict("own_account")  # never self-approval

    p, corr = ev._policy(), new_correlation_id()
    with writer_atomic():
        connection = transaction.get_connection(DEFAULT_DB_ALIAS)
        if connection.vendor != "mysql" or connection.isolation_level != "read committed":
            raise AccountStatusUnavailable("Assisted recovery requires primary MySQL READ COMMITTED.")
        # Lock order shared with WF-02.03/02.04/02.05 and permission management.
        services = {row.service_code: row for row in Service.objects.select_for_update()
                    .filter(service_code__in=["access_control", "accounts"]).order_by("service_id")}
        if set(services) != {"access_control", "accounts"} or not all(s.is_active for s in services.values()):
            raise AccountStatusUnavailable("Active approved service definitions are required.")
        if Permission.objects.select_for_update().filter(
                permission_code=ASSIST_CODE, service_id=services["accounts"].pk).count() != 1:
            raise AccountStatusUnavailable("Assisted recovery authority is not provisioned.")
        accounts = {row.pk: row for row in Account.objects.select_for_update()
                    .filter(pk__in=[actor.pk, target_id]).order_by("account_id")}
        if set(accounts) != {actor.pk, target_id}:
            raise AccountStatusDenied("The operator or target no longer exists.")
        operator, target = accounts[actor.pk], accounts[target_id]
        if operator.is_staff or operator.is_superuser or not operator.is_active or operator.request_status != "Approved":
            raise AccountStatusDenied("An eligible Workspace administrator is required.")
        assignments = list(AccountRole.objects.select_for_update()
                           .filter(account_id__in=[actor.pk, target_id]).order_by("account_role_id"))
        roles = {row.pk: row for row in Role.objects.select_for_update()
                 .filter(pk__in={a.role_id for a in assignments}).order_by("role_id")}
        operator_roles = [roles[a.role_id] for a in assignments if a.account_id == actor.pk and a.role_id in roles]
        if not any(r.role_name == "Admin" and r.is_active for r in operator_roles):
            raise AccountStatusDenied("The operator needs an active Admin assignment.")
        list(RolePermission.objects.select_for_update().filter(role_id__in={r.pk for r in operator_roles})
             .order_by("role_permission_id").values_list("pk", flat=True))
        list(AccountPermission.objects.select_for_update().filter(account_id=actor.pk)
             .order_by("account_permission_id").values_list("pk", flat=True))
        if not has_permission(operator, ASSIST_CODE):
            raise AccountStatusDenied("The operator lacks this exact effective permission.")

        # Pending/Rejected targets look like unknown ones (same as WF-02.05).
        if target.request_status != "Approved":
            raise AccountStatusDenied("The account is not an eligible school account.")
        target_roles = [roles[a.role_id] for a in assignments if a.account_id == target_id and a.role_id in roles]
        if target.is_staff or target.is_superuser or any(is_reserved_role(r.role_name) for r in target_roles):
            # Authorization boundary: mailbox control alone must never restore privileged access.
            raise AssistedRecoveryConflict("privileged_account")
        if not target.is_active:
            raise AssistedRecoveryConflict("inactive_account")  # reactivation is a separate decision
        if not any(r.is_active for r in target_roles):
            raise AssistedRecoveryConflict("no_operational_role")
        if not target.email:
            raise AssistedRecoveryConflict("email_missing")
        if ev.is_verified(target):
            raise AssistedRecoveryConflict("already_verified")  # normal Forgot Password already works

        now = ev._now()
        challenge = AccountEmailVerification.objects.select_for_update().filter(account=target).first()
        fresh = (challenge is None or challenge.purpose != ASSISTED or now >= challenge.window_start + p["window"])
        if fresh:
            challenge = challenge or AccountEmailVerification(account=target)
            challenge.window_start, challenge.attempts, challenge.sends, challenge.locked = now, 0, 0, False
            challenge.issued_at = 0
        if not fresh:
            wait = None
            if challenge.locked or challenge.sends >= p["sends"]:
                wait = challenge.window_start + p["window"] - now
            elif challenge.issued_at and now - challenge.issued_at < p["resend"]:
                wait = challenge.issued_at + p["resend"] - now
            if wait is not None:
                raise AssistedRecoveryConflict("recovery_wait", retry_after=max(1, wait))
        code = f"{secrets.randbelow(1_000_000):06d}"
        challenge.purpose, challenge.authorized_by = ASSISTED, operator
        challenge.issued_at, challenge.sends = now, challenge.sends + 1
        challenge.email_digest = ev._email_digest(target)
        challenge.code_digest = ev._code_digest(target, challenge, code)
        challenge.save()
        # The operator's authorization is the audited fact; no code, address or digest is stored.
        record_access_audit(actor=operator, target=target, action=AUTHORIZE_ACTION)
        trace("otp_created", corr, flow=SecurityMailOutbox.KIND_ASSISTED_RECOVERY)
        recovery_mail.queue(SecurityMailOutbox.KIND_ASSISTED_RECOVERY, target, code=code,
                            challenge_issued_at=now, correlation_id=corr)
    return {"account_id": target_id, "status": "code_queued", "code_valid_seconds": p["code"]}


def _assisted_target(email):
    """The one account an assisted code may recover, or None (all failures look identical)."""
    ids = list(Account.objects.filter(email__iexact=email).values_list("pk", flat=True)[:2])
    if len(ids) != 1:
        return None
    account = Account.objects.select_for_update().filter(pk=ids[0]).first()
    if (account is None or account.is_staff or account.is_superuser or not account.is_active
            or account.request_status != "Approved"):
        return None
    roles = list(AccountRole.objects.filter(account=account).select_related("role"))
    if any(is_reserved_role(a.role.role_name) for a in roles) or not any(a.role.is_active for a in roles):
        return None
    return account


def verify_assisted_code(email, code):
    """Public step. Returns a reset ticket, or None for every failure (caller answers neutrally)."""
    p = ev._policy()
    with transaction.atomic():
        account = _assisted_target(email)
        challenge = (AccountEmailVerification.objects.select_for_update().filter(account=account, purpose=ASSISTED).first()
                     if account is not None else None)
        if challenge is None:
            ev._digest("email-verification-otp", f"0:0:0:{email}:assisted:{code}")  # similar work
            return None
        now = ev._now()
        live = (not challenge.locked and challenge.issued_at and challenge.attempts < p["attempts"]
                and now < ev._expires(challenge, p) and not ev.is_verified(account)
                and hmac.compare_digest(challenge.email_digest, ev._email_digest(account)))
        if not live:
            return None
        if not hmac.compare_digest(challenge.code_digest, ev._code_digest(account, challenge, code)):
            challenge.attempts += 1
            challenge.locked = challenge.attempts >= p["attempts"]
            challenge.save(update_fields=["attempts", "locked"])
            return None
        Account.objects.filter(pk=account.pk).update(email_verified_at=timezone.now(), email_verified_address=account.email)
        challenge.delete()
        record_access_audit(actor=account, target=account, action=VERIFIED_ACTION)
        account.refresh_from_db()
        # The proof now satisfies the unchanged D-21 rule; reuse the normal single-use ticket.
        locked = password_reset._lock_eligible(account.email)
        if locked is None:
            raise DatabaseError("Recovered account is not eligible under D-21.")  # rolls everything back
        return password_reset.issue_ticket(locked, now)


# ----------------------------------------------------------------------------- views
class AssistedRecoveryStartView(RegistrationReviewAPI):
    """Operator: same CSRF, bounded JSON, no-store, Admin pre-check and error mapping as WF-02.05."""

    http_method_names = ["post", "options"]
    throttle_classes = [ReviewBurstThrottle]

    def review_gate_open(self):
        return gate_open()

    def handle_exception(self, exc):
        if isinstance(exc, AssistedRecoveryConflict):
            error = {"code": "assisted_recovery_conflict", "reason": exc.reason,
                     "message": "Assisted recovery could not be started."}
            if exc.retry_after:
                error["retry_after"] = exc.retry_after
            return Response({"error": error}, status=409)
        return super().handle_exception(exc)

    def post(self, request, account_id):
        actor = self.require_actor(request, ASSIST_CODE)
        data = request.data
        # The operator attests the out-of-band identity check; there is nothing else to send.
        if not isinstance(data, dict) or set(data) != {"identity_confirmed"} or data["identity_confirmed"] is not True:
            raise exceptions.ValidationError("Confirm that you checked this person's identity.")
        if not 1 <= account_id <= MAX_ACCOUNT_ID:
            raise exceptions.NotFound()
        return Response(start_assisted_recovery(actor=actor, target_id=account_id), status=202)


class AssistedRecoveryVerifyView(WorkspaceSessionAPI):
    """Public: email + code in; success = the normal reset ticket cookie. Neutral on any failure."""

    http_method_names = ["post", "options"]
    throttle_classes = [password_reset.VerifyThrottle, password_reset.VerifyDailyThrottle]

    def handle_exception(self, exc):
        if isinstance(exc, exceptions.ValidationError) and isinstance(exc.detail, dict) and "code" in exc.detail:
            return password_reset._code_invalid()
        return super().handle_exception(exc)

    def post(self, request):
        refusal = password_reset._refusal()
        if refusal is not None:
            return refusal
        if not gate_open():
            return Response({"error": {"code": "recovery_disabled",
                                       "message": "Account recovery is not available yet."}}, status=503)
        serializer = password_reset.PasswordResetVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = password_reset.normalize_account_email(serializer.validated_data["email"])
        password_reset._enforce_identity_budget(email, "assisted", password_reset.VERIFY_IDENTITY_RATES)
        try:
            ticket = verify_assisted_code(email, serializer.validated_data["code"])
        except DatabaseError:
            logger.warning("Workspace assisted recovery verification database error.")
            return password_reset._recovery_unavailable()
        if ticket is None:
            return password_reset._code_invalid()
        return password_reset.ticket_response(ticket)
