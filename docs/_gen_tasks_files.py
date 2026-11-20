"""One-shot generator: docs/TASKS_CRUD_Users_Email.xlsx + .docx"""

from pathlib import Path

from docx import Document
from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation

ROOT = Path(__file__).resolve().parent

ROWS = [
    ("Task1", "Configurer envoi e-mail (Mailpit / Gmail)", 1, "Si .env n'existe pas: copier .env.example vers .env"),
    ("Task1", "Configurer envoi e-mail (Mailpit / Gmail)", 2, "Ecrire dans .env: EMAIL_HOST=127.0.0.1 EMAIL_PORT=1025 EMAIL_USE_SSL=False EMAIL_USE_TLS=False DEFAULT_FROM_EMAIL=noreply@2osgestion.local"),
    ("Task1", "Configurer envoi e-mail (Mailpit / Gmail)", 3, "Demarrer Mailpit: docker compose up -d mailpit"),
    ("Task1", "Configurer envoi e-mail (Mailpit / Gmail)", 4, "Ouvrir http://127.0.0.1:8025"),
    ("Task1", "Configurer envoi e-mail (Mailpit / Gmail)", 5, "Redemarrer Django: poetry run python manage.py runserver"),
    ("Task1", "Configurer envoi e-mail (Mailpit / Gmail)", 6, "Verifier SMTP (attendu smtp.EmailBackend + 127.0.0.1 1025)"),
    ("Task1", "Configurer envoi e-mail (Mailpit / Gmail)", 7, "Optionnel Gmail: EMAIL_HOST=smtp.gmail.com + App Password (ne pas committer .env)"),
    ("Task2", "CREATE user + envoyer password par e-mail", 1, "Login Admin /admin/login/ (superuser)"),
    ("Task2", "CREATE user + envoyer password par e-mail", 2, "Aller a /admin/users/user/add/"),
    ("Task2", "CREATE user + envoyer password par e-mail", 3, "Remplir: E-mail, Prenom, Nom, Telephone, Type (Admin/Super Admin)"),
    ("Task2", "CREATE user + envoyer password par e-mail", 4, "Ne pas taper de mot de passe (genere auto)"),
    ("Task2", "CREATE user + envoyer password par e-mail", 5, "Cliquer Enregistrer"),
    ("Task2", "CREATE user + envoyer password par e-mail", 6, "Voir message: Utilisateur cree. Mot de passe envoye a ..."),
    ("Task2", "CREATE user + envoyer password par e-mail", 7, "Ouvrir Mailpit http://127.0.0.1:8025 et lire Password: ..."),
    ("Task2", "CREATE user + envoyer password par e-mail", 8, "Lire code: users/services.py + UserCreationForm.save + UserAdmin.save_model"),
    ("Task2", "CREATE user + envoyer password par e-mail", 9, "OK: user cree + email avec password"),
    ("Task3", "READ liste + fiche utilisateur", 1, "Ouvrir /admin/users/user/"),
    ("Task3", "READ liste + fiche utilisateur", 2, "Verifier list_display dans UserAdmin (users/admin.py)"),
    ("Task3", "READ liste + fiche utilisateur", 3, "Verifier search_fields"),
    ("Task3", "READ liste + fiche utilisateur", 4, "Verifier ordering = (-date_joined,)"),
    ("Task3", "READ liste + fiche utilisateur", 5, "Tester la recherche (e-mail / nom)"),
    ("Task3", "READ liste + fiche utilisateur", 6, "Ouvrir fiche /admin/users/user/<id>/change/"),
    ("Task3", "READ liste + fiche utilisateur", 7, "OK: liste + recherche + fiche sans erreur"),
    ("Task4", "UPDATE user (ou lecture seule)", 1, "Demander au lead: update autorise OU lecture seule?"),
    ("Task4", "UPDATE user (ou lecture seule)", 2, "Si update: editer prenom/telephone puis Enregistrer"),
    ("Task4", "UPDATE user (ou lecture seule)", 3, "Si update: ne pas renvoyer password a chaque save"),
    ("Task4", "UPDATE user (ou lecture seule)", 4, "Si update: recharger page -> valeur sauvee"),
    ("Task4", "UPDATE user (ou lecture seule)", 5, "Si lecture seule: get_readonly_fields pour tous les champs si obj existe"),
    ("Task4", "UPDATE user (ou lecture seule)", 6, "Si lecture seule: show_save=False / show_save_and_continue=False / show_save_and_add_another=False"),
    ("Task4", "UPDATE user (ou lecture seule)", 7, "OK: comportement = decision lead"),
    ("Task5", "DELETE user (ou interdire)", 1, "Demander au lead: delete autorise OU interdit?"),
    ("Task5", "DELETE user (ou interdire)", 2, "Si interdit: has_delete_permission return False"),
    ("Task5", "DELETE user (ou interdire)", 3, "Si interdit: actions=None / get_actions={}"),
    ("Task5", "DELETE user (ou interdire)", 4, "Si interdit: tester pas de suppression"),
    ("Task5", "DELETE user (ou interdire)", 5, "Si autorise: supprimer user de test seulement (pas superuser principal)"),
    ("Task5", "DELETE user (ou interdire)", 6, "Alternative soft delete: is_active=False"),
    ("Task5", "DELETE user (ou interdire)", 7, "OK: comportement = decision lead"),
    ("Task6", "Recette finale CRUD + mail", 1, "Task1 mail SMTP OK"),
    ("Task6", "Recette finale CRUD + mail", 2, "Task2 CREATE + password dans Mailpit/Gmail OK"),
    ("Task6", "Recette finale CRUD + mail", 3, "Login nouveau user avec ce password OK"),
    ("Task6", "Recette finale CRUD + mail", 4, "Task3 READ OK"),
    ("Task6", "Recette finale CRUD + mail", 5, "Task4 UPDATE / lecture seule OK"),
    ("Task6", "Recette finale CRUD + mail", 6, "Task5 DELETE / interdit OK"),
    ("Task6", "Recette finale CRUD + mail", 7, "Aucun secret dans Git"),
]

SUMMARY = [
    ("Task1", "Configurer envoi e-mail (Mailpit / Gmail)"),
    ("Task2", "CREATE user + envoyer password par e-mail"),
    ("Task3", "READ liste + fiche utilisateur"),
    ("Task4", "UPDATE user (ou lecture seule)"),
    ("Task5", "DELETE user (ou interdire)"),
    ("Task6", "Recette finale CRUD + mail"),
]

FILLS = {
    "Task1": PatternFill("solid", fgColor="FDF2F4"),
    "Task2": PatternFill("solid", fgColor="F0FDF4"),
    "Task3": PatternFill("solid", fgColor="EFF6FF"),
    "Task4": PatternFill("solid", fgColor="FFF7ED"),
    "Task5": PatternFill("solid", fgColor="F5F3FF"),
    "Task6": PatternFill("solid", fgColor="F8FAFC"),
}


def write_xlsx() -> Path:
    wb = Workbook()
    ws = wb.active
    ws.title = "Tasks"

    headers = ["Done", "Task", "Titre", "Step #", "Description / etape", "Assignee", "Notes"]
    header_fill = PatternFill("solid", fgColor="8B1E2D")
    header_font = Font(bold=True, color="FFFFFF")
    thin = Border(
        left=Side(style="thin", color="D1D5DB"),
        right=Side(style="thin", color="D1D5DB"),
        top=Side(style="thin", color="D1D5DB"),
        bottom=Side(style="thin", color="D1D5DB"),
    )

    for col, h in enumerate(headers, 1):
        cell = ws.cell(1, col, h)
        cell.fill = header_fill
        cell.font = header_font
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    for i, (task, titre, step, desc) in enumerate(ROWS, 2):
        ws.cell(i, 1, "☐")
        ws.cell(i, 2, task)
        ws.cell(i, 3, titre)
        ws.cell(i, 4, step)
        ws.cell(i, 5, desc)
        ws.cell(i, 6, "")
        ws.cell(i, 7, "")
        fill = FILLS.get(task)
        for c in range(1, 8):
            cell = ws.cell(i, c)
            cell.border = thin
            cell.alignment = Alignment(vertical="center", wrap_text=True)
            if fill:
                cell.fill = fill

    dv = DataValidation(type="list", formula1='"☐,☑"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"A2:A{1 + len(ROWS)}")

    ws.column_dimensions["A"].width = 8
    ws.column_dimensions["B"].width = 10
    ws.column_dimensions["C"].width = 42
    ws.column_dimensions["D"].width = 8
    ws.column_dimensions["E"].width = 75
    ws.column_dimensions["F"].width = 16
    ws.column_dimensions["G"].width = 24
    ws.row_dimensions[1].height = 24
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:G{1 + len(ROWS)}"

    ws2 = wb.create_sheet("Summary")
    for col, h in enumerate(["Task", "Titre", "Done?"], 1):
        cell = ws2.cell(1, col, h)
        cell.fill = header_fill
        cell.font = header_font
    for i, (t, title) in enumerate(SUMMARY, 2):
        ws2.cell(i, 1, t)
        ws2.cell(i, 2, title)
        ws2.cell(i, 3, "☐")
    ws2.column_dimensions["A"].width = 10
    ws2.column_dimensions["B"].width = 50
    ws2.column_dimensions["C"].width = 10

    ws3 = wb.create_sheet("Erreurs frequentes")
    ws3["A1"] = "Probleme"
    ws3["B1"] = "Solution"
    ws3["A1"].fill = header_fill
    ws3["B1"].fill = header_fill
    ws3["A1"].font = header_font
    ws3["B1"].font = header_font
    errs = [
        ("Mailpit vide", "docker compose up -d mailpit + redemarrer Django"),
        ("console.EmailBackend", "EMAIL_HOST vide dans .env"),
        ("CREATE OK mais login KO", "Relire password dans Mailpit / verifier is_staff=True"),
    ]
    for i, (p, s) in enumerate(errs, 2):
        ws3.cell(i, 1, p)
        ws3.cell(i, 2, s)
    ws3.column_dimensions["A"].width = 28
    ws3.column_dimensions["B"].width = 60

    out = ROOT / "TASKS_CRUD_Users_Email.xlsx"
    wb.save(out)
    return out


def write_docx() -> Path:
    doc = Document()
    doc.add_heading("Tasks — CRUD Utilisateurs + send mail (junior)", level=1)
    doc.add_paragraph("Coche ☐ → ☑ quand c'est fait. Partager ce fichier Word à l'équipe.")

    by_task: dict[str, list] = {}
    titres: dict[str, str] = {}
    for task, titre, step, desc in ROWS:
        titres[task] = titre
        by_task.setdefault(task, []).append((step, desc))

    for task in ["Task1", "Task2", "Task3", "Task4", "Task5", "Task6"]:
        doc.add_heading(f"{task} — {titres[task]}", level=2)
        p = doc.add_paragraph()
        r = p.add_run("Titre: ")
        r.bold = True
        p.add_run(titres[task])
        doc.add_paragraph("Description:")
        for _step, desc in by_task[task]:
            doc.add_paragraph(f"☐  {desc}")

    doc.add_heading("Erreurs frequentes", level=2)
    doc.add_paragraph("☐  Mailpit vide → docker compose up -d mailpit + redemarrer Django")
    doc.add_paragraph("☐  console.EmailBackend → EMAIL_HOST vide dans .env")
    doc.add_paragraph("☐  CREATE OK mais login KO → relire password Mailpit / is_staff")

    out = ROOT / "TASKS_CRUD_Users_Email.docx"
    doc.save(out)
    return out


if __name__ == "__main__":
    xlsx = write_xlsx()
    docx = write_docx()
    print("WROTE", xlsx)
    print("WROTE", docx)
