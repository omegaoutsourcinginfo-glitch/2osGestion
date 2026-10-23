from django.core.validators import FileExtensionValidator
from django.db import IntegrityError, models, transaction
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Intervenant(TimeStampedModel):
    class TypeIntervenant(models.TextChoices):
        MO = "MO", "Maître d'ouvrage"
        ARCHITECTE = "ARCHITECTE", "Architecte"
        IGT = "IGT", "Ingénieur topographe (IGT)"
        BET = "BET", "Bureau d'études techniques (BET)"
        BC = "BC", "Bureau de contrôle (BC)"
        LABO = "LABO", "Laboratoire"
        ENTREPRISE = "ENTREPRISE", "Entreprise"
        AUTRE = "AUTRE", "Autre"

    type_intervenant = models.CharField(
        max_length=20, choices=TypeIntervenant.choices, verbose_name="Type d'intervenant"
    )
    nom_ou_cabinet = models.CharField(max_length=255, verbose_name="Nom ou cabinet")
    contact = models.CharField(max_length=255, blank=True, verbose_name="Contact")

    class Meta:
        verbose_name = "Intervenant"
        verbose_name_plural = "Intervenants"
        ordering = ["nom_ou_cabinet"]

    def __str__(self):
        return f"{self.nom_ou_cabinet} ({self.get_type_intervenant_display()})"


class Project(TimeStampedModel):
    class StatutProjet(models.TextChoices):
        INSTRUCTION = "INSTRUCTION", "En cours d'instruction"
        EXECUTION = "EXECUTION", "En cours d'exécution"

    code = models.CharField(max_length=5, unique=True, editable=False)
    prefecture = models.CharField(max_length=255, verbose_name="Préfecture / Province")
    commune = models.CharField(max_length=255, verbose_name="Commune")
    titre = models.CharField(max_length=255, verbose_name="Titre du projet")
    consistance_globale = models.TextField(verbose_name="Consistance du projet")
    nombre_lots = models.PositiveIntegerField(null=True, blank=True, verbose_name="Nombre de lots / Unités")
    situation_localisation = models.TextField(verbose_name="Situation & Localisation")
    voie_acces = models.CharField(max_length=255, verbose_name="Accès au site")
    emprise_servitudes = models.TextField(blank=True, verbose_name="Servitudes d'urbanisme")
    statut_actuel = models.CharField(
        max_length=20,
        choices=StatutProjet.choices,
        default=StatutProjet.INSTRUCTION,
        verbose_name="Statut actuel du projet"
    )
    is_archived = models.BooleanField(
        default=False,
        verbose_name="Archivé",
        help_text="Les projets archivés sont masqués de la liste principale.",
    )
    intervenants = models.ManyToManyField(
        Intervenant,
        blank=True,
        related_name="projects",
        verbose_name="Intervenants"
    )

    class Meta:
        verbose_name = "Projet"
        verbose_name_plural = "Projets"

    def __str__(self):
        return f"{self.code} - {self.titre}"

    def get_absolute_url(self):
        from django.urls import reverse

        return f"{reverse('admin:index')}?projet={self.code}"

    @classmethod
    def next_code(cls):
        yy = timezone.now().strftime("%y")
        # Match the year at positions 1-2 only: "A2627" contains "27" but belongs to 2026.
        last = cls.objects.filter(code__regex=f"^[A-Z]{yy}").order_by("-code").first()

        if last is None:
            return f"A{yy}01"

        letter = last.code[0]
        number = int(last.code[3:]) + 1

        if number > 99:
            letter = chr(ord(letter) + 1)
            number = 1

        return f"{letter}{yy}{number:02d}"

    def save(self, *args, **kwargs):
        if self.code:
            return super().save(*args, **kwargs)

        # Two simultaneous saves can compute the same code; the unique constraint catches it.
        for _ in range(5):
            self.code = self.next_code()
            try:
                with transaction.atomic():
                    return super().save(*args, **kwargs)
            except IntegrityError:
                self.code = ""
        raise IntegrityError("Could not generate a unique project code.")


class TerrainMere(TimeStampedModel):
    class UniteSuperficie(models.TextChoices):
        M2 = "M2", "m²"
        HA = "HA", "ha"

    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="terrain_mere",
        verbose_name="Projet"
    )
    titre_foncier_mere = models.CharField(max_length=100, verbose_name="Titre foncier mère")
    suffixe = models.CharField(max_length=50, blank=True, verbose_name="Suffixe")
    superficie_totale = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        verbose_name="Superficie totale",
    )
    superficie_unite = models.CharField(
        max_length=2,
        choices=UniteSuperficie.choices,
        default=UniteSuperficie.M2,
        verbose_name="Unité",
    )

    class Meta:
        verbose_name = "Terrain Mère"
        verbose_name_plural = "Terrains Mères"

    def __str__(self):
        return f"{self.titre_foncier_mere} ({self.project.code})"

    @property
    def superficie_affichee(self):
        return f"{self.superficie_totale} {self.get_superficie_unite_display()}"


class Autorisation(TimeStampedModel):
    class TypePermis(models.TextChoices):
        AMENAGER = "AMENAGER", "Permis d'aménager"
        CONSTRUIRE = "CONSTRUIRE", "Permis de construire"
        LOTIR = "LOTIR", "Autorisation de lotir"
        MORCELER = "MORCELER", "Autorisation de morceler"
        HABITER = "HABITER", "Permis d'habiter"
        CONFORMITE = "CONFORMITE", "Certificat de conformité"
        AUTRE = "AUTRE", "Autre"

    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="autorisation",
        verbose_name="Projet"
    )
    type_permis = models.CharField(max_length=20, choices=TypePermis.choices, verbose_name="Type de permis")
    numero_autorisation = models.CharField(max_length=100, verbose_name="Numéro d'autorisation")
    date_delivrance = models.DateField(null=True, blank=True, verbose_name="Date de délivrance")

    class Meta:
        verbose_name = "Permis d’aménager / construire"
        verbose_name_plural = "Permis d’aménager / construire"
        ordering = ["-date_delivrance"]

    def __str__(self):
        return f"{self.get_type_permis_display()} n° {self.numero_autorisation} ({self.project.code})"


DOCUMENT_EXTENSIONS = ["pdf", "jpg", "jpeg", "png", "doc", "docx", "dwg"]


class ProgrammeTechnique(TimeStampedModel):
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="programme_technique",
        verbose_name="Projet"
    )
    voirie_vrd = models.BooleanField(default=False, verbose_name="Voirie (VRD)")
    observations = models.TextField(blank=True, verbose_name="Observations")

    class Meta:
        verbose_name = "Programme technique & viabilisation"
        verbose_name_plural = "Programme technique & viabilisation"

    def __str__(self):
        return f"Programme technique ({self.project.code})"


class ProjectDocument(TimeStampedModel):
    """Plusieurs fichiers par type de document technique."""

    class Kind(models.TextChoices):
        VOIRIE_VRD = "VOIRIE_VRD", "Voirie (VRD)"
        TELECOM_FIBRE = "TELECOM_FIBRE", "Télécom / Fibre"
        AMENAGEMENT_PAYSAGER = "AMENAGEMENT_PAYSAGER", "Aménagement paysager"
        FICHE_LOT_PARCELLE = "FICHE_LOT_PARCELLE", "Fiche lot / parcelle"

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Projet",
    )
    kind = models.CharField(
        max_length=32,
        choices=Kind.choices,
        verbose_name="Type de document",
    )
    fichier = models.FileField(
        upload_to="programme_technique/%Y/%m/",
        validators=[FileExtensionValidator(DOCUMENT_EXTENSIONS)],
        verbose_name="Fichier",
        help_text="PDF, image (JPG, PNG), Word (DOC, DOCX) ou AutoCAD (DWG)",
    )

    class Meta:
        verbose_name = "Document technique"
        verbose_name_plural = "Documents techniques"
        ordering = ["kind", "-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} — {self.project.code}"


class ProjectImage(TimeStampedModel):
    """Plusieurs photos par projet (galerie)."""

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="images",
        verbose_name="Projet",
    )
    image = models.ImageField(
        upload_to="projets/images/%Y/%m/",
        validators=[FileExtensionValidator(["jpg", "jpeg", "png", "webp", "gif"])],
        verbose_name="Image",
        help_text="JPG, PNG, WEBP ou GIF — plusieurs images possibles",
    )
    legende = models.CharField(
        max_length=255,
        blank=True,
        verbose_name="Légende",
    )
    ordre = models.PositiveIntegerField(default=0, verbose_name="Ordre")

    class Meta:
        verbose_name = "Image projet"
        verbose_name_plural = "Images projet"
        ordering = ["ordre", "-created_at"]

    def __str__(self):
        return self.legende or f"Image — {self.project.code}"


class StructureFinancement(TimeStampedModel):
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="structure_financement",
        verbose_name="Projet"
    )
    fonds_propres_fp = models.DecimalField(
        max_digits=16, decimal_places=2, default=0, verbose_name="FP : Fonds propres (DH)"
    )
    credit_moyen_terme_cmt = models.DecimalField(
        max_digits=16, decimal_places=2, default=0, verbose_name="CMT : Crédit moyen terme (DH)"
    )
    investissement_total = models.DecimalField(
        max_digits=16, decimal_places=2, default=0, editable=False, verbose_name="Total investissement (DH)"
    )

    class Meta:
        verbose_name = "Planning financier & structure de financement"
        verbose_name_plural = "Planning financier & structure de financement"

    def __str__(self):
        return f"Financement ({self.project.code})"

    def save(self, *args, **kwargs):
        self.investissement_total = self.fonds_propres_fp + self.credit_moyen_terme_cmt
        super().save(*args, **kwargs)


class FinancementDocument(TimeStampedModel):
    """Plusieurs PDF de financement par structure."""

    financement = models.ForeignKey(
        StructureFinancement,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Financement",
    )
    fichier = models.FileField(
        upload_to="financement/%Y/%m/",
        validators=[FileExtensionValidator(["pdf"])],
        verbose_name="Document financement (PDF)",
        help_text="PDF uniquement — plusieurs fichiers possibles",
    )

    class Meta:
        verbose_name = "Document financement"
        verbose_name_plural = "Documents financement"
        ordering = ["-created_at"]

    def __str__(self):
        return f"PDF financement ({self.financement.project.code})"


class PlanningExecution(TimeStampedModel):
    """Conteneur OneToOne — PDFs par phase via le menu latéral."""

    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="planning_execution",
        verbose_name="Projet",
    )

    class Meta:
        verbose_name = "Planning d'exécution"
        verbose_name_plural = "Planning d'exécution du projet"

    def __str__(self):
        return f"Planning d'exécution ({self.project.code})"


class PlanningDocument(TimeStampedModel):
    """Plusieurs PDF par phase de planning d'exécution."""

    class Phase(models.TextChoices):
        ETUDES = "ETUDES", "Études techniques, géotechniques & Permis"
        VIABILISATION = "VIABILISATION", "Travaux de Viabilisation (VRD & Réseaux)"
        RECEPTION = "RECEPTION", "Réception provisoire & Titres fonciers individuels"

    PHASE_ORDER = {
        Phase.ETUDES: 1,
        Phase.VIABILISATION: 2,
        Phase.RECEPTION: 3,
    }

    planning = models.ForeignKey(
        PlanningExecution,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Planning",
    )
    phase = models.CharField(
        max_length=32,
        choices=Phase.choices,
        verbose_name="Phase de projet",
    )
    fichier = models.FileField(
        upload_to="planning_execution/%Y/%m/",
        validators=[FileExtensionValidator(["pdf"])],
        verbose_name="PDF",
        help_text="PDF uniquement — plusieurs fichiers possibles par phase",
    )

    class Meta:
        verbose_name = "PDF planning d'exécution"
        verbose_name_plural = "PDFs planning d'exécution"
        ordering = ["phase", "-created_at"]

    def __str__(self):
        return f"{self.get_phase_display()} — {self.planning.project.code}"


class AnnexeDossier(TimeStampedModel):
    """Conteneur OneToOne — pièces jointes PDF du dossier administratif."""

    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="annexe_dossier",
        verbose_name="Projet",
    )

    class Meta:
        verbose_name = "Annexe"
        verbose_name_plural = "Annexes"

    def __str__(self):
        return f"Annexes ({self.project.code})"


class AnnexeDocument(TimeStampedModel):
    """PDF pièce jointe obligatoire du dossier administratif."""

    class Kind(models.TextChoices):
        CERTIFICAT_PROPRIETE = (
            "CERTIFICAT_PROPRIETE",
            "Certificat de propriété (ANCFCC) — Titre Foncier Mère",
        )
        PLAN_CADASTRAL = (
            "PLAN_CADASTRAL",
            "Plan Cadastral et Calque topographique (IGT)",
        )
        PLAN_ARCHITECTURE = (
            "PLAN_ARCHITECTURE",
            "Plan d'Architecture & Lotissement « Ne Varietur »",
        )
        ATTESTATIONS = (
            "ATTESTATIONS",
            "Attestations concessionnaires (Eaux, Électricité, Télécom)",
        )
        CAHIER_CHARGES = (
            "CAHIER_CHARGES",
            "Cahier des charges et PV de réception",
        )

    dossier = models.ForeignKey(
        AnnexeDossier,
        on_delete=models.CASCADE,
        related_name="documents",
        verbose_name="Dossier annexes",
    )
    kind = models.CharField(
        max_length=32,
        choices=Kind.choices,
        verbose_name="Type de pièce",
    )
    fichier = models.FileField(
        upload_to="annexes/%Y/%m/",
        validators=[FileExtensionValidator(["pdf"])],
        verbose_name="PDF",
        help_text="PDF uniquement",
    )

    class Meta:
        verbose_name = "Pièce jointe (PDF)"
        verbose_name_plural = "Pièces jointes (PDF)"
        ordering = ["kind", "-created_at"]

    def __str__(self):
        return f"{self.get_kind_display()} — {self.dossier.project.code}"
