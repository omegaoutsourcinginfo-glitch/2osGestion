"""User helpers (admin create — auto password + email). No API/serializers."""

from __future__ import annotations

import secrets
import string

from django.conf import settings
from django.core.mail import send_mail

from users.models import User


def generate_password(length: int = 12) -> str:
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*()"
    return "".join(secrets.choice(alphabet) for _ in range(length))


def send_account_credentials_email(user: User, password: str) -> None:
    company = getattr(settings, "COMPANY_NAME", "2os Gestion")
    subject = company
    message = f"""Hello {user.email},

Your account has been created successfully. Please use the password below to login.

Password: {password}

For security reasons, we recommend changing it after your first login.

Thank you for using {company}!
"""
    send_mail(
        subject=subject,
        message=message,
        from_email=getattr(settings, "DEFAULT_FROM_EMAIL", None),
        recipient_list=[user.email],
        fail_silently=False,
    )
