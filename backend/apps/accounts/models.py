from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.password_validation import validate_password
from django.db import models, transaction

from .fields import CurrentTimestamp, MySQLEnumField, MySQLTimestampField
from .email_identity import normalize_account_email

# WF-03.01 SR-1 Stage A (owner-authorized 19 Nov 2026): the persistent per-account session-revocation counter.
# Only apps.accounts.session_revocation.advance() changes it (one atomic SQL increment). The guards below are
# APPLICATION-level only: they refuse ORM writes that name the counter and stop a stale full save() from writing
# an old value back. They do not bind QuerySet.update() on the base manager, raw SQL or a privileged database
# user; only the separately approved non-decrease trigger (tested on disposable databases) works at that level.
SESSION_REVOCATION_FIELD = "session_revocation_version"
SESSION_HASH_SALT = "ctug.workspace.accounts.session_revocation.v2"


class SessionRevocationWriteRefused(ValueError):
    """An ORM write named the session-revocation counter outside session_revocation.advance()."""


class AccountQuerySet(models.QuerySet):
    def update(self, **kwargs):
        if SESSION_REVOCATION_FIELD in kwargs:
            raise SessionRevocationWriteRefused("Use apps.accounts.session_revocation.advance().")
        return super().update(**kwargs)

    def bulk_update(self, objs, fields, batch_size=None):
        if SESSION_REVOCATION_FIELD in set(fields):
            raise SessionRevocationWriteRefused("Use apps.accounts.session_revocation.advance().")
        return super().bulk_update(objs, fields, batch_size=batch_size)


class AccountManager(BaseUserManager):
    def get_queryset(self):
        return AccountQuerySet(self.model, using=self._db)

    @classmethod
    def normalize_email(cls, email):
        return normalize_account_email(email)

    def create_user(self, school_id, email=None, password=None, **extra_fields):
        """Create a pending account; requested roles never assign privileges."""
        requested_role = extra_fields.pop("requested_role", None)
        if extra_fields:
            raise ValueError(
                "Unsupported account creation fields: " + ", ".join(sorted(extra_fields))
            )
        if not isinstance(school_id, str) or not school_id.strip():
            raise ValueError("CTU-G ID is required.")

        school_id = self.model.normalize_username(school_id.strip())
        school_id = self.model._meta.get_field("school_id").clean(school_id, None)
        email = self.normalize_email(email)
        email = self.model._meta.get_field("email").clean(email, None)

        if requested_role is not None:
            role_model = self.model._meta.get_field("requested_role").remote_field.model
            if not isinstance(requested_role, role_model) or requested_role.pk is None:
                raise ValueError("Requested role must be an existing Role.")
            try:
                requested_role = role_model._default_manager.db_manager(self._db).get(
                    pk=requested_role.pk, is_active=True
                )
            except role_model.DoesNotExist as exc:
                raise ValueError("Requested role must be active and exist.") from exc
            if requested_role.role_name not in {"Student", "Instructor"}:
                raise ValueError("Only Student or Instructor roles may be requested.")

        account = self.model(
            school_id=school_id,
            email=email,
            requested_role=requested_role,
            request_status="Pending",
            is_active=False,
        )
        if password is not None:
            validate_password(password, user=account)
        account.set_password(password)
        account.save(using=self._db)
        return account

    def create_superuser(self, school_id, email=None, password=None, **extra_fields):
        """Create a Django framework administrator, not an application Super Admin."""

        if extra_fields:
            raise ValueError(
            "Unsupported superuser fields: "
            + ", ".join(sorted(extra_fields))
            )

        if not isinstance(password, str) or not password:
            raise ValueError("Superuser password is required.")

        with transaction.atomic(using=self._db):
            account = self.create_user(
            school_id=school_id,
            email=email,
            password=password,
            )

            account.is_staff = True
            account.is_superuser = True
            account.is_active = True
            account.request_status = "Approved"

            account.save(
            using=self._db,
            update_fields=[
                "is_staff",
                "is_superuser",
                "is_active",
                "request_status",
            ],
            )

        return account


class Account(AbstractBaseUser):
    REQUEST_STATUS_CHOICES = [
        ("Pending", "Pending"),
        ("Approved", "Approved"),
        ("Rejected", "Rejected"),
    ]

    account_id = models.AutoField(primary_key=True)
    school_id = models.CharField(max_length=50, unique=True)
    password = models.CharField(max_length=255, db_column="password_hash")
    email = models.EmailField(max_length=150, null=True, blank=True, unique=True)
    email_verified_at = models.DateTimeField(null=True, blank=True, editable=False)
    email_verified_address = models.EmailField(max_length=150, null=True, blank=True, editable=False)

    requested_role = models.ForeignKey(
        "access_control.Role",
        db_column="requested_role_id",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="requesting_accounts",
    )
    request_status = MySQLEnumField(
        max_length=8,
        choices=REQUEST_STATUS_CHOICES,
        default="Pending",
        db_default="Pending",
    )
    is_active = models.BooleanField(default=False, db_default=False)
    created_at = MySQLTimestampField(db_default=CurrentTimestamp(), editable=False)

    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        db_column="reviewed_by",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reviewed_accounts",
        editable=False,
    )
    reviewed_at = MySQLTimestampField(null=True, blank=True, editable=False)
    rejection_reason = models.CharField(
        max_length=255, null=True, blank=True, editable=False
    )
    password_reset_token = models.CharField(max_length=255, null=True, blank=True)
    password_reset_token_expires = MySQLTimestampField(null=True, blank=True)

    last_login = None

    is_staff = models.BooleanField(
    default=False,
    db_default=False,
    )

    is_superuser = models.BooleanField(
    default=False,
    db_default=False,
    )

    # SR-1 Stage A: authoritative for role/status session revocation; never derived from an audit receipt.
    session_revocation_version = models.PositiveBigIntegerField(
        default=0,
        db_default=0,
        editable=False,
    )

    objects = AccountManager()

    USERNAME_FIELD = "school_id"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts"

    def save(self, *args, **kwargs):
        # Do not expand partial approval/password writes to include email.
        update_fields = kwargs.get("update_fields")
        if update_fields is not None and SESSION_REVOCATION_FIELD in set(update_fields):
            raise SessionRevocationWriteRefused("Use apps.accounts.session_revocation.advance().")
        if update_fields is None or "email" in update_fields:
            self.email = normalize_account_email(self.email)
        if update_fields is None and not self._state.adding and not kwargs.get("force_insert"):
            # SR-1: a full save of an existing account never writes the counter, so a stale instance cannot
            # lower it, and a deleted row is not silently re-created with an old value (Django refuses an
            # update_fields save that matches no row).
            deferred = self.get_deferred_fields()
            kwargs["update_fields"] = [
                field.name for field in self._meta.concrete_fields
                if not field.primary_key and field.name != SESSION_REVOCATION_FIELD and field.attname not in deferred
            ]
        return super().save(*args, **kwargs)

    def has_perm(self, perm, obj=None):
        """Delegate global permissions; object-specific access has no policy yet."""
        if obj is not None:
            return False
        from apps.access_control.services import has_permission

        return has_permission(self, perm)

    def has_module_perms(self, app_label):
        # Django app labels are not an application permission catalogue.
        return False

    def _get_session_auth_hash(self, secret=None):
        """WF-02.05 D-66 / WF-03.01 D-83, SR-1 Stage A: bind every session to the password AND the
        account's persistent session-revocation counter.

        Django re-checks this hash on every request (django.contrib.auth.get_user) and flushes a
        mismatching session. Every approved session-ending event (suspension, reactivation, School
        Admin and Technical Super Admin grants and revocations, the protected bootstrap, password
        reset) advances the counter in the same transaction as its change, so every session signed in
        before it fails the check on every device, including after a later reactivation or after a
        removed role is added again.

        The counter is stored on the account row, never derived from audit receipts: deleting,
        changing or forging a receipt cannot change it (SR-1). The v2 domain applies even at counter
        0 and there is NO fallback to the earlier receipt-epoch hash or to Django's plain hash, so
        every session created before this contract fails once (one-time sign-out). Password changes
        still change the base hash. SECRET_KEY_FALLBACKS are handled by Django as before.
        """
        from django.utils.crypto import salted_hmac

        version = self.session_revocation_version
        if type(version) is not int or version < 0:
            raise ValueError("The session-revocation counter is invalid.")  # fail closed, never a default
        base = super()._get_session_auth_hash(secret=secret)
        return salted_hmac(SESSION_HASH_SALT, f"{base}:{version}", secret=secret, algorithm="sha256").hexdigest()

    def __str__(self):
        return self.school_id


class UserProfile(models.Model):
    user_id = models.AutoField(primary_key=True)
    account = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        db_column="account_id",
        on_delete=models.PROTECT,
        related_name="profile",
    )
    first_name = models.CharField(max_length=100, null=True, blank=True)
    middle_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    suffix = models.CharField(
        max_length=20, db_column="suffix_name", null=True, blank=True
    )

    class Meta:
        db_table = "users"

    def __str__(self):
        name = " ".join(part for part in (self.first_name, self.last_name) if part)
        return name or f"Profile for account {self.account_id}"

class StudentRegistrationStage(models.Model):
    """Encrypted short-lived data; keyed identity digests reserve staged attempts."""

    token_hash = models.CharField(max_length=64, unique=True)
    school_id_digest = models.CharField(max_length=64, unique=True)
    email_digest = models.CharField(max_length=64, unique=True)
    encrypted_payload = models.TextField()
    otp_digest = models.CharField(max_length=64, blank=True, default="")
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    attempt_count = models.PositiveSmallIntegerField(default=0)
    resend_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField()
    expires_at = models.DateTimeField(db_index=True)
    last_sent_at = models.DateTimeField()
    email_verified_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "student_registration_staging"


from .outbox_models import RegistrationNotificationOutbox  # noqa: E402,F401
