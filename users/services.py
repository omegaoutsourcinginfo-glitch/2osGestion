"""User helpers (admin create — auto password + email). No API/serializers."""

from __future__ import annotations

import secrets
import string
import textwrap

from django.conf import settings
from django.contrib.auth.models import Group, Permission
from django.core.mail import send_mail
from django.db.models import Q

from users.models import User

UTILISATEUR_GROUP = "Utilisateur"


def generate_password(length: int = 12) -> str:
    # Avoid ambiguous / hard-to-type chars (O/0, l/1, quotes, %, *…).
    alphabet = (
        "ABCDEFGHJKLMNPQRSTUVWXYZ"
        "abcdefghijkmnopqrstuvwxyz"
        "23456789"
        "!@#$?"
    )
    return "".join(secrets.choice(alphabet) for _ in range(length))


def ensure_utilisateur_group() -> Group:
    """
    Staff group for génie civil project work.
    - Full access to `projects` (+ presence in `accounts`)
    - Never includes `users` permissions (no user directory)
    """
    group, _ = Group.objects.get_or_create(name=UTILISATEUR_GROUP)
    perms = Permission.objects.filter(
        Q(content_type__app_label="projects")
        | Q(content_type__app_label="accounts")
    ).exclude(content_type__app_label="users")
    group.permissions.set(perms)
    return group


def apply_role_access(user: User) -> None:
    """
    Sync Django auth flags + group for product login.
    - Super Admin → is_superuser (users + projects + everything)
    - Utilisateur → is_staff + projects only (gestion de projets)
    """
    user.is_staff = True  # required for /admin/ login
    user.is_superuser = user.kind == User.UserKind.SUPER_ADMIN
    # Groups need a persisted pk — caller must save() first when creating.
    if not user.pk:
        return
    group = ensure_utilisateur_group()
    if user.kind == User.UserKind.USER:
        user.groups.add(group)
        # Hard strip any accidental user-admin perms.
        user.user_permissions.clear()
    else:
        user.groups.remove(group)


def send_account_credentials_email(
    user: User,
    password: str,
    *,
    reset: bool = False,
) -> None:
    """Send login password by e-mail (create or reset)."""
    company = getattr(settings, "COMPANY_NAME", "2os Gestion")
    subject = company
    if reset:
        message = textwrap.dedent(
            f"""\
            Bonjour {user.get_full_name() or user.email},

            Un nouveau mot de passe a été généré pour votre compte {company}.

            Mot de passe : {password}

            Pour des raisons de sécurité, changez-le après votre prochaine connexion.

            Cordialement,
            {company}
            """
        )
    else:
        message = textwrap.dedent(
            f"""\
            Bonjour {user.get_full_name() or user.email},

            Votre compte {company} a été créé. Utilisez le mot de passe ci-dessous pour vous connecter.

            Mot de passe : {password}

            Pour des raisons de sécurité, changez-le après votre première connexion.

            Cordialement,
            {company}
            """
        )
    sent = send_mail(
        subject,
        message,
        settings.DEFAULT_FROM_EMAIL,
        [user.email],
        fail_silently=False,
    )
    if not sent:
        raise RuntimeError(f"send_mail returned {sent} for {user.email}")


def reset_and_email_password(user: User) -> str:
    """Generate a new password, save it, e-mail credentials. Returns plaintext."""
    password = generate_password()
    user.set_password(password)
    user.save(update_fields=["password"])
    send_account_credentials_email(user, password, reset=True)
    return password
