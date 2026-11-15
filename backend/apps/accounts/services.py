from django.core.exceptions import ValidationError
from django.db import DatabaseError, IntegrityError, transaction
from django.db.models import Q

from apps.access_control.models import Role

from .models import Account, UserProfile


class RegistrationUnavailable(Exception):
    """Safe service failure; database details never reach public responses."""


def register_account(data, *, registration_token=None):
    """Stage Student requests for OTP; retain direct Instructor registration.

    Instructor duplicates retain their existing public acknowledgement.
    Student permanent writes occur only in the locked OTP completion service.
    """
    if data.get("requested_role") == "Student":
        from .registration_staging import begin_student_registration
        return begin_student_registration(data, registration_token)
    from apps.access_control.executor.client import LOCAL, remote_call
    from apps.access_control.writer_boundary import WriterBoundaryUnavailable
    try:
        remote = remote_call("registration.submit", {"data": data})
    except WriterBoundaryUnavailable:
        raise RegistrationUnavailable() from None
    if remote is not LOCAL:
        return remote
    email = None
    try:
        email = Account.objects.normalize_email(data["email"])
        with transaction.atomic():
            role = Role.objects.select_for_update().get(role_name=data["requested_role"], is_active=True)
            if role.role_name not in {"Student", "Instructor"}:
                raise RegistrationUnavailable()
            account = Account.objects.create_user(
                school_id=data["school_id"], email=email,
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
                duplicate = Q(school_id=data["school_id"])
                if email is not None:
                    duplicate |= Q(email=email)
                if Account.objects.filter(duplicate).exists():
                    return
            except DatabaseError:
                pass
        raise RegistrationUnavailable() from exc
    except (DatabaseError, Role.DoesNotExist, ValueError, ValidationError) as exc:
        raise RegistrationUnavailable() from exc
