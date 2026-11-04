from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0037_structurefinancement_cpc_excel"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="autorisation",
            options={
                "ordering": ["-date_delivrance"],
                "verbose_name": "Permis d'aménagement",
                "verbose_name_plural": "Permis d'aménagement",
            },
        ),
    ]
