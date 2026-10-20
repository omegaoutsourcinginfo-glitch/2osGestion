# Generated manually for planning PDFs by phase (no dates)

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0031_planning_pdf_labels"),
    ]

    operations = [
        migrations.AddField(
            model_name="planningdocument",
            name="phase",
            field=models.CharField(
                choices=[
                    ("ETUDES", "Études techniques, géotechniques & Permis"),
                    ("VIABILISATION", "Travaux de Viabilisation (VRD & Réseaux)"),
                    ("RECEPTION", "Réception provisoire & Titres fonciers individuels"),
                ],
                default="ETUDES",
                max_length=32,
                verbose_name="Phase de projet",
            ),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name="planningdocument",
            name="fichier",
            field=models.FileField(
                help_text="PDF uniquement — plusieurs fichiers possibles par phase",
                upload_to="planning_execution/%Y/%m/",
                validators=[django.core.validators.FileExtensionValidator(["pdf"])],
                verbose_name="PDF",
            ),
        ),
        migrations.AlterModelOptions(
            name="planningdocument",
            options={
                "ordering": ["phase", "-created_at"],
                "verbose_name": "PDF planning d'exécution",
                "verbose_name_plural": "PDFs planning d'exécution",
            },
        ),
        migrations.DeleteModel(
            name="PhaseExecution",
        ),
    ]
