"""Core HTTP helpers (protected media serving)."""

from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib.admin.views.decorators import staff_member_required
from django.http import FileResponse, Http404, HttpRequest, HttpResponse
from django.views.decorators.http import require_GET


@staff_member_required
@require_GET
def protected_media(request: HttpRequest, path: str) -> HttpResponse:
    """
    Serve uploaded files only to authenticated staff.

    Replaces the public DEBUG-only django.conf.urls.static.static() mount so
    certificates, CPC workbooks and plans are not world-readable by URL.
    """
    if not path or path.startswith("/") or "\\" in path:
        raise Http404("Fichier introuvable.")

    media_root = Path(settings.MEDIA_ROOT).resolve()
    try:
        full_path = (media_root / path).resolve(strict=False)
    except OSError as exc:
        raise Http404("Fichier introuvable.") from exc

    try:
        full_path.relative_to(media_root)
    except ValueError as exc:
        raise Http404("Fichier introuvable.") from exc
    if not full_path.is_file():
        raise Http404("Fichier introuvable.")

    return FileResponse(full_path.open("rb"), as_attachment=False, filename=full_path.name)
