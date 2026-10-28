"""Conditional Unfold STYLES / SCRIPTS so list pages stay light."""

from django.templatetags.static import static


def _path(request) -> str:
    return (getattr(request, "path", "") or "").rstrip("/") or "/"


def style_dashboard(request):
    # Only the admin home / project fiche need dashboard styles.
    path = _path(request)
    if path == "/admin":
        return static("projects/css/dashboard.css")
    return ""


def style_admin_form(request):
    return static("projects/css/admin_form.css")


def style_search_autocomplete(request):
    return static("projects/css/search_autocomplete.css")


def script_dashboard(request):
    path = _path(request)
    if path == "/admin":
        return static("projects/js/dashboard.js")
    return ""


def script_search_autocomplete(request):
    return static("projects/js/search_autocomplete.js")
