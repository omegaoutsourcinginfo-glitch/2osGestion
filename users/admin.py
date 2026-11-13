from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import Group
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm

from users.models import User
from users.services import generate_password, send_account_credentials_email

admin.site.unregister(Group)


class UserCreationForm(forms.ModelForm):
    """Admin creates user with identity fields only; password is generated."""

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone", "kind")

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "A user is already registered with this e-mail address."
            )
        return email

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if phone and User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("Phone number already exists")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        password = generate_password()
        user.set_password(password)
        user._generated_password = password
        # Flags follow kind (fields hidden on add form).
        if user.kind == User.UserKind.SUPER_ADMIN:
            user.is_staff = True
            user.is_superuser = True
        elif user.kind == User.UserKind.ADMIN:
            user.is_staff = True
            user.is_superuser = False
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Mot de passe",
        help_text=(
            "Les mots de passe ne sont pas stockés en clair. "
            "Vous pouvez les modifier avec le formulaire dédié."
        ),
    )

    class Meta:
        model = User
        fields = (
            "email",
            "password",
            "first_name",
            "last_name",
            "phone",
            "kind",
            "image",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")
        if not phone:
            return phone
        qs = User.objects.filter(phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Phone number already exists")
        return phone


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    change_list_template = "admin/users/user/change_list.html"
    actions = None
    ordering = ("-date_joined",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "phone",
        "kind",
        "is_staff",
        "is_active",
        "date_joined",
    )
    list_filter = ("kind", "is_staff", "is_superuser", "is_active")
    search_fields = ("email", "first_name", "last_name", "phone", "reference")
    readonly_fields = ("reference", "last_login", "date_joined")
    list_select_related = ("presence",)

    fieldsets = (
        (None, {"fields": ("email", "password", "reference")}),
        (
            "Informations",
            {"fields": ("first_name", "last_name", "phone", "kind", "image")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "description": (
                    "Le mot de passe est généré automatiquement et envoyé par e-mail."
                ),
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "phone",
                    "kind",
                ),
            },
        ),
    )
    filter_horizontal = ("groups", "user_permissions")

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if change:
            return
        password = getattr(obj, "_generated_password", None)
        if not password:
            return
        try:
            send_account_credentials_email(obj, password)
            self.message_user(
                request,
                f"Compte créé. Mot de passe envoyé à {obj.email}.",
                messages.SUCCESS,
            )
        except Exception as exc:
            self.message_user(
                request,
                f"Compte créé, mais l'e-mail a échoué: {exc}",
                messages.WARNING,
            )

    class Media:
        css = {"all": ("accounts/css/user_cards.css",)}
