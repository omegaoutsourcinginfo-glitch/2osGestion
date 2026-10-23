from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch, Sum
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils import timezone

from .models import (
    FinancementDocument,
    Intervenant,
    PlanningDocument,
    Project,
    ProjectDocument,
    ProjectImage,
    StructureFinancement,
)


def _pct(part, total):
    return round(part / total * 100) if total else 0


def related_or_none(obj, name):
    try:
        return getattr(obj, name)
    except ObjectDoesNotExist:
        return None


def _file_kind(file_field):
    name = (file_field.name or "").lower()
    if name.endswith(".pdf"):
        return "pdf"
    if name.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
        return "image"
    return "file"


def _doc_entry(label, file_field, group):
    if not file_field:
        return None
    kind = _file_kind(file_field)
    return {
        "label": label,
        "group": group,
        "url": file_field.url,
        "name": file_field.name.rsplit("/", 1)[-1],
        "kind": kind,
        "previewable": kind in {"pdf", "image"},
    }


def collect_documents(project):
    documents = []
    for doc in project.documents.all():
        entry = _doc_entry(doc.get_kind_display(), doc.fichier, "Programme technique")
        if entry:
            documents.append(entry)

    financement = related_or_none(project, "structure_financement")
    if financement is not None:
        for doc in financement.documents.all():
            entry = _doc_entry("Document financement", doc.fichier, "Financement")
            if entry:
                documents.append(entry)

    planning = related_or_none(project, "planning_execution")
    if planning is not None:
        for doc in planning.documents.all():
            entry = _doc_entry(doc.get_phase_display(), doc.fichier, "Planning")
            if entry:
                entry["phase"] = doc.phase
                documents.append(entry)
    return documents


def planning_phases_for_display(project):
    """Always return the 3 fiche phases with their PDF lists."""
    planning = related_or_none(project, "planning_execution")
    docs_by_phase = {code: [] for code, _label in PlanningDocument.Phase.choices}
    if planning is not None:
        for doc in planning.documents.all():
            entry = _doc_entry(doc.get_phase_display(), doc.fichier, "Planning")
            if entry and doc.phase in docs_by_phase:
                docs_by_phase[doc.phase].append(entry)
    rows = []
    for code, label in PlanningDocument.Phase.choices:
        docs = docs_by_phase[code]
        rows.append(
            {
                "code": code,
                "label": label,
                "docs": docs,
                "filled": bool(docs),
            }
        )
    return rows


ANNEXES_OBLIGATOIRES = [
    "Certificat de propriété récent (ANCFCC) du Titre Foncier Mère.",
    "Plan Cadastral et Calque topographique restitué par l'IGT.",
    "Plan d'Architecture & Plan de Lotissement autorisés « Ne Varietur ».",
    "Attestations d'approbation des concessionnaires (Eaux, Électricité, Télécom).",
    "Cahier des charges du projet et PV de réception provisoire/définitive.",
]


def build_crm_project(project):
    financement = related_or_none(project, "structure_financement")
    fp_pct = cmt_pct = 0
    if financement and financement.investissement_total:
        total = float(financement.investissement_total)
        if total > 0:
            fp_pct = round(float(financement.fonds_propres_fp) / total * 100, 1)
            cmt_pct = round(float(financement.credit_moyen_terme_cmt) / total * 100, 1)

    documents = collect_documents(project)
    programme_docs = [d for d in documents if d["group"] == "Programme technique"]
    finance_docs = [d for d in documents if d["group"] == "Financement"]
    planning_docs = [d for d in documents if d["group"] == "Planning"]
    planning_phases = planning_phases_for_display(project)
    project_images = [
        {
            "url": img.image.url,
            "legende": img.legende,
            "name": img.image.name.rsplit("/", 1)[-1],
        }
        for img in project.images.all()
        if img.image
    ]
    return {
        "project": project,
        "terrain": related_or_none(project, "terrain_mere"),
        "autorisation": related_or_none(project, "autorisation"),
        "documents": documents,
        "programme_docs": programme_docs,
        "finance_docs": finance_docs,
        "planning_docs": planning_docs,
        "programme_has_docs": bool(programme_docs),
        "project_images": project_images,
        "financement": financement,
        "fp_pct": fp_pct,
        "cmt_pct": cmt_pct,
        "planning_phases": planning_phases,
        "planning_has_data": any(p["filled"] for p in planning_phases),
        "annexes_pieces": ANNEXES_OBLIGATOIRES,
        "edit_url": reverse("admin:projects_project_change", args=[project.pk]),
        "list_url": reverse("admin:projects_project_changelist"),
        "crm_url": f"{reverse('admin:index')}?projet={project.code}",
    }


def dashboard_callback(request, context):
    selected_code = (request.GET.get("projet") or request.GET.get("project") or "").strip()
    if selected_code:
        selected = (
            Project.objects.prefetch_related(
                Prefetch(
                    "intervenants",
                    queryset=Intervenant.objects.order_by("nom_ou_cabinet"),
                ),
                Prefetch(
                    "documents",
                    queryset=ProjectDocument.objects.order_by("kind", "-created_at"),
                ),
                Prefetch(
                    "images",
                    queryset=ProjectImage.objects.order_by("ordre", "-created_at"),
                ),
                Prefetch(
                    "structure_financement__documents",
                    queryset=FinancementDocument.objects.order_by("-created_at"),
                ),
                Prefetch(
                    "planning_execution__documents",
                    queryset=PlanningDocument.objects.order_by("phase", "-created_at"),
                ),
            )
            .filter(code__iexact=selected_code)
            .first()
        )
        if selected:
            context.update(
                {
                    "dash_project": build_crm_project(selected),
                    "dash_today": timezone.localdate(),
                }
            )
            return context

    projects = Project.objects.filter(is_archived=False)
    total = projects.count()
    instruction = projects.filter(statut_actuel=Project.StatutProjet.INSTRUCTION).count()
    execution = projects.filter(statut_actuel=Project.StatutProjet.EXECUTION).count()
    investissement = (
        StructureFinancement.objects.filter(project__is_archived=False).aggregate(
            total=Sum("investissement_total")
        )["total"]
        or 0
    )

    recent = []
    for project in Project.objects.filter(is_archived=False).order_by("-updated_at", "-code")[:12]:
        recent.append(
            {
                "code": project.code,
                "titre": project.titre,
                "commune": project.commune,
                "statut_actuel": project.statut_actuel,
                "statut_label": project.get_statut_actuel_display(),
                "url": f"{reverse('admin:index')}?projet={project.code}",
            }
        )

    context.update(
        {
            "dash_project": None,
            "dash_today": timezone.localdate(),
            "dash_total": total,
            "dash_instruction": instruction,
            "dash_execution": execution,
            "dash_investissement": investissement,
            "dash_recent": recent,
            "dash_pct_instruction": _pct(instruction, total),
            "dash_pct_execution": _pct(execution, total),
        }
    )
    return context


@staff_member_required
def project_detail(request, code):
    get_object_or_404(Project, code=code)
    return redirect(f"{reverse('admin:index')}?projet={code}")


