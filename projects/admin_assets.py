"""Conditional Unfold STYLES / SCRIPTS so list pages stay light."""

from pathlib import Path

from django.templatetags.static import static

_BASE = Path(__file__).resolve().parent.parent
_STATIC_ROOT = Path(__file__).resolve().parent / "static" / "projects"
_ACCOUNTS_STATIC = _BASE / "accounts" / "static" / "accounts"


def _path(request) -> str:
    return (getattr(request, "path", "") or "").rstrip("/") or "/"


def _v(rel: str, *, root: Path | None = None) -> str:
    """Cache-bust from file mtime so browser always gets the latest JS/CSS."""
    base = root or _STATIC_ROOT
    try:
        return str(int((base / rel).stat().st_mtime))
    except OSError:
        return "1"


def style_tailwind(request):
    """Single compiled stylesheet (npm run build:css → frontend/dist/app.css)."""
    dist = _BASE / "frontend" / "dist" / "app.css"
    try:
        ver = str(int(dist.stat().st_mtime))
    except OSError:
        ver = "1"
    return static("app.css") + "?v=" + ver


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
    # Never run SPA on the login page — HTMX swaps leave a stale CSRF token.
    if _is_login(request):
        return ""
    return static("projects/js/spa_nav.js") + "?v=" + _v("js/spa_nav.js")


def script_dropdowns(request):
    """Runs after admin form.media so Select2 is remounted once jQuery is final."""
    if _is_login(request):
        return ""
    return static("projects/js/dropdowns.js") + "?v=" + _v("js/dropdowns.js")


def script_dashboard(request):
    if _is_login(request):
        return ""
    return static("projects/js/dashboard.js") + "?v=" + _v("js/dashboard.js")


def script_search_autocomplete(request):
    if _is_login(request):
        return ""
    return static("projects/js/search_autocomplete.js") + "?v=" + _v("js/search_autocomplete.js")


def script_required_fields(request):
    if _is_login(request):
        return ""
    return static("projects/js/required_fields.js") + "?v=" + _v("js/required_fields.js")


def script_user_cards_menu(request):
    if _is_login(request):
        return ""
    return (
        static("accounts/js/user_cards_menu.js")
        + "?v="
        + _v("js/user_cards_menu.js", root=_ACCOUNTS_STATIC)
    )


def script_logout_dialog(request):
    if _is_login(request):
        return ""
    return (
        static("accounts/js/logout_dialog.js")
        + "?v="
        + _v("js/logout_dialog.js", root=_ACCOUNTS_STATIC)
    )


def script_user_form_prefixes(request):
    if _is_login(request):
        return ""
    path = _path(request)
    if "/admin/users/user" not in path:
        return ""
    return (
        static("accounts/js/user_form_prefixes.js")
        + "?v="
        + _v("js/user_form_prefixes.js", root=_ACCOUNTS_STATIC)
    )


def script_user_add_dialog(request):
    """Add-user dialog (Tailwind only). Global so SPA #main swaps still work."""
    if _is_login(request):
        return ""
    return (
        static("accounts/js/user_add_dialog.js")
        + "?v="
        + _v("js/user_add_dialog.js", root=_ACCOUNTS_STATIC)
    )
