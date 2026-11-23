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


def style_modern(request):
    if _is_login(request):
        return ""
    return static("projects/css/modern.css") + "?v=" + _v("css/modern.css")


def style_dashboard(request):
    # Global so HTMX can open fiches from changelist/search without a full reload.
    return static("projects/css/dashboard.css") + "?v=" + _v("css/dashboard.css")


def style_user_cards(request):
    # Global: SPA swaps #main only, so ModelAdmin Media CSS never loads until refresh.
    if _is_login(request):
        return ""
    return (
        static("accounts/css/user_cards.css")
        + "?v="
        + _v("css/user_cards.css", root=_ACCOUNTS_STATIC)
    )


def style_user_form(request):
    if _is_login(request):
        return ""
    return (
        static("accounts/css/user_form.css")
        + "?v="
        + _v("css/user_form.css", root=_ACCOUNTS_STATIC)
    )


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


def style_logout_dialog(request):
    if _is_login(request):
        return ""
    return (
        static("accounts/css/logout_dialog.css")
        + "?v="
        + _v("css/logout_dialog.css", root=_ACCOUNTS_STATIC)
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
