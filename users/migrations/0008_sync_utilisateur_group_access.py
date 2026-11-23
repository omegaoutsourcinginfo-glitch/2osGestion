from django.db import migrations


def forwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    User = apps.get_model("users", "User")

    group, _ = Group.objects.get_or_create(name="Utilisateur")
    perms = Permission.objects.filter(
        content_type__app_label__in=["projects", "accounts"]
    )
    group.permissions.set(perms)

    for user in User.objects.all():
        user.is_staff = True
        user.is_superuser = user.kind == "SUPER_ADMIN"
        user.save(update_fields=["is_staff", "is_superuser"])
        if user.kind == "USER":
            user.groups.add(group)
        else:
            user.groups.remove(group)


def backwards(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name="Utilisateur").delete()


class Migration(migrations.Migration):

    dependencies = [
        ("users", "0007_user_kind_super_admin_and_user"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("projects", "0044_indexes_validators_amounts"),
        ("accounts", "0001_user_presence"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
