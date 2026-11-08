from collections.abc import Mapping

from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .models import Account


class StringField(serializers.CharField):
    """Reject numeric coercion for public string fields."""

    def to_internal_value(self, data):
        if not isinstance(data, str):
            self.fail("invalid")
        return super().to_internal_value(data)


class RegistrationSerializer(serializers.Serializer):
    school_id = StringField(max_length=50)
    email = StringField(max_length=150, allow_blank=True, required=False, default="")
    first_name = StringField(max_length=100)
    middle_name = StringField(max_length=100, allow_blank=True, required=False, default="")
    last_name = StringField(max_length=100)
    suffix = StringField(max_length=20, allow_blank=True, required=False, default="")
    requested_role = serializers.ChoiceField(
        choices=["Student", "Instructor"],
        error_messages={"invalid_choice": "Select Student or Instructor."},
    )
    password = StringField(max_length=128, trim_whitespace=False, write_only=True)
    password_confirmation = StringField(max_length=128, trim_whitespace=False, write_only=True)

    def to_internal_value(self, data):
        if not isinstance(data, Mapping):
            raise serializers.ValidationError({"non_field_errors": ["Provide a JSON object."]})
        if set(data) - set(self.fields):
            raise serializers.ValidationError({"non_field_errors": ["The request contains unsupported fields."]})
        return super().to_internal_value(data)

    def validate_school_id(self, value):
        value = Account.normalize_username(value)
        if len(value) > 50:
            raise serializers.ValidationError("Ensure this field has no more than 50 characters.")
        return value

    def validate_email(self, value):
        if value:
            try:
                Account._meta.get_field("email").clean(value, None)
            except DjangoValidationError as exc:
                raise serializers.ValidationError(exc.messages) from exc
        return value

    def validate(self, data):
        if data["password"] != data["password_confirmation"]:
            raise serializers.ValidationError({"password_confirmation": ["Passwords do not match."]})
        candidate = Account(school_id=data["school_id"], email=data["email"] or None)
        candidate.first_name, candidate.last_name = data["first_name"], data["last_name"]
        candidate.username = data["school_id"]
        try:
            validate_password(data["password"], user=candidate)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc
        return data
