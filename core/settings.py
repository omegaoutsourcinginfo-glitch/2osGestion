"""
Django settings for core project (admin-only + Unfold).
"""

from pathlib import Path
from urllib.parse import urlparse

import environ
from django.core.exceptions import ImproperlyConfigured
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env(
    DJANGO_DEBUG=(bool, True),
    DJANGO_SECURE_SSL_REDIRECT=(bool, False),
    DJANGO_BEHIND_PROXY=(bool, False),
    RUN_MIGRATIONS=(bool, True),
)

# Read .env if present (never commit secrets).
environ.Env.read_env(BASE_DIR / ".env")

DEBUG = env.bool("DJANGO_DEBUG", default=True)

_secret = env("DJANGO_SECRET_KEY", default="").strip()
if _secret:
    SECRET_KEY = _secret
elif DEBUG:
    SECRET_KEY = "django-insecure-dev-only-do-not-use-in-production"
else:
    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY must be set when DJANGO_DEBUG=0."
    )

ALLOWED_HOSTS = env.list(
    "DJANGO_ALLOWED_HOSTS",
    default=["localhost", "127.0.0.1", "testserver"],
)
if DEBUG and "testserver" not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append("testserver")

CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

COMPANY_NAME = env("COMPANY_NAME", default="2os Gestion")

INSTALLED_APPS = [
    "unfold",
    "unfold.contrib.filters",
    "unfold.contrib.forms",
    "unfold.contrib.inlines",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "phonenumber_field",
    "users.apps.UsersConfig",
    "accounts.apps.AccountsConfig",
    "projects.apps.ProjectsConfig",
]

AUTH_USER_MODEL = "users.User"

AUTHENTICATION_BACKENDS = [
    "users.backends.EmailBackend",
    "django.contrib.auth.backends.ModelBackend",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "accounts.middleware.UserPresenceMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "core.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


def _database_from_url(url: str) -> dict:
    parsed = urlparse(url)
    scheme = (parsed.scheme or "").lower()
    if scheme not in {"postgres", "postgresql", "pgsql"}:
        raise ImproperlyConfigured(
            f"Unsupported DATABASE_URL scheme: {scheme or '(empty)'}"
        )
    return {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": (parsed.path or "/").lstrip("/") or "postgres",
        "USER": parsed.username or "",
        "PASSWORD": parsed.password or "",
        "HOST": parsed.hostname or "",
        "PORT": str(parsed.port or 5432),
    }


_database_url = env("DATABASE_URL", default="").strip()
_db_engine = env("DJANGO_DB_ENGINE", default="").strip().lower()
# Brief-style aliases (DB_*) + existing Docker names (POSTGRES_*)
_db_name = env("DB_NAME", default=env("POSTGRES_DB", default="2osgestion"))
_db_user = env("DB_USER", default=env("POSTGRES_USER", default="2osgestion"))
_db_password = env("DB_PASSWORD", default=env("POSTGRES_PASSWORD", default=""))
_db_host = env("DB_HOST", default=env("POSTGRES_HOST", default="localhost"))
_db_port = env("DB_PORT", default=env("POSTGRES_PORT", default="5432"))

if _database_url:
    DATABASES = {"default": _database_from_url(_database_url)}
elif _db_engine in {"postgres", "postgresql", "pgsql"} or env.bool(
    "USE_POSTGRES", default=False
):
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": _db_name,
            "USER": _db_user,
            "PASSWORD": _db_password,
            "HOST": _db_host,
            "PORT": str(_db_port),
        }
    }
else:
    _sqlite_path = env("DJANGO_SQLITE_PATH", default=str(BASE_DIR / "db.sqlite3"))
    Path(_sqlite_path).parent.mkdir(parents=True, exist_ok=True)
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": _sqlite_path,
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "fr-fr"
LANGUAGES = [
    ("fr", _("Français")),
    ("en", _("English")),
]
TIME_ZONE = "Africa/Casablanca"
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": (
            "whitenoise.storage.CompressedManifestStaticFilesStorage"
            if not DEBUG
            else "django.contrib.staticfiles.storage.StaticFilesStorage"
        ),
    },
}

UNFOLD = {
    "SITE_TITLE": COMPANY_NAME,
    "SITE_HEADER": COMPANY_NAME,
    "SITE_SUBHEADER": "Gestion des projets",
    "SITE_SYMBOL": "folder",
    "SHOW_HISTORY": True,
    "SHOW_VIEW_ON_SITE": False,
    "SHOW_BACK_BUTTON": True,
    "DASHBOARD_CALLBACK": "projects.views.dashboard_callback",
    "STYLES": [
        "projects.admin_assets.style_dashboard",
        "projects.admin_assets.style_project_info",
        "projects.admin_assets.style_login",
        "projects.admin_assets.style_select2",
        "projects.admin_assets.style_select2_admin",
        "projects.admin_assets.style_admin_form",
        "projects.admin_assets.style_search_autocomplete",
    ],
    "SCRIPTS": [
        "projects.admin_assets.script_spa_nav",
        "projects.admin_assets.script_dashboard",
        "projects.admin_assets.script_search_autocomplete",
        "projects.admin_assets.script_required_fields",
        "projects.admin_assets.script_dropdowns",
    ],
    "COLORS": {
        "primary": {
            "50": "#fdf2f4",
            "100": "#f8e9ec",
            "200": "#f0d0d7",
            "300": "#e2a8b4",
            "400": "#c96b7d",
            "500": "#a8334a",
            "600": "#8b1e2d",
            "700": "#731828",
            "800": "#5c1421",
            "900": "#41101a",
            "950": "#2a0a11",
        },
    },
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,
        "navigation": [
            {
                "title": _("Navigation"),
                "separator": True,
                "items": [
                    {
                        "title": _("Dashboard"),
                        "icon": "dashboard",
                        "link": reverse_lazy("admin:index"),
                    },
                ],
            },
            {
                "title": _("Comptes"),
                "items": [
                    {
                        "title": _("Utilisateurs"),
                        "icon": "group",
                        "link": reverse_lazy("admin:users_user_changelist"),
                        "permission": lambda request: request.user.has_perm(
                            "users.view_user"
                        ),
                    },
                ],
            },
            {
                "title": _("Projets"),
                "items": [
                    {
                        "title": _("Projets"),
                        "icon": "folder",
                        "link": reverse_lazy("admin:projects_project_changelist"),
                        "permission": lambda request: request.user.has_perm(
                            "projects.view_project"
                        ),
                    },
                    {
                        "title": _("Planning financier"),
                        "icon": "payments",
                        "link": reverse_lazy(
                            "admin:projects_structurefinancement_changelist"
                        ),
                        "permission": lambda request: request.user.has_perm(
                            "projects.view_structurefinancement"
                        ),
                    },
                    {
                        "title": _("Planning d'exécution"),
                        "icon": "calendar_month",
                        "link": reverse_lazy(
                            "admin:projects_planningexecution_changelist"
                        ),
                        "permission": lambda request: request.user.has_perm(
                            "projects.view_planningexecution"
                        ),
                    },
                    {
                        "title": _("Planning d'approvisionnement"),
                        "icon": "local_shipping",
                        "link": reverse_lazy(
                            "admin:projects_planningapprovisionnement_changelist"
                        ),
                        "permission": lambda request: request.user.has_perm(
                            "projects.view_planningapprovisionnement"
                        ),
                    },
                    {
                        "title": _("Planning matériel"),
                        "icon": "handyman",
                        "link": reverse_lazy(
                            "admin:projects_planningmateriel_changelist"
                        ),
                        "permission": lambda request: request.user.has_perm(
                            "projects.view_planningmateriel"
                        ),
                    },
                    {
                        "title": _("Matériaux"),
                        "icon": "construction",
                        "link": reverse_lazy(
                            "admin:projects_materiauxdossier_changelist"
                        ),
                        "permission": lambda request: request.user.has_perm(
                            "projects.view_materiauxdossier"
                        ),
                    },
                    {
                        "title": _("Inventaire"),
                        "icon": "inventory_2",
                        "link": reverse_lazy(
                            "admin:projects_inventairedossier_changelist"
                        ),
                        "permission": lambda request: request.user.has_perm(
                            "projects.view_inventairedossier"
                        ),
                    },
                    {
                        "title": _("Annexes"),
                        "icon": "attachment",
                        "link": reverse_lazy(
                            "admin:projects_annexedossier_changelist"
                        ),
                        "permission": lambda request: request.user.has_perm(
                            "projects.view_annexedossier"
                        ),
                    },
                ],
            },
        ],
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DATA_UPLOAD_MAX_MEMORY_SIZE = env.int(
    "DJANGO_DATA_UPLOAD_MAX_MEMORY_SIZE", default=25 * 1024 * 1024
)
FILE_UPLOAD_MAX_MEMORY_SIZE = env.int(
    "DJANGO_FILE_UPLOAD_MAX_MEMORY_SIZE", default=25 * 1024 * 1024
)
MAX_UPLOAD_SIZE = env.int("DJANGO_MAX_UPLOAD_SIZE", default=25 * 1024 * 1024)

LOGIN_REDIRECT_URL = "/admin/"
LOGOUT_REDIRECT_URL = "/admin/login/"
LOGIN_URL = "/admin/login/"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
    SECURE_SSL_REDIRECT = env.bool("DJANGO_SECURE_SSL_REDIRECT", default=False)
    _hsts = env("DJANGO_SECURE_HSTS_SECONDS", default="").strip()
    if _hsts:
        SECURE_HSTS_SECONDS = int(_hsts)
        SECURE_HSTS_INCLUDE_SUBDOMAINS = True
        SECURE_HSTS_PRELOAD = True
    if env.bool("DJANGO_BEHIND_PROXY", default=False):
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

MAILERS = {
    "default": {
        "BACKEND": "django.core.mail.backends.console.EmailBackend",
    },
}
DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default=f"noreply@{COMPANY_NAME.lower().replace(' ', '')}.local",
)

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
