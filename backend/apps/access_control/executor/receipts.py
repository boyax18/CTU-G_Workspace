"""Independent verification of persisted executor evidence and commit receipts."""
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from apps.access_control.protected_requests import canonical, digest, require
from .trust import DOMAIN as ROOT_DOMAIN

EVIDENCE_DOMAIN = b"CTUG:EXECUTOR:EVIDENCE:v1\x00"
RESULT_DOMAIN = b"CTUG:EXECUTOR:RESULT:v1\x00"


def verify_receipt(evidence, result, root_public_key):
    archived = evidence["root_roster"]
    try:
        Ed25519PublicKey.from_public_bytes(bytes.fromhex(root_public_key)).verify(
            bytes.fromhex(archived["signature"]), ROOT_DOMAIN + canonical(archived["payload"]))
        issuer = Ed25519PublicKey.from_public_bytes(bytes.fromhex(evidence["issuer_public_key"]))
        require(evidence["issuer_public_key"] in archived["payload"]["issuers"])
        unsigned = {k: v for k, v in evidence.items() if k != "executor_signature"}
        issuer.verify(bytes.fromhex(evidence["executor_signature"]), EVIDENCE_DOMAIN + canonical(unsigned))
        if result is not None:
            require(result["evidence_hash"] == digest(evidence)
                    and result["request_id"] == evidence["request"]["request_id"]
                    and result["request_hash"] == digest(evidence["request"]))
            issuer.verify(bytes.fromhex(result["executor_signature"]), RESULT_DOMAIN + canonical(
                {k: v for k, v in result.items() if k != "executor_signature"}))
    except Exception:
        require(False)
    return True
