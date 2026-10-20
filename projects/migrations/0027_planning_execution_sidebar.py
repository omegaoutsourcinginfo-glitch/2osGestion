import django.db.models.deletion
from django.db import migrations, models


def forwards_move_phases_to_planning(apps, schema_editor):
    PhaseExecution = apps.get_model("projects", "PhaseExecution")
    PlanningExecution = apps.get_model("projects", "PlanningExecution")

    project_ids = (
        PhaseExecution.objects.exclude(project_id__isnull=True)
        .values_list("project_id", flat=True)
        .distinct()
    )
    for project_id in project_ids:
        planning, _ = PlanningExecution.objects.get_or_create(project_id=project_id)
        PhaseExecution.objects.filter(project_id=project_id).update(planning_id=planning.pk)


def noop_reverse(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("projects", "0026_planning_execution"),
    ]

    operations = [
        migrations.CreateModel(
            name="PlanningExecution",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "project",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="planning_execution",
                        to="projects.project",
                        verbose_name="Projet",
                    ),
                ),
            ],
            options={
                "verbose_name": "Planning d'exécution du projet",
                "verbose_name_plural": "Planning d'exécution du projet",
            },
        ),
        migrations.AddField(
            model_name="phaseexecution",
            name="planning",
            field=models.ForeignKey(
                null=True,
                blank=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="phases",
                to="projects.planningexecution",
                verbose_name="Planning",
            ),
        ),
        migrations.RunPython(forwards_move_phases_to_planning, noop_reverse),
        migrations.RemoveConstraint(
            model_name="phaseexecution",
            name="uniq_phase_execution_project_phase",
        ),
        migrations.RemoveField(
            model_name="phaseexecution",
            name="project",
        ),
        migrations.AlterField(
            model_name="phaseexecution",
            name="planning",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="phases",
                to="projects.planningexecution",
                verbose_name="Planning",
            ),
        ),
        migrations.AddConstraint(
            model_name="phaseexecution",
            constraint=models.UniqueConstraint(
                fields=("planning", "phase"),
                name="uniq_phase_execution_planning_phase",
            ),
        ),
        migrations.AlterModelOptions(
            name="phaseexecution",
            options={
                "ordering": ["ordre", "phase"],
                "verbose_name": "Phase d'exécution",
                "verbose_name_plural": "Phases d'exécution",
            },
        ),
    ]
