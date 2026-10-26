"""Export the conceptual data model (MCD) of 2os Gestion as a PDF.

Usage:
    python manage.py export_mcd_pdf
    python manage.py export_mcd_pdf --output docs/MCD_2osGestion.pdf
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# Entity tables: (name, list of (attribute, type, notes))
ENTITIES = [
    (
        "PROJECT (Projet)",
        [
            ("id", "PK", "Identifiant"),
            ("code", "Char(5) UNIQUE", "Ex: A2601 — auto"),
            ("prefecture", "Char(255)", "Préfecture / Province"),
            ("commune", "Char(255)", "Commune"),
            ("titre", "Char(255)", "Titre du projet"),
            ("consistance_globale", "Text", "Consistance"),
            ("nombre_lots", "Int NULL", "Lots / Unités"),
            ("situation_localisation", "Text", "Situation"),
            ("voie_acces", "Char(255)", "Accès au site"),
            ("emprise_servitudes", "Text", "Servitudes"),
            ("statut_actuel", "Char(20)", "INSTRUCTION | EXECUTION"),
            ("is_archived", "Boolean", "Archivé oui/non"),
            ("created_at / updated_at", "DateTime", "Horodatage"),
        ],
    ),
    (
        "INTERVENANT",
        [
            ("id", "PK", "Identifiant"),
            ("type_intervenant", "Char(20)", "MO, ARCHITECTE, IGT, BET…"),
            ("nom_ou_cabinet", "Char(255)", "Nom / cabinet"),
            ("contact", "Char(255)", "Contact optionnel"),
            ("created_at / updated_at", "DateTime", "Horodatage"),
        ],
    ),
    (
        "TERRAIN_MERE",
        [
            ("id", "PK", "Identifiant"),
            ("project_id", "FK 1—1 PROJECT", "Projet lié"),
            ("titre_foncier_mere", "Char(100)", "Titre foncier"),
            ("suffixe", "Char(50)", "Suffixe"),
            ("superficie_totale", "Decimal(12,2)", "Superficie"),
            ("superficie_unite", "Char(2)", "M2 | HA"),
        ],
    ),
    (
        "AUTORISATION",
        [
            ("id", "PK", "Identifiant"),
            ("project_id", "FK 1—1 PROJECT", "Projet lié"),
            ("type_permis", "Char(20)", "AMENAGER, LOTIR…"),
            ("numero_autorisation", "Char(100)", "N° autorisation"),
            ("date_delivrance", "Date NULL", "Date délivrance"),
        ],
    ),
    (
        "PROGRAMME_TECHNIQUE",
        [
            ("id", "PK", "Identifiant"),
            ("project_id", "FK 1—1 PROJECT", "Projet lié"),
            ("voirie_vrd", "Boolean", "Voirie VRD"),
            ("observations", "Text", "Observations"),
        ],
    ),
    (
        "PROJECT_DOCUMENT (Document technique)",
        [
            ("id", "PK", "Identifiant"),
            ("project_id", "FK N—1 PROJECT", "Projet"),
            ("kind", "Char(32)", "VOIRIE, TELECOM, ESPACE_VERT, STEP…"),
            ("fichier", "File", "PDF / image / DOC / DWG"),
        ],
    ),
    (
        "PROJECT_IMAGE",
        [
            ("id", "PK", "Identifiant"),
            ("project_id", "FK N—1 PROJECT", "Projet"),
            ("image", "Image", "JPG / PNG / WEBP / GIF"),
            ("legende", "Char(255)", "Légende optionnelle"),
            ("ordre", "Int", "Ordre d'affichage"),
        ],
    ),
    (
        "STRUCTURE_FINANCEMENT",
        [
            ("id", "PK", "Identifiant"),
            ("project_id", "FK 1—1 PROJECT", "Projet lié"),
            ("fonds_propres_fp", "Decimal(16,2)", "FP (DH)"),
            ("credit_moyen_terme_cmt", "Decimal(16,2)", "CMT (DH)"),
            ("investissement_total", "Decimal(16,2)", "FP + CMT (calculé)"),
        ],
    ),
    (
        "FINANCEMENT_DOCUMENT",
        [
            ("id", "PK", "Identifiant"),
            ("financement_id", "FK N—1 STRUCTURE_FINANCEMENT", "Financement"),
            ("fichier", "File PDF", "Document financement"),
        ],
    ),
    (
        "PLANNING_EXECUTION",
        [
            ("id", "PK", "Identifiant"),
            ("project_id", "FK 1—1 PROJECT", "Projet lié"),
        ],
    ),
    (
        "PLANNING_DOCUMENT",
        [
            ("id", "PK", "Identifiant"),
            ("planning_id", "FK N—1 PLANNING_EXECUTION", "Planning"),
            ("phase", "Char(32)", "ETUDES | VIABILISATION | RECEPTION"),
            ("fichier", "File PDF", "PDF de phase"),
        ],
    ),
    (
        "ANNEXE_DOSSIER",
        [
            ("id", "PK", "Identifiant"),
            ("project_id", "FK 1—1 PROJECT", "Projet lié"),
        ],
    ),
    (
        "ANNEXE_DOCUMENT",
        [
            ("id", "PK", "Identifiant"),
            ("dossier_id", "FK N—1 ANNEXE_DOSSIER", "Dossier annexes"),
            ("kind", "Char(32)", "CERTIFICAT, PLAN, ATTESTATIONS…"),
            ("fichier", "File PDF", "Pièce jointe"),
        ],
    ),
]

RELATIONS = [
    ("PROJECT", "INTERVENANT", "N — N", "projects_intervenants (M2M)"),
    ("PROJECT", "TERRAIN_MERE", "1 — 1", "Un terrain mère par projet"),
    ("PROJECT", "AUTORISATION", "1 — 1", "Un permis / autorisation"),
    ("PROJECT", "PROGRAMME_TECHNIQUE", "1 — 1", "Programme technique"),
    ("PROJECT", "PROJECT_DOCUMENT", "1 — N", "Plusieurs docs techniques"),
    ("PROJECT", "PROJECT_IMAGE", "1 — N", "Plusieurs photos"),
    ("PROJECT", "STRUCTURE_FINANCEMENT", "1 — 1", "Un financement"),
    ("STRUCTURE_FINANCEMENT", "FINANCEMENT_DOCUMENT", "1 — N", "Plusieurs PDF finance"),
    ("PROJECT", "PLANNING_EXECUTION", "1 — 1", "Un planning d'exécution"),
    ("PLANNING_EXECUTION", "PLANNING_DOCUMENT", "1 — N", "PDF par phase"),
    ("PROJECT", "ANNEXE_DOSSIER", "1 — 1", "Dossier annexes"),
    ("ANNEXE_DOSSIER", "ANNEXE_DOCUMENT", "1 — N", "Pièces jointes PDF"),
]

CARDINALITIES_LEGEND = (
    "1 — 1 : association un-à-un &nbsp;&nbsp;|&nbsp;&nbsp; "
    "1 — N : un-à-plusieurs &nbsp;&nbsp;|&nbsp;&nbsp; "
    "N — N : plusieurs-à-plusieurs"
)


class Command(BaseCommand):
    help = "Génère le PDF MCD (tables + relations) de 2os Gestion."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="",
            help="Chemin du PDF (défaut: docs/MCD_2osGestion.pdf)",
        )

    def handle(self, *args, **options):
        out = options["output"] or str(Path(settings.BASE_DIR) / "docs" / "MCD_2osGestion.pdf")
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "MCDTitle",
            parent=styles["Heading1"],
            fontSize=18,
            textColor=colors.HexColor("#8b1e2d"),
            alignment=TA_CENTER,
            spaceAfter=8,
        )
        subtitle = ParagraphStyle(
            "MCDSub",
            parent=styles["Normal"],
            fontSize=10,
            textColor=colors.HexColor("#4b5563"),
            alignment=TA_CENTER,
            spaceAfter=16,
        )
        h2 = ParagraphStyle(
            "MCDH2",
            parent=styles["Heading2"],
            fontSize=12,
            textColor=colors.HexColor("#1e3a5f"),
            spaceBefore=12,
            spaceAfter=6,
        )
        body = ParagraphStyle(
            "MCDBody",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            alignment=TA_LEFT,
        )
        cell = ParagraphStyle(
            "MCDCell",
            parent=styles["Normal"],
            fontSize=8,
            leading=10,
        )

        story = []
        story.append(Paragraph("2os Gestion — Modèle Conceptuel de Données (MCD)", title_style))
        story.append(
            Paragraph(
                "Dictionnaire des entités, attributs et relations &nbsp;|&nbsp; Application de gestion de projets",
                subtitle,
            )
        )
        story.append(Paragraph(CARDINALITIES_LEGEND, body))
        story.append(Spacer(1, 0.4 * cm))

        # Relations overview table first
        story.append(Paragraph("1. Relations entre entités", h2))
        rel_header = [
            Paragraph("<b>Entité A</b>", cell),
            Paragraph("<b>Entité B</b>", cell),
            Paragraph("<b>Cardinalité</b>", cell),
            Paragraph("<b>Description</b>", cell),
        ]
        rel_data = [rel_header]
        for a, b, card, desc in RELATIONS:
            rel_data.append(
                [
                    Paragraph(a, cell),
                    Paragraph(b, cell),
                    Paragraph(card, cell),
                    Paragraph(desc, cell),
                ]
            )
        rel_table = Table(rel_data, colWidths=[4.2 * cm, 4.5 * cm, 2.2 * cm, 6.5 * cm])
        rel_table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fafc")),
                    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#cbd5e1")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f5f9")]),
                ]
            )
        )
        story.append(rel_table)
        story.append(PageBreak())

        story.append(Paragraph("2. Dictionnaire des entités (tables)", h2))
        story.append(
            Paragraph(
                "Chaque tableau décrit une entité du MCD avec ses attributs, types et notes.",
                body,
            )
        )
        story.append(Spacer(1, 0.3 * cm))

        for name, attrs in ENTITIES:
            story.append(Paragraph(name, h2))
            data = [
                [
                    Paragraph("<b>Attribut</b>", cell),
                    Paragraph("<b>Type / rôle</b>", cell),
                    Paragraph("<b>Notes</b>", cell),
                ]
            ]
            for attr, typ, note in attrs:
                data.append(
                    [
                        Paragraph(attr, cell),
                        Paragraph(typ, cell),
                        Paragraph(note, cell),
                    ]
                )
            t = Table(data, colWidths=[5.2 * cm, 5.5 * cm, 6.7 * cm])
            t.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#8b1e2d")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                        ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#d1d5db")),
                        ("VALIGN", (0, 0), (-1, -1), "TOP"),
                        ("LEFTPADDING", (0, 0), (-1, -1), 4),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                        ("TOPPADDING", (0, 0), (-1, -1), 3),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                        (
                            "ROWBACKGROUNDS",
                            (0, 1),
                            (-1, -1),
                            [colors.white, colors.HexColor("#fafafa")],
                        ),
                    ]
                )
            )
            story.append(t)
            story.append(Spacer(1, 0.35 * cm))

        story.append(Spacer(1, 0.5 * cm))
        story.append(
            Paragraph(
                "<b>Légende PK</b> = clé primaire &nbsp;|&nbsp; "
                "<b>FK</b> = clé étrangère &nbsp;|&nbsp; "
                "Horodatage <i>created_at / updated_at</i> présent sur les entités horodatées.",
                body,
            )
        )

        def _footer(canvas, doc):
            canvas.saveState()
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#6b7280"))
            canvas.drawString(2 * cm, 1.2 * cm, "2os Gestion — MCD")
            canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")
            canvas.restoreState()

        doc = SimpleDocTemplate(
            str(path),
            pagesize=A4,
            leftMargin=1.6 * cm,
            rightMargin=1.6 * cm,
            topMargin=1.6 * cm,
            bottomMargin=2 * cm,
            title="MCD 2os Gestion",
            author="2os Gestion",
        )
        doc.build(story, onFirstPage=_footer, onLaterPages=_footer)

        self.stdout.write(self.style.SUCCESS(f"MCD PDF généré : {path.resolve()}"))
