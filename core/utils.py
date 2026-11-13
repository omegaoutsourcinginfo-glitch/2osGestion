"""Shared model field helpers."""

from __future__ import annotations

import secrets
import string

from django.db import models


class PrefixedRandomCharField(models.CharField):
    """CharField that auto-fills ``{prefix}_{random}`` on first save."""

    def __init__(self, *args, prefix: str = "", length: int = 16, **kwargs):
        self.prefix = prefix or ""
        self.random_length = length
        max_len = len(self.prefix) + (1 if self.prefix else 0) + length
        kwargs.setdefault("max_length", max_len)
        kwargs.setdefault("editable", False)
        super().__init__(*args, **kwargs)

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        kwargs["prefix"] = self.prefix
        kwargs["length"] = self.random_length
        return name, path, args, kwargs

    def pre_save(self, model_instance, add):
        value = getattr(model_instance, self.attname)
        if not value:
            alphabet = string.ascii_lowercase + string.digits
            token = "".join(secrets.choice(alphabet) for _ in range(self.random_length))
            value = f"{self.prefix}_{token}" if self.prefix else token
            setattr(model_instance, self.attname, value)
        return value
