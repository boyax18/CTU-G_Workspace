class RegistrationUnavailable(Exception):
    """Safe service failure; database details never reach public responses."""


def register_account(data, *, registration_token=None):
    """Stage both public roles; permanent writes require locked OTP completion."""
    if data.get("requested_role") == "Student":
        from .registration_staging import begin_student_registration
        return begin_student_registration(data, registration_token)
    if data.get("requested_role") == "Instructor":
        from .registration_staging import begin_instructor_registration
        return begin_instructor_registration(data, registration_token)
    raise RegistrationUnavailable()
