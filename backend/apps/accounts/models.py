from django.conf import settings
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager
from django.contrib.auth.password_validation import validate_password
from django.db import models, transaction

from .fields import CurrentTimestamp, MySQLEnumField, MySQLTimestampField


class AccountManager(BaseUserManager):
    def create_user(self, school_id, email=None, password=None, **extra_fields):
        """Create a pending account; requested roles never assign privileges."""
        requested_role = extra_fields.pop("requested_role", None)
        if extra_fields:
            raise ValueError(
                "Unsupported account creation fields: " + ", ".join(sorted(extra_fields))
            )
        if not isinstance(school_id, str) or not school_id.strip():
            raise ValueError("School ID is required.")

        school_id = self.model.normalize_username(school_id.strip())
        school_id = self.model._meta.get_field("school_id").clean(school_id, None)
        if email is not None and not isinstance(email, str):
            raise ValueError("Email must be a string or None.")
        email = self.normalize_email(email.strip()) if email and email.strip() else None
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
    email = models.EmailField(max_length=150, null=True, blank=True)

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



    objects = AccountManager()

    USERNAME_FIELD = "school_id"
    REQUIRED_FIELDS = []

    class Meta:
        db_table = "accounts"

    def has_perm(self, perm, obj=None):
        """Delegate global permissions; object-specific access has no policy yet."""
        if obj is not None:
            return False
        from apps.access_control.services import has_permission

        return has_permission(self, perm)

    def has_module_perms(self, app_label):
        # Django app labels are not an application permission catalogue.
        return False

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
