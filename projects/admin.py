from django import forms
from django.contrib import admin, messages
from django.core.exceptions import ValidationError
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.html import format_html
from unfold.admin import ModelAdmin, StackedInline, TabularInline
from unfold.decorators import action
from unfold.enums import ActionVariant

from .models import (
    AnnexeDocument,
    AnnexeDossier,
    Autorisation,
    FinancementDocument,
    Intervenant,
    PlanningDocument,
    PlanningExecution,
    Project,
    ProjectDocument,
    ProjectImage,
    StructureFinancement,
    TerrainMere,
)


class EditUpdateActionsMixin:
    """Adds Modifier in the row three-dot menu."""

    actions_row = ["modifier"]

    @action(
        description="Modifier",
        icon="edit",
        variant=ActionVariant.PRIMARY,
        url_path="modifier",
        permissions=["change"],
    )
    def modifier(self, request, object_id):
        opts = self.model._meta
        return redirect(
            reverse(f"admin:{opts.app_label}_{opts.model_name}_change", args=[object_id])
        )


class ProjectFicheListLinkMixin:
    """Changelist code/titre open the project fiche (optional tab hash)."""

    fiche_tab = ""

    def _fiche_url(self, project):
        url = project.get_absolute_url()
        tab = getattr(self, "fiche_tab", "") or ""
        if tab:
            return f"{url}#{tab}"
        return url

    def _fiche_link(self, project, text):
        return format_html(
            '<a class="project-detail-link" href="{}" data-detail-url="{}">{}</a>',
            self._fiche_url(project),
            self._fiche_url(project),
            text,
        )


class ProjectArchiveRowMixin:
    """Three-dot Voir archive + list Archives for models linked to Project."""

    archive_changelist_flag = "_related_project_changelist"
    actions_list = ["voir_archives"]

    def changelist_view(self, request, extra_context=None):
        setattr(request, self.archive_changelist_flag, True)
        return super().changelist_view(request, extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if getattr(request, self.archive_changelist_flag, False):
            if (
                "project__is_archived__exact" not in request.GET
                and "project__is_archived" not in request.GET
            ):
                qs = qs.filter(project__is_archived=False)
        return qs

    def _changelist_url(self):
        opts = self.model._meta
        return reverse(f"admin:{opts.app_label}_{opts.model_name}_changelist")

    def _toggle_project_archive(self, request, project):
        if project.is_archived:
            project.is_archived = False
            project.save(update_fields=["is_archived", "updated_at"])
            messages.success(request, f"{project.code} a été désarchivé.")
        else:
            project.is_archived = True
            project.save(update_fields=["is_archived", "updated_at"])
            messages.success(request, f"{project.code} a été archivé.")
        return redirect(self._changelist_url())

    @action(
        description="Archiver",
        icon="archive",
        variant=ActionVariant.DEFAULT,
        url_path="voir-archive",
        permissions=["change"],
    )
    def voir_archive(self, request, object_id):
        obj = self.get_object(request, object_id)
        if obj is None:
            return redirect(self._changelist_url())
        return self._toggle_project_archive(request, obj.project)

    @action(
        description="Archives",
        icon="inventory_2",
        url_path="voir-archives",
        permissions=["view"],
    )
    def voir_archives(self, request):
        return redirect(f"{self._changelist_url()}?project__is_archived__exact=1")


class SimpleSaveMixin:
    """Only show the primary Enregistrer button (hide save-and-continue / add-another)."""

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        extra_context.update(
            {
                "show_save_and_continue": False,
                "show_save_and_add_another": False,
            }
        )
        return super().changeform_view(request, object_id, form_url, extra_context)


class RebindInlinesToSavedParentMixin:
    """Fix inline saves when form.save() swaps to an existing OneToOne parent.

    Admin builds formsets against a placeholder instance. If the form later
    replaces ``instance`` with a row already in the DB (upsert-by-project),
    inlines still point at the unsaved placeholder and raise:
    ``save() prohibited … unsaved related object 'planning'``.
    """

    def save_related(self, request, form, formsets, change):
        parent = form.instance
        if parent.pk is None:
            parent.save()
        for formset in formsets:
            formset.instance = parent
            fk = getattr(formset, "fk", None)
            if fk is not None:
                for inline_form in formset.forms:
                    setattr(inline_form.instance, fk.name, parent)
        super().save_related(request, form, formsets, change)


class TerrainMereAdminForm(forms.ModelForm):
    """Ignore model default on superficie_unite for empty extra inlines."""

    class Meta:
        model = TerrainMere
        fields = ("titre_foncier_mere", "suffixe", "superficie_totale", "superficie_unite")

    def has_changed(self):
        if not super().has_changed():
            return False
        if self.instance.pk:
            return True
        # Default M2 alone must not mark a blank Terrain Mère row as filled.
        return any(name != "superficie_unite" for name in self.changed_data)


class TerrainMereInline(StackedInline):
    model = TerrainMere
    form = TerrainMereAdminForm
    fields = ("titre_foncier_mere", "suffixe", "superficie_totale", "superficie_unite")
    can_delete = False
    extra = 1
    max_num = 1
    tab = True


class AutorisationInline(StackedInline):
    model = Autorisation
    fields = ("type_permis", "numero_autorisation", "date_delivrance")
    can_delete = False
    extra = 1
    max_num = 1
    tab = True


class ProjectIntervenantThroughForm(forms.ModelForm):
    """Intervenants are optional on the project form (empty extra row is OK)."""

    class Meta:
        model = Project.intervenants.through
        fields = ("intervenant",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if "intervenant" in self.fields:
            self.fields["intervenant"].required = False
            self.fields["intervenant"].widget.attrs["data-placeholder"] = (
                "Rechercher un intervenant…"
            )

    def has_changed(self):
        if self.instance.pk:
            return super().has_changed()
        if not self.is_bound:
            return False
        return bool(str(self.data.get(self.add_prefix("intervenant"), "") or "").strip())


class IntervenantInline(TabularInline):
    model = Project.intervenants.through
    form = ProjectIntervenantThroughForm
    autocomplete_fields = ("intervenant",)
    # Show one empty row on add — with extra=0 the tab looked blank.
    extra = 1
    tab = True
    verbose_name = "Intervenant"
    verbose_name_plural = "Intervenants"

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        formfield = super().formfield_for_foreignkey(db_field, request, **kwargs)
        if db_field.name == "intervenant" and formfield is not None:
            formfield.required = False
            formfield.widget.attrs["data-placeholder"] = "Rechercher un intervenant…"
        return formfield


class ProjectDocumentAdminForm(forms.ModelForm):
    class Meta:
        model = ProjectDocument
        fields = ("kind", "fichier")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Documents are optional on the project form.
        self.fields["kind"].required = False
        self.fields["fichier"].required = False

    def has_changed(self):
        # Extra row with only the default "kind" select must not count as filled
        # (otherwise Django requires fichier and blocks Enregistrer).
        if self.instance.pk:
            return super().has_changed()
        file_name = self.add_prefix("fichier")
        if not self.files.get(file_name):
            return False
        return True

    def clean(self):
        cleaned = super().clean()
        fichier = cleaned.get("fichier")
        kind = cleaned.get("kind")
        if fichier and not kind:
            self.add_error("kind", "Indiquez le type de document.")
        return cleaned


class ProjectDocumentInline(TabularInline):
    model = ProjectDocument
    form = ProjectDocumentAdminForm
    # One empty row for UX; has_changed() ignores it until a file is chosen.
    extra = 1
    tab = True
    fields = ("kind", "fichier")
    verbose_name = "Document technique"
    verbose_name_plural = "Documents techniques (plusieurs par type)"


class ProjectImageAdminForm(forms.ModelForm):
    class Meta:
        model = ProjectImage
        fields = ("image", "legende", "ordre")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Images are optional on the project form.
        self.fields["image"].required = False
        self.fields["legende"].required = False
        self.fields["ordre"].required = False

    def has_changed(self):
        if self.instance.pk:
            return super().has_changed()
        file_name = self.add_prefix("image")
        if not self.files.get(file_name):
            return False
        return True


class ProjectImageInline(TabularInline):
    model = ProjectImage
    form = ProjectImageAdminForm
    # One empty row for UX; has_changed() ignores it until an image is chosen.
    extra = 1
    tab = True
    fields = ("image", "legende", "ordre")
    verbose_name = "Image"
    verbose_name_plural = "Images du projet (plusieurs)"


class FinancementDocumentAdminForm(forms.ModelForm):
    class Meta:
        model = FinancementDocument
        fields = ("fichier",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["fichier"].required = False

    def has_changed(self):
        if self.instance.pk:
            return super().has_changed()
        return bool(self.files.get(self.add_prefix("fichier")))


class FinancementDocumentInline(TabularInline):
    model = FinancementDocument
    form = FinancementDocumentAdminForm
    extra = 1
    fields = ("fichier",)
    verbose_name = "Document PDF"
    verbose_name_plural = "Documents financement (plusieurs PDF)"


class PlanningDocumentAdminForm(forms.ModelForm):
    class Meta:
        model = PlanningDocument
        fields = ("phase", "fichier")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Extra empty row: phase alone must not force a file.
        self.fields["phase"].required = False
        self.fields["fichier"].required = False

    def has_changed(self):
        if self.instance.pk:
            return super().has_changed()
        return bool(self.files.get(self.add_prefix("fichier")))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("fichier") and not cleaned.get("phase"):
            self.add_error("phase", "Indiquez la phase du document.")
        return cleaned


class PlanningDocumentInline(TabularInline):
    model = PlanningDocument
    form = PlanningDocumentAdminForm
    extra = 1
    fields = ("phase", "fichier")
    verbose_name = "PDF"
    verbose_name_plural = "PDFs par phase (plusieurs fichiers)"
    tab = True


class AnnexeDocumentAdminForm(forms.ModelForm):
    class Meta:
        model = AnnexeDocument
        fields = ("kind", "fichier")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["kind"].required = False
        self.fields["fichier"].required = False

    def has_changed(self):
        if self.instance.pk:
            return super().has_changed()
        return bool(self.files.get(self.add_prefix("fichier")))

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("fichier") and not cleaned.get("kind"):
            self.add_error("kind", "Indiquez le type de pièce.")
        return cleaned


class AnnexeDocumentInline(TabularInline):
    model = AnnexeDocument
    form = AnnexeDocumentAdminForm
    extra = 1
    fields = ("kind", "fichier")
    verbose_name = "PDF"
    verbose_name_plural = "Pièces jointes (PDF)"
    tab = True


@admin.register(Project)
class ProjectAdmin(SimpleSaveMixin, ModelAdmin):
    # No bulk checkboxes on the changelist.
    actions = None
    list_display = (
        "code_link",
        "titre_link",
        "statut_link",
    )
    list_display_links = None
    list_per_page = 10
    show_full_result_count = False
    search_fields = ("code", "titre", "prefecture", "commune")
    list_filter = ("statut_actuel", "is_archived", "prefecture", "commune")
    ordering = ("-code",)
    readonly_fields = ("code_display", "is_archived", "created_at", "updated_at")
    inlines = (
        TerrainMereInline,
        AutorisationInline,
        IntervenantInline,
        ProjectDocumentInline,
        ProjectImageInline,
    )
    actions_detail = ["voir_fiche", "modifier", "modifier_financement", "modifier_planning"]
    actions_list = ["voir_archives"]
    # Three-dot row menu: Fiche + Modifier + Voir archive
    actions_row = ["voir_fiche", "modifier", "voir_archive"]

    class Media:
        js = ("projects/js/changelist_row_detail.js",)
        css = {"all": ("projects/css/changelist_row.css",)}

    fieldsets = (
        ("Identification", {"classes": ["tab"], "fields": ("code_display", "titre", "statut_actuel", "is_archived")}),
        ("Localisation", {"classes": ["tab"], "fields": ("prefecture", "commune", "situation_localisation", "voie_acces")}),
        ("Description", {"classes": ["tab"], "fields": ("consistance_globale", "nombre_lots", "emprise_servitudes")}),
        ("Historique", {"classes": ["tab"], "fields": ("created_at", "updated_at")}),
    )

    def changelist_view(self, request, extra_context=None):
        # Mark changelist so get_queryset can hide archived rows by default.
        request._project_changelist = True
        return super().changelist_view(request, extra_context)

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        # Default list: active projects only (unless filtering archives explicitly).
        if getattr(request, "_project_changelist", False):
            if "is_archived__exact" not in request.GET and "is_archived" not in request.GET:
                qs = qs.filter(is_archived=False)
        return qs

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return (
                ("Identification", {"classes": ["tab"], "fields": ("code_display", "titre", "statut_actuel")}),
                ("Localisation", {"classes": ["tab"], "fields": ("prefecture", "commune", "situation_localisation", "voie_acces")}),
                ("Description", {"classes": ["tab"], "fields": ("consistance_globale", "nombre_lots", "emprise_servitudes")}),
            )
        return self.fieldsets

    @admin.display(description="Code")
    def code_display(self, obj):
        if obj and obj.code:
            return obj.code
        # Only a preview: another project saved first would take this code.
        return Project.next_code()

    def _detail_link(self, obj, text):
        return format_html(
            '<a class="project-detail-link" href="{}" data-detail-url="{}">{}</a>',
            obj.get_absolute_url(),
            obj.get_absolute_url(),
            text,
        )

    @admin.display(description="Code", ordering="code")
    def code_link(self, obj):
        return self._detail_link(obj, obj.code)

    @admin.display(description="Titre du projet", ordering="titre")
    def titre_link(self, obj):
        return self._detail_link(obj, obj.titre)

    @admin.display(description="Statut actuel du projet", ordering="statut_actuel")
    def statut_link(self, obj):
        return self._detail_link(obj, obj.get_statut_actuel_display())

    def get_actions(self, request):
        return {}

    @action(
        description="Voir la fiche",
        icon="visibility",
        variant=ActionVariant.PRIMARY,
        url_path="voir-fiche",
        permissions=["view"],
    )
    def voir_fiche(self, request, object_id):
        project = self.get_object(request, object_id)
        return redirect(project.get_absolute_url())

    @action(
        description="Modifier",
        icon="edit",
        variant=ActionVariant.PRIMARY,
        url_path="modifier",
        permissions=["change"],
    )
    def modifier(self, request, object_id):
        return redirect(
            reverse("admin:projects_project_change", args=[object_id])
        )

    @action(
        description="Archiver",
        icon="archive",
        variant=ActionVariant.DEFAULT,
        url_path="voir-archive",
        permissions=["change"],
    )
    def voir_archive(self, request, object_id):
        project = self.get_object(request, object_id)
        if project is None:
            return redirect(reverse("admin:projects_project_changelist"))
        if project.is_archived:
            project.is_archived = False
            project.save(update_fields=["is_archived", "updated_at"])
            messages.success(request, f"{project.code} a été désarchivé.")
        else:
            project.is_archived = True
            project.save(update_fields=["is_archived", "updated_at"])
            messages.success(request, f"{project.code} a été archivé.")
        return redirect(reverse("admin:projects_project_changelist"))

    @action(
        description="Archives",
        icon="inventory_2",
        url_path="voir-archives",
        permissions=["view"],
    )
    def voir_archives(self, request):
        return redirect(
            f"{reverse('admin:projects_project_changelist')}?is_archived__exact=1"
        )

    @action(
        description="Modifier le financement",
        icon="payments",
        variant=ActionVariant.PRIMARY,
        url_path="modifier-financement",
        permissions=["projects.change_structurefinancement"],
    )
    def modifier_financement(self, request, object_id):
        project = self.get_object(request, object_id)
        financement = StructureFinancement.objects.filter(project=project).first()
        if financement is None:
            return redirect(
                f"{reverse('admin:projects_structurefinancement_add')}?project={project.pk}"
            )
        return redirect(
            reverse("admin:projects_structurefinancement_change", args=[financement.pk])
        )

    @action(
        description="Modifier le planning",
        icon="calendar_month",
        variant=ActionVariant.PRIMARY,
        url_path="modifier-planning",
        permissions=["projects.change_planningexecution"],
    )
    def modifier_planning(self, request, object_id):
        project = self.get_object(request, object_id)
        planning = PlanningExecution.objects.filter(project=project).first()
        if planning is None:
            return redirect(
                f"{reverse('admin:projects_planningexecution_add')}?project={project.pk}"
            )
        return redirect(
            reverse("admin:projects_planningexecution_change", args=[planning.pk])
        )


@admin.register(Intervenant)
class IntervenantAdmin(EditUpdateActionsMixin, ModelAdmin):
    list_display = ("nom_ou_cabinet", "type_intervenant", "contact")
    search_fields = ("nom_ou_cabinet", "contact")
    list_filter = ("type_intervenant",)
    fields = ("type_intervenant", "nom_ou_cabinet", "contact")

    def has_module_permission(self, request):
        # Hidden from the sidebar; reached from the project page's Intervenants tab.
        return False


class StructureFinancementAdminForm(forms.ModelForm):
    """Show every project; saving an already-financed project updates that row."""

    class Meta:
        model = StructureFinancement
        fields = "__all__"

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        if not self.instance.pk:
            exclude.add("project")
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as error:
            self._update_errors(error)

    def save(self, commit=True):
        if not self.instance.pk:
            existing = StructureFinancement.objects.filter(
                project=self.cleaned_data["project"]
            ).first()
            if existing is not None:
                existing.fonds_propres_fp = self.cleaned_data["fonds_propres_fp"]
                existing.credit_moyen_terme_cmt = self.cleaned_data["credit_moyen_terme_cmt"]
                self.instance = existing
                if commit:
                    existing.save()
                    self._save_m2m()
                else:
                    self.save_m2m = self._save_m2m
                return existing
        return super().save(commit=commit)


@admin.register(StructureFinancement)
class StructureFinancementAdmin(
    ProjectFicheListLinkMixin,
    RebindInlinesToSavedParentMixin,
    ProjectArchiveRowMixin,
    SimpleSaveMixin,
    ModelAdmin,
):
    form = StructureFinancementAdminForm
    fiche_tab = "financement"
    # No bulk checkboxes on the changelist.
    actions = None
    autocomplete_fields = ("project",)
    list_display = (
        "project_code",
        "project_titre",
        "fonds_propres_fp",
        "credit_moyen_terme_cmt",
        "investissement_total",
    )
    list_display_links = None
    list_per_page = 10
    show_full_result_count = False
    list_select_related = ("project",)
    search_fields = ("project__code", "project__titre")
    list_filter = ("project__is_archived",)
    ordering = ("-project__code",)
    readonly_fields = ("total_live", "created_at", "updated_at")
    inlines = (FinancementDocumentInline,)
    # Three-dot row menu: Modifier + Voir archive
    actions_row = ["modifier_financement_row", "voir_archive"]
    actions_list = ["voir_archives"]

    class Media:
        js = (
            "projects/js/financement_total.js",
            "projects/js/changelist_row_detail.js",
        )
        css = {"all": ("projects/css/changelist_row.css",)}

    fieldsets = (
        (
            "Projet",
            {
                "fields": ("project",),
                "description": (
                    "Choisissez le projet (A2601, A2602, …). "
                    "Un seul financement par projet : s'il existe déjà, l'enregistrement le met à jour."
                ),
            },
        ),
        ("Sources de financement", {
            "fields": ("fonds_propres_fp", "credit_moyen_terme_cmt", "total_live"),
        }),
        ("Historique", {"fields": ("created_at", "updated_at")}),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.fieldsets[:-1]
        return self.fieldsets

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return self.readonly_fields + ("project",)
        return self.readonly_fields

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        project_id = request.GET.get("project")
        if project_id and Project.objects.filter(pk=project_id).exists():
            initial["project"] = project_id
        return initial

    def add_view(self, request, form_url="", extra_context=None):
        # Deep-link ?project=… with an existing financement opens the edit page.
        if request.method == "GET":
            project_id = request.GET.get("project")
            if project_id:
                existing = StructureFinancement.objects.filter(project_id=project_id).first()
                if existing is not None:
                    messages.info(
                        request,
                        f"Le projet a déjà un financement — modification de {existing.project.code}.",
                    )
                    return redirect(
                        reverse(
                            "admin:projects_structurefinancement_change",
                            args=[existing.pk],
                        )
                    )
        return super().add_view(request, form_url, extra_context)

    @admin.display(description="Total investissement (DH)")
    def total_live(self, obj):
        value = obj.investissement_total if obj and obj.pk else 0
        return format_html(
            '<span id="id_investissement_total_live">{}</span>',
            f"{value:.2f}".replace(".", ","),
        )

    def get_actions(self, request):
        return {}

    @admin.display(description="Code projet", ordering="project__code")
    def project_code(self, obj):
        return self._fiche_link(obj.project, obj.project.code)

    @admin.display(description="Titre projet", ordering="project__titre")
    def project_titre(self, obj):
        return self._fiche_link(obj.project, obj.project.titre)

    @action(
        description="Modifier",
        icon="edit",
        variant=ActionVariant.PRIMARY,
        url_path="modifier-row",
        permissions=["change"],
    )
    def modifier_financement_row(self, request, object_id):
        return redirect(
            reverse("admin:projects_structurefinancement_change", args=[object_id])
        )


class PlanningExecutionAdminForm(forms.ModelForm):
    """Un seul planning par projet : réenregistrement met à jour la fiche existante."""

    class Meta:
        model = PlanningExecution
        fields = "__all__"

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        if not self.instance.pk:
            exclude.add("project")
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as error:
            self._update_errors(error)

    def save(self, commit=True):
        if not self.instance.pk:
            existing = PlanningExecution.objects.filter(
                project=self.cleaned_data["project"]
            ).first()
            if existing is not None:
                self.instance = existing
                if commit:
                    existing.save()
                    self._save_m2m()
                else:
                    self.save_m2m = self._save_m2m
                return existing
        return super().save(commit=commit)


@admin.register(PlanningExecution)
class PlanningExecutionAdmin(
    ProjectFicheListLinkMixin,
    RebindInlinesToSavedParentMixin,
    ProjectArchiveRowMixin,
    SimpleSaveMixin,
    ModelAdmin,
):
    form = PlanningExecutionAdminForm
    fiche_tab = "planning"
    actions = None
    autocomplete_fields = ("project",)
    list_display = ("project_code", "project_titre", "phases_count", "updated_at")
    list_display_links = None
    list_per_page = 10
    show_full_result_count = False
    list_select_related = ("project",)
    search_fields = ("project__code", "project__titre")
    list_filter = ("project__is_archived",)
    ordering = ("-project__code",)
    readonly_fields = ()
    inlines = (PlanningDocumentInline,)
    # Three-dot row menu: Modifier + Voir archive
    actions_row = ["modifier_planning_row", "voir_archive"]
    actions_list = ["voir_archives"]
    change_form_show_cancel_button = True

    class Media:
        js = ("projects/js/changelist_row_detail.js",)
        css = {
            "all": (
                "projects/css/changelist_row.css",
                "projects/css/planning_form.css",
            )
        }

    fieldsets = (
        (
            "Projet",
            {
                "fields": ("project",),
                "description": (
                    "Choisissez le projet, puis ajoutez les PDF par phase "
                    "(études, viabilisation, réception) — plusieurs PDF possibles."
                ),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return ("project",)
        return ()

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        project_id = request.GET.get("project")
        if project_id and Project.objects.filter(pk=project_id).exists():
            initial["project"] = project_id
        return initial

    def add_view(self, request, form_url="", extra_context=None):
        if request.method == "GET":
            project_id = request.GET.get("project")
            if project_id:
                existing = PlanningExecution.objects.filter(project_id=project_id).first()
                if existing is not None:
                    messages.info(
                        request,
                        f"Le projet a déjà un planning — modification de {existing.project.code}.",
                    )
                    return redirect(
                        reverse(
                            "admin:projects_planningexecution_change",
                            args=[existing.pk],
                        )
                    )
        return super().add_view(request, form_url, extra_context)

    def get_actions(self, request):
        return {}

    @admin.display(description="Code projet", ordering="project__code")
    def project_code(self, obj):
        return self._fiche_link(obj.project, obj.project.code)

    @admin.display(description="Titre projet", ordering="project__titre")
    def project_titre(self, obj):
        return self._fiche_link(obj.project, obj.project.titre)

    @admin.display(description="PDFs")
    def phases_count(self, obj):
        return obj.documents.count()

    @action(
        description="Modifier",
        icon="edit",
        variant=ActionVariant.PRIMARY,
        url_path="modifier-row",
        permissions=["change"],
    )
    def modifier_planning_row(self, request, object_id):
        return redirect(
            reverse("admin:projects_planningexecution_change", args=[object_id])
        )


class AnnexeDossierAdminForm(forms.ModelForm):
    """Un seul dossier annexes par projet."""

    class Meta:
        model = AnnexeDossier
        fields = "__all__"

    def validate_unique(self):
        exclude = self._get_validation_exclusions()
        if not self.instance.pk:
            exclude.add("project")
        try:
            self.instance.validate_unique(exclude=exclude)
        except ValidationError as error:
            self._update_errors(error)

    def save(self, commit=True):
        if not self.instance.pk:
            existing = AnnexeDossier.objects.filter(
                project=self.cleaned_data["project"]
            ).first()
            if existing is not None:
                self.instance = existing
                if commit:
                    existing.save()
                    self._save_m2m()
                else:
                    self.save_m2m = self._save_m2m
                return existing
        return super().save(commit=commit)


@admin.register(AnnexeDossier)
class AnnexeDossierAdmin(
    ProjectFicheListLinkMixin,
    RebindInlinesToSavedParentMixin,
    ProjectArchiveRowMixin,
    SimpleSaveMixin,
    ModelAdmin,
):
    form = AnnexeDossierAdminForm
    fiche_tab = "annexes"
    actions = None
    autocomplete_fields = ("project",)
    list_display = ("project_code", "project_titre", "docs_count", "updated_at")
    list_display_links = None
    list_per_page = 10
    show_full_result_count = False
    list_select_related = ("project",)
    search_fields = ("project__code", "project__titre")
    list_filter = ("project__is_archived",)
    ordering = ("-project__code",)
    inlines = (AnnexeDocumentInline,)
    actions_row = ["modifier_annexe_row", "voir_archive"]
    actions_list = ["voir_archives"]
    change_form_show_cancel_button = True

    class Media:
        js = ("projects/js/changelist_row_detail.js",)
        css = {"all": ("projects/css/changelist_row.css",)}

    fieldsets = (
        (
            "Projet",
            {
                "fields": ("project",),
                "description": (
                    "Choisissez le projet, puis ajoutez les pièces jointes PDF "
                    "(certificat ANCFCC, plans, attestations, cahier des charges)."
                ),
            },
        ),
    )

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return ("project",)
        return ()

    def get_changeform_initial_data(self, request):
        initial = super().get_changeform_initial_data(request)
        project_id = request.GET.get("project")
        if project_id and Project.objects.filter(pk=project_id).exists():
            initial["project"] = project_id
        return initial

    def add_view(self, request, form_url="", extra_context=None):
        if request.method == "GET":
            project_id = request.GET.get("project")
            if project_id:
                existing = AnnexeDossier.objects.filter(project_id=project_id).first()
                if existing is not None:
                    messages.info(
                        request,
                        f"Le projet a déjà des annexes — modification de {existing.project.code}.",
                    )
                    return redirect(
                        reverse(
                            "admin:projects_annexedossier_change",
                            args=[existing.pk],
                        )
                    )
        return super().add_view(request, form_url, extra_context)

    def get_actions(self, request):
        return {}

    @admin.display(description="Code projet", ordering="project__code")
    def project_code(self, obj):
        return self._fiche_link(obj.project, obj.project.code)

    @admin.display(description="Titre projet", ordering="project__titre")
    def project_titre(self, obj):
        return self._fiche_link(obj.project, obj.project.titre)

    @admin.display(description="PDFs")
    def docs_count(self, obj):
        return obj.documents.count()

    @action(
        description="Modifier",
        icon="edit",
        variant=ActionVariant.PRIMARY,
        url_path="modifier-row",
        permissions=["change"],
    )
    def modifier_annexe_row(self, request, object_id):
        return redirect(
            reverse("admin:projects_annexedossier_change", args=[object_id])
        )
