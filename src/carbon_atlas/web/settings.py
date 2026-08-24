"""Django settings — minimal, read-only v1 API (ADR-0011).

Configuration is environment-driven with dev-only defaults; anything shared
sets the CARBON_ATLAS_* variables. The database DSN is the same one the ETL
and tests use, parsed with psycopg's own conninfo tools rather than a new
dependency.
"""

import os

from psycopg import conninfo

# Dev-only fallback; any shared deployment must set the real key. The value is
# deliberately self-describing so it can never pass as a production secret.
SECRET_KEY = os.environ.get("CARBON_ATLAS_SECRET_KEY", "dev-only-insecure-secret-key")

DEBUG = os.environ.get("CARBON_ATLAS_DEBUG", "") == "1"
ALLOWED_HOSTS = [h for h in os.environ.get("CARBON_ATLAS_ALLOWED_HOSTS", "").split(",") if h]

INSTALLED_APPS = [
    "rest_framework",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.middleware.common.CommonMiddleware",
]

ROOT_URLCONF = "carbon_atlas.web.urls"

_DSN = os.environ.get(
    "CARBON_ATLAS_DB_URL", "postgresql://carbon_atlas:carbon_atlas_dev@localhost:5434/carbon_atlas"
)
_parsed = conninfo.conninfo_to_dict(_DSN)
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": _parsed.get("dbname"),
        "USER": _parsed.get("user"),
        "PASSWORD": _parsed.get("password"),
        "HOST": _parsed.get("host"),
        "PORT": _parsed.get("port"),
    }
}

# Read-only public API: no sessions, no auth machinery until contributor
# features arrive (PROJECT_SPEC step 8) — an empty authenticator list keeps
# django.contrib.auth and its tables out of the install entirely.
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.AllowAny"],
    "UNAUTHENTICATED_USER": None,
}

USE_TZ = True
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
