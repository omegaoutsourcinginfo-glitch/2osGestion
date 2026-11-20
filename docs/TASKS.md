# Tasks — CRUD Utilisateurs + send mail (junior)

Fichiers utiles : `users/admin.py`, `users/services.py`, `core/settings.py`, `.env`, `docker-compose.yml`

**Pour l’équipe (partage facile) :**
- Excel : [`TASKS_CRUD_Users_Email.xlsx`](TASKS_CRUD_Users_Email.xlsx) — colonnes Done / Task / Titre / Step / Assignee
- Word : [`TASKS_CRUD_Users_Email.docx`](TASKS_CRUD_Users_Email.docx) — cases ☐ à cocher

Coche `- [ ]` → `- [x]` (Markdown) ou ☐ → ☑ (Excel/Word) quand c’est fait.

---

## Task1 — Ajouter / configurer le mail (SMTP)

- [ ] **Titre :** Configurer l’envoi d’e-mail (Mailpit local ou Gmail).

**Description :**

- [ ] Si `.env` n’existe pas : copier `.env.example` → `.env`
- [ ] **Mailpit (local)** — écrire dans `.env` :
  ```env
  EMAIL_HOST=127.0.0.1
  EMAIL_PORT=1025
  EMAIL_HOST_USER=
  EMAIL_HOST_PASSWORD=
  EMAIL_USE_SSL=False
  EMAIL_USE_TLS=False
  DEFAULT_FROM_EMAIL=noreply@2osgestion.local
  ```
- [ ] Démarrer Mailpit : `docker compose up -d mailpit`
- [ ] Ouvrir la boîte : http://127.0.0.1:8025
- [ ] Redémarrer Django : `poetry run python manage.py runserver`
- [ ] Vérifier SMTP :
  ```powershell
  poetry run python manage.py shell -c "from django.conf import settings; print(settings.EMAIL_BACKEND); print(settings.EMAIL_HOST, settings.EMAIL_PORT)"
  ```
  Attendu : `smtp.EmailBackend` + `127.0.0.1 1025`
- [ ] **(Optionnel Gmail)** — dans `.env` :
  ```env
  EMAIL_HOST=smtp.gmail.com
  EMAIL_HOST_USER=ton@gmail.com
  EMAIL_HOST_PASSWORD=app-password-google
  EMAIL_PORT=465
  EMAIL_USE_SSL=True
  EMAIL_USE_TLS=False
  DEFAULT_FROM_EMAIL=ton@gmail.com
  ```
  (App Password Google uniquement. Ne jamais committer `.env`)

---

## Task2 — CREATE user + send password mail

- [ ] **Titre :** Créer un utilisateur et envoyer le mot de passe par e-mail.

**Description :**

- [ ] Login Admin : `/admin/login/` (compte superuser)
- [ ] Aller à `/admin/users/user/add/`
- [ ] Remplir : E-mail, Prénom, Nom, Téléphone, Type (`Admin` / `Super Admin`)
- [ ] Ne pas taper de mot de passe (généré auto)
- [ ] Cliquer **Enregistrer**
- [ ] Voir le message : `Utilisateur créé. Mot de passe envoyé à …`
- [ ] Ouvrir http://127.0.0.1:8025 → lire `Password: …`
- [ ] Lire le code : `users/services.py` + `UserCreationForm.save` + `UserAdmin.save_model` dans `users/admin.py`
- [ ] **OK :** user créé + e-mail avec password dans Mailpit (ou Gmail)

---

## Task3 — READ liste + fiche user

- [ ] **Titre :** Afficher la liste et la fiche utilisateur.

**Description :**

- [ ] Ouvrir `/admin/users/user/`
- [ ] Vérifier `list_display` dans `UserAdmin` (`users/admin.py`)
- [ ] Vérifier `search_fields`
- [ ] Vérifier `ordering = ("-date_joined",)`
- [ ] Tester la recherche (e-mail / nom)
- [ ] Ouvrir une fiche `/admin/users/user/<id>/change/` et lire les infos
- [ ] **OK :** liste + recherche + fiche sans erreur

---

## Task4 — UPDATE user (ou lecture seule)

- [ ] **Titre :** Modifier un utilisateur existant (ou le laisser en lecture seule).

**Description :**

- [ ] Demander au lead : update autorisé **ou** lecture seule ?
- [ ] Si **update autorisé** :
  - [ ] Éditer prénom / téléphone → **Enregistrer**
  - [ ] Ne pas renvoyer le password à chaque save (seulement à la création)
  - [ ] Recharger → valeur sauvée
- [ ] Si **lecture seule** (dans `UserAdmin`) :
  - [ ] `get_readonly_fields` : tous les champs si `obj` existe
  - [ ] `changeform_view` : `show_save=False`, `show_save_and_continue=False`, `show_save_and_add_another=False`
  - [ ] Tester : pas de modification possible
- [ ] **OK :** comportement = décision lead

---

## Task5 — DELETE user (ou interdire)

- [ ] **Titre :** Supprimer un utilisateur (ou bloquer la suppression).

**Description :**

- [ ] Demander au lead : delete autorisé **ou** interdit ?
- [ ] Si **interdit** dans `UserAdmin` :
  - [ ] `has_delete_permission` → `return False`
  - [ ] `actions = None` / `get_actions` → `{}`
  - [ ] Tester : pas de suppression
- [ ] Si **autorisé** :
  - [ ] Supprimer un user de test seulement (pas le superuser principal)
  - [ ] Vérifier qu’il disparaît de la liste
- [ ] Alternative : `is_active=False` (soft delete) si le lead le demande
- [ ] **OK :** comportement = décision lead

---

## Task6 — Recette finale

- [ ] **Titre :** Valider tout le CRUD Utilisateurs + mail.

**Description :**

- [ ] Task1 mail SMTP OK
- [ ] Task2 CREATE + password dans Mailpit/Gmail OK
- [ ] Login du nouveau user avec ce password OK
- [ ] Task3 READ OK
- [ ] Task4 UPDATE / lecture seule OK
- [ ] Task5 DELETE / interdit OK
- [ ] Aucun secret dans Git

---

## Erreurs fréquentes

- Mailpit vide → `docker compose up -d mailpit` + redémarrer Django
- `console.EmailBackend` → `EMAIL_HOST` vide dans `.env`
- CREATE OK mais login KO → mauvais password (relire Mailpit) ou `is_staff=False`
