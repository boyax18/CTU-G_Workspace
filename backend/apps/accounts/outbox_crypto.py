"""Development-only envelope encryption for CTU-G registration notifications.

Only internal trusted services should call these functions. Keep the active
wrapping key OUTSIDE Git and MySQL. This is not a production KMS integration.
"""

import base64
import binascii
import os
import re
import secrets

from django.conf import settings


class OutboxCryptoUnavailable(RuntimeError):
    """A key, dependency or authenticated envelope is unavailable."""


_VERSION = re.compile(r"v[1-9][0-9]{0,4}\Z", re.ASCII)
_TEMPLATE_CODES = frozenset({"registration.approved", "registration.rejected"})


def _aesgcm():
    try:
        from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    except ImportError as exc:
        raise OutboxCryptoUnavailable("Registration outbox encryption is unavailable.") from exc
    return AESGCM


def _wrapping_key(version):
    if type(version) is not str or not _VERSION.fullmatch(version):
        raise OutboxCryptoUnavailable("Registration outbox key version is unavailable.")
    # One version = one independently provisioned environment variable.
    name = f"WORKSPACE_OUTBOX_KEK_{version.upper()}_B64"
    value = os.environ.get(name)
    if type(value) is not str or not value:
        raise OutboxCryptoUnavailable("Registration outbox wrapping key is unavailable.")
    try:
        key = base64.b64decode(value, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise OutboxCryptoUnavailable("Registration outbox wrapping key is invalid.") from exc
    if len(key) != 32:
        raise OutboxCryptoUnavailable("Registration outbox wrapping key is invalid.")
    return key


def _associated_data(*, audit_log_id, template_code, template_version):
    if (type(audit_log_id) is not int or not 1 <= audit_log_id <= 2_147_483_647
            or template_code not in _TEMPLATE_CODES
            or type(template_version) is not int or not 1 <= template_version <= 2_147_483_647):
        raise OutboxCryptoUnavailable("Registration outbox context is invalid.")
    return f"ctug:registration-outbox:v1:{audit_log_id}:{template_code}:{template_version}".encode("ascii")


def encrypt_recipient(*, email, audit_log_id, template_code, template_version=1):
    """Return encrypted fields for one authenticated, audit-bound email address.

    A fresh 256-bit DEK encrypts the address; a separately provisioned 256-bit
    KEK encrypts that DEK. Wrapped key field stores nonce || ciphertext || tag.
    """
    if type(email) is not str or not email or len(email.encode("utf-8")) > 254:
        raise OutboxCryptoUnavailable("Registration outbox recipient is invalid.")
    version = getattr(settings, "WORKSPACE_OUTBOX_ACTIVE_KEY_VERSION", "v1")
    aad = _associated_data(
        audit_log_id=audit_log_id,
        template_code=template_code,
        template_version=template_version,
    )
    AESGCM = _aesgcm()
    data_key = secrets.token_bytes(32)
    recipient_nonce = secrets.token_bytes(12)
    wrapped_nonce = secrets.token_bytes(12)
    encrypted = AESGCM(data_key).encrypt(recipient_nonce, email.encode("utf-8"), aad + b":email")
    wrapped = wrapped_nonce + AESGCM(_wrapping_key(version)).encrypt(
        wrapped_nonce, data_key, aad + b":dek"
    )
    if len(encrypted) > 1024 or len(wrapped) > 512:
        raise OutboxCryptoUnavailable("Registration outbox envelope is too large.")
    return {
        "encrypted_recipient": encrypted,
        "recipient_nonce": recipient_nonce,
        "wrapped_data_key": wrapped,
        "encryption_key_version": version,
    }


def decrypt_recipient(*, encrypted_recipient, recipient_nonce, wrapped_data_key,
                      encryption_key_version, audit_log_id, template_code,
                      template_version=1):
    """Internal-only decryptor for a future protected worker; never expose by API."""
    aad = _associated_data(
        audit_log_id=audit_log_id,
        template_code=template_code,
        template_version=template_version,
    )
    AESGCM = _aesgcm()
    try:
        encrypted = bytes(encrypted_recipient)
        nonce = bytes(recipient_nonce)
        wrapped = bytes(wrapped_data_key)
        if len(nonce) != 12 or len(wrapped) != 60 or len(encrypted) < 17:
            raise ValueError("Invalid envelope sizes")
        key = AESGCM(_wrapping_key(encryption_key_version)).decrypt(
            wrapped[:12], wrapped[12:], aad + b":dek"
        )
        email = AESGCM(key).decrypt(nonce, encrypted, aad + b":email")
        return email.decode("utf-8")
    except Exception as exc:
        # Do not include ciphertext, raw recipient or third-party errors.
        raise OutboxCryptoUnavailable("Registration outbox recipient cannot be decrypted.") from exc
