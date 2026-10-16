from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import Intervenant, Project, StructureFinancement


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
    programme = related_or_none(project, "programme_technique")
    if programme:
        for label, field in [
            ("Voirie (VRD)", programme.voirie_vrd_pdf),
            ("Télécom / Fibre", programme.telecom_fibre_pdf),
            ("Aménagement paysager", programme.amenagement_paysager_pdf),
            ("Fiche lot / parcelle", programme.fiche_lot_parcelle_pdf),
        ]:
            entry = _doc_entry(label, field, "Programme technique")
            if entry:
                documents.append(entry)

    financement = related_or_none(project, "structure_financement")
    if financement and financement.document_pdf:
        entry = _doc_entry("Document financement", financement.document_pdf, "Financement")
        if entry:
            documents.append(entry)
    return documents


def build_crm_project(project):
    financement = related_or_none(project, "structure_financement")
    fp_pct = cmt_pct = 0
    if financement and financement.investissement_total:
        total = float(financement.investissement_total)
        if total > 0:
            fp_pct = round(float(financement.fonds_propres_fp) / total * 100, 1)
            cmt_pct = round(float(financement.credit_moyen_terme_cmt) / total * 100, 1)

    documents = collect_documents(project)
    return {
        "project": project,
        "terrain": related_or_none(project, "terrain_mere"),
        "autorisation": related_or_none(project, "autorisation"),
        "documents": documents,
        "programme_has_docs": any(d["group"] == "Programme technique" for d in documents),
        "financement": financement,
        "fp_pct": fp_pct,
        "cmt_pct": cmt_pct,
        "edit_url": reverse("admin:projects_project_change", args=[project.pk]),
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
                )
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

    projects = Project.objects.all()
    total = projects.count()
    instruction = projects.filter(statut_actuel=Project.StatutProjet.INSTRUCTION).count()
    execution = projects.filter(statut_actuel=Project.StatutProjet.EXECUTION).count()
    investissement = (
        StructureFinancement.objects.aggregate(total=Sum("investissement_total"))["total"] or 0
    )

    recent = []
    for project in Project.objects.order_by("-updated_at", "-code")[:12]:
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
