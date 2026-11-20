"""WF-03.01 D-100 trusted appointment-evidence boundary (STAGED, default deny).

Neither the current Django models nor the uploaded November 20 schema contain a
reviewed Treasurer appointment or independently appointed SSG Advisor record.
There is therefore NO safe way to infer an appointment from a role, a typed
reference, the requester's confirmation, or an access-audit receipt.

Only an independently reviewed, persisted source-of-truth adapter may replace
this implementation after its own authorization, expiry/revocation semantics,
locking, and tests are approved. Do not turn this into a user-supplied checkbox,
string, or environment-variable bypass. Grants must fail closed until then.

Revoking an existing ordinary role does not require a new appointment.
"""


def appointment_verified_for(*, target_account_id: int, role_name: str) -> bool:
    """No approved appointment source is available: refuse all ordinary grants."""
    return False
