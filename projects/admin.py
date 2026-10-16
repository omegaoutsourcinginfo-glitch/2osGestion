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
    Autorisation,
    Intervenant,
    ProgrammeTechnique,
    Project,
    StructureFinancement,
    TerrainMere,
)


class EditUpdateActionsMixin:
    """Adds a visible Modifier button on each changelist row."""

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


class TerrainMereInline(StackedInline):
    model = TerrainMere
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


class IntervenantInline(TabularInline):
    model = Project.intervenants.through
    autocomplete_fields = ("intervenant",)
    extra = 0
    tab = True
    verbose_name = "Intervenant"
    verbose_name_plural = "Intervenants"


class ProgrammeTechniqueInline(StackedInline):
    model = ProgrammeTechnique
    can_delete = False
    extra = 1
    max_num = 1
    tab = True
    show_title = False
    fields = (
        "voirie_vrd_pdf",
        "telecom_fibre_pdf",
        "amenagement_paysager_pdf",
        "fiche_lot_parcelle_pdf",
    )


@admin.register(Project)
class ProjectAdmin(EditUpdateActionsMixin, ModelAdmin):
    list_display = (
        "code_link",
        "titre_link",
        "prefecture_link",
        "commune_link",
        "statut_link",
        "created_link",
    )
    list_display_links = None
    search_fields = ("code", "titre", "prefecture", "commune")
    list_filter = ("statut_actuel", "prefecture", "commune", "created_at")
    ordering = ("-code",)
    readonly_fields = ("code_display", "created_at", "updated_at")
    inlines = (
        TerrainMereInline,
        AutorisationInline,
        IntervenantInline,
        ProgrammeTechniqueInline,
    )
    actions_detail = ["voir_fiche", "modifier_financement"]

    class Media:
        js = ("projects/js/changelist_row_detail.js",)
        css = {"all": ("projects/css/changelist_row.css",)}

    fieldsets = (
        ("Identification", {"classes": ["tab"], "fields": ("code_display", "titre", "statut_actuel")}),
        ("Localisation", {"classes": ["tab"], "fields": ("prefecture", "commune", "situation_localisation", "voie_acces")}),
        ("Description", {"classes": ["tab"], "fields": ("consistance_globale", "nombre_lots", "emprise_servitudes")}),
        ("Historique", {"classes": ["tab"], "fields": ("created_at", "updated_at")}),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.fieldsets[:-1]
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

    @admin.display(description="Préfecture / Province", ordering="prefecture")
    def prefecture_link(self, obj):
        return self._detail_link(obj, obj.prefecture)

    @admin.display(description="Commune", ordering="commune")
    def commune_link(self, obj):
        return self._detail_link(obj, obj.commune)

    @admin.display(description="Statut actuel du projet", ordering="statut_actuel")
    def statut_link(self, obj):
        return self._detail_link(obj, obj.get_statut_actuel_display())

    @admin.display(description="Created at", ordering="created_at")
    def created_link(self, obj):
        return self._detail_link(obj, obj.created_at.strftime("%d/%m/%Y %H:%M"))

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
                document = self.cleaned_data.get("document_pdf")
                if document:
                    existing.document_pdf = document
                self.instance = existing
                if commit:
                    existing.save()
                    self._save_m2m()
                else:
                    self.save_m2m = self._save_m2m
                return existing
        return super().save(commit=commit)


@admin.register(StructureFinancement)
class StructureFinancementAdmin(EditUpdateActionsMixin, ModelAdmin):
    form = StructureFinancementAdminForm
    list_display = (
        "project_code",
        "project_titre",
        "fonds_propres_fp",
        "credit_moyen_terme_cmt",
        "investissement_total",
    )
    list_display_links = ("project_code", "project_titre")
    list_select_related = ("project",)
    search_fields = ("project__code", "project__titre")
    ordering = ("-project__code",)
    readonly_fields = ("total_live", "created_at", "updated_at")

    class Media:
        js = ("projects/js/financement_total.js",)

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
            "fields": ("fonds_propres_fp", "credit_moyen_terme_cmt", "total_live", "document_pdf"),
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

    @admin.display(description="Code projet", ordering="project__code")
    def project_code(self, obj):
        return obj.project.code

    @admin.display(description="Titre projet", ordering="project__titre")
    def project_titre(self, obj):
        return obj.project.titre
