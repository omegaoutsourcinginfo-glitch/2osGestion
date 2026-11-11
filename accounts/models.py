from __future__ import annotations

from django.conf import settings
from django.db import models
from django.utils import timezone


class UserPresence(models.Model):
    """Last activity of a site user (staff session)."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="presence",
        verbose_name="Utilisateur",
    )
    last_seen_at = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        verbose_name="Dernière activité",
    )
    last_ip = models.GenericIPAddressField(
        null=True,
        blank=True,
        verbose_name="Dernière IP",
    )

    class Meta:
        verbose_name = "Présence utilisateur"
        verbose_name_plural = "Présences utilisateurs"
        ordering = ["-last_seen_at"]

    def __str__(self) -> str:
        return f"{self.user.get_username()} — {self.last_seen_at:%Y-%m-%d %H:%M}"

    @property
    def is_online(self) -> bool:
        from accounts.services import ONLINE_WINDOW

        return self.last_seen_at >= timezone.now() - ONLINE_WINDOW
