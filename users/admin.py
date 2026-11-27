from django import forms
from django.contrib import admin, messages
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.models import Group
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import path, reverse
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm
from unfold.widgets import UnfoldAdminImageSmallFieldWidget

from users.models import User
from users.services import (
    apply_role_access,
    reset_and_email_password,
    send_account_credentials_email,
)

admin.site.unregister(Group)


class RoleRadioSelect(forms.RadioSelect):
    """Rôle as visible radio buttons (not a select dropdown)."""

    template_name = "users/widgets/role_radio.html"
    option_template_name = "users/widgets/role_option.html"


class EmailAdminAuthenticationForm(AuthenticationForm):
    """Admin login uses email in the username field."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Adresse e-mail"
        self.fields["username"].widget.attrs.update(
            {
                "autocomplete": "username",
                "placeholder": "email@exemple.com",
            }
        )


admin.site.login_form = EmailAdminAuthenticationForm

_orig_admin_login = admin.site.login


def _admin_login(request, extra_context=None):
    """After login, never send Utilisateur to /admin/users/ (403 looks like failed login)."""
    response = _orig_admin_login(request, extra_context=extra_context)
    user = getattr(request, "user", None)
    if (
        request.method == "POST"
        and user is not None
        and user.is_authenticated
        and not user.is_superuser
        and isinstance(response, HttpResponseRedirect)
    ):
        target = response.url or ""
        if "/users/" in target:
            return HttpResponseRedirect(reverse("admin:index"))
    return response


admin.site.login = _admin_login


def _apply_kind_flags(user: User) -> None:
    """Keep Django auth flags in sync with Rôle (Super Admin / Utilisateur)."""
    apply_role_access(user)


class UserCreationForm(forms.ModelForm):
    """Admin creates user with identity fields only; password is generated."""

    class Meta:
        model = User
        fields = ("email", "first_name", "last_name", "phone", "kind")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        labels = {
            "email": "Adresse e-mail",
            "first_name": "Prénom",
            "last_name": "Nom",
            "phone": "Téléphone",
            "kind": "Rôle",
        }
        for name in ("email", "first_name", "last_name", "phone", "kind"):
            self.fields[name].required = True
            if name in labels:
                self.fields[name].label = labels[name]
        self.fields["kind"].widget = RoleRadioSelect(
            choices=User.UserKind.choices,
        )
        self.fields["kind"].initial = User.UserKind.USER

    def clean_email(self):
        email = self.cleaned_data.get("email")
        if email and User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "Un utilisateur est déjà enregistré avec cette adresse e-mail."
            )
        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            raise forms.ValidationError("Ce champ est obligatoire.")
        if User.objects.filter(phone=phone).exists():
            raise forms.ValidationError("Ce numéro de téléphone existe déjà.")
        return phone

    def clean_kind(self):
        kind = self.cleaned_data.get("kind")
        request = getattr(self, "request", None)
        if request is not None and not request.user.is_superuser:
            raise forms.ValidationError(
                "Seul un Super Admin peut créer un utilisateur."
            )
        if kind not in (
            User.UserKind.SUPER_ADMIN,
            User.UserKind.USER,
        ):
            raise forms.ValidationError("Rôle invalide.")
        return kind

    def save(self, commit=True):
        # Like serializer.create(): generate password then set_password.
        from users.services import generate_password

        user = super().save(commit=False)
        password = generate_password(12)
        user.set_password(password)
        # Keep on both form + instance (admin save_form uses commit=False).
        self._generated_password = password
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
        labels = {
            "email": "Adresse e-mail",
            "first_name": "Prénom",
            "last_name": "Nom",
            "phone": "Téléphone",
            "kind": "Rôle",
            "image": "Photo",
            "is_active": "Actif",
        }
        for name, label in labels.items():
            if name in self.fields:
                self.fields[name].label = label
        for name in ("email", "first_name", "last_name", "phone", "kind"):
            if name in self.fields:
                self.fields[name].required = True
        if "kind" in self.fields:
            self.fields["kind"].widget = RoleRadioSelect(
                choices=User.UserKind.choices,
            )

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
                "Seul un Super Admin peut modifier le rôle."
            )
        if kind not in (
            User.UserKind.SUPER_ADMIN,
            User.UserKind.USER,
        ):
            raise forms.ValidationError("Rôle invalide.")
        return kind


@admin.register(User)
class UserAdmin(DjangoUserAdmin, ModelAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm
    change_list_template = "admin/users/user/change_list.html"
    change_form_template = "admin/users/user/change_form.html"
    # Hero is included inside change_form.html (one connected composition).
    change_form_outer_before_template = None
    # Skip Django's auth add_form.html ("After you've created a user…").
    add_form_template = "admin/users/user/change_form.html"
    actions = None

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        # Keep create page short: one primary Enregistrer in view.
        extra_context = extra_context or {}
        if object_id is None:
            extra_context.update(
                {
                    "show_save_and_continue": False,
                    "show_save_and_add_another": False,
                }
            )
        return super().changeform_view(request, object_id, form_url, extra_context)
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
    # Card UI: hide Unfold Filters button / sidebar.
    list_filter = ()
    search_fields = ("email", "first_name", "last_name", "phone", "reference")
    readonly_fields = ("reference", "last_login", "date_joined")
    list_select_related = ("presence",)

    fieldsets = (
        (
            "Profil",
            {
                "description": (
                    '<div class="user-alert flex items-start gap-3 border-0 bg-primary-50 p-3 text-sm text-primary-800 shadow-none dark:bg-primary-950 dark:text-primary-200">'
                    '<span class="material-symbols-outlined flex h-8 w-8 shrink-0 items-center justify-center bg-white text-base text-primary-600 shadow-none dark:bg-base-800" aria-hidden="true">badge</span>'
                    '<div><strong class="block font-bold text-primary-900 dark:text-primary-100">Profil utilisateur</strong>'
                    '<span class="text-primary-800 dark:text-primary-200">Ces informations apparaissent sur la fiche et dans la liste des comptes.</span>'
                    "</div></div>"
                ),
                "fields": (
                    ("email", "phone"),
                    ("first_name", "last_name"),
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
                "description": (
                    '<div class="user-alert flex items-start gap-3 border-0 bg-primary-50 p-3 text-sm text-primary-800 shadow-none dark:bg-primary-950 dark:text-primary-200">'
                    '<span class="material-symbols-outlined flex h-8 w-8 shrink-0 items-center justify-center bg-white text-base text-primary-600 shadow-none dark:bg-base-800" aria-hidden="true">auto_awesome</span>'
                    '<div><strong class="block font-bold text-primary-900 dark:text-primary-100">Mot de passe automatique</strong>'
                    '<span class="text-primary-800 dark:text-primary-200">Créé à l\'enregistrement et envoyé par e-mail à l\'utilisateur.</span>'
                    "</div></div>"
                ),
                "fields": (
                    ("email", "phone"),
                    ("first_name", "last_name"),
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
        if db_field.name == "kind":
            # Only two roles in the product UI — radio pills, not a select.
            kwargs["choices"] = list(User.UserKind.choices)
            if not request.user.is_superuser:
                kwargs["choices"] = [
                    c for c in kwargs["choices"] if c[0] == User.UserKind.USER
                ]
            kwargs["widget"] = RoleRadioSelect()
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def get_readonly_fields(self, request, obj=None):
        readonly = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser and "kind" not in readonly:
            readonly.append("kind")
        return readonly

    def has_module_permission(self, request):
        # Utilisateur must not see the users app at all.
        return bool(request.user.is_superuser)

    def has_view_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_change_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_delete_permission(self, request, obj=None):
        return bool(request.user.is_superuser)

    def has_add_permission(self, request):
        # Only Super Admin can create accounts.
        return bool(request.user.is_superuser)

    def _redirect_non_superuser(self, request):
        """Avoid raw 403 after login when ``next`` points at /admin/users/…"""
        if request.user.is_superuser:
            return None
        messages.warning(
            request,
            "Accès réservé au Super Admin. Bienvenue sur le tableau de bord projets.",
        )
        return HttpResponseRedirect(reverse("admin:index"))

    def get_urls(self):
        opts = self.model._meta
        custom = [
            path(
                "<path:object_id>/detail/",
                self.admin_site.admin_view(self.detail_view),
                name=f"{opts.app_label}_{opts.model_name}_detail",
            ),
            path(
                "<path:object_id>/quick-delete/",
                self.admin_site.admin_view(self.quick_delete_view),
                name=f"{opts.app_label}_{opts.model_name}_quick_delete",
            ),
            path(
                "<path:object_id>/send-password/",
                self.admin_site.admin_view(self.send_password_view),
                name=f"{opts.app_label}_{opts.model_name}_send_password",
            ),
        ]
        return custom + super().get_urls()

    def send_password_view(self, request, object_id):
        """POST: reset password + send it by e-mail (AJAX JSON)."""
        opts = self.model._meta
        obj = get_object_or_404(self.get_queryset(request), pk=object_id)
        changelist = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
        wants_json = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in (request.headers.get("Accept") or "")
        )

        def _json(ok, message, status=200):
            return JsonResponse(
                {"ok": ok, "message": message, "id": str(object_id)},
                status=status,
            )

        if request.method != "POST":
            if wants_json:
                return _json(False, "Méthode non autorisée.", status=405)
            return HttpResponseRedirect(changelist)

        if not self.has_change_permission(request, obj):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied

        if not obj.email:
            msg = "Cet utilisateur n'a pas d'adresse e-mail."
            if wants_json:
                return _json(False, msg, status=400)
            self.message_user(request, msg, messages.ERROR)
            return HttpResponseRedirect(changelist)

        try:
            reset_and_email_password(obj)
        except Exception as e:
            msg = f"Impossible d'envoyer le mot de passe à {obj.email} : {e}"
            if wants_json:
                return _json(False, msg, status=400)
            self.message_user(request, msg, messages.ERROR)
            return HttpResponseRedirect(changelist)

        msg = f"Nouveau mot de passe envoyé à {obj.email}."
        if wants_json:
            return _json(True, msg)
        self.message_user(request, msg, messages.SUCCESS)
        return HttpResponseRedirect(changelist)

    def quick_delete_view(self, request, object_id):
        """POST delete from cards/detail. AJAX → JSON (no full page refresh)."""
        opts = self.model._meta
        obj = get_object_or_404(self.get_queryset(request), pk=object_id)
        changelist = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
        wants_json = (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in (request.headers.get("Accept") or "")
        )

        def _json(ok, message, status=200):
            return JsonResponse(
                {"ok": ok, "message": message, "id": str(object_id)},
                status=status,
            )

        if request.method != "POST":
            if wants_json:
                return _json(False, "Méthode non autorisée.", status=405)
            return HttpResponseRedirect(changelist)

        if not self.has_delete_permission(request, obj):
            from django.core.exceptions import PermissionDenied

            raise PermissionDenied

        if obj.pk == request.user.pk:
            msg = "Vous ne pouvez pas supprimer votre propre compte."
            if wants_json:
                return _json(False, msg, status=400)
            self.message_user(request, msg, messages.ERROR)
            return HttpResponseRedirect(changelist)

        label = str(obj)
        try:
            self.log_deletions(request, [obj])
            self.delete_model(request, obj)
        except Exception as e:
            msg = f"Impossible de supprimer {label} : {e}"
            if wants_json:
                return _json(False, msg, status=400)
            self.message_user(request, msg, messages.ERROR)
            return HttpResponseRedirect(changelist)

        msg = f"Utilisateur « {label} » supprimé avec succès."
        if wants_json:
            return _json(True, msg)
        self.message_user(request, msg, messages.SUCCESS)
        return HttpResponseRedirect(changelist)

    def detail_view(self, request, object_id, extra_context=None):
        denied = self._redirect_non_superuser(request)
        if denied is not None:
            return denied
        opts = self.model._meta
        obj = get_object_or_404(
            self.get_queryset(request).select_related("presence"),
            pk=object_id,
        )
        if not self.has_view_permission(request, obj):
            return self._redirect_non_superuser(request) or HttpResponseRedirect(
                reverse("admin:index")
            )

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
        denied = self._redirect_non_superuser(request)
        if denied is not None:
            return denied
        extra_context = extra_context or {}
        extra_context.setdefault(
            "has_change_permission",
            self.has_change_permission(request),
        )
        extra_context.setdefault(
            "has_delete_permission",
            self.has_delete_permission(request),
        )
        return super().changelist_view(request, extra_context=extra_context)

    def _wants_add_dialog(self, request) -> bool:
        if request.POST.get("_dialog") == "1" or request.GET.get("dialog") == "1":
            return True
        if request.headers.get("X-Dialog") == "1":
            return True
        return False

    def _wants_json(self, request) -> bool:
        return (
            request.headers.get("X-Requested-With") == "XMLHttpRequest"
            or "application/json" in (request.headers.get("Accept") or "")
        )

    def _prepare_add_dialog_form(self, form):
        """Compact Tailwind-friendly widgets for the dialog partial."""
        placeholders = {
            "email": "email@exemple.com",
            "phone": "+212 6 …",
            "first_name": "Prénom",
            "last_name": "Nom",
        }
        for name, ph in placeholders.items():
            if name not in form.fields:
                continue
            form.fields[name].widget.attrs.update(
                {
                    "placeholder": ph,
                    "autocomplete": "off",
                    "class": (
                        "h-10 w-full rounded-xl border border-base-200 bg-white "
                        "py-2 pl-9 pr-3 text-sm shadow-none outline-none "
                        "focus:border-primary-500 focus:ring-2 focus:ring-primary-600/15 "
                        "dark:border-base-600 dark:bg-base-800"
                    ),
                }
            )
        return form

    def add_dialog_view(self, request):
        """GET: form HTML partial. POST: create user → JSON (or form HTML on error)."""
        opts = self.model._meta
        changelist = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
        form_action = reverse(f"admin:{opts.app_label}_{opts.model_name}_add")
        denied = self._redirect_non_superuser(request)
        if denied is not None:
            if self._wants_json(request) and request.method == "POST":
                return JsonResponse(
                    {"ok": False, "message": "Permission refusée."},
                    status=403,
                )
            return denied

        if not self.has_add_permission(request):
            if self._wants_json(request):
                return JsonResponse(
                    {"ok": False, "message": "Permission refusée."},
                    status=403,
                )
            return HttpResponseRedirect(changelist)

        Form = self.add_form

        if request.method == "POST":
            form = Form(request.POST, request.FILES)
            form.request = request
            self._prepare_add_dialog_form(form)
            if form.is_valid():
                obj = form.save(commit=False)
                self.save_model(request, obj, form, change=False)
                form.save_m2m()
                self.save_related(request, form, [], change=False)

                password = getattr(request, "_new_user_password", None) or getattr(
                    form, "_generated_password", None
                )
                message = f"Utilisateur créé ({obj.email})."
                if password:
                    try:
                        send_account_credentials_email(obj, password)
                        message = f"Utilisateur créé — e-mail envoyé à {obj.email}."
                    except Exception as e:
                        message = (
                            f"Utilisateur créé ({obj.email}), "
                            f"mais l'e-mail n'a pas pu être envoyé : {e}"
                        )

                if self._wants_json(request):
                    return JsonResponse(
                        {
                            "ok": True,
                            "message": message,
                            "id": str(obj.pk),
                        }
                    )
                return HttpResponseRedirect(changelist)

            # Validation errors → re-render form HTML for the dialog body
            return render(
                request,
                "admin/users/user/add_dialog.html",
                {
                    "form": form,
                    "form_action": form_action,
                    "opts": opts,
                },
                status=400,
            )

        form = Form()
        form.request = request
        self._prepare_add_dialog_form(form)
        return render(
            request,
            "admin/users/user/add_dialog.html",
            {
                "form": form,
                "form_action": form_action,
                "opts": opts,
            },
        )

    def add_view(self, request, form_url="", extra_context=None):
        denied = self._redirect_non_superuser(request)
        if denied is not None:
            return denied

        # Dialog / AJAX path — never a full admin page
        if self._wants_add_dialog(request) or (
            request.method == "POST" and self._wants_json(request)
        ):
            return self.add_dialog_view(request)

        # Direct visit to /add/ → open dialog on the changelist instead
        if request.method == "GET":
            opts = self.model._meta
            url = reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
            return HttpResponseRedirect(f"{url}?open_add=1")

        return super().add_view(request, form_url, extra_context)

    def change_view(self, request, object_id, form_url="", extra_context=None):
        denied = self._redirect_non_superuser(request)
        if denied is not None:
            return denied
        return super().change_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        if "kind" in form.cleaned_data:
            _apply_kind_flags(obj)
        super().save_model(request, obj, form, change)
        # Groups need pk — sync again after save.
        apply_role_access(obj)
        if change:
            return
        # Stash plaintext password for response_add (serializer.create email step).
        request._new_user_password = (
            getattr(form, "_generated_password", None)
            or getattr(obj, "_generated_password", None)
        )

    def response_add(self, request, obj, post_url_continue=None):
        # Same as serializer.create(): send login password by e-mail after save.
        password = getattr(request, "_new_user_password", None)
        if password:
            try:
                send_account_credentials_email(obj, password)
                self.message_user(
                    request,
                    f"Utilisateur créé — e-mail envoyé à {obj.email}.",
                    messages.SUCCESS,
                )
            except Exception as e:
                print(f"Error sending email: {e}")
                self.message_user(
                    request,
                    f"Utilisateur créé ({obj.email}), mais l'e-mail n'a pas pu être envoyé : {e}",
                    messages.ERROR,
                )
        else:
            self.message_user(
                request,
                f"Utilisateur créé ({obj.email}), mais aucun mot de passe à envoyer.",
                messages.WARNING,
            )
        opts = self.model._meta
        if "_addanother" in request.POST:
            return HttpResponseRedirect(request.path)
        return HttpResponseRedirect(
            reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")
        )

