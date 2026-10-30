"""Conditional Unfold STYLES / SCRIPTS so list pages stay light."""

from pathlib import Path

from django.templatetags.static import static

_STATIC_ROOT = Path(__file__).resolve().parent / "static" / "projects"


def _path(request) -> str:
    return (getattr(request, "path", "") or "").rstrip("/") or "/"


def _v(rel: str) -> str:
    """Cache-bust from file mtime so browser always gets the latest JS/CSS."""
    try:
        return str(int((_STATIC_ROOT / rel).stat().st_mtime))
    except OSError:
        return "1"


def style_dashboard(request):
    # Global so HTMX can open fiches from changelist/search without a full reload.
    return static("projects/css/dashboard.css") + "?v=" + _v("css/dashboard.css")


def style_project_info(request):
    return static("projects/css/project_info.css") + "?v=" + _v("css/project_info.css")


def style_login(request):
    path = _path(request)
    if path == "/admin/login":
        return static("projects/css/login.css") + "?v=" + _v("css/login.css")
    return ""


def style_admin_form(request):
    return static("projects/css/admin_form.css") + "?v=" + _v("css/admin_form.css")


def style_search_autocomplete(request):
    return static("projects/css/search_autocomplete.css") + "?v=" + _v("css/search_autocomplete.css")


def _is_login(request) -> bool:
    return _path(request) == "/admin/login"


def style_select2(request):
    """Select2 base CSS so every admin dropdown can use the Intervenants look."""
    if _is_login(request):
        return ""
    return static("admin/css/vendor/select2/select2.css")


def style_select2_admin(request):
    if _is_login(request):
        return ""
    return static("admin/css/autocomplete.css")


def script_spa_nav(request):
    return static("projects/js/spa_nav.js") + "?v=" + _v("js/spa_nav.js")


def script_dropdowns(request):
    """Runs after admin form.media so Select2 is remounted once jQuery is final."""
    if _is_login(request):
        return ""
    return static("projects/js/dropdowns.js") + "?v=" + _v("js/dropdowns.js")


def script_dashboard(request):
    return static("projects/js/dashboard.js") + "?v=" + _v("js/dashboard.js")


def script_search_autocomplete(request):
    return static("projects/js/search_autocomplete.js") + "?v=" + _v("js/search_autocomplete.js")


def script_required_fields(request):
    return static("projects/js/required_fields.js") + "?v=" + _v("js/required_fields.js")
