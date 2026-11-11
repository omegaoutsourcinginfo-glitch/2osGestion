from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from accounts.models import UserPresence
from accounts.services import ONLINE_WINDOW, dashboard_users, touch_presence


class UserPresenceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser("dashuser", "d@test.com", "pass")

    def test_touch_presence_creates_row(self):
        touch_presence(self.user, ip="127.0.0.1", min_interval_seconds=0)
        presence = UserPresence.objects.get(user=self.user)
        self.assertEqual(presence.last_ip, "127.0.0.1")
        self.assertTrue(presence.is_online)

    def test_middleware_updates_presence_on_admin(self):
        self.client.force_login(self.user)
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(UserPresence.objects.filter(user=self.user).exists())

    def test_dashboard_users_counts_online(self):
        other = get_user_model().objects.create_user(
            "staff2", "s2@test.com", "pass", is_staff=True
        )
        touch_presence(self.user, min_interval_seconds=0)
        UserPresence.objects.create(
            user=other,
            last_seen_at=timezone.now() - ONLINE_WINDOW - timedelta(minutes=1),
        )
        data = dashboard_users()
        self.assertEqual(data["dash_users_total"], 2)
        self.assertEqual(data["dash_users_online"], 1)
        self.assertTrue(any(u["username"] == "dashuser" and u["is_online"] for u in data["dash_users"]))

    def test_dashboard_shows_users_section(self):
        self.client.force_login(self.user)
        response = self.client.get("/admin/")
        body = response.content.decode("utf-8")
        self.assertIn("Utilisateurs", body)
        self.assertIn("dashuser", body)
        self.assertIn(reverse("admin:auth_user_changelist"), body)
