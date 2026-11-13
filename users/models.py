from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.custom_phone_number_field import CustomPhoneNumberField
from core.utils import PrefixedRandomCharField
from users.managers import UserManager


class User(AbstractUser):
    """
    Custom email-based user (no username).
    Admins create / update / delete users via Unfold admin.
    """

    objects = UserManager()

    username = None

    reference = PrefixedRandomCharField(length=16, prefix="user", unique=True)

    email = models.EmailField(
        blank=False,
        max_length=254,
        unique=True,
        verbose_name="email address",
    )
    phone = CustomPhoneNumberField(null=True, blank=True, unique=True)

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = []

    class UserKind(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", _("Super Admin")
        ADMIN = "ADMIN", _("Admin")
        OTHER = "OTHER", _("Other")

    kind = models.CharField(
        max_length=255,
        choices=UserKind.choices,
        default=UserKind.OTHER,
    )
    image = models.ImageField(
        upload_to="users/images/",
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.email
