from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction

from apps.access_control.models import Role

from .models import Account, UserProfile


class RegistrationUnavailable(Exception):
    """Safe service failure; database details never reach public responses."""


def register_account(data):
    """Atomically create a Pending/inactive account and profile, without grants.

    Valid duplicates receive the same public acknowledgement. Hashing is still
    performed to avoid a cheap timing path; existing records are never updated.
    """
    try:
        with transaction.atomic():
            role = Role.objects.select_for_update().get(role_name=data["requested_role"], is_active=True)
            if role.role_name not in {"Student", "Instructor"}:
                raise RegistrationUnavailable()
            account = Account.objects.create_user(
                school_id=data["school_id"], email=data["email"] or None,
                password=data["password"], requested_role=role,
            )
            UserProfile.objects.create(
                account=account, first_name=data["first_name"],
                middle_name=data["middle_name"] or None, last_name=data["last_name"],
                suffix=data["suffix"] or None,
            )
    except IntegrityError as exc:
        # The atomic block has exited; a failed INSERT cannot leave an orphan.
        if exc.args and exc.args[0] == 1062:
            try:
                if Account.objects.filter(school_id=data["school_id"]).exists():
                    return
            except DatabaseError:
                pass
        raise RegistrationUnavailable() from exc
    except (DatabaseError, Role.DoesNotExist, ValueError, ValidationError) as exc:
        raise RegistrationUnavailable() from exc
