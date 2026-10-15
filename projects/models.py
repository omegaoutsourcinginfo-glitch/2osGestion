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
    qualite = models.CharField(max_length=150, blank=True, verbose_name="Qualité")

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
        verbose_name="Superficie totale (m² / ha)"
    )

    class Meta:
        verbose_name = "Terrain Mère"
        verbose_name_plural = "Terrains Mères"

    def __str__(self):
        return f"{self.titre_foncier_mere} ({self.project.code})"


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


def document_field(label):
    return models.FileField(
        upload_to="programme_technique/%Y/%m/",
        blank=True,
        validators=[FileExtensionValidator(DOCUMENT_EXTENSIONS)],
        verbose_name=f"Document {label}",
        help_text="PDF, image (JPG, PNG), Word (DOC, DOCX) ou AutoCAD (DWG)"
    )


class ProgrammeTechnique(TimeStampedModel):
    project = models.OneToOneField(
        Project,
        on_delete=models.CASCADE,
        related_name="programme_technique",
        verbose_name="Projet"
    )
    voirie_vrd = models.BooleanField(default=False, verbose_name="Voirie (VRD)")
    voirie_vrd_pdf = document_field("Voirie (VRD)")
    telecom_fibre_pdf = document_field("Télécom / Fibre")
    amenagement_paysager_pdf = document_field("Aménagement paysager")
    fiche_lot_parcelle_pdf = document_field("Fiche lot / parcelle")
    observations = models.TextField(blank=True, verbose_name="Observations")

    class Meta:
        verbose_name = "Programme technique & viabilisation"
        verbose_name_plural = "Programme technique & viabilisation"

    def __str__(self):
        return f"Programme technique ({self.project.code})"


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
    document_pdf = models.FileField(
        upload_to="financement/%Y/%m/",
        blank=True,
        validators=[FileExtensionValidator(["pdf"])],
        verbose_name="Document financement (PDF)",
        help_text="PDF uniquement"
    )

    class Meta:
        verbose_name = "Planning financier & structure de financement"
        verbose_name_plural = "Planning financier & structure de financement"

    def __str__(self):
        return f"Financement ({self.project.code})"

    def save(self, *args, **kwargs):
        self.investissement_total = self.fonds_propres_fp + self.credit_moyen_terme_cmt
        super().save(*args, **kwargs)
