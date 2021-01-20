import os
from django.utils.translation import ugettext_lazy as _
from dotenv import load_dotenv
from celery.schedules import crontab
import api.tasks

PROJECT_DIR = os.path.dirname(__file__) 
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

SECRET_KEY = os.environ.get('DJANGO_SECRET_KEY')
FCM_APIKEY = os.environ.get('FCM_SERVER_KEY')
FCM_DEVICE_MODEL = 'api.MyDevice'
FCM_DJANGO_SETTINGS = {
        "FCM_SERVER_KEY": os.environ.get('FCM_SERVER_KEY'),
}
STRIPE_APIKEY = os.environ.get('STRIPE_SECRET_KEY')

DEBUG = os.environ.get('DEBUG')

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS').split(' ')

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.environ.get("EMAIL_HOST", "localhost")
EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
EMAIL_PORT = 587
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = 'Riko App <noreply@riko.app>'

CELERY_BROKER_URL = "redis://redis:6379"
CELERY_RESULT_BACKEND = "redis://redis:6379"
CELERY_BEAT_SCHEDULE = {
    "sample_task": {
        "task": "core.tasks.sample_task",
        "schedule": crontab(minute="*/1"),
    },
}


INSTALLED_APPS = [
    'web',
    'backend',
    'rest_framework',
    'api.apps.ApiConfig',
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'rest_framework.authtoken',
    'rest_auth',
    'fcm',
    'modeltranslation',
    'multiselectfield'
]

AUTH_USER_MODEL = 'api.User'


REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ]
}


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['./web/templates/web'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'backend.wsgi.application'


# DATABASES = {
#     'default': {
#         'ENGINE': 'django.db.backends.postgresql_psycopg2',
#         'NAME': 'riko',
#         'USER': 'nlvargas',
#         'PASSWORD': 'jumperchile12',
#         'HOST': 'localhost',
#         'PORT': '',
#     }
# }

DATABASES = {
    "default": {
        "ENGINE": os.environ.get("SQL_ENGINE"),
        "NAME": os.environ.get("SQL_DATABASE"),
        "USER": os.environ.get("SQL_USER"),
        "PASSWORD": os.environ.get("SQL_PASSWORD"),
        "HOST": os.environ.get("SQL_HOST"),
        "PORT": os.environ.get("SQL_PORT"),
    },
    # "CL": {
    #     "ENGINE": os.environ.get("SQL_ENGINE"),
    #     "NAME": os.environ.get("SQL_DATABASE_CL"),
    #     "USER": os.environ.get("SQL_USER"),
    #     "PASSWORD": os.environ.get("SQL_PASSWORD"),
    #     "HOST": os.environ.get("SQL_HOST_CL"),
    #     "PORT": os.environ.get("SQL_PORT"),
    # },
    # "FR": {
    #     "ENGINE": os.environ.get("SQL_ENGINE", "django.db.backends.postgresql_psycopg2"),
    #     "NAME": os.environ.get("SQL_DATABASE_FR"),
    #     "USER": os.environ.get("SQL_USER"),
    #     "PASSWORD": os.environ.get("SQL_PASSWORD"),
    #     "HOST": os.environ.get("SQL_HOST_FR"),
    #     "PORT": os.environ.get("SQL_PORT"),
    # }
}


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": "redis://redis:6379/0",
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        }
    }
}


AUTH_PASSWORD_VALIDATORS = [
    # {
    #     'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    # },
    # {
    #     'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    # },
]


LANGUAGE_CODE = 'es'

LANGUAGES = (
    ('en-us', _('English')),
    ('fr', _('French')),
    ('es', _('Spanish')),
)

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True



STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static/')
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media/')

STATICFILES_FINDERS = (
'django.contrib.staticfiles.finders.AppDirectoriesFinder',
'django.contrib.staticfiles.finders.FileSystemFinder',
)

STATICFILES_DIR = [
os.path.join(BASE_DIR, 'static'),
]


CORS_REPLACE_HTTPS_REFERER      = False
HOST_SCHEME                     = "http://"
# SECURE_PROXY_SSL_HEADER         = None
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_SSL_REDIRECT             = False
SESSION_COOKIE_SECURE           = False
CSRF_COOKIE_SECURE              = False
SECURE_HSTS_SECONDS             = None
SECURE_HSTS_INCLUDE_SUBDOMAINS  = False
SECURE_FRAME_DENY               = False