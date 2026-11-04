from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0038_autorisation_permis_amenagement_label"),
    ]

    operations = [
        migrations.AddField(
            model_name="autorisation",
            name="precision_autre",
            field=models.CharField(
                blank=True,
                help_text="Obligatoire lorsque le type est « Autre ».",
                max_length=255,
                verbose_name="Si Autre, préciser",
            ),
        ),
        migrations.AddField(
            model_name="intervenant",
            name="precision_autre",
            field=models.CharField(
                blank=True,
                help_text="Obligatoire lorsque le type est « Autre ».",
                max_length=255,
                verbose_name="Si Autre, préciser",
            ),
        ),
    ]
