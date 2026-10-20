import tempfile
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase

from .models import (
    Autorisation,
    FinancementDocument,
    Intervenant,
    PlanningDocument,
    PlanningExecution,
    ProgrammeTechnique,
    Project,
    ProjectDocument,
    StructureFinancement,
    TerrainMere,
)

FIELDS = dict(
    prefecture="Rabat",
    commune="Agdal",
    titre="Lotissement",
    consistance_globale="x",
    situation_localisation="x",
    voie_acces="x",
    emprise_servitudes="x",
    statut_actuel="INSTRUCTION",
)

EMPTY_INLINES = {
    "terrain_mere-TOTAL_FORMS": "1",
    "terrain_mere-INITIAL_FORMS": "0",
    "autorisation-TOTAL_FORMS": "1",
    "autorisation-INITIAL_FORMS": "0",
    "Project_intervenants-TOTAL_FORMS": "0",
    "Project_intervenants-INITIAL_FORMS": "0",
    "documents-TOTAL_FORMS": "0",
    "documents-INITIAL_FORMS": "0",
}

EMPTY_FINANCE_DOCS = {
    "documents-TOTAL_FORMS": "0",
    "documents-INITIAL_FORMS": "0",
}

EMPTY_PLANNING_DOCS = {
    "documents-TOTAL_FORMS": "0",
    "documents-INITIAL_FORMS": "0",
}


class ProjectCodeTests(TestCase):
    def test_codes_increment_and_roll_over_letter(self):
        first = Project.objects.create(**FIELDS)
        second = Project.objects.create(**FIELDS)
        yy = first.code[1:3]
        self.assertEqual(first.code, f"A{yy}01")
        self.assertEqual(second.code, f"A{yy}02")

        Project.objects.create(code=f"A{yy}99", **FIELDS)
        self.assertEqual(Project.objects.create(**FIELDS).code, f"B{yy}01")

    def test_statut_defaults_to_instruction(self):
        fields = {k: v for k, v in FIELDS.items() if k != "statut_actuel"}
        project = Project.objects.create(**fields)
        self.assertEqual(project.get_statut_actuel_display(), "En cours d'instruction")

    def test_section_1_fields(self):
        project = Project.objects.create(**FIELDS, nombre_lots=120)
        autorisation = Autorisation.objects.create(
            project=project, type_permis="AMENAGER", numero_autorisation="12/2026"
        )
        project.refresh_from_db()
        self.assertEqual(project.nombre_lots, 120)
        self.assertEqual(autorisation.get_type_permis_display(), "Permis d'aménager")

    def test_update_keeps_code(self):
        project = Project.objects.create(**FIELDS)
        code = project.code
        project.titre = "Nouveau"
        project.save()
        project.refresh_from_db()
        self.assertEqual(project.code, code)

    def test_one_autorisation_per_project(self):
        project = Project.objects.create(**FIELDS)
        Autorisation.objects.create(project=project, type_permis="LOTIR", numero_autorisation="1")
        with self.assertRaises(IntegrityError):
            Autorisation.objects.create(project=project, type_permis="CONSTRUIRE", numero_autorisation="2")


class ProjectAdminTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_superuser("admin", "a@a.ma", "pass")
        self.client.force_login(user)

    def test_admin_crud_pages(self):
        project = Project.objects.create(**FIELDS)
        for url in [
            "/admin/projects/project/",
            "/admin/projects/project/add/",
            f"/admin/projects/project/{project.pk}/change/",
            f"/admin/projects/project/{project.pk}/delete/",
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, url)

    def test_changeform_hides_header_tous_and_add(self):
        response = self.client.get("/admin/projects/project/add/")
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, ">Tous</span>")
        self.assertNotContains(response, "addlink")
        self.assertContains(response, 'title="Go back"')

    def test_changeform_hides_extra_save_buttons(self):
        response = self.client.get("/admin/projects/project/add/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="_save"')
        self.assertNotContains(response, 'name="_continue"')
        self.assertNotContains(response, 'name="_addanother"')

    def test_changelist_keeps_add_button(self):
        response = self.client.get("/admin/projects/project/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "addlink")

    def test_admin_add_project_with_terrain_and_autorisation(self):
        data = {
            **FIELDS,
            **EMPTY_INLINES,
            "terrain_mere-0-titre_foncier_mere": "TF 12345/R",
            "terrain_mere-0-superficie_totale": "15000.50",
            "terrain_mere-0-superficie_unite": "M2",
            "autorisation-0-type_permis": "LOTIR",
            "autorisation-0-numero_autorisation": "123/2026",
        }
        response = self.client.post("/admin/projects/project/add/", data)
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get()
        self.assertEqual(str(project.terrain_mere), f"TF 12345/R ({project.code})")
        self.assertEqual(project.terrain_mere.superficie_unite, "M2")
        self.assertEqual(project.terrain_mere.superficie_affichee, "15000.50 m²")
        self.assertEqual(str(project.autorisation), f"Autorisation de lotir n° 123/2026 ({project.code})")

    def test_sidebar_only_lists_projects(self):
        response = self.client.get("/admin/")
        self.assertContains(response, "/admin/projects/project/")
        self.assertContains(response, "/admin/projects/structurefinancement/")
        self.assertContains(response, "/admin/projects/planningexecution/")
        self.assertNotContains(response, "/admin/projects/terrainmere/")
        self.assertNotContains(response, "/admin/projects/autorisation/")
        self.assertNotContains(response, "/admin/projects/intervenant/")
        self.assertNotContains(response, "/admin/projects/phaseexecution/")

    def test_link_intervenants_from_project_page(self):
        architecte = Intervenant.objects.create(type_intervenant="ARCHITECTE", nom_ou_cabinet="Cabinet Alami")
        igt = Intervenant.objects.create(type_intervenant="IGT", nom_ou_cabinet="Topo Sud")
        data = {
            **FIELDS,
            **EMPTY_INLINES,
            "Project_intervenants-TOTAL_FORMS": "2",
            "Project_intervenants-0-intervenant": architecte.pk,
            "Project_intervenants-1-intervenant": igt.pk,
        }
        response = self.client.post("/admin/projects/project/add/", data)
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get()
        self.assertEqual(set(project.intervenants.all()), {architecte, igt})

        # The same intervenant can work on several projects.
        other = Project.objects.create(**FIELDS)
        other.intervenants.add(architecte)
        self.assertEqual(architecte.projects.count(), 2)

    def test_intervenant_popup_and_search(self):
        Intervenant.objects.create(type_intervenant="BC", nom_ou_cabinet="Bureau Veritas")
        self.assertEqual(self.client.get("/admin/projects/intervenant/add/").status_code, 200)
        response = self.client.get(
            "/admin/autocomplete/",
            {"term": "Veritas", "app_label": "projects", "model_name": "project", "field_name": "intervenants"},
        )
        self.assertContains(response, "Bureau Veritas")

    def test_edit_related_from_project_page(self):
        project = Project.objects.create(**FIELDS)
        terrain = TerrainMere.objects.create(
            project=project,
            titre_foncier_mere="TF 1/R",
            superficie_totale=500,
            superficie_unite="HA",
        )
        autorisation = Autorisation.objects.create(
            project=project, type_permis="CONSTRUIRE", numero_autorisation="45/2026"
        )

        data = {
            **FIELDS,
            "terrain_mere-TOTAL_FORMS": "1",
            "terrain_mere-INITIAL_FORMS": "1",
            "terrain_mere-0-id": terrain.pk,
            "terrain_mere-0-project": project.pk,
            "terrain_mere-0-titre_foncier_mere": "TF 1/R",
            "terrain_mere-0-suffixe": "B",
            "terrain_mere-0-superficie_totale": "1.25",
            "terrain_mere-0-superficie_unite": "HA",
            "autorisation-TOTAL_FORMS": "1",
            "autorisation-INITIAL_FORMS": "1",
            "autorisation-0-id": autorisation.pk,
            "autorisation-0-project": project.pk,
            "autorisation-0-type_permis": "CONSTRUIRE",
            "autorisation-0-numero_autorisation": "45/2026",
            "autorisation-0-date_delivrance": "2026-10-01",
            "Project_intervenants-TOTAL_FORMS": "0",
            "Project_intervenants-INITIAL_FORMS": "0",
            "documents-TOTAL_FORMS": "0",
            "documents-INITIAL_FORMS": "0",
        }
        response = self.client.post(f"/admin/projects/project/{project.pk}/change/", data)
        self.assertEqual(response.status_code, 302)

        terrain.refresh_from_db()
        autorisation.refresh_from_db()
        self.assertEqual(terrain.suffixe, "B")
        self.assertEqual(terrain.superficie_unite, "HA")
        self.assertEqual(terrain.superficie_affichee, "1.25 ha")
        self.assertEqual(str(autorisation.date_delivrance), "2026-10-01")

    def test_admin_add_generates_code(self):
        response = self.client.post("/admin/projects/project/add/", {**FIELDS, **EMPTY_INLINES})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TerrainMere.objects.exists())
        self.assertFalse(Autorisation.objects.exists())
        self.assertFalse(ProgrammeTechnique.objects.exists())
        self.assertRegex(Project.objects.get().code, r"^A\d{2}01$")

    def test_programme_documents_accept_pdf_image_and_word(self):
        for filename in ["voirie.pdf", "voirie.jpg", "voirie.docx", "voirie.dwg"]:
            with self.subTest(filename=filename):
                data = {
                    **FIELDS,
                    **EMPTY_INLINES,
                    "documents-TOTAL_FORMS": "1",
                    "documents-INITIAL_FORMS": "0",
                    "documents-0-kind": ProjectDocument.Kind.VOIRIE_VRD,
                    "documents-0-fichier": SimpleUploadedFile(filename, b"content"),
                }
                with tempfile.TemporaryDirectory() as media, self.settings(MEDIA_ROOT=media):
                    response = self.client.post("/admin/projects/project/add/", data)
                    self.assertEqual(response.status_code, 302)
                    project = Project.objects.get()
                    document = project.documents.get()
                    self.assertEqual(document.kind, ProjectDocument.Kind.VOIRIE_VRD)
                    self.assertTrue(document.fichier.name.endswith(filename.rsplit(".", 1)[1]))
                    document.fichier.close()
                    project.delete()

    def test_programme_documents_multiple_per_kind(self):
        data = {
            **FIELDS,
            **EMPTY_INLINES,
            "documents-TOTAL_FORMS": "3",
            "documents-INITIAL_FORMS": "0",
            "documents-0-kind": ProjectDocument.Kind.TELECOM_FIBRE,
            "documents-0-fichier": SimpleUploadedFile("fibre.pdf", b"content"),
            "documents-1-kind": ProjectDocument.Kind.AMENAGEMENT_PAYSAGER,
            "documents-1-fichier": SimpleUploadedFile("jardin.png", b"content"),
            "documents-2-kind": ProjectDocument.Kind.TELECOM_FIBRE,
            "documents-2-fichier": SimpleUploadedFile("fibre-2.pdf", b"content"),
        }
        with tempfile.TemporaryDirectory() as media, self.settings(MEDIA_ROOT=media):
            response = self.client.post("/admin/projects/project/add/", data)
            self.assertEqual(response.status_code, 302)
            project = Project.objects.get()
            self.assertEqual(project.documents.count(), 3)
            self.assertEqual(
                project.documents.filter(kind=ProjectDocument.Kind.TELECOM_FIBRE).count(),
                2,
            )

    def test_structure_financement_pages(self):
        project = Project.objects.create(**FIELDS)
        free = Project.objects.create(**FIELDS)
        financement = StructureFinancement.objects.create(project=project, fonds_propres_fp=100)
        for url in [
            "/admin/projects/structurefinancement/",
            "/admin/projects/structurefinancement/add/",
            f"/admin/projects/structurefinancement/{financement.pk}/change/",
            f"/admin/projects/structurefinancement/{financement.pk}/delete/",
        ]:
            self.assertEqual(self.client.get(url).status_code, 200, url)
        self.assertContains(self.client.get("/admin/projects/structurefinancement/"), project.code)
        self.assertContains(self.client.get("/admin/projects/structurefinancement/add/"), free.code)

    def test_financement_no_longer_a_project_tab(self):
        project = Project.objects.create(**FIELDS)
        response = self.client.get(f"/admin/projects/project/{project.pk}/change/")
        self.assertNotContains(response, "structure_financement-TOTAL_FORMS")

    def test_structure_financement_total_is_computed(self):
        project = Project.objects.create(**FIELDS)
        data = {
            "project": project.pk,
            "fonds_propres_fp": "4000000.00",
            "credit_moyen_terme_cmt": "6000000.50",
            **EMPTY_FINANCE_DOCS,
        }
        response = self.client.post("/admin/projects/structurefinancement/add/", data)
        self.assertEqual(response.status_code, 302)
        financement = StructureFinancement.objects.get(project=project)
        self.assertEqual(financement.investissement_total, Decimal("10000000.50"))

        financement.credit_moyen_terme_cmt = Decimal("1000000")
        financement.save()
        financement.refresh_from_db()
        self.assertEqual(financement.investissement_total, Decimal("5000000.00"))

    def test_structure_financement_pdf(self):
        project = Project.objects.create(**FIELDS)
        data = {
            "project": project.pk,
            "fonds_propres_fp": "1000",
            "credit_moyen_terme_cmt": "0",
            "documents-TOTAL_FORMS": "2",
            "documents-INITIAL_FORMS": "0",
            "documents-0-fichier": SimpleUploadedFile("bilan.pdf", b"content"),
            "documents-1-fichier": SimpleUploadedFile("bilan-2.pdf", b"content"),
        }
        with tempfile.TemporaryDirectory() as media, self.settings(MEDIA_ROOT=media):
            response = self.client.post("/admin/projects/structurefinancement/add/", data)
            self.assertEqual(response.status_code, 302)
            financement = StructureFinancement.objects.get(project=project)
            self.assertEqual(financement.documents.count(), 2)
            for document in financement.documents.all():
                self.assertTrue(document.fichier.name.startswith("financement/"))
                self.assertTrue(document.fichier.name.endswith(".pdf"))
                document.fichier.close()

    def test_structure_financement_rejects_word(self):
        project = Project.objects.create(**FIELDS)
        data = {
            "project": project.pk,
            "fonds_propres_fp": "0",
            "credit_moyen_terme_cmt": "0",
            "documents-TOTAL_FORMS": "1",
            "documents-INITIAL_FORMS": "0",
            "documents-0-fichier": SimpleUploadedFile("bilan.docx", b"content"),
        }
        with tempfile.TemporaryDirectory() as media, self.settings(MEDIA_ROOT=media):
            response = self.client.post("/admin/projects/structurefinancement/add/", data)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(StructureFinancement.objects.exists())
        self.assertFalse(FinancementDocument.objects.exists())

    def test_one_financement_per_project(self):
        project = Project.objects.create(**FIELDS)
        StructureFinancement.objects.create(
            project=project, fonds_propres_fp=10, credit_moyen_terme_cmt=20
        )
        data = {
            "project": project.pk,
            "fonds_propres_fp": "50",
            "credit_moyen_terme_cmt": "51",
            **EMPTY_FINANCE_DOCS,
        }
        response = self.client.post("/admin/projects/structurefinancement/add/", data)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(StructureFinancement.objects.count(), 1)
        financement = StructureFinancement.objects.get(project=project)
        self.assertEqual(financement.fonds_propres_fp, Decimal("50"))
        self.assertEqual(financement.investissement_total, Decimal("101"))

    def test_add_form_shows_all_projects(self):
        taken = Project.objects.create(**FIELDS)
        free = Project.objects.create(**FIELDS)
        StructureFinancement.objects.create(project=taken)
        response = self.client.get("/admin/projects/structurefinancement/add/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, taken.code)
        self.assertContains(response, free.code)

    def test_edit_existing_financement(self):
        project = Project.objects.create(**FIELDS)
        financement = StructureFinancement.objects.create(
            project=project, fonds_propres_fp=10, credit_moyen_terme_cmt=20
        )
        data = {
            "fonds_propres_fp": "50",
            "credit_moyen_terme_cmt": "51",
            **EMPTY_FINANCE_DOCS,
        }
        response = self.client.post(
            f"/admin/projects/structurefinancement/{financement.pk}/change/", data
        )
        self.assertEqual(response.status_code, 302)
        financement.refresh_from_db()
        self.assertEqual(financement.fonds_propres_fp, Decimal("50"))
        self.assertEqual(financement.investissement_total, Decimal("101"))

    def test_modifier_row_button_on_lists(self):
        project = Project.objects.create(**FIELDS)
        financement = StructureFinancement.objects.create(project=project)
        for url, object_id, action_path in [
            ("/admin/projects/project/", project.pk, "modifier"),
            ("/admin/projects/structurefinancement/", financement.pk, "modifier-row"),
        ]:
            response = self.client.get(url)
            self.assertContains(response, "Modifier")
            self.assertContains(response, f"/{object_id}/{action_path}/")
            self.assertContains(response, "Actions")
            self.assertContains(response, "field-actions_holder")

    def test_project_row_has_three_actions_including_archive(self):
        project = Project.objects.create(**FIELDS)
        response = self.client.get("/admin/projects/project/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Voir la fiche")
        self.assertContains(response, "Modifier")
        self.assertContains(response, "Archiver")
        self.assertContains(response, f"/admin/projects/project/{project.pk}/voir-fiche/")
        self.assertContains(response, f"/admin/projects/project/{project.pk}/modifier/")
        self.assertContains(response, f"/admin/projects/project/{project.pk}/archiver/")
        self.assertContains(response, "Archives")

        archive = self.client.get(f"/admin/projects/project/{project.pk}/archiver/")
        self.assertEqual(archive.status_code, 302)
        project.refresh_from_db()
        self.assertTrue(project.is_archived)

        # Archived projects leave the default result list (ignore flash messages).
        listing = self.client.get("/admin/projects/project/")
        self.assertNotContains(listing, f'data-detail-url="{project.get_absolute_url()}"')

        archives = self.client.get("/admin/projects/project/?is_archived__exact=1")
        self.assertContains(archives, f'data-detail-url="{project.get_absolute_url()}"')

        restore = self.client.get(f"/admin/projects/project/{project.pk}/archiver/")
        self.assertEqual(restore.status_code, 302)
        project.refresh_from_db()
        self.assertFalse(project.is_archived)

    def test_add_with_project_query_redirects_to_edit(self):
        project = Project.objects.create(**FIELDS)
        financement = StructureFinancement.objects.create(project=project)
        response = self.client.get(
            f"/admin/projects/structurefinancement/add/?project={project.pk}"
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f"/admin/projects/structurefinancement/{financement.pk}/change/",
            response.url,
        )

    def test_add_page_shows_live_total(self):
        Project.objects.create(**FIELDS)
        response = self.client.get("/admin/projects/structurefinancement/add/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "projects/js/financement_total.js")
        self.assertContains(response, "id_investissement_total_live")

    def test_modifier_financement_from_project_page(self):
        project = Project.objects.create(**FIELDS)
        financement = StructureFinancement.objects.create(project=project)
        response = self.client.get(f"/admin/projects/project/{project.pk}/change/")
        self.assertContains(response, "Modifier le financement")

        response = self.client.get(
            f"/admin/projects/project/{project.pk}/modifier-financement/"
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn(
            f"/admin/projects/structurefinancement/{financement.pk}/change/",
            response.url,
        )

    def test_programme_documents_reject_other_files(self):
        for filename in ["virus.exe", "archive.zip"]:
            with self.subTest(filename=filename):
                data = {
                    **FIELDS,
                    **EMPTY_INLINES,
                    "documents-TOTAL_FORMS": "1",
                    "documents-INITIAL_FORMS": "0",
                    "documents-0-kind": ProjectDocument.Kind.VOIRIE_VRD,
                    "documents-0-fichier": SimpleUploadedFile(filename, b"content"),
                }
                with tempfile.TemporaryDirectory() as media, self.settings(MEDIA_ROOT=media):
                    response = self.client.post("/admin/projects/project/add/", data)
                self.assertEqual(response.status_code, 200)
                self.assertFalse(Project.objects.exists())

    def test_admin_dashboard(self):
        project = Project.objects.create(**FIELDS)
        StructureFinancement.objects.create(
            project=project, fonds_propres_fp=1000, credit_moyen_terme_cmt=2000
        )
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Tableau de bord")
        self.assertContains(response, "studio-head")
        self.assertContains(response, "Projets récents")
        self.assertContains(response, project.code)
        self.assertContains(response, "projects/css/dashboard.css")
        self.assertContains(response, "Investissement")
        self.assertContains(response, f"?projet={project.code}")
        self.assertNotContains(response, "project-info")

    def test_financing_list_hides_pdf_column(self):
        project = Project.objects.create(**FIELDS)
        StructureFinancement.objects.create(project=project)
        response = self.client.get("/admin/projects/structurefinancement/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, project.code)
        self.assertNotContains(response, "Document financement (PDF)")
        self.assertNotContains(response, "FicheModifier")
        self.assertNotContains(response, 'name="_selected_action"')

    def test_project_list_row_links_to_detail(self):
        project = Project.objects.create(**FIELDS)
        response = self.client.get("/admin/projects/project/")
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, project.get_absolute_url())
        self.assertContains(response, "project-detail-link")
        self.assertContains(response, "changelist_row_detail.js")
        self.assertContains(response, "changelist_row.css")
        self.assertContains(response, project.code)
        self.assertContains(response, project.titre)
        self.assertContains(response, "Voir la fiche")
        self.assertContains(response, "Modifier")
        self.assertNotContains(response, "Created at")
        self.assertNotContains(response, "FicheModifier")
        self.assertNotContains(response, 'name="_selected_action"')

        detail = self.client.get(project.get_absolute_url())
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, project.titre)
        self.assertContains(detail, "Identification")
        self.assertContains(detail, "project-info")
        self.assertContains(detail, "project-info-meta")
        self.assertContains(detail, "pi-tabs")
        self.assertContains(detail, "Général")
        self.assertNotContains(detail, "studio-metrics")
        self.assertNotContains(detail, "Projets récents")

    def test_project_detail_shows_only_project_info(self):
        project = Project.objects.create(**FIELDS)
        ProjectDocument.objects.create(
            project=project,
            kind=ProjectDocument.Kind.VOIRIE_VRD,
            fichier=SimpleUploadedFile("voirie.pdf", b"%PDF-1.4"),
        )
        financement = StructureFinancement.objects.create(project=project)
        FinancementDocument.objects.create(
            financement=financement,
            fichier=SimpleUploadedFile("finance.pdf", b"%PDF-1.4"),
        )
        response = self.client.get(f"/projets/{project.code}/")
        self.assertEqual(response.status_code, 302)
        self.assertIn(f"?projet={project.code}", response.url)

        detail = self.client.get(f"/admin/?projet={project.code}")
        self.assertEqual(detail.status_code, 200)
        self.assertContains(detail, project.titre)
        self.assertContains(detail, "Identification")
        self.assertContains(detail, "Voirie (VRD)")
        self.assertContains(detail, "Documents financement")
        self.assertContains(detail, "Structure de financement")
        self.assertContains(detail, "Financement")
        self.assertContains(detail, "project-info")
        self.assertContains(detail, "is-full")
        self.assertContains(detail, "data-tab=\"financement\"")
        self.assertContains(detail, "data-subtab=\"structure\"")
        self.assertContains(detail, "data-subtab=\"documents\"")
        self.assertContains(detail, "data-tab=\"planning\"")
        self.assertContains(detail, "Planning d'exécution du projet")
        self.assertContains(detail, "Études techniques, géotechniques &amp; Permis")
        self.assertContains(detail, "Travaux de Viabilisation (VRD &amp; Réseaux)")
        self.assertContains(detail, "Réception provisoire &amp; Titres fonciers individuels")
        self.assertNotContains(detail, "Date de début")
        self.assertNotContains(detail, "studio-metrics")

    def test_planning_execution_via_sidebar_admin(self):
        project = Project.objects.create(**FIELDS)
        add_page = self.client.get("/admin/projects/planningexecution/add/")
        self.assertEqual(add_page.status_code, 200)
        self.assertContains(add_page, "documents-TOTAL_FORMS")
        self.assertContains(add_page, "PDFs par phase")
        self.assertContains(add_page, "Études techniques")
        self.assertContains(add_page, "Viabilisation")
        self.assertNotContains(add_page, "date_debut")
        self.assertNotContains(add_page, "Date de début")

        data = {
            "project": project.pk,
            **EMPTY_PLANNING_DOCS,
        }
        response = self.client.post("/admin/projects/planningexecution/add/", data)
        self.assertEqual(response.status_code, 302)
        planning = PlanningExecution.objects.get(project=project)
        self.assertEqual(planning.documents.count(), 0)

        list_page = self.client.get("/admin/projects/planningexecution/")
        self.assertContains(list_page, project.code)
        self.assertNotContains(list_page, 'name="_selected_action"')

    def test_planning_execution_multiple_pdfs(self):
        project = Project.objects.create(**FIELDS)
        data = {
            "project": project.pk,
            "documents-TOTAL_FORMS": "3",
            "documents-INITIAL_FORMS": "0",
            "documents-0-phase": PlanningDocument.Phase.ETUDES,
            "documents-0-fichier": SimpleUploadedFile("etudes.pdf", b"%PDF-1.4"),
            "documents-1-phase": PlanningDocument.Phase.VIABILISATION,
            "documents-1-fichier": SimpleUploadedFile("viab-a.pdf", b"%PDF-1.4"),
            "documents-2-phase": PlanningDocument.Phase.VIABILISATION,
            "documents-2-fichier": SimpleUploadedFile("viab-b.pdf", b"%PDF-1.4"),
        }
        with tempfile.TemporaryDirectory() as media, self.settings(MEDIA_ROOT=media):
            response = self.client.post("/admin/projects/planningexecution/add/", data)
            self.assertEqual(response.status_code, 302)
            planning = PlanningExecution.objects.get(project=project)
            self.assertEqual(planning.documents.count(), 3)
            self.assertEqual(
                planning.documents.filter(phase=PlanningDocument.Phase.VIABILISATION).count(),
                2,
            )

            detail = self.client.get(f"/admin/?projet={project.code}")
            self.assertContains(detail, "Études techniques, géotechniques &amp; Permis")
            self.assertContains(detail, "Travaux de Viabilisation (VRD &amp; Réseaux)")
            self.assertContains(detail, "etudes")
            self.assertContains(detail, "viab-a")
            self.assertContains(detail, "viab-b")
            self.assertNotContains(detail, "Date de début")
