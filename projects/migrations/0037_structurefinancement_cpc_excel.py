# Adds CPC Excel upload on StructureFinancement so Total investissement
# can be filled from CPC ligne IV (II + III1…III6).
import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0036_image_legende_titre"),
    ]

    operations = [
        migrations.AddField(
            model_name="structurefinancement",
            name="cpc_excel",
            field=models.FileField(
                blank=True,
                help_text=(
                    "Importer le Compte des Produits et Charges (.xlsx). "
                    "Le Total investissement (IV) est lu automatiquement."
                ),
                upload_to="cpc/%Y/%m/",
                validators=[
                    django.core.validators.FileExtensionValidator(["xlsx"])
                ],
                verbose_name="CPC Excel",
            ),
        ),
        migrations.AlterField(
            model_name="structurefinancement",
            name="investissement_total",
            field=models.DecimalField(
                decimal_places=2,
                default=0,
                editable=False,
                help_text="Issu de la ligne IV du CPC Excel (II + III1…III6).",
                max_digits=16,
                verbose_name="Total investissement (DH)",
            ),
        ),
    ]
