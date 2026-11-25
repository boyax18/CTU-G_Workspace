"""Durable security-mail outbox and email-verification challenges (24 Nov 2026).

SecurityMailOutbox replaces the in-memory password-recovery queue. A row stores no plaintext:
the only secret (an OTP) is sealed with the existing outbox KEK (outbox_crypto.seal_secret) and
erased when the row reaches a terminal state. The recipient is read from the account at send
time and every OTP is re-checked against the account's CURRENT challenge before sending, so an
expired or superseded code is never mailed. "Accepted" means Gmail/SMTP accepted the message;
it is never presented as inbox delivery.
"""

from django.conf import settings
from django.db import models


class SecurityMailOutbox(models.Model):
    KIND_RESET_CODE = "reset_code"
    KIND_PASSWORD_CHANGED = "password_changed"
    KIND_EMAIL_VERIFICATION = "email_verification_code"
    KIND_ASSISTED_RECOVERY = "assisted_recovery_code"
    KINDS = [(KIND_RESET_CODE, KIND_RESET_CODE), (KIND_PASSWORD_CHANGED, KIND_PASSWORD_CHANGED),
             (KIND_EMAIL_VERIFICATION, KIND_EMAIL_VERIFICATION),
             (KIND_ASSISTED_RECOVERY, KIND_ASSISTED_RECOVERY)]
    STATUSES = [(s, s) for s in ("Pending", "Leased", "Retry", "Accepted", "Dead", "Expired", "Superseded")]

    outbox_id = models.BigAutoField(primary_key=True)
    account = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="security_mail", db_column="account_id")
    kind = models.CharField(max_length=32, choices=KINDS)
    row_token = models.CharField(max_length=32, unique=True)  # AEAD binding; not a secret
    correlation_id = models.CharField(max_length=32, db_index=True)
    challenge_issued_at = models.BigIntegerField(null=True, blank=True)  # binds an OTP to its challenge
    encrypted_secret = models.BinaryField(max_length=256, null=True, blank=True)
    secret_nonce = models.BinaryField(max_length=12, null=True, blank=True)
    wrapped_data_key = models.BinaryField(max_length=128, null=True, blank=True)
    encryption_key_version = models.CharField(max_length=16, null=True, blank=True)
    status = models.CharField(max_length=12, choices=STATUSES, default="Pending", db_index=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    next_attempt_at = models.DateTimeField(null=True, blank=True)
    lease_token = models.CharField(max_length=64, null=True, blank=True)
    lease_expires_at = models.DateTimeField(null=True, blank=True)
    last_failure_code = models.CharField(max_length=48, null=True, blank=True)
    message_id = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    secret_erased_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "security_mail_outbox"
        indexes = [models.Index(fields=["status", "next_attempt_at"], name="security_mail_due_idx")]


class AccountEmailVerification(models.Model):
    """At most one live challenge per account for confirming its CURRENT email address.

    purpose "self": requested by the signed-in owner (My profile). purpose "assisted" (25 Nov 2026):
    started by an authorized operator for an account that cannot sign in; the code is mailed to the
    account's current address and redeemed only on the public recovery step. A challenge of one
    purpose is never accepted by the other step.
    """

    PURPOSE_SELF = "self"
    PURPOSE_ASSISTED = "assisted"

    account = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, primary_key=True,
                                   related_name="email_verification_challenge", db_column="account_id")
    code_digest = models.CharField(max_length=64)
    email_digest = models.CharField(max_length=64)  # keyed digest; the address itself is not copied
    window_start = models.BigIntegerField()
    issued_at = models.BigIntegerField()
    attempts = models.PositiveSmallIntegerField(default=0)
    sends = models.PositiveSmallIntegerField(default=0)
    locked = models.BooleanField(default=False)
    purpose = models.CharField(max_length=16, default=PURPOSE_SELF,
                               choices=[(PURPOSE_SELF, PURPOSE_SELF), (PURPOSE_ASSISTED, PURPOSE_ASSISTED)])
    # The operator who authorized an assisted challenge (audited separately); null for "self".
    authorized_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name="+", db_column="authorized_by_id")

    class Meta:
        db_table = "account_email_verification"
