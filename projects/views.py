# Create your views here.
from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, TypedDict, TypeVar
from urllib.parse import quote_plus

from django.contrib.admin.views.decorators import staff_member_required
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Prefetch, Q, QuerySet, Sum
from django.http import HttpRequest, HttpResponse, HttpResponseBadRequest
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone

from .models import (
    AnnexeDocument,
    AnnexeDossier,
    Autorisation,
    FinancementDocument,
    Intervenant,
    PlanningDocument,
    PlanningExecution,
    ProgrammeTechnique,
    Project,
    ProjectDocument,
    ProjectImage,
    StructureFinancement,
    TerrainMere,
)

DocT = TypeVar("DocT", bound="DocumentWithFile")
RelatedT = TypeVar("RelatedT")


class UploadedFileLike(Protocol):
    name: str
    url: str
    size: int


class DocumentWithFile(Protocol):
    fichier: UploadedFileLike | None
    created_at: datetime


class FileInfo(TypedDict, total=False):
    label: str
    group: str
    url: str
    name: str
    kind: str
    previewable: bool
    size_label: str | None
    uploaded_at: datetime | None
    phase: str
    _kind: str


class AnnexeRow(TypedDict):
    code: str
    label: str
    docs: list[FileInfo]
    filled: bool
    status: str


class AnnexeProgress(TypedDict):
    total: int
    filled: int
    pct: int
    label: str


class PlanningPhaseRow(TypedDict):
    code: str
    label: str
    docs: list[FileInfo]
    filled: bool


class PhotoInfo(TypedDict):
    url: str
    legende: str
    name: str


class SearchResult(TypedDict):
    code: str
    titre: str
    label: str
    kind: str
    kind_label: str
    url: str


SEARCH_KIND_LABELS: dict[str, str] = {
    "project": "Projet",
    "financement": "Planning financier",
    "planning": "Planning d'exécution",
    "annexe": "Annexes",
}


class RecentProject(TypedDict):
    code: str
    titre: str
    commune: str
    statut_actuel: str
    statut_label: str
    url: str


PI_TABS: list[tuple[str, str]] = [
    ("general", "Général"),
    ("localisation", "Localisation"),
    ("technique", "Technique"),
    ("intervenants", "Intervenants"),
    ("photos", "Photos"),
    ("financement", "Financement"),
    ("planning", "Planning"),
    ("fichiers", "Fichiers"),
    ("annexes", "Annexes"),
]

VALID_TABS: set[str] = {tab_id for tab_id, _label in PI_TABS}


class ProjectFiche(TypedDict):
    project: Project
    terrain: TerrainMere | None
    autorisation: Autorisation | None
    programme: ProgrammeTechnique | None
    financement: StructureFinancement | None
    fp_pct: float
    cmt_pct: float
    documents: list[FileInfo]
    programme_docs: list[FileInfo]
    finance_docs: list[FileInfo]
    planning_docs: list[FileInfo]
    programme_has_docs: bool
    project_images: list[PhotoInfo]
    planning_phases: list[PlanningPhaseRow]
    planning_has_data: bool
    annexe_rows: list[AnnexeRow]
    annexes_has_docs: bool
    annexes_progress: AnnexeProgress
    annexes_edit_url: str
    planning_edit_url: str
    maps_url: str | None
    edit_url: str
    list_url: str
    crm_url: str
    active_tab: str
    pi_tabs: list[tuple[str, str]]


class DashboardData(TypedDict):
    dash_project: ProjectFiche | None
    dash_today: date
    dash_total: int
    dash_instruction: int
    dash_execution: int
    dash_investissement: Decimal | int
    dash_recent: list[RecentProject]
    dash_pct_instruction: int
    dash_pct_execution: int


def _typed_list(items: Iterable[RelatedT], item_type: type[RelatedT]) -> list[RelatedT]:
    """Build a typed list (avoids list[Any] from Django QuerySet without stubs)."""
    result: list[RelatedT] = []
    for item in items:
        if isinstance(item, item_type):
            result.append(item)
    return result


def _project_documents(project: Project) -> list[ProjectDocument]:
    return _typed_list(project.documents.all(), ProjectDocument)


def _financement_documents(financement: StructureFinancement) -> list[FinancementDocument]:
    return _typed_list(financement.documents.all(), FinancementDocument)


def _planning_documents(planning: PlanningExecution) -> list[PlanningDocument]:
    return _typed_list(planning.documents.all(), PlanningDocument)


def _annexe_documents(dossier: AnnexeDossier) -> list[AnnexeDocument]:
    return _typed_list(dossier.documents.all(), AnnexeDocument)


def _project_images(project: Project) -> list[ProjectImage]:
    return _typed_list(project.images.all(), ProjectImage)


def _project_document_label(document: ProjectDocument) -> str:
    return document.get_kind_display()


def _planning_document_label(document: PlanningDocument) -> str:
    return document.get_phase_display()


def _annexe_document_label(document: AnnexeDocument) -> str:
    return document.get_kind_display()


def _add_planning_phase(info: FileInfo, document: PlanningDocument) -> None:
    info["phase"] = document.phase


def _add_annexe_kind(info: FileInfo, document: AnnexeDocument) -> None:
    info["_kind"] = document.kind


class FileHelper:
    @staticmethod
    def percent(part: float | int, total: float | int) -> int:
        if not total:
            return 0
        return round(part / total * 100)

    @staticmethod
    def get_related(
        project: Project,
        relation_name: str,
        related_type: type[RelatedT],
    ) -> RelatedT | None:
        try:
            related = getattr(project, relation_name)
        except ObjectDoesNotExist:
            return None
        if isinstance(related, related_type):
            return related
        return None

    @staticmethod
    def file_type(file_field: UploadedFileLike) -> str:
        name = (file_field.name or "").lower()
        if name.endswith(".pdf"):
            return "pdf"
        if name.endswith((".jpg", ".jpeg", ".png", ".gif", ".webp")):
            return "image"
        return "file"

    @staticmethod
    def file_size_text(num_bytes: float | int | None) -> str | None:
        if num_bytes is None:
            return None
        try:
            size = float(num_bytes)
        except (TypeError, ValueError):
            return None
        if size < 1024:
            return f"{int(size)} B"
        if size < 1024 * 1024:
            return f"{size / 1024:.1f} KB"
        return f"{size / (1024 * 1024):.1f} MB"

    @classmethod
    def make_file_info(
        cls,
        label: str,
        file_field: UploadedFileLike | None,
        group: str,
        uploaded_at: datetime | None = None,
    ) -> FileInfo | None:
        if not file_field:
            return None

        kind = cls.file_type(file_field)
        try:
            size_bytes: int | None = file_field.size
        except Exception:
            size_bytes = None

        file_name = file_field.name.rsplit("/", 1)[-1]
        return {
            "label": label,
            "group": group,
            "url": file_field.url,
            "name": file_name,
            "kind": kind,
            "previewable": kind in {"pdf", "image"},
            "size_label": cls.file_size_text(size_bytes),
            "uploaded_at": uploaded_at,
        }

    @classmethod
    def list_uploaded_files(
        cls,
        document_list: Iterable[DocT] | None,
        group: str,
        label: str | None = None,
        get_label: Callable[[DocT], str] | None = None,
        add_extra: Callable[[FileInfo, DocT], None] | None = None,
    ) -> list[FileInfo]:
        result: list[FileInfo] = []
        if not document_list:
            return result

        for document in document_list:
            if get_label is not None:
                file_label = get_label(document)
            else:
                file_label = label or ""

            info = cls.make_file_info(
                label=file_label,
                file_field=document.fichier,
                group=group,
                uploaded_at=document.created_at,
            )
            if not info:
                continue

            if add_extra is not None:
                add_extra(info, document)

            result.append(info)

        return result


# Project ViewSet
class ProjectViewSet:
    queryset: QuerySet[Project] = Project.objects.all()
    ordering_fields: list[str] = ["-updated_at", "-code"]
    search_fields: list[str] = ["titre", "code"]

    def get_queryset(self) -> QuerySet[Project]:
        return self.queryset.prefetch_related(
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
            Prefetch(
                "annexe_dossier__documents",
                queryset=AnnexeDocument.objects.order_by("kind", "-created_at"),
            ),
        )

    def get_object(self, code: str) -> Project | None:
        return self.get_queryset().filter(code__iexact=code).first()

    def retrieve(self, project: Project) -> ProjectFiche:
        financement = self._get_financement(project)
        fp_pct, cmt_pct = self.finance_percents(financement)

        all_docs = self.documents(project)
        programme_docs = [d for d in all_docs if d["group"] == "Programme technique"]
        finance_docs = [d for d in all_docs if d["group"] == "Financement"]
        planning_docs = [d for d in all_docs if d["group"] == "Planning"]

        planning_phases = self.planning_phases(project)
        annexe_rows = self.annexe_rows(project)

        planning_has_data = False
        for phase in planning_phases:
            if phase["filled"]:
                planning_has_data = True
                break

        annexes_has_docs = False
        for row in annexe_rows:
            if row["filled"]:
                annexes_has_docs = True
                break

        return {
            "project": project,
            "terrain": self._get_terrain(project),
            "autorisation": self._get_autorisation(project),
            "programme": self._get_programme(project),
            "financement": financement,
            "fp_pct": fp_pct,
            "cmt_pct": cmt_pct,
            "documents": all_docs,
            "programme_docs": programme_docs,
            "finance_docs": finance_docs,
            "planning_docs": planning_docs,
            "programme_has_docs": len(programme_docs) > 0,
            "project_images": self.photos(project),
            "planning_phases": planning_phases,
            "planning_has_data": planning_has_data,
            "annexe_rows": annexe_rows,
            "annexes_has_docs": annexes_has_docs,
            "annexes_progress": self.annexe_progress(annexe_rows),
            "annexes_edit_url": self.annexe_edit_link(project),
            "planning_edit_url": self.planning_edit_link(project),
            "maps_url": self.google_maps_link(project),
            "edit_url": reverse("admin:projects_project_change", args=[project.pk]),
            "list_url": reverse("admin:index"),
            "crm_url": f"{reverse('admin:index')}?projet={project.code}",
            "active_tab": "general",
            "pi_tabs": PI_TABS,
        }

    def _get_terrain(self, project: Project) -> TerrainMere | None:
        return FileHelper.get_related(project, "terrain_mere", TerrainMere)

    def _get_autorisation(self, project: Project) -> Autorisation | None:
        return FileHelper.get_related(project, "autorisation", Autorisation)

    def _get_programme(self, project: Project) -> ProgrammeTechnique | None:
        return FileHelper.get_related(project, "programme_technique", ProgrammeTechnique)

    def _get_financement(self, project: Project) -> StructureFinancement | None:
        return FileHelper.get_related(project, "structure_financement", StructureFinancement)

    def _get_planning(self, project: Project) -> PlanningExecution | None:
        return FileHelper.get_related(project, "planning_execution", PlanningExecution)

    def _get_annexe_dossier(self, project: Project) -> AnnexeDossier | None:
        return FileHelper.get_related(project, "annexe_dossier", AnnexeDossier)

    def documents(self, project: Project) -> list[FileInfo]:
        documents: list[FileInfo] = []

        documents += FileHelper.list_uploaded_files(
            document_list=_project_documents(project),
            group="Programme technique",
            get_label=_project_document_label,
        )

        financement = self._get_financement(project)
        if financement is not None:
            documents += FileHelper.list_uploaded_files(
                document_list=_financement_documents(financement),
                group="Financement",
                label="Document financement",
            )

        planning = self._get_planning(project)
        if planning is not None:
            documents += FileHelper.list_uploaded_files(
                document_list=_planning_documents(planning),
                group="Planning",
                get_label=_planning_document_label,
                add_extra=_add_planning_phase,
            )

        for row in self.annexe_rows(project):
            documents += row["docs"]

        return documents

    def annexe_rows(self, project: Project) -> list[AnnexeRow]:
        dossier = self._get_annexe_dossier(project)

        files_by_kind: dict[str, list[FileInfo]] = {}
        for code, label in AnnexeDocument.Kind.choices:
            files_by_kind[str(code)] = []

        uploaded: list[FileInfo] = []
        if dossier is not None:
            uploaded = FileHelper.list_uploaded_files(
                document_list=_annexe_documents(dossier),
                group="Annexes",
                get_label=_annexe_document_label,
                add_extra=_add_annexe_kind,
            )

        for info in uploaded:
            kind_code = info.pop("_kind", None)
            if kind_code in files_by_kind:
                files_by_kind[kind_code].append(info)

        rows: list[AnnexeRow] = []
        for code, label in AnnexeDocument.Kind.choices:
            kind_code = str(code)
            files = files_by_kind[kind_code]
            has_file = len(files) > 0
            rows.append(
                {
                    "code": kind_code,
                    "label": str(label),
                    "docs": files,
                    "filled": has_file,
                    "status": "Fourni" if has_file else "En attente",
                }
            )
        return rows

    def annexe_progress(self, rows: list[AnnexeRow]) -> AnnexeProgress:
        total = len(rows)
        filled = 0
        for row in rows:
            if row["filled"]:
                filled += 1

        pct = FileHelper.percent(filled, total)
        return {
            "total": total,
            "filled": filled,
            "pct": pct,
            "label": f"{filled}/{total} documents fournis ({pct}%)",
        }

    def annexe_edit_link(self, project: Project) -> str:
        dossier = self._get_annexe_dossier(project)
        if dossier is not None:
            return reverse("admin:projects_annexedossier_change", args=[dossier.pk])
        add_url = reverse("admin:projects_annexedossier_add")
        return f"{add_url}?project={project.pk}"

    def planning_edit_link(self, project: Project) -> str:
        planning = self._get_planning(project)
        if planning is not None:
            return reverse("admin:projects_planningexecution_change", args=[planning.pk])
        add_url = reverse("admin:projects_planningexecution_add")
        return f"{add_url}?project={project.pk}"

    def google_maps_link(self, project: Project) -> str | None:
        parts: list[str] = []
        for value in (
            project.situation_localisation,
            project.commune,
            project.prefecture,
            "Maroc",
        ):
            text = (value or "").strip()
            if text:
                parts.append(text)

        if not parts:
            return None

        query = ", ".join(parts)
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(query)}"

    def planning_phases(self, project: Project) -> list[PlanningPhaseRow]:
        planning = self._get_planning(project)

        files_by_phase: dict[str, list[FileInfo]] = {}
        for code, label in PlanningDocument.Phase.choices:
            files_by_phase[str(code)] = []

        uploaded: list[FileInfo] = []
        if planning is not None:
            uploaded = FileHelper.list_uploaded_files(
                document_list=_planning_documents(planning),
                group="Planning",
                get_label=_planning_document_label,
                add_extra=_add_planning_phase,
            )

        for info in uploaded:
            phase_code = info.get("phase")
            if phase_code in files_by_phase:
                files_by_phase[phase_code].append(info)

        rows: list[PlanningPhaseRow] = []
        for code, label in PlanningDocument.Phase.choices:
            phase_code = str(code)
            files = files_by_phase[phase_code]
            rows.append(
                {
                    "code": phase_code,
                    "label": str(label),
                    "docs": files,
                    "filled": len(files) > 0,
                }
            )
        return rows

    def photos(self, project: Project) -> list[PhotoInfo]:
        photos: list[PhotoInfo] = []
        image_list = _project_images(project)
        if not image_list:
            return photos

        for image in image_list:
            if not image.image:
                continue
            photos.append(
                {
                    "url": image.image.url,
                    "legende": image.legende,
                    "name": image.image.name.rsplit("/", 1)[-1],
                }
            )
        return photos

    def finance_percents(
        self,
        financement: StructureFinancement | None,
    ) -> tuple[float, float]:
        if financement is None:
            return 0.0, 0.0

        total = float(financement.investissement_total or 0)
        if total <= 0:
            return 0.0, 0.0

        fp = round(float(financement.fonds_propres_fp) / total * 100, 1)
        cmt = round(float(financement.credit_moyen_terme_cmt) / total * 100, 1)
        return fp, cmt

    def search(self, q: str = "") -> list[SearchResult]:
        """Project-only search (dashboard recent filter)."""
        projects = Project.objects.filter(is_archived=False).order_by("-code")
        if q:
            projects = projects.filter(Q(titre__icontains=q) | Q(code__icontains=q))

        results: list[SearchResult] = []
        for project in projects[:12]:
            results.append(
                {
                    "code": project.code,
                    "titre": project.titre,
                    "label": f"{project.code} — {project.titre}",
                    "kind": "project",
                    "kind_label": SEARCH_KIND_LABELS["project"],
                    "url": f"{reverse('admin:index')}?projet={project.code}",
                }
            )
        return results


def global_admin_search(q: str = "", per_kind: int = 4) -> list[SearchResult]:
    """Search Projets + Planning financier + Planning d'exécution + Annexes."""
    q = (q or "").strip()
    if not q:
        return []

    project_q = Q(titre__icontains=q) | Q(code__icontains=q)
    related_q = Q(project__titre__icontains=q) | Q(project__code__icontains=q)
    results: list[SearchResult] = []

    for project in (
        Project.objects.filter(is_archived=False)
        .filter(project_q)
        .order_by("-code")[:per_kind]
    ):
        results.append(
            {
                "code": project.code,
                "titre": project.titre,
                "label": f"{project.code} — {project.titre}",
                "kind": "project",
                "kind_label": SEARCH_KIND_LABELS["project"],
                "url": project.get_absolute_url(),
            }
        )

    for obj in (
        StructureFinancement.objects.filter(project__is_archived=False)
        .filter(related_q)
        .select_related("project")
        .order_by("-project__code")[:per_kind]
    ):
        results.append(
            {
                "code": obj.project.code,
                "titre": obj.project.titre,
                "label": f"{obj.project.code} — {obj.project.titre}",
                "kind": "financement",
                "kind_label": SEARCH_KIND_LABELS["financement"],
                "url": f"{obj.project.get_absolute_url()}#financement",
            }
        )

    for obj in (
        PlanningExecution.objects.filter(project__is_archived=False)
        .filter(related_q)
        .select_related("project")
        .order_by("-project__code")[:per_kind]
    ):
        results.append(
            {
                "code": obj.project.code,
                "titre": obj.project.titre,
                "label": f"{obj.project.code} — {obj.project.titre}",
                "kind": "planning",
                "kind_label": SEARCH_KIND_LABELS["planning"],
                "url": f"{obj.project.get_absolute_url()}#planning",
            }
        )

    for obj in (
        AnnexeDossier.objects.filter(project__is_archived=False)
        .filter(related_q)
        .select_related("project")
        .order_by("-project__code")[:per_kind]
    ):
        results.append(
            {
                "code": obj.project.code,
                "titre": obj.project.titre,
                "label": f"{obj.project.code} — {obj.project.titre}",
                "kind": "annexe",
                "kind_label": SEARCH_KIND_LABELS["annexe"],
                "url": f"{obj.project.get_absolute_url()}#annexes",
            }
        )

    return results


# Dashboard ViewSet
class DashboardViewSet:
    queryset: QuerySet[Project] = Project.objects.filter(is_archived=False)
    ordering_fields: list[str] = ["-updated_at", "-code"]

    def get_queryset(self) -> QuerySet[Project]:
        return self.queryset.all()

    def list(self) -> DashboardData:
        active_projects = self.get_queryset()

        total = active_projects.count()
        instruction = active_projects.filter(
            statut_actuel=Project.StatutProjet.INSTRUCTION
        ).count()
        execution = active_projects.filter(
            statut_actuel=Project.StatutProjet.EXECUTION
        ).count()

        investissement = (
            StructureFinancement.objects.filter(project__is_archived=False).aggregate(
                total=Sum("investissement_total")
            )["total"]
            or 0
        )

        recent: list[RecentProject] = []
        latest = active_projects.order_by("-updated_at", "-code")[:12]
        for project in latest:
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

        return {
            "dash_project": None,
            "dash_today": timezone.localdate(),
            "dash_total": total,
            "dash_instruction": instruction,
            "dash_execution": execution,
            "dash_investissement": investissement,
            "dash_recent": recent,
            "dash_pct_instruction": FileHelper.percent(instruction, total),
            "dash_pct_execution": FileHelper.percent(execution, total),
        }


def dashboard_callback(request: HttpRequest, context: DashboardData) -> DashboardData:
    selected_code = (
        request.GET.get("projet") or request.GET.get("project") or ""
    ).strip()

    if selected_code:
        project_view = ProjectViewSet()
        selected = project_view.get_object(selected_code)
        if selected:
            context["dash_project"] = project_view.retrieve(selected)
            context["dash_today"] = timezone.localdate()
            return context

    home = DashboardViewSet().list()
    context.update(home)
    return context


def _with_active_tab(fiche: ProjectFiche, active_tab: str) -> ProjectFiche:
    tab = active_tab if active_tab in VALID_TABS else "general"
    updated: ProjectFiche = dict(fiche)
    updated["active_tab"] = tab
    updated["pi_tabs"] = PI_TABS
    return updated


@staff_member_required
def project_detail(request: HttpRequest, code: str) -> HttpResponse:
    get_object_or_404(Project, code=code)
    admin_home = reverse("admin:index")
    return redirect(f"{admin_home}?projet={code}")


@staff_member_required
def project_search_autocomplete(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    results = global_admin_search(q) if q else []
    return render(
        request,
        "projects/partials/search_autocomplete_results.html",
        {"results": results, "q": q},
    )


@staff_member_required
def dashboard_home(request: HttpRequest) -> HttpResponse:
    return render(
        request,
        "projects/partials/dashboard_home.html",
        DashboardViewSet().list(),
    )


@staff_member_required
def dashboard_recent(request: HttpRequest) -> HttpResponse:
    q = (request.GET.get("q") or "").strip()
    if q:
        matches = ProjectViewSet().search(q)
        recent: list[RecentProject] = []
        for item in matches:
            project = Project.objects.filter(code=item["code"]).first()
            if project is None:
                continue
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
    else:
        recent = DashboardViewSet().list()["dash_recent"]
    return render(
        request,
        "projects/partials/dashboard_recent_list.html",
        {"dash_recent": recent, "q": q},
    )


@staff_member_required
def project_fiche(request: HttpRequest, code: str) -> HttpResponse:
    project_view = ProjectViewSet()
    selected = project_view.get_object(code)
    if selected is None:
        return HttpResponseBadRequest("Projet introuvable")
    fiche = _with_active_tab(project_view.retrieve(selected), "general")
    return render(request, "projects/partials/project_fiche_root.html", fiche)


@staff_member_required
def project_tab(request: HttpRequest, code: str, tab: str) -> HttpResponse:
    if tab not in VALID_TABS:
        return HttpResponseBadRequest("Onglet invalide")
    project_view = ProjectViewSet()
    selected = project_view.get_object(code)
    if selected is None:
        return HttpResponseBadRequest("Projet introuvable")
    fiche = _with_active_tab(project_view.retrieve(selected), tab)
    return render(
        request,
        "projects/partials/project_tab_content.html",
        {**fiche, "tab": tab},
    )
