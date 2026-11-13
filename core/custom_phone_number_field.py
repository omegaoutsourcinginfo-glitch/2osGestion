"""Project phone number field (phonenumber_field wrapper)."""

from phonenumber_field.modelfields import PhoneNumberField


class CustomPhoneNumberField(PhoneNumberField):
    """Phone field used by ``users.User`` and other models."""

    pass
