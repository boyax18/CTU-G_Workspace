"""Ephemeral fictional signers; no production identity or key enrollment."""

import secrets

from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from apps.access_control.protected_requests import (
    CORE_PERMISSIONS, DOMAIN, ExecutionTrust, TrustedSigner, canonical,
)


def trust_fixture(schema, actor_id, now):
    keys = {duty: Ed25519PrivateKey.generate() for duty in ("actor", "institutional", "technical")}
    signers = tuple(TrustedSigner(
        key_id=secrets.token_hex(32), person_id=secrets.token_hex(32), duty=duty,
        public_key=key.public_key().public_bytes_raw(),
        account_id=actor_id if duty == "actor" else None,
    ) for duty, key in keys.items())
    trust = ExecutionTrust(schema, secrets.token_hex(32), 1, secrets.token_hex(32),
                           secrets.token_hex(32), secrets.token_hex(32), signers, now + 120)
    return trust, keys


def sign_fixture(request, trust, keys):
    signatures = []
    for signer in trust.signers:
        value = {"request": request, "key_id": signer.key_id, "duty": signer.duty}
        signatures.append({"key_id": signer.key_id, "duty": signer.duty,
                           "signature": keys[signer.duty].sign(DOMAIN + canonical(value)).hex()})
    return {"request": request, "signatures": signatures}


def request_fixture(trust, keys, actor_id, *, now, before_hash, target_id=None):
    request = {
        "version": 1, "operation": "technical_role.provision" if target_id is None else "technical_admin.bootstrap",
        "request_id": secrets.token_hex(32), "nonce": secrets.token_hex(32),
        "actor_id": actor_id, "target_id": target_id, "schema": trust.schema,
        "incarnation": trust.incarnation, "epoch": trust.epoch,
        "release_hash": trust.release_hash, "fence_hash": trust.fence_hash,
        "recovery_hash": trust.recovery_hash, "before_hash": before_hash,
        "issued_at": now, "expires_at": now + 60, "permission_codes": list(CORE_PERMISSIONS),
    }
    return sign_fixture(request, trust, keys)
