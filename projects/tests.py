from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import Project, TerrainMere

FIELDS = dict(
    perfecture="Rabat",
    commune="Agdal",
    titre="Lotissement",
    consistane_gloable="x",
    situation_localisation="x",
    voie_access="x",
    emprise_project="x",
)


class ProjectCodeTests(TestCase):
    def test_codes_increment_and_roll_over_letter(self):
        first = Project.objects.create(**FIELDS)
        second = Project.objects.create(**FIELDS)
        yy = first.code[1:3]
        self.assertEqual(first.code, f"A{yy}01")
        self.assertEqual(second.code, f"A{yy}02")

        Project.objects.create(code=f"A{yy}99", **FIELDS)
        self.assertEqual(Project.objects.create(**FIELDS).code, f"B{yy}01")

    def test_update_keeps_code(self):
        project = Project.objects.create(**FIELDS)
        code = project.code
        project.titre = "Nouveau"
        project.save()
        project.refresh_from_db()
        self.assertEqual(project.code, code)


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

    def test_admin_add_project_with_terrain_mere(self):
        data = {
            **FIELDS,
            "terrain_mere-TOTAL_FORMS": "1",
            "terrain_mere-INITIAL_FORMS": "0",
            "terrain_mere-0-titre_foncier_mere": "TF 12345/R",
            "terrain_mere-0-superficie_totale": "15000.50",
        }
        response = self.client.post("/admin/projects/project/add/", data)
        self.assertEqual(response.status_code, 302)
        project = Project.objects.get()
        self.assertEqual(str(project.terrain_mere), f"TF 12345/R ({project.code})")
        self.assertEqual(self.client.get("/admin/projects/terrainmere/").status_code, 200)

    def test_terrain_mere_admin_crud(self):
        project = Project.objects.create(**FIELDS)
        base = "/admin/projects/terrainmere/"
        terrain_data = {"project": project.pk, "titre_foncier_mere": "TF 1/R", "superficie_totale": "500"}

        self.assertEqual(self.client.post(f"{base}add/", terrain_data).status_code, 302)
        terrain = TerrainMere.objects.get()

        self.assertContains(self.client.get(base), project.code)
        self.assertEqual(self.client.get(f"{base}{terrain.pk}/change/").status_code, 200)

        terrain_data["suffixe"] = "B"
        terrain_data["commentaire"] = "Bornage à refaire"
        self.assertEqual(self.client.post(f"{base}{terrain.pk}/change/", terrain_data).status_code, 302)
        terrain.refresh_from_db()
        self.assertEqual(terrain.suffixe, "B")
        self.assertEqual(terrain.commentaire, "Bornage à refaire")

        # A second terrain for the same project is refused.
        self.assertEqual(self.client.post(f"{base}add/", terrain_data).status_code, 200)
        self.assertEqual(TerrainMere.objects.count(), 1)

        self.assertEqual(self.client.post(f"{base}{terrain.pk}/delete/", {"post": "yes"}).status_code, 302)
        self.assertFalse(TerrainMere.objects.exists())

    def test_admin_add_generates_code(self):
        data = {**FIELDS, "terrain_mere-TOTAL_FORMS": "1", "terrain_mere-INITIAL_FORMS": "0"}
        response = self.client.post("/admin/projects/project/add/", data)
        self.assertEqual(response.status_code, 302)
        self.assertFalse(TerrainMere.objects.exists())
        self.assertRegex(Project.objects.get().code, r"^A\d{2}01$")
