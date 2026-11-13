"""Helpers for dashboard user presence."""

from __future__ import annotations

from datetime import timedelta
from typing import TypedDict

from django.contrib.auth import get_user_model
from django.db.models import BooleanField, Case, Value, When
from django.urls import reverse
from django.utils import timezone

ONLINE_WINDOW = timedelta(minutes=15)


class DashboardUser(TypedDict):
    username: str
    full_name: str
    is_online: bool
    is_superuser: bool
    last_seen_at: str
    url: str


class DashboardUsersData(TypedDict):
    dash_users_total: int
    dash_users_online: int
    dash_users: list[DashboardUser]


def client_ip(request) -> str | None:
    forwarded = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    if forwarded:
        return forwarded[:45]
    remote = request.META.get("REMOTE_ADDR") or ""
    return remote[:45] or None


def touch_presence(user, *, ip: str | None = None, min_interval_seconds: int = 60) -> None:
    """Create/update UserPresence, throttled to avoid a write on every request."""
    if user is None or not getattr(user, "is_authenticated", False):
        return
    if not getattr(user, "is_active", False):
        return

    from accounts.models import UserPresence

    now = timezone.now()
    presence, created = UserPresence.objects.get_or_create(
        user=user,
        defaults={"last_seen_at": now, "last_ip": ip},
    )
    if created:
        return
    if (now - presence.last_seen_at).total_seconds() < min_interval_seconds:
        return
    presence.last_seen_at = now
    if ip:
        presence.last_ip = ip
    presence.save(update_fields=["last_seen_at", "last_ip"])


def dashboard_users(*, limit: int = 12) -> DashboardUsersData:
    """Active staff users for the admin dashboard."""
    User = get_user_model()
    now = timezone.now()
    online_since = now - ONLINE_WINDOW

    staff = User.objects.filter(is_active=True, is_staff=True)
    total = staff.count()
    online = staff.filter(presence__last_seen_at__gte=online_since).count()

    users: list[DashboardUser] = []
    qs = (
        staff.select_related("presence")
        .annotate(
            _online=Case(
                When(presence__last_seen_at__gte=online_since, then=Value(True)),
                default=Value(False),
                output_field=BooleanField(),
            )
        )
        .order_by("-_online", "-presence__last_seen_at", "email")[:limit]
    )
    for user in qs:
        presence = getattr(user, "presence", None)
        last_seen = getattr(presence, "last_seen_at", None)
        is_online = bool(last_seen and last_seen >= online_since)
        full_name = (user.get_full_name() or "").strip()
        users.append(
            {
                "username": user.get_username(),
                "full_name": full_name,
                "is_online": is_online,
                "is_superuser": bool(user.is_superuser),
                "last_seen_at": (
                    timezone.localtime(last_seen).strftime("%d/%m/%Y %H:%M")
                    if last_seen
                    else "—"
                ),
                "url": reverse("admin:users_user_change", args=[user.pk]),
            }
        )

    return {
        "dash_users_total": total,
        "dash_users_online": online,
        "dash_users": users,
    }
