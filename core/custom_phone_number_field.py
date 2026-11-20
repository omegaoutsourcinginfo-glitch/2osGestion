"""Free-text phone field (any number / format accepted)."""

from django.db import models


class CustomPhoneNumberField(models.CharField):
    """Phone field used by ``users.User`` — no international validation."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("max_length", 128)
        # Drop phonenumber_field-only kwargs if present in old migrations/code.
        kwargs.pop("region", None)
        super().__init__(*args, **kwargs)
