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

    first_name = models.CharField("Prénom", max_length=150)
    last_name = models.CharField("Nom", max_length=150)

    email = models.EmailField(
        blank=False,
        max_length=254,
        unique=True,
        verbose_name="Adresse e-mail",
    )
    phone = CustomPhoneNumberField(unique=True, verbose_name="Téléphone")

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name", "phone"]

    class UserKind(models.TextChoices):
        SUPER_ADMIN = "SUPER_ADMIN", "Super Admin"
        USER = "USER", "Utilisateur"

    kind = models.CharField(
        max_length=255,
        choices=UserKind.choices,
        default=UserKind.USER,
        verbose_name="Rôle",
    )
    image = models.ImageField(
        upload_to="users/images/",
        null=True,
        blank=True,
        verbose_name="Photo",
    )

    class Meta:
        verbose_name = "Utilisateur"
        verbose_name_plural = "Utilisateurs"
        ordering = ["-date_joined"]

    def __str__(self) -> str:
        return self.email
