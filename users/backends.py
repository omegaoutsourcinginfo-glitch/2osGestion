from django.contrib.auth.backends import ModelBackend

from users.models import User


class EmailBackend(ModelBackend):
    """Authenticate with email (admin login still posts ``username`` = email)."""

    def authenticate(self, request, username=None, email=None, password=None, **kwargs):
        identifier = email or username
        if not identifier or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=identifier)
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
