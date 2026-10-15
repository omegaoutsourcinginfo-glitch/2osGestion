from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline, TabularInline

from .models import (
    Autorisation,
    Intervenant,
    ProgrammeTechnique,
    Project,
    StructureFinancement,
    TerrainMere,
)


class TerrainMereInline(StackedInline):
    model = TerrainMere
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
class ProjectAdmin(ModelAdmin):
    list_display = ("code", "titre", "prefecture", "commune", "statut_actuel", "created_at")
    list_display_links = ("code", "titre")
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


@admin.register(Intervenant)
class IntervenantAdmin(ModelAdmin):
    list_display = ("nom_ou_cabinet", "type_intervenant", "contact", "qualite")
    search_fields = ("nom_ou_cabinet", "contact")
    list_filter = ("type_intervenant",)
    fields = ("type_intervenant", "nom_ou_cabinet", "contact", "qualite")

    def has_module_permission(self, request):
        # Hidden from the sidebar; reached from the project page's Intervenants tab.
        return False


@admin.register(StructureFinancement)
class StructureFinancementAdmin(ModelAdmin):
    list_display = (
        "project_code",
        "project_titre",
        "fonds_propres_fp",
        "credit_moyen_terme_cmt",
        "investissement_total",
        "document_pdf",
    )
    list_display_links = ("project_code", "project_titre")
    list_select_related = ("project",)
    search_fields = ("project__code", "project__titre")
    autocomplete_fields = ("project",)
    ordering = ("-project__code",)
    readonly_fields = ("investissement_total", "created_at", "updated_at")

    fieldsets = (
        ("Projet", {"fields": ("project",)}),
        ("Sources de financement", {
            "fields": ("fonds_propres_fp", "credit_moyen_terme_cmt", "investissement_total", "document_pdf"),
        }),
        ("Historique", {"fields": ("created_at", "updated_at")}),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.fieldsets[:-1]
        return self.fieldsets

    @admin.display(description="Code projet", ordering="project__code")
    def project_code(self, obj):
        return obj.project.code

    @admin.display(description="Titre projet", ordering="project__titre")
    def project_titre(self, obj):
        return obj.project.titre
