class AuthenticationDenied(RuntimeError):
    """Credentials refused without disclosing account existence."""


class ExecutionDenied(RuntimeError):
    """Verified infrastructure refused application authorization."""
