# Generated manually — roles: Super Admin + Utilisateur only.

from django.db import migrations, models


def forwards_admin_to_user(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(kind="ADMIN").update(kind="USER")
    User.objects.filter(kind="OTHER").update(kind="USER")


def backwards_user_to_admin(apps, schema_editor):
    User = apps.get_model("users", "User")
    User.objects.filter(kind="USER").update(kind="ADMIN")


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0006_user_french_verbose_names"),
    ]

    operations = [
        migrations.RunPython(forwards_admin_to_user, backwards_user_to_admin),
        migrations.AlterField(
            model_name="user",
            name="kind",
            field=models.CharField(
                choices=[
                    ("SUPER_ADMIN", "Super Admin"),
                    ("USER", "Utilisateur"),
                ],
                default="USER",
                max_length=255,
                verbose_name="Rôle",
            ),
        ),
    ]
