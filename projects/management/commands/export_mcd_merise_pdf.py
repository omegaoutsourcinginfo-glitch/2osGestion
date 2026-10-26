"""Export Merise MCD diagram like the reference schema (entities + ovals + cardinalities).

Usage:
    python manage.py export_mcd_merise_pdf
"""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas

NAVY = colors.HexColor("#1e3a5f")
GRAY = colors.HexColor("#374151")
LINE = colors.HexColor("#9ca3af")
BLUE = colors.HexColor("#2563eb")
CARD = colors.HexColor("#1d4ed8")


def draw_entity(c, cx, cy, title, attrs, w=155, highlight=False):
    row_h = 10.5
    title_h = 15
    pad = 3
    h = title_h + pad + len(attrs) * row_h + pad
    x0, y0 = cx - w / 2, cy - h / 2
    x1, y1 = x0 + w, y0 + h

    c.setStrokeColor(BLUE if highlight else GRAY)
    c.setLineWidth(2 if highlight else 1.15)
    c.setFillColor(colors.white)
    c.rect(x0, y0, w, h, fill=1, stroke=1)

    c.setFillColor(NAVY if highlight else colors.HexColor("#111827"))
    c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(cx, y1 - 11, title)

    c.setStrokeColor(LINE)
    c.setLineWidth(0.55)
    c.line(x0 + 4, y1 - title_h, x1 - 4, y1 - title_h)

    y = y1 - title_h - pad - 7.5
    for attr in attrs:
        if attr.startswith("#"):
            c.setFont("Helvetica-Bold", 6.8)
            c.setFillColor(colors.HexColor("#111827"))
        else:
            c.setFont("Helvetica", 6.8)
            c.setFillColor(GRAY)
        c.drawString(x0 + 6, y, attr[:40])
        y -= row_h
    return (cx, cy, w / 2, h / 2)


def draw_oval(c, cx, cy, name, rw=78, rh=26):
    c.setStrokeColor(colors.HexColor("#111827"))
    c.setLineWidth(1)
    c.setFillColor(colors.white)
    c.ellipse(cx - rw / 2, cy - rh / 2, cx + rw / 2, cy + rh / 2, fill=1, stroke=1)
    c.setFillColor(colors.HexColor("#111827"))
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(cx, cy - 2.5, name)
    return cx, cy


def edge_point(cx, cy, hw, hh, tx, ty):
    """Point on entity box border toward target (tx, ty)."""
    dx, dy = tx - cx, ty - cy
    if dx == 0 and dy == 0:
        return cx, cy
    # Scale to hit rectangle border
    sx = hw / abs(dx) if dx != 0 else 1e9
    sy = hh / abs(dy) if dy != 0 else 1e9
    s = min(sx, sy)
    return cx + dx * s, cy + dy * s


def connect(c, e1, e2, rel_name, card_left, card_right):
    """Connect two entities via relationship oval with cardinalities."""
    cx1, cy1, hw1, hh1 = e1
    cx2, cy2, hw2, hh2 = e2
    mx = cx1 + (cx2 - cx1) * 0.48
    my = cy1 + (cy2 - cy1) * 0.48
    draw_oval(c, mx, my, rel_name)

    p1 = edge_point(cx1, cy1, hw1, hh1, mx, my)
    p2 = edge_point(cx2, cy2, hw2, hh2, mx, my)
    # oval edge approximations
    o1 = edge_point(mx, my, 39, 13, cx1, cy1)
    o2 = edge_point(mx, my, 39, 13, cx2, cy2)

    c.setStrokeColor(LINE)
    c.setLineWidth(0.95)
    c.line(p1[0], p1[1], o1[0], o1[1])
    c.line(o2[0], o2[1], p2[0], p2[1])

    # Cardinalities
    c.setFillColor(CARD)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawCentredString((p1[0] + o1[0]) / 2, (p1[1] + o1[1]) / 2 + 5, card_left)
    c.drawCentredString((p2[0] + o2[0]) / 2, (p2[1] + o2[1]) / 2 + 5, card_right)


class Command(BaseCommand):
    help = "Génère le MCD Merise (comme le schéma entités-associations)."

    def add_arguments(self, parser):
        parser.add_argument("--output", default="")

    def handle(self, *args, **options):
        targets = (
            [Path(options["output"])]
            if options["output"]
            else [
                Path(settings.BASE_DIR) / "docs" / "MCD_Merise_2osGestion.pdf",
                Path.home() / "Desktop" / "MCD_Merise_2osGestion.pdf",
            ]
        )

        pw, ph = landscape(A4)
        cx, cy = pw / 2, ph / 2 - 5

        # Layout matching the reference Merise star (angles approx.)
        # (angle_deg, distance, title, attrs, relation, card_projet, card_entity)
        import math

        # Angles in degrees (0=right, 90=up) — star layout like the reference MCD
        nodes = [
            (
                125,
                255,
                "TERRAIN_MERE",
                ["# id", "titre_foncier_mere", "suffixe", "superficie_totale (m2/ha)"],
                "Situer",
                "(1,1)",
                "(1,1)",
            ),
            (
                90,
                250,
                "AUTORISATION",
                ["# id", "type_permis [Construire, ...]", "numero_autorisation", "date_delivrance"],
                "Autoriser",
                "(1,n)",
                "(1,1)",
            ),
            (
                55,
                255,
                "INTERVENANT",
                ["# id", "type_intervenant [MO, IGT...]", "nom_ou_cabinet", "contact / qualite"],
                "Intervenir",
                "(1,n)",
                "(1,n)",
            ),
            (
                20,
                260,
                "PROGRAMME_VRD",
                [
                    "# id",
                    "voirie_vrd",
                    "assainissement (EP/EU)",
                    "eau_potable (AEP)",
                    "electricite_mt_bt",
                    "eclairage_public",
                    "telecom_fibre",
                    "amenagement_paysager",
                ],
                "Equiper",
                "(1,1)",
                "(1,1)",
            ),
            (
                340,
                255,
                "VALIDATION_VISA",
                ["# id", "entite_validatrice", "nom_signataire", "date_visa", "signature_cachet_url"],
                "Viser",
                "(1,n)",
                "(1,1)",
            ),
            (
                305,
                255,
                "PIECE_ANNEXE_DOC",
                ["# id", "type_piece [ANCFCC, IGT]", "chemin_fichier / depot", "est_obligatoire (bool)"],
                "Joindre",
                "(1,n)",
                "(1,1)",
            ),
            (
                270,
                250,
                "PLANNING_PHASE",
                ["# id", "nom_phase [VRD, Rec...]", "date_debut / fin", "statut_avancement"],
                "Planifier",
                "(1,n)",
                "(1,1)",
            ),
            (
                235,
                255,
                "LOT_PARCELLE",
                ["# id", "numero_lot", "superficie", "type_usage [Hab, Com...]", "statut"],
                "Decomposer",
                "(1,n)",
                "(1,1)",
            ),
            (
                160,
                255,
                "STRUCTURE_FINANCEMENT",
                ["# id", "fonds_propres_fp", "credit_moyen_terme_cmt", "investissement_total"],
                "Financer",
                "(1,1)",
                "(1,1)",
            ),
        ]

        projet_attrs = [
            "# id",
            "code",
            "prefecture",
            "commune",
            "titre",
            "consistance_globale",
            "situation_localisation",
            "voie_acces",
            "emprise / servitudes",
        ]

        for path in targets:
            path.parent.mkdir(parents=True, exist_ok=True)
            c = canvas.Canvas(str(path), pagesize=landscape(A4))
            c.setTitle("MCD Merise 2os Gestion")

            c.setFillColor(colors.HexColor("#8b1e2d"))
            c.setFont("Helvetica-Bold", 13)
            c.drawCentredString(cx, ph - 18, "MCD (Merise) — Gestion de projets / lotissements")
            c.setFillColor(GRAY)
            c.setFont("Helvetica", 7.5)
            c.drawCentredString(
                cx,
                ph - 30,
                "Entites (rectangles) · Associations (ovales) · Cardinalites (min,max)",
            )

            projet = draw_entity(c, cx, cy, "PROJET", projet_attrs, w=170, highlight=True)

            for angle, dist, title, attrs, rel, card_p, card_e in nodes:
                rad = math.radians(angle)
                ex = cx + dist * math.cos(rad)
                ey = cy + dist * math.sin(rad)
                # Keep inside page margins
                ex = max(95, min(pw - 95, ex))
                ey = max(85, min(ph - 55, ey))
                ent = draw_entity(c, ex, ey, title, attrs, w=152 if len(attrs) < 6 else 160)
                connect(c, projet, ent, rel, card_p, card_e)

            # Legend
            c.setStrokeColor(LINE)
            c.setFillColor(colors.HexColor("#f9fafb"))
            c.rect(16, 10, 300, 36, fill=1, stroke=1)
            c.setFillColor(NAVY)
            c.setFont("Helvetica-Bold", 7.5)
            c.drawString(22, 32, "Legende")
            c.setFont("Helvetica", 6.8)
            c.setFillColor(GRAY)
            c.drawString(22, 20, "Rectangle = Entite   |   Ovale = Association / relation")
            c.drawString(22, 10, "# id = cle   |   (1,1)(1,n)(0,n) = cardinalites")

            c.save()
            self.stdout.write(self.style.SUCCESS(f"MCD Merise PDF : {path.resolve()}"))
