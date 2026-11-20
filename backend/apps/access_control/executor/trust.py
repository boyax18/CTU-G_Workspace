"""Root-authenticated deployment roster; pins come from deployment, not HTTP."""
import json
from pathlib import Path

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from apps.access_control.protected_requests import ExecutionTrust, TrustedSigner, canonical, require, digest
from .protocol import now

DOMAIN = b"CTUG:EXECUTOR:ROSTER:v1\x00"


def definition_hash(payload):
    """Only validity times may change during routine same-generation refresh."""
    return digest({k: v for k, v in payload.items() if k not in {"issued", "expires"}})


class TrustStore:
    def __init__(self, config):
        self.config = config

    def load(self, control=None):
        c = self.config
        require(type(c["minimum_epoch"]) is int and c["minimum_epoch"] > 0)
        data = Path(c["roster"]).read_bytes()
        require(len(data) <= 32768)
        from .protocol import decode
        envelope = decode(data)
        require(set(envelope) == {"payload", "signature"})
        p = envelope["payload"]
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(c["root_public_key"])).verify(
                bytes.fromhex(envelope["signature"]), DOMAIN + canonical(p))
        except Exception:
            require(False)
        require(set(p) == {"schema", "server_uuid", "incarnation", "epoch", "release_hash", "fence_hash",
                          "recovery_hash", "policy_hash", "issued", "expires", "signers", "issuers", "peers"})
        require(p["policy_hash"] == c["policy_hash"])
        require(p["schema"] == c["schema"] and p["server_uuid"] == c["server_uuid"])
        require(type(p["epoch"]) is int and p["epoch"] >= c["minimum_epoch"])
        require(type(p["issued"]) is int and type(p["expires"]) is int
                and p["issued"] <= now() < p["expires"] <= p["issued"] + 300)
        if control is not None:
            require(control == (p["epoch"], p["incarnation"], digest(p), p["fence_hash"], p["recovery_hash"], p["release_hash"]))
        signers = tuple(TrustedSigner(**{**s, "public_key": bytes.fromhex(s["public_key"])}) for s in p["signers"])
        trust = ExecutionTrust(p["schema"], p["incarnation"], p["epoch"], p["release_hash"],
                               p["fence_hash"], p["recovery_hash"], signers, p["expires"])
        from apps.access_control.protected_requests import validate_trust
        validate_trust(trust, now())
        issuers = tuple(Ed25519PublicKey.from_public_bytes(bytes.fromhex(key)) for key in p["issuers"])
        require(issuers and type(p["peers"]) is dict and 1 <= len(p["peers"]) <= 64)
        from apps.access_control.protected_requests import _hex
        require(all(_hex(peer) and type(kinds) is list and kinds and len(kinds) == len(set(kinds))
                    and set(kinds) <= {"ordinary", "protected"} for peer, kinds in p["peers"].items()))
        return p, trust, issuers

    def archive(self, payload):
        """Retain the exact verified root endorsement alongside each request."""
        from .protocol import decode
        envelope = decode(Path(self.config["roster"]).read_bytes())
        require(envelope["payload"] == payload)
        try:
            Ed25519PublicKey.from_public_bytes(bytes.fromhex(self.config["root_public_key"])).verify(
                bytes.fromhex(envelope["signature"]), DOMAIN + canonical(payload))
        except Exception:
            require(False)
        return envelope
