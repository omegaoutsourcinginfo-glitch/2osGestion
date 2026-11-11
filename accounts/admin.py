from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import GroupAdmin as DjangoGroupAdmin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm

from .models import UserPresence

User = get_user_model()

admin.site.unregister(User)
admin.site.unregister(Group)


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "is_staff",
        "is_active",
        "last_login",
        "presence_last_seen",
    )
    list_filter = ("is_staff", "is_superuser", "is_active", "groups")
    ordering = ("username",)
    list_select_related = ("presence",)

    @admin.display(description="Dernière activité", ordering="presence__last_seen_at")
    def presence_last_seen(self, obj):
        presence = getattr(obj, "presence", None)
        if presence is None:
            return "—"
        return presence.last_seen_at


@admin.register(Group)
class GroupAdmin(DjangoGroupAdmin, ModelAdmin):
    pass


@admin.register(UserPresence)
class UserPresenceAdmin(ModelAdmin):
    list_display = ("user", "last_seen_at", "last_ip", "online_badge")
    list_filter = ("last_seen_at",)
    search_fields = ("user__username", "user__email", "last_ip")
    readonly_fields = ("user", "last_seen_at", "last_ip")
    ordering = ("-last_seen_at",)

    @admin.display(description="En ligne", boolean=True)
    def online_badge(self, obj):
        return obj.is_online

    def has_add_permission(self, request):
        return False
