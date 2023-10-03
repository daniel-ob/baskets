"""
Django settings for config project.

Generated by 'django-admin startproject' using Django 3.2.4.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/3.2/ref/settings/
"""

import os
from pathlib import Path

import dj_database_url
from django.core.validators import RegexValidator
from environs import Env

env = Env()
env.read_env()  # read .env file, if it exists

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/3.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool("DEBUG", default=False)

ALLOWED_HOSTS = env.str("ALLOWED_HOSTS").split(",")

# Application definition

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # 3rd party
    "allauth",
    "allauth.account",
    "django_extensions",
    "rest_framework",
    "rest_framework_simplejwt",

    # local
    "accounts",
    "baskets",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [os.path.join(BASE_DIR, "templates")],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Get Database config from env var DATABASE_URL
# example: DATABASE_URL=postgres://POSTGRES_USER:POSTGRES_PASSWORD@HOST:5432/POSTGRES_DB
# if using Docker set HOST=baskets-db
DATABASES = {"default": env.dj_db_url("DATABASE_URL")}
DATABASES["default"]["TEST"] = {"NAME": "test_baskets"}

AUTH_USER_MODEL = "accounts.CustomUser"

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

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

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

LANGUAGE_CODE = "en"

TIME_ZONE = "Europe/Paris"

USE_I18N = True

LOCALE_PATHS = [os.path.join(BASE_DIR, "locale/")]

USE_L10N = True

USE_TZ = True

FR_PHONE_REGEX = RegexValidator(
    regex=r"^"
    r"(?:(?:\+|00)33|0)"  # Dialing code
    r"\s*[1-9]"  # First number (from 1 to 9)
    r"(?:[\s.-]*\d{2}){4}"  # End of the phone number
    r"$"
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/

STATIC_URL = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, "static/")  # for django.contrib.staticfiles

LOGIN_URL = "account_login"

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=2592000)  # 30 days
SECURE_HSTS_INCLUDE_SUBDOMAINS = env.bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", default=True
)
SECURE_HSTS_PRELOAD = env.bool("SECURE_HSTS_PRELOAD", default=True)
SESSION_COOKIE_SECURE = env.bool("SESSION_COOKIE_SECURE", default=True)
CSRF_COOKIE_SECURE = env.bool("CSRF_COOKIE_SECURE", default=True)
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
# EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
DEFAULT_FROM_EMAIL = env.str("DEFAULT_FROM_EMAIL")

# SMTP server settings
EMAIL_HOST = env.str("EMAIL_HOST")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)
EMAIL_HOST_USER = env.str("EMAIL_HOST_USER")
EMAIL_HOST_PASSWORD = env.str("EMAIL_HOST_PASSWORD")
EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)

# allauth
LOGIN_REDIRECT_URL = "index"
ACCOUNT_LOGOUT_REDIRECT_URL = "account_login"
SITE_ID = 1
AUTHENTICATION_BACKENDS = (
    # Needed to log in by username in Django admin, regardless of `allauth`
    "django.contrib.auth.backends.ModelBackend",
    # `allauth` specific authentication methods, such as login by e-mail
    "allauth.account.auth_backends.AuthenticationBackend",
)
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = (
    "mandatory"  # User can't log in until email address is verified
)
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_SIGNUP_PASSWORD_ENTER_TWICE = True
ACCOUNT_SESSION_REMEMBER = True
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_FORMS = {
    "login": "accounts.forms.CustomLoginForm",
    "signup": "accounts.forms.CustomSignupForm",
    "reset_password": "accounts.forms.CustomResetPasswordForm",
    "reset_password_from_key": "accounts.forms.CustomResetPasswordKeyForm",
}
ACCOUNT_LOGOUT_ON_GET = True  # Do not ask for confirmation before logging out

# rest_framework
REST_FRAMEWORK = {
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",  # for Browsable API log in / log out
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
}
# Disable browsable API on prod
if not DEBUG:
    REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] = (
        "rest_framework.renderers.JSONRenderer",
    )
