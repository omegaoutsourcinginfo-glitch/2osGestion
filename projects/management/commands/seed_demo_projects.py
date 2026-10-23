"""Seed 5 realistic demo projects with ALL related data.

Includes: terrain, permis, intervenants, docs techniques, images,
financement + PDFs, planning + PDFs, annexes + PDFs.

Usage:
    python manage.py seed_demo_projects
    python manage.py seed_demo_projects --clear
"""

from datetime import date
from decimal import Decimal
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.db import transaction

from projects.models import (
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

def _escape_pdf(text: str) -> str:
    return text.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def build_pdf(title: str, *lines: str) -> bytes:
    """One-page PDF with readable Helvetica text (no external deps)."""
    content_lines = [
        "BT",
        "/F1 16 Tf",
        "50 780 Td",
        f"({_escape_pdf(title[:80])}) Tj",
        "/F1 11 Tf",
        "0 -28 Td",
    ]
    for line in lines:
        content_lines.append(f"({_escape_pdf(line[:95])}) Tj")
        content_lines.append("0 -16 Td")
    content_lines.append("ET")
    stream = "\n".join(content_lines).encode("latin-1", errors="replace")

    objects = [
        b"1 0 obj<< /Type /Catalog /Pages 2 0 R >>endobj\n",
        b"2 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 >>endobj\n",
        b"3 0 obj<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] "
        b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>endobj\n",
        (
            b"4 0 obj<< /Length %d >>stream\n" % len(stream)
            + stream
            + b"\nendstream\nendobj\n"
        ),
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n",
    ]

    out = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for obj in objects:
        offsets.append(len(out))
        out.extend(obj)
    xref_pos = len(out)
    out.extend(f"xref\n0 {len(offsets)}\n".encode())
    out.extend(b"0000000000 65535 f \n")
    for off in offsets[1:]:
        out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(
        f"trailer<< /Size {len(offsets)} /Root 1 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n".encode()
    )
    return bytes(out)


DEMO_PROJECTS = [
    {
        "prefecture": "Préfecture de Rabat",
        "commune": "Hassan",
        "titre": "Lotissement Al Amal — Hassan",
        "consistance_globale": (
            "Lotissement résidentiel de standing moyen : voirie interne, "
            "réseaux VRD, espaces verts et 86 lots individuels."
        ),
        "nombre_lots": 86,
        "situation_localisation": (
            "Quartier Hassan, à proximité de l'avenue Mohamed V, "
            "sur un terrain plat bordé au nord par une voie communale."
        ),
        "voie_acces": "Avenue Mohamed V puis rue Ibnou Sina",
        "emprise_servitudes": "Servitude de passage 4 m sur la limite est.",
        "statut_actuel": Project.StatutProjet.EXECUTION,
        "terrain": {
            "titre_foncier_mere": "TF 45.218/R",
            "suffixe": "Lot A",
            "superficie_totale": Decimal("18500.00"),
            "superficie_unite": TerrainMere.UniteSuperficie.M2,
        },
        "autorisation": {
            "type_permis": Autorisation.TypePermis.LOTIR,
            "numero_autorisation": "AL/2024/118",
            "date_delivrance": date(2024, 6, 12),
        },
        "financement": {
            "fonds_propres_fp": Decimal("12500000.00"),
            "credit_moyen_terme_cmt": Decimal("18000000.00"),
        },
        "docs": [
            (ProjectDocument.Kind.VOIRIE_VRD, "voirie_al_amal.pdf"),
            (ProjectDocument.Kind.TELECOM_FIBRE, "fibre_al_amal.pdf"),
            (ProjectDocument.Kind.FICHE_LOT_PARCELLE, "fiche_lots_al_amal.pdf"),
        ],
        "finance_docs": ["bilan_al_amal.pdf", "plan_financement_al_amal.pdf"],
        "planning_docs": [
            (PlanningDocument.Phase.ETUDES, "etudes_al_amal.pdf"),
            (PlanningDocument.Phase.VIABILISATION, "viabilisation_al_amal.pdf"),
            (PlanningDocument.Phase.RECEPTION, "reception_al_amal.pdf"),
        ],
    },
    {
        "prefecture": "Préfecture de Salé",
        "commune": "Salé Medina",
        "titre": "Résidence Les Jardins de Bouregreg",
        "consistance_globale": (
            "Programme mixte : 42 villas + 120 appartements, "
            "aménagement paysager et parking sous-sol."
        ),
        "nombre_lots": 162,
        "situation_localisation": (
            "Rive droite du Bouregreg, secteur Bab Lamrissa, "
            "vue partielle sur le fleuve."
        ),
        "voie_acces": "Route de Kenitra — sortie Bab Lamrissa",
        "emprise_servitudes": "Bande non aedificandi 8 m le long du fleuve.",
        "statut_actuel": Project.StatutProjet.INSTRUCTION,
        "terrain": {
            "titre_foncier_mere": "TF 12.904/S",
            "suffixe": "",
            "superficie_totale": Decimal("3.20"),
            "superficie_unite": TerrainMere.UniteSuperficie.HA,
        },
        "autorisation": {
            "type_permis": Autorisation.TypePermis.AMENAGER,
            "numero_autorisation": "PA/2025/042",
            "date_delivrance": date(2025, 2, 28),
        },
        "financement": {
            "fonds_propres_fp": Decimal("22000000.00"),
            "credit_moyen_terme_cmt": Decimal("35000000.00"),
        },
        "docs": [
            (ProjectDocument.Kind.AMENAGEMENT_PAYSAGER, "paysager_bouregreg.pdf"),
            (ProjectDocument.Kind.VOIRIE_VRD, "vrd_bouregreg.pdf"),
            (ProjectDocument.Kind.FICHE_LOT_PARCELLE, "parcelles_bouregreg.pdf"),
        ],
        "finance_docs": ["montage_bouregreg.pdf"],
        "planning_docs": [
            (PlanningDocument.Phase.ETUDES, "etudes_bouregreg.pdf"),
            (PlanningDocument.Phase.VIABILISATION, "vrd_phase_bouregreg.pdf"),
        ],
    },
    {
        "prefecture": "Préfecture de Skhirat-Témara",
        "commune": "Témara",
        "titre": "Lotissement Oued Cherrat",
        "consistance_globale": (
            "Lotissement économique : 210 lots sociaux, équipements de proximité "
            "et réseau d'assainissement séparatif."
        ),
        "nombre_lots": 210,
        "situation_localisation": (
            "Zone d'extension sud de Témara, à 1,5 km de la RN1, "
            "terrain en légère pente vers l'ouest."
        ),
        "voie_acces": "RN1 puis chemin communal C-214",
        "emprise_servitudes": "Passage d'oued saisonnier — emprise 12 m.",
        "statut_actuel": Project.StatutProjet.EXECUTION,
        "terrain": {
            "titre_foncier_mere": "TF 78.331/T",
            "suffixe": "Secteur B",
            "superficie_totale": Decimal("42500.00"),
            "superficie_unite": TerrainMere.UniteSuperficie.M2,
        },
        "autorisation": {
            "type_permis": Autorisation.TypePermis.LOTIR,
            "numero_autorisation": "AL/2023/087",
            "date_delivrance": date(2023, 11, 5),
        },
        "financement": {
            "fonds_propres_fp": Decimal("8000000.00"),
            "credit_moyen_terme_cmt": Decimal("24000000.00"),
        },
        "docs": [
            (ProjectDocument.Kind.VOIRIE_VRD, "voirie_cherrat.pdf"),
            (ProjectDocument.Kind.TELECOM_FIBRE, "telecom_cherrat.pdf"),
            (ProjectDocument.Kind.FICHE_LOT_PARCELLE, "lots_cherrat.pdf"),
        ],
        "finance_docs": ["fp_cmt_cherrat.pdf", "tableau_amortissement_cherrat.pdf"],
        "planning_docs": [
            (PlanningDocument.Phase.ETUDES, "geo_cherrat.pdf"),
            (PlanningDocument.Phase.VIABILISATION, "travaux_vrd_cherrat.pdf"),
            (PlanningDocument.Phase.VIABILISATION, "reseaux_cherrat.pdf"),
            (PlanningDocument.Phase.RECEPTION, "pv_reception_cherrat.pdf"),
        ],
    },
    {
        "prefecture": "Préfecture de Casablanca-Anfa",
        "commune": "Anfa",
        "titre": "Îlot commercial Ain Diab Extension",
        "consistance_globale": (
            "Aménagement d'un îlot commercial : 18 cellules, "
            "parking de 90 places et façade sur boulevard de la Corniche."
        ),
        "nombre_lots": 18,
        "situation_localisation": (
            "Ain Diab, angle boulevard de la Corniche / rue Abou Faris Al-Marini."
        ),
        "voie_acces": "Boulevard de la Corniche",
        "emprise_servitudes": "Alignement urbain 5 m sur le boulevard.",
        "statut_actuel": Project.StatutProjet.INSTRUCTION,
        "terrain": {
            "titre_foncier_mere": "TF 201.556/C",
            "suffixe": "Îlot 3",
            "superficie_totale": Decimal("4200.00"),
            "superficie_unite": TerrainMere.UniteSuperficie.M2,
        },
        "autorisation": {
            "type_permis": Autorisation.TypePermis.CONSTRUIRE,
            "numero_autorisation": "PC/2025/309",
            "date_delivrance": date(2025, 9, 18),
        },
        "financement": {
            "fonds_propres_fp": Decimal("15000000.00"),
            "credit_moyen_terme_cmt": Decimal("12000000.00"),
        },
        "docs": [
            (ProjectDocument.Kind.VOIRIE_VRD, "acces_ain_diab.pdf"),
            (ProjectDocument.Kind.AMENAGEMENT_PAYSAGER, "facade_ain_diab.pdf"),
        ],
        "finance_docs": ["business_plan_ain_diab.pdf"],
        "planning_docs": [
            (PlanningDocument.Phase.ETUDES, "permis_ain_diab.pdf"),
        ],
    },
    {
        "prefecture": "Province de Benslimane",
        "commune": "Benslimane",
        "titre": "Domaine El Menzeh — Villae",
        "consistance_globale": (
            "Lotissement de villas haut standing : 34 lots de 800 à 1 200 m², "
            "voirie privée, éclairage LED et portail contrôlé."
        ),
        "nombre_lots": 34,
        "situation_localisation": (
            "Périphérie nord de Benslimane, zone forestière classée à 400 m, "
            "accès depuis la RP 3205."
        ),
        "voie_acces": "RP 3205 — km 7",
        "emprise_servitudes": "Zone tampon forestière 20 m (non constructible).",
        "statut_actuel": Project.StatutProjet.EXECUTION,
        "terrain": {
            "titre_foncier_mere": "TF 9.112/B",
            "suffixe": "Domaine",
            "superficie_totale": Decimal("4.85"),
            "superficie_unite": TerrainMere.UniteSuperficie.HA,
        },
        "autorisation": {
            "type_permis": Autorisation.TypePermis.AMENAGER,
            "numero_autorisation": "PA/2024/055",
            "date_delivrance": date(2024, 4, 3),
        },
        "financement": {
            "fonds_propres_fp": Decimal("28000000.00"),
            "credit_moyen_terme_cmt": Decimal("15000000.00"),
        },
        "docs": [
            (ProjectDocument.Kind.VOIRIE_VRD, "voirie_menzeh.pdf"),
            (ProjectDocument.Kind.AMENAGEMENT_PAYSAGER, "paysager_menzeh.pdf"),
            (ProjectDocument.Kind.TELECOM_FIBRE, "fibre_menzeh.pdf"),
            (ProjectDocument.Kind.FICHE_LOT_PARCELLE, "fiche_villae_menzeh.pdf"),
        ],
        "finance_docs": ["structure_menzeh.pdf", "banque_menzeh.pdf"],
        "planning_docs": [
            (PlanningDocument.Phase.ETUDES, "etudes_menzeh.pdf"),
            (PlanningDocument.Phase.VIABILISATION, "viab_menzeh.pdf"),
            (PlanningDocument.Phase.RECEPTION, "tf_individuels_menzeh.pdf"),
        ],
    },
]

DEMO_INTERVENANTS = [
    (Intervenant.TypeIntervenant.MO, "SARL Atlas Promotion", "05 37 70 12 34"),
    (Intervenant.TypeIntervenant.ARCHITECTE, "Cabinet Naciri & Associés", "06 61 22 45 78"),
    (Intervenant.TypeIntervenant.IGT, "Topographie Al Maghrib", "05 22 98 11 20"),
    (Intervenant.TypeIntervenant.BET, "BET Ingénierie Plus", "05 37 26 88 01"),
    (Intervenant.TypeIntervenant.ENTREPRISE, "Travaux Généraux du Maroc", "05 22 44 67 90"),
]


# Photo legends per project (several images each).
DEMO_IMAGE_LEGENDES = [
    "Vue d'ensemble du site",
    "Accès principal",
    "Voirie en cours",
    "Espace vert",
    "Façade / implantation",
]


class Command(BaseCommand):
    help = (
        "Crée 5 projets démo complets : terrain, permis, intervenants, "
        "docs techniques, photos, financement, planning et annexes PDF."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Supprime d'abord les projets dont le titre correspond à la démo.",
        )

    def handle(self, *args, **options):
        if options["clear"]:
            titres = [p["titre"] for p in DEMO_PROJECTS]
            deleted, _ = Project.objects.filter(titre__in=titres).delete()
            self.stdout.write(self.style.WARNING(f"Supprimé {deleted} objet(s) liés à la démo."))

        intervenants = self._ensure_intervenants()

        created = []
        with transaction.atomic():
            for index, data in enumerate(DEMO_PROJECTS):
                project = self._create_project(data, intervenants, index)
                created.append(project)

        self.stdout.write(self.style.SUCCESS(f"{len(created)} projets créés :"))
        for project in created:
            n_docs = project.documents.count()
            n_imgs = project.images.count()
            n_fin = (
                project.structure_financement.documents.count()
                if hasattr(project, "structure_financement")
                else 0
            )
            n_plan = (
                project.planning_execution.documents.count()
                if hasattr(project, "planning_execution")
                else 0
            )
            n_ann = (
                project.annexe_dossier.documents.count()
                if hasattr(project, "annexe_dossier")
                else 0
            )
            self.stdout.write(
                f"  • {project.code} — {project.titre} "
                f"(tech: {n_docs}, photos: {n_imgs}, finance: {n_fin}, "
                f"planning: {n_plan}, annexes: {n_ann})"
            )

    def _ensure_intervenants(self):
        result = []
        for type_int, nom, contact in DEMO_INTERVENANTS:
            obj, _ = Intervenant.objects.get_or_create(
                type_intervenant=type_int,
                nom_ou_cabinet=nom,
                defaults={"contact": contact},
            )
            result.append(obj)
        return result

    def _pdf(self, name, title, *lines):
        return ContentFile(build_pdf(title, *lines), name=name)

    def _image(self, name, label, color=(139, 30, 45)):
        """Generate a simple JPG placeholder (requires Pillow)."""
        from PIL import Image, ImageDraw, ImageFont

        img = Image.new("RGB", (800, 600), color=color)
        draw = ImageDraw.Draw(img)
        draw.rectangle((40, 40, 760, 560), outline=(255, 255, 255), width=3)
        try:
            font = ImageFont.truetype("arial.ttf", 28)
            font_sm = ImageFont.truetype("arial.ttf", 18)
        except OSError:
            font = ImageFont.load_default()
            font_sm = font
        draw.text((60, 250), label[:40], fill=(255, 255, 255), font=font)
        draw.text((60, 300), "Photo demo — 2os Gestion", fill=(230, 230, 230), font=font_sm)
        buf = BytesIO()
        img.save(buf, format="JPEG", quality=85)
        return ContentFile(buf.getvalue(), name=name)

    def _create_project(self, data, intervenants, index):
        project = Project.objects.create(
            prefecture=data["prefecture"],
            commune=data["commune"],
            titre=data["titre"],
            consistance_globale=data["consistance_globale"],
            nombre_lots=data["nombre_lots"],
            situation_localisation=data["situation_localisation"],
            voie_acces=data["voie_acces"],
            emprise_servitudes=data["emprise_servitudes"],
            statut_actuel=data["statut_actuel"],
        )
        project.intervenants.set(intervenants[:3] if index % 2 else intervenants)

        TerrainMere.objects.create(project=project, **data["terrain"])
        Autorisation.objects.create(project=project, **data["autorisation"])

        for kind, filename in data["docs"]:
            label = dict(ProjectDocument.Kind.choices).get(kind, kind)
            doc = ProjectDocument(project=project, kind=kind)
            doc.fichier.save(
                filename,
                self._pdf(
                    filename,
                    f"{project.code} — {label}",
                    project.titre,
                    f"Commune: {project.commune}",
                    f"Document technique: {label}",
                    "Fichier de demonstration 2os Gestion.",
                ),
                save=True,
            )

        # Several photos per project (different colors).
        palette = [
            (139, 30, 45),
            (30, 58, 95),
            (15, 118, 110),
            (180, 83, 9),
            (55, 65, 81),
        ]
        for i, legende in enumerate(DEMO_IMAGE_LEGENDES):
            filename = f"{project.code.lower()}_photo_{i + 1}.jpg"
            pimg = ProjectImage(project=project, legende=legende, ordre=i)
            pimg.image.save(
                filename,
                self._image(filename, f"{project.code} — {legende}", palette[i % len(palette)]),
                save=True,
            )

        financement = StructureFinancement.objects.create(
            project=project, **data["financement"]
        )
        for filename in data["finance_docs"]:
            fdoc = FinancementDocument(financement=financement)
            fdoc.fichier.save(
                filename,
                self._pdf(
                    filename,
                    f"{project.code} — Planning financier",
                    project.titre,
                    f"FP: {financement.fonds_propres_fp} DH",
                    f"CMT: {financement.credit_moyen_terme_cmt} DH",
                    f"Total: {financement.investissement_total} DH",
                    "Document financement (PDF demo).",
                ),
                save=True,
            )

        planning = PlanningExecution.objects.create(project=project)
        for phase, filename in data["planning_docs"]:
            label = dict(PlanningDocument.Phase.choices).get(phase, phase)
            pdoc = PlanningDocument(planning=planning, phase=phase)
            pdoc.fichier.save(
                filename,
                self._pdf(
                    filename,
                    f"{project.code} — Planning d'execution",
                    project.titre,
                    f"Phase: {label}",
                    "Document planning (PDF demo).",
                ),
                save=True,
            )

        dossier = AnnexeDossier.objects.create(project=project)
        for kind, label in AnnexeDocument.Kind.choices:
            slug = kind.lower()
            filename = f"annexe_{slug}_{project.code.lower()}.pdf"
            adoc = AnnexeDocument(dossier=dossier, kind=kind)
            adoc.fichier.save(
                filename,
                self._pdf(
                    filename,
                    f"{project.code} — Annexe",
                    project.titre,
                    label,
                    "Piece jointe dossier administratif (demo).",
                ),
                save=True,
            )

        return project
