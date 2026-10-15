from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0007_remove_autorisation_commentaire_and_more'),
    ]

    operations = [
        migrations.RenameField('project', 'perfecture', 'prefecture'),
        migrations.RenameField('project', 'consistane_gloable', 'consistance_globale'),
        migrations.RenameField('project', 'voie_access', 'voie_acces'),
        migrations.RenameField('project', 'emprise_project', 'emprise_servitudes'),
    ]
