"""Exact MySQL column mappings for the approved-development outbox schema.

Keep this module importable by historical migrations. No email/network operations.
"""

from django.db import NotSupportedError, models


class MySQLVarBinaryField(models.BinaryField):
    """Map BinaryField to MySQL VARBINARY(N), not MySQL LONGBLOB."""

    def db_type(self, connection):
        if connection.vendor != "mysql":
            raise NotSupportedError("Registration outbox VARBINARY requires MySQL.")
        if type(self.max_length) is not int or not 1 <= self.max_length <= 65535:
            raise ValueError("VARBINARY length must be between 1 and 65535.")
        return f"varbinary({self.max_length})"


class MySQLFixedBinaryField(models.BinaryField):
    """Map the 96-bit AES-GCM nonce to MySQL BINARY(12)."""

    def db_type(self, connection):
        if connection.vendor != "mysql":
            raise NotSupportedError("Registration outbox BINARY requires MySQL.")
        if type(self.max_length) is not int or not 1 <= self.max_length <= 255:
            raise ValueError("BINARY length must be between 1 and 255.")
        return f"binary({self.max_length})"


class MySQLDateTimeSecondsField(models.DateTimeField):
    """Map zero-precision DATETIME exactly as specified in the v2 DBML."""

    def db_type(self, connection):
        if connection.vendor != "mysql":
            raise NotSupportedError("Registration outbox DATETIME requires MySQL.")
        return "datetime"
