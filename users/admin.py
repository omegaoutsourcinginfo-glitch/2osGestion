from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm
from unfold.widgets import UnfoldAdminImageSmallFieldWidget

from users.models import User
from users.services import generate_password, send_account_credentials_email

admin.site.unregister(Group)


def _apply_kind_flags(user: User) -> None:
    if user.kind == User.UserKind.SUPER_ADMIN:
        user.is_staff = True
        user.is_superuser = True
    elif user.kind == User.UserKind.ADMIN:
        user.is_staff = True
        user.is_superuser = False


class UserCreationForm(forms.ModelForm):
    """Admin creates user with identity fields only; password is generated."""

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone", "kind")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("email", "first_name", "last_name", "phone", "kind"):
            self.fields[name].required = True

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "A user is already registered with this e-mail address."
            )
        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            raise forms.ValidationError("Ce champ est obligatoire.")
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("Phone number already exists")
        return phone

    def clean_kind(self):
        kind = self.cleaned_data.get("kind")
        request = getattr(self, "request", None)
        if request is not None and not request.user.is_superuser:
            raise forms.ValidationError(
                "Seul un superutilisateur peut créer un Admin."
            )
        return kind

    def save(self, commit=True):
        user = super().save(commit=False)
        password = generate_password()
        user.set_password(password)
        user._generated_password = password
        _apply_kind_flags(user)
        if commit:
            user.save()
            self.save_m2m()
        return user


class UserChangeForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "phone",
            "kind",
            "image",
            "is_active",
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name in ("email", "first_name", "last_name", "phone", "kind"):
            if name in self.fields:
                self.fields[name].required = True

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            raise forms.ValidationError("Ce champ est obligatoire.")
        qs = User.objects.filter(phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("Phone number already exists")
        return phone

    def clean_kind(self):
        kind = self.cleaned_data.get("kind")
        request = getattr(self, "request", None)
        if request is not None and not request.user.is_superuser:
            raise forms.ValidationError(
                "Seul un superutilisateur peut définir un Admin."
            )
        return kind


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    change_list_template = "admin/users/user/change_list.html"
    change_form_template = "admin/users/user/change_form.html"
    change_form_outer_before_template = "admin/users/user/change_form_hero.html"
    # Skip Django's auth add_form.html ("After you've created a user…").
    add_form_template = "admin/users/user/change_form.html"
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
        (
            "Profil",
            {
                "description": "Informations du compte affichées sur la fiche utilisateur.",
                "fields": (
                    "email",
                    "first_name",
                    "last_name",
                    "phone",
                    "kind",
                    "image",
                    "is_active",
                ),
            },
        ),
    )
    add_fieldsets = (
        (
            "Profil",
            {
                "classes": ("wide",),
                "description": "Créez le compte. Le mot de passe est généré automatiquement.",
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
    filter_horizontal = ()

    def get_form(self, request, obj=None, change=False, **kwargs):
        Form = super().get_form(request, obj, change=change, **kwargs)

        class RequestForm(Form):
            def __init__(self, *args, **form_kwargs):
                super().__init__(*args, **form_kwargs)
                self.request = request

        return RequestForm

    def formfield_for_dbfield(self, db_field, request, **kwargs):
        if db_field.name == "image":
            kwargs["widget"] = UnfoldAdminImageSmallFieldWidget(
                attrs={"accept": "image/*"}
            )
            return db_field.formfield(**kwargs)
        return super().formfield_for_dbfield(db_field, request, **kwargs)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "kind" and not request.user.is_superuser:
            # Non-superuser cannot assign Admin / Super Admin.
            kwargs["choices"] = []
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser and "kind" not in readonly:
            readonly.append("kind")
        return readonly

    def has_add_permission(self, request):
        # Only a superuser can create Admin / Super Admin accounts.
        return request.user.is_superuser and super().has_add_permission(request)

    def get_urls(self):
        opts = self.model._meta
        custom = [
            path(
                "<path:object_id>/detail/",
                self.admin_site.admin_view(self.detail_view),
                name=f"{opts.app_label}_{opts.model_name}_detail",
            ),
        ]
        return custom + super().get_urls()

    def detail_view(self, request, object_id, extra_context=None):
        opts = self.model._meta
        obj = get_object_or_404(
            self.get_queryset(request).select_related("presence"),
            pk=object_id,
        )
        if not self.has_view_permission(request, obj):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied

        context = {
            **self.admin_site.each_context(request),
            "title": f"Détail — {obj}",
            "opts": opts,
            "original": obj,
            "presence": getattr(obj, "presence", None),
            "has_view_permission": self.has_view_permission(request, obj),
            "has_change_permission": self.has_change_permission(request, obj),
            "has_delete_permission": self.has_delete_permission(request, obj),
            "preserved_filters": self.get_preserved_filters(request),
            **(extra_context or {}),
        }
        return render(request, "admin/users/user/detail.html", context)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context.setdefault(
            "has_delete_permission",
            self.has_delete_permission(request),
        )
        return super().changelist_view(request, extra_context=extra_context)

    def response_add(self, request, obj, post_url_continue=None):
        # One success alert, then back to the user list (no stay-on-edit).
        self.message_user(
            request,
            f"Utilisateur créé avec succès ({obj.email}).",
            messages.SUCCESS,
        )
        opts = self.model._meta
        if "_addanother" in request.POST:
            return HttpResponseRedirect(request.path)
        return HttpResponseRedirect(
            reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
        )

    def save_model(self, request, obj, form, change):
        if "kind" in form.cleaned_data:
            _apply_kind_flags(obj)
        super().save_model(request, obj, form, change)
        if change:
            return
        password = getattr(obj, "_generated_password", None)
        if not password:
            return
        try:
            send_account_credentials_email(obj, password)
        except Exception:
            # Email failure must not block create; success alert is shown in response_add.
            pass

