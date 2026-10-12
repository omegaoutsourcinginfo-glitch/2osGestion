from django.db import IntegrityError, models, transaction
from django.utils import timezone


class TimeStampedModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    commentaire = models.TextField(blank=True, verbose_name="Commentaire")

    class Meta:
        abstract = True


# Create your models here.
class Project(TimeStampedModel):
    code = models.CharField(max_length=5, unique=True, editable=False)
    perfecture=models.CharField(max_length=255)
    commune=models.CharField(max_length=255)
    titre=models.CharField(max_length=255)
    consistane_gloable=models.TextField()
    situation_localisation=models.TextField()
    voie_access=models.CharField(max_length=255)
    emprise_project=models.TextField()

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
        number = int(last.code[3:])
        number = number + 1

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
