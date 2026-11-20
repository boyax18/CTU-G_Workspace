"""Native MySQL types used by the approved authentication schema."""

import re

from django.db import NotSupportedError, models


class MySQLEnumField(models.CharField):
    """Store simple string choices as a native MySQL ENUM."""

    non_db_attrs = tuple(
        attr for attr in models.CharField.non_db_attrs if attr != "choices"
    )

    def db_type(self, connection):
        if connection.vendor != "mysql":
            raise NotSupportedError("The authentication ENUM requires MySQL.")

        values = [value for value, _label in self.flatchoices]
        if not values or any(
            not isinstance(value, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", value)
            for value in values
        ):
            raise ValueError("Authentication ENUM values must be simple string codes.")
        return "enum(" + ",".join(f"'{value}'" for value in values) + ")"


class MySQLTimestampField(models.DateTimeField):
    """Use zero-precision TIMESTAMP with the UTC session in config.settings."""

    def db_type(self, connection):
        if connection.vendor != "mysql":
            raise NotSupportedError("The authentication TIMESTAMP requires MySQL.")
        return "timestamp"


class CurrentTimestamp(models.Func):
    """Match CURRENT_TIMESTAMP without Now()'s MySQL fractional precision."""

    template = "CURRENT_TIMESTAMP"
    arity = 0
    output_field = models.DateTimeField()
