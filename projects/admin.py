from django.contrib import admin
from unfold.admin import ModelAdmin, StackedInline

from .models import Project, TerrainMere


class TerrainMereInline(StackedInline):
    model = TerrainMere
    can_delete = False
    extra = 1
    max_num = 1


@admin.register(Project)
class ProjectAdmin(ModelAdmin):
    list_display = ("code", "titre", "perfecture", "commune", "created_at")
    list_display_links = ("code", "titre")
    search_fields = ("code", "titre", "perfecture", "commune")
    list_filter = ("perfecture", "commune", "created_at")
    ordering = ("-code",)
    readonly_fields = ("code_display", "created_at", "updated_at")
    inlines = (TerrainMereInline,)

    fieldsets = (
        ("Identification", {"fields": ("code_display", "titre")}),
        ("Localisation", {"fields": ("perfecture", "commune", "situation_localisation", "voie_access")}),
        ("Description", {"fields": ("consistane_gloable", "emprise_project")}),
        ("Commentaire", {"fields": ("commentaire",)}),
        ("Historique", {"fields": ("created_at", "updated_at")}),
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


@admin.register(TerrainMere)
class TerrainMereAdmin(ModelAdmin):
    list_display = ("project_code", "project_titre", "titre_foncier_mere", "suffixe", "superficie_totale", "created_at")
    list_display_links = ("project_code", "titre_foncier_mere")
    list_select_related = ("project",)
    search_fields = ("project__code", "project__titre", "titre_foncier_mere", "suffixe")
    list_filter = ("project__perfecture", "project__commune", "created_at")
    autocomplete_fields = ("project",)
    ordering = ("-project__code",)
    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Projet", {"fields": ("project",)}),
        ("Terrain", {"fields": ("titre_foncier_mere", "suffixe", "superficie_totale")}),
        ("Commentaire", {"fields": ("commentaire",)}),
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
