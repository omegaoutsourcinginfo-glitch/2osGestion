"""Update UserPresence on authenticated staff requests."""

from __future__ import annotations

from accounts.services import client_ip, touch_presence


class UserPresenceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        user = getattr(request, "user", None)
        if user is not None and getattr(user, "is_authenticated", False):
            if getattr(user, "is_staff", False):
                touch_presence(user, ip=client_ip(request))
        return response
