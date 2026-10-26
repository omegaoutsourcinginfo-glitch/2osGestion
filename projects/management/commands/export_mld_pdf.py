"""Export the Logical Data Model (MLD) of 2os Gestion as a visual PDF of tables.

Usage:
    python manage.py export_mld_pdf
    python manage.py export_mld_pdf --output Desktop
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

# Visual table: (title, rows) where row = (col_name, type, flag)
# flag: "PK" | "FK" | ""
TABLES = [
    (
        "PROJECT",
        [
            ("id", "INTEGER", "PK"),
            ("code", "VARCHAR(5) UNIQUE", ""),
            ("prefecture", "VARCHAR(255)", ""),
            ("commune", "VARCHAR(255)", ""),
            ("titre", "VARCHAR(255)", ""),
            ("consistance_globale", "TEXT", ""),
            ("nombre_lots", "INTEGER NULL", ""),
            ("situation_localisation", "TEXT", ""),
            ("voie_acces", "VARCHAR(255)", ""),
            ("emprise_servitudes", "TEXT", ""),
            ("statut_actuel", "VARCHAR(20)", ""),
            ("is_archived", "BOOLEAN", ""),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
    (
        "INTERVENANT",
        [
            ("id", "INTEGER", "PK"),
            ("type_intervenant", "VARCHAR(20)", ""),
            ("nom_ou_cabinet", "VARCHAR(255)", ""),
            ("contact", "VARCHAR(255)", ""),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
    (
        "PROJECT_INTERVENANTS (M2M)",
        [
            ("id", "INTEGER", "PK"),
            ("project_id", "INTEGER", "FK"),
            ("intervenant_id", "INTEGER", "FK"),
        ],
    ),
    (
        "TERRAIN_MERE",
        [
            ("id", "INTEGER", "PK"),
            ("project_id", "INTEGER UNIQUE", "FK"),
            ("titre_foncier_mere", "VARCHAR(100)", ""),
            ("suffixe", "VARCHAR(50)", ""),
            ("superficie_totale", "DECIMAL(12,2)", ""),
            ("superficie_unite", "VARCHAR(2)", ""),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
    (
        "AUTORISATION",
        [
            ("id", "INTEGER", "PK"),
            ("project_id", "INTEGER UNIQUE", "FK"),
            ("type_permis", "VARCHAR(20)", ""),
            ("numero_autorisation", "VARCHAR(100)", ""),
            ("date_delivrance", "DATE NULL", ""),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
    (
        "PROGRAMME_TECHNIQUE",
        [
            ("id", "INTEGER", "PK"),
            ("project_id", "INTEGER UNIQUE", "FK"),
            ("voirie_vrd", "BOOLEAN", ""),
            ("observations", "TEXT", ""),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
    (
        "PROJECT_DOCUMENT",
        [
            ("id", "INTEGER", "PK"),
            ("project_id", "INTEGER", "FK"),
            ("kind", "VARCHAR(32)", ""),
            ("fichier", "VARCHAR (path)", ""),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
    (
        "PROJECT_IMAGE",
        [
            ("id", "INTEGER", "PK"),
            ("project_id", "INTEGER", "FK"),
            ("image", "VARCHAR (path)", ""),
            ("legende", "VARCHAR(255)", ""),
            ("ordre", "INTEGER", ""),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
    (
        "STRUCTURE_FINANCEMENT",
        [
            ("id", "INTEGER", "PK"),
            ("project_id", "INTEGER UNIQUE", "FK"),
            ("fonds_propres_fp", "DECIMAL(16,2)", ""),
            ("credit_moyen_terme_cmt", "DECIMAL(16,2)", ""),
            ("investissement_total", "DECIMAL(16,2)", ""),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
    (
        "FINANCEMENT_DOCUMENT",
        [
            ("id", "INTEGER", "PK"),
            ("financement_id", "INTEGER", "FK"),
            ("fichier", "VARCHAR (path)", ""),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
    (
        "PLANNING_EXECUTION",
        [
            ("id", "INTEGER", "PK"),
            ("project_id", "INTEGER UNIQUE", "FK"),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
    (
        "PLANNING_DOCUMENT",
        [
            ("id", "INTEGER", "PK"),
            ("planning_id", "INTEGER", "FK"),
            ("phase", "VARCHAR(32)", ""),
            ("fichier", "VARCHAR (path)", ""),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
    (
        "ANNEXE_DOSSIER",
        [
            ("id", "INTEGER", "PK"),
            ("project_id", "INTEGER UNIQUE", "FK"),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
    (
        "ANNEXE_DOCUMENT",
        [
            ("id", "INTEGER", "PK"),
            ("dossier_id", "INTEGER", "FK"),
            ("kind", "VARCHAR(32)", ""),
            ("fichier", "VARCHAR (path)", ""),
            ("created_at", "DATETIME", ""),
            ("updated_at", "DATETIME", ""),
        ],
    ),
]

FK_LINKS = [
    "PROJECT_INTERVENANTS.project_id  -->  PROJECT.id",
    "PROJECT_INTERVENANTS.intervenant_id  -->  INTERVENANT.id",
    "TERRAIN_MERE.project_id  -->  PROJECT.id   (1:1)",
    "AUTORISATION.project_id  -->  PROJECT.id   (1:1)",
    "PROGRAMME_TECHNIQUE.project_id  -->  PROJECT.id   (1:1)",
    "PROJECT_DOCUMENT.project_id  -->  PROJECT.id   (1:N)",
    "PROJECT_IMAGE.project_id  -->  PROJECT.id   (1:N)",
    "STRUCTURE_FINANCEMENT.project_id  -->  PROJECT.id   (1:1)",
    "FINANCEMENT_DOCUMENT.financement_id  -->  STRUCTURE_FINANCEMENT.id   (1:N)",
    "PLANNING_EXECUTION.project_id  -->  PROJECT.id   (1:1)",
    "PLANNING_DOCUMENT.planning_id  -->  PLANNING_EXECUTION.id   (1:N)",
    "ANNEXE_DOSSIER.project_id  -->  PROJECT.id   (1:1)",
    "ANNEXE_DOCUMENT.dossier_id  -->  ANNEXE_DOSSIER.id   (1:N)",
]

MAROON = colors.HexColor("#8b1e2d")
NAVY = colors.HexColor("#1e3a5f")
HEADER_BG = colors.HexColor("#1e3a5f")
PK_BG = colors.HexColor("#fef3c7")
FK_BG = colors.HexColor("#dbeafe")
ROW_ALT = colors.HexColor("#f8fafc")
BORDER = colors.HexColor("#94a3b8")


def _table_height(n_rows, title_h=18, row_h=13, pad=4):
    return title_h + pad + n_rows * row_h + pad


def _draw_table_box(c, x, y_top, width, title, columns):
    """Draw a classic MLD table box. y_top is the top of the box."""
    title_h = 18
    row_h = 13
    pad = 3
    n = len(columns)
    height = title_h + pad + n * row_h + pad
    y_bottom = y_top - height

    # Outer box
    c.setStrokeColor(BORDER)
    c.setLineWidth(1)
    c.setFillColor(colors.white)
    c.roundRect(x, y_bottom, width, height, 3, fill=1, stroke=1)

    # Title bar
    c.setFillColor(HEADER_BG)
    c.roundRect(x, y_top - title_h, width, title_h, 3, fill=1, stroke=0)
    c.rect(x, y_top - title_h, width, 6, fill=1, stroke=0)  # square bottom of title
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9)
    c.drawCentredString(x + width / 2, y_top - 13, title)

    # Column rows
    y = y_top - title_h - pad - 10
    for i, (col, typ, flag) in enumerate(columns):
        row_top = y_top - title_h - pad - i * row_h
        row_bot = row_top - row_h
        if flag == "PK":
            c.setFillColor(PK_BG)
            c.rect(x + 1, row_bot, width - 2, row_h, fill=1, stroke=0)
        elif flag == "FK":
            c.setFillColor(FK_BG)
            c.rect(x + 1, row_bot, width - 2, row_h, fill=1, stroke=0)
        elif i % 2 == 1:
            c.setFillColor(ROW_ALT)
            c.rect(x + 1, row_bot, width - 2, row_h, fill=1, stroke=0)

        c.setFillColor(colors.HexColor("#111827"))
        c.setFont("Helvetica-Bold" if flag else "Helvetica", 7.5)
        label = col
        if flag:
            label = f"{flag}  {col}"
        c.drawString(x + 5, row_bot + 3.5, label[:28])
        c.setFont("Helvetica", 6.5)
        c.setFillColor(colors.HexColor("#64748b"))
        c.drawRightString(x + width - 5, row_bot + 3.5, typ[:18])

    # Separator under title
    c.setStrokeColor(BORDER)
    c.setLineWidth(0.6)
    c.line(x, y_top - title_h, x + width, y_top - title_h)

    return height


class Command(BaseCommand):
    help = "Génère le PDF MLD (tables logiques visibles) de 2os Gestion."

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="",
            help="Chemin PDF (défaut: docs + Desktop)",
        )

    def handle(self, *args, **options):
        targets = []
        if options["output"]:
            targets.append(Path(options["output"]))
        else:
            targets.append(Path(settings.BASE_DIR) / "docs" / "MLD_2osGestion.pdf")
            desktop = Path.home() / "Desktop" / "MLD_2osGestion.pdf"
            targets.append(desktop)

        page = landscape(A4)
        page_w, page_h = page
        margin = 28
        gap = 12
        col_w = (page_w - 2 * margin - 2 * gap) / 3

        # Pack tables into pages (3 columns)
        pages_content = []
        current = []
        col_y = [page_h - margin - 50] * 3
        col_i = 0

        def new_page_state():
            return [], [page_h - margin - 50] * 3, 0

        for title, cols in TABLES:
            h = _table_height(len(cols))
            placed = False
            for attempt in range(3):
                ci = (col_i + attempt) % 3
                if col_y[ci] - h >= margin + 20:
                    x = margin + ci * (col_w + gap)
                    current.append((x, col_y[ci], col_w, title, cols))
                    col_y[ci] -= h + gap
                    col_i = (ci + 1) % 3
                    placed = True
                    break
            if not placed:
                pages_content.append(current)
                current, col_y, col_i = new_page_state()
                x = margin
                current.append((x, col_y[0], col_w, title, cols))
                col_y[0] -= h + gap
                col_i = 1
        if current:
            pages_content.append(current)

        # FK links page
        for path in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            c = canvas.Canvas(str(path), pagesize=page)
            c.setTitle("MLD 2os Gestion — Tables")

            for page_idx, boxes in enumerate(pages_content):
                # Header
                c.setFillColor(MAROON)
                c.setFont("Helvetica-Bold", 16)
                c.drawString(margin, page_h - 22, "2os Gestion — MLD (Modele Logique de Donnees)")
                c.setFillColor(colors.HexColor("#64748b"))
                c.setFont("Helvetica", 9)
                c.drawString(margin, page_h - 36, "Tables SQL / Django — PK = jaune  |  FK = bleu")
                c.setFont("Helvetica", 8)
                c.drawRightString(page_w - margin, page_h - 22, f"Page {page_idx + 1}")

                for x, y_top, w, title, cols in boxes:
                    _draw_table_box(c, x, y_top, w, title, cols)

                c.showPage()

            # Last page: foreign keys
            c.setFillColor(MAROON)
            c.setFont("Helvetica-Bold", 16)
            c.drawString(margin, page_h - 22, "2os Gestion — MLD : Cles etrangeres (FK)")
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Bold", 11)
            c.drawString(margin, page_h - 50, "Liens entre tables")

            y = page_h - 70
            c.setFont("Courier", 9)
            for link in FK_LINKS:
                if y < margin + 30:
                    c.showPage()
                    y = page_h - 40
                    c.setFont("Courier", 9)
                c.setFillColor(colors.HexColor("#1f2937"))
                c.drawString(margin + 10, y, f"•  {link}")
                y -= 16

            y -= 20
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Bold", 10)
            c.drawString(margin, y, "Legende")
            y -= 18
            c.setFillColor(PK_BG)
            c.rect(margin, y - 2, 14, 12, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.setFont("Helvetica", 9)
            c.drawString(margin + 20, y, "PK — cle primaire")
            y -= 16
            c.setFillColor(FK_BG)
            c.rect(margin, y - 2, 14, 12, fill=1, stroke=1)
            c.setFillColor(colors.black)
            c.drawString(margin + 20, y, "FK — cle etrangere")

            c.save()
            self.stdout.write(self.style.SUCCESS(f"MLD PDF : {path.resolve()}"))
