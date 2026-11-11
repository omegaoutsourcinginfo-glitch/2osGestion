from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from accounts.services import client_ip, touch_presence


@receiver(user_logged_in)
def mark_presence_on_login(sender, request, user, **kwargs):
    touch_presence(user, ip=client_ip(request), min_interval_seconds=0)
