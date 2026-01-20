"""
Django settings for PICK 4 Baseball Pick em' - PRODUCTION
Generated for PythonAnywhere deployment

For cheald10's PythonAnywhere account
Project: Pick4baseball
"""

from pathlib import Path
import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# ==============================================================================
# SECURITY SETTINGS
# ==============================================================================

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = '%8kmfm8(tv*67*&ai_1=f)@fl-qagjyq+rri&z3qw0lcah+l=6'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# IMPORTANT: Replace 'yourusername' with your PythonAnywhere username
ALLOWED_HOSTS = [
    'cheald10.pythonanywhere.com',
    'www.cheald10.pythonanywhere.com',
]

# Security Headers
SECURE_SSL_REDIRECT = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# HSTS (HTTP Strict Transport Security)
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True

# Additional security settings
SECURE_REFERRER_POLICY = 'same-origin'

# ==============================================================================
# APPLICATION DEFINITION
# ==============================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    # Third-party apps
    'widget_tweaks',

    # Your apps - add your actual app names here
    # 'accounts',
    # 'picks',
    # 'games',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = "Pick4baseball.Pick4baseball.urls"

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
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

WSGI_APPLICATION = 'Pick4baseball.wsgi.application'

# ==============================================================================
# DATABASE CONFIGURATION
# ==============================================================================

# IMPORTANT: Replace 'cheald10' with your PythonAnywhere username
#            Replace 'your-mysql-password' with your actual MySQL password
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.mysql',
        'NAME': 'cheald10$default',
        'USER': 'cheald10',
        'PASSWORD': 'Pick4db2025!',  # CHANGE THIS!
        'HOST': 'cheald10.mysql.pythonanywhere-services.com',
        'PORT': '3306',
        'OPTIONS': {
            'init_command': "SET sql_mode='STRICT_TRANS_TABLES'",
            'charset': 'utf8mb4',
        },
        'CONN_MAX_AGE': 600,  # Connection pooling
    }
}

# ==============================================================================
# PASSWORD VALIDATION
# ==============================================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        'OPTIONS': {
            'min_length': 8,
        }
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Password hashing
PASSWORD_HASHERS = [
    'django.contrib.auth.hashers.Argon2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2PasswordHasher',
    'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
    'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
]

# ==============================================================================
# INTERNATIONALIZATION
# ==============================================================================

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'America/New_York'  # Adjust to your timezone

USE_I18N = True

USE_TZ = True

# ==============================================================================
# STATIC FILES (CSS, JavaScript, Images)
# ==============================================================================

# IMPORTANT: Replace 'cheald10' with your PythonAnywhere username
STATIC_URL = '/static/'
STATIC_ROOT = '/home/cheald10/PythonAW/Pick4baseball/static'

STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# ==============================================================================
# MEDIA FILES (User Uploads)
# ==============================================================================

# IMPORTANT: Replace 'cheald10' with your PythonAnywhere username
MEDIA_URL = '/media/'
MEDIA_ROOT = '/home/cheald10/PythonAW/Pick4baseball/media'

# ==============================================================================
# SESSION CONFIGURATION
# ==============================================================================

SESSION_ENGINE = 'django.contrib.sessions.backends.db'
SESSION_COOKIE_AGE = 1209600  # 2 weeks in seconds
SESSION_SAVE_EVERY_REQUEST = False
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_NAME = 'pick4_sessionid'
SESSION_COOKIE_SAMESITE = 'Lax'

# ==============================================================================
# CSRF CONFIGURATION
# ==============================================================================

CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_NAME = 'pick4_csrftoken'
CSRF_COOKIE_SAMESITE = 'Lax'
CSRF_USE_SESSIONS = False
CSRF_COOKIE_SECURE = True

# ==============================================================================
# AUTHENTICATION SETTINGS
# ==============================================================================

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'

# Password reset timeout (24 hours)
PASSWORD_RESET_TIMEOUT = 86400

# ==============================================================================
# EMAIL CONFIGURATION
# ==============================================================================

# For development/testing - prints emails to console
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# For production - uncomment and configure with your email provider
# EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
# EMAIL_HOST = 'smtp.gmail.com'
# EMAIL_PORT = 587
# EMAIL_USE_TLS = True
# EMAIL_HOST_USER = 'your-email@gmail.com'
# EMAIL_HOST_PASSWORD = 'your-app-password'  # Use App Password for Gmail
# DEFAULT_FROM_EMAIL = 'PICK 4 Baseball <noreply@yourdomain.com>'
# SERVER_EMAIL = 'admin@yourdomain.com'

# ==============================================================================
# LOGGING CONFIGURATION
# ==============================================================================

# IMPORTANT: Replace 'yourusername' with your PythonAnywhere username
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        },
        'file': {
            'level': 'ERROR',
            'class': 'logging.FileHandler',
            'filename': '/home/cheald10/PythonAW/Pick4baseball/logs/error.log',
            'formatter': 'verbose',
        },
        'security_file': {
            'level': 'WARNING',
            'class': 'logging.FileHandler',
            'filename': '/home/cheald10/PythonAW/Pick4baseball/logs/security.log',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.request': {
            'handlers': ['file'],
            'level': 'ERROR',
            'propagate': False,
        },
        'django.security': {
            'handlers': ['security_file'],
            'level': 'WARNING',
            'propagate': False,
        },
    },
}

# ==============================================================================
# CACHING CONFIGURATION
# ==============================================================================

CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.db.DatabaseCache',
        'LOCATION': 'cache_table',
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
            'CULL_FREQUENCY': 3,
        }
    }
}

# ==============================================================================
# DEFAULT PRIMARY KEY FIELD TYPE
# ==============================================================================

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ==============================================================================
# CUSTOM SETTINGS FOR PICK 4 BASEBALL
# ==============================================================================

# Add your custom application settings here
# For example:
# PICKS_DEADLINE_HOURS = 1  # Hours before game start
# MAX_PICKS_PER_WEEK = 4
# POINTS_PER_CORRECT_PICK = 10

# ==============================================================================
# ADMIN CUSTOMIZATION
# ==============================================================================

ADMINS = [
    ('Admin Name', 'admin@yourdomain.com'),
]

MANAGERS = ADMINS

# ==============================================================================
# FILE UPLOAD SETTINGS
# ==============================================================================

# Maximum file upload size (10 MB)
FILE_UPLOAD_MAX_MEMORY_SIZE = 10485760

# Allowed file types for uploads
ALLOWED_UPLOAD_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.pdf']

# ==============================================================================
# SECURITY NOTES
# ==============================================================================

"""
IMPORTANT SECURITY REMINDERS:

1. Never commit this file with real passwords to version control
   - Add settings_prod.py to .gitignore
   - Use environment variables for sensitive data in production

2. Replace all 'yourusername' placeholders with your actual PythonAnywhere username

3. Replace 'your-mysql-password' with your actual MySQL database password

4. For email configuration, use App Passwords (not your regular password)
   - Gmail: https://support.google.com/accounts/answer/185833
   - Other providers: Check their documentation

5. Create the logs directory before deployment:
   mkdir -p /home/yourusername/pick4baseball/logs

6. Create the cache table after deployment:
   python manage.py createcachetable

7. Collect static files:
   python manage.py collectstatic

8. Run migrations:
   python manage.py migrate

9. Create a superuser:
   python manage.py createsuperuser

10. Test the deployment checklist:
    python manage.py check --deploy
"""
