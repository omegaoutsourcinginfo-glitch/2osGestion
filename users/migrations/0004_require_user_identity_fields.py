from django.db import migrations, models

import core.custom_phone_number_field


def fill_required_identity(apps, schema_editor):
    User = apps.get_model("users", "User")
    for user in User.objects.all():
        changed = False
        if not (user.first_name or "").strip():
            user.first_name = "—"
            changed = True
        if not (user.last_name or "").strip():
            user.last_name = "—"
            changed = True
        if not user.phone:
            # Unique placeholder per user until edited in admin.
            user.phone = f"+212600{user.pk:06d}"
            changed = True
        if changed:
            user.save(update_fields=["first_name", "last_name", "phone"])


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0003_remove_user_kind_other"),
    ]

    operations = [
        migrations.RunPython(fill_required_identity, noop_reverse),
        migrations.AlterField(
            model_name="user",
            name="first_name",
            field=models.CharField(max_length=150, verbose_name="first name"),
        ),
        migrations.AlterField(
            model_name="user",
            name="last_name",
            field=models.CharField(max_length=150, verbose_name="last name"),
        ),
        migrations.AlterField(
            model_name="user",
            name="phone",
            field=core.custom_phone_number_field.CustomPhoneNumberField(
                region=None,
                unique=True,
            ),
        ),
    ]
