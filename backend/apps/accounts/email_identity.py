"""Canonical account email policy; School ID remains the login identifier."""


def normalize_account_email(email):
    if email is None:
        return None
    if not isinstance(email, str):
        raise ValueError("Email must be a string or None.")
    return email.strip().lower() or None
