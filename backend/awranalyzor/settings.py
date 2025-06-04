"""
Oracle AWR分析器 - Django设置配置
{{CHENGQI: P2-LD-013 API接口完善和错误处理 - 集成中间件和配置 - 2025-06-03T11:00:00}}

更新配置以支持全局异常处理、限流和标准化响应
"""

import os
from pathlib import Path

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = 'django-insecure-change-this-in-production'

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    # Third party apps
    'rest_framework',
    'rest_framework.authtoken',
    'corsheaders',
    
    # Local apps
    'accounts',
    'awr_upload',
    'awr_parser',
    'performance',
    'diagnostics', 
    'reports',
    'comparisons',
    'exports',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    
    # 自定义中间件 - P2-LD-013
    'analyzer.middleware.rate_limiting.RateLimitingMiddleware',
    'analyzer.middleware.exception_handler.ExceptionHandlerMiddleware',
]

ROOT_URLCONF = 'awranalyzor.urls'

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

WSGI_APPLICATION = 'awranalyzor.wsgi.application'

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'Asia/Shanghai'

USE_I18N = True

USE_TZ = True

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Django REST Framework configuration
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework.authentication.TokenAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_FILTER_BACKENDS': [
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ],
    # P2-LD-013: 集成自定义异常处理器
    'EXCEPTION_HANDLER': 'analyzer.middleware.exception_handler.custom_drf_exception_handler',
}

# CORS configuration
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",  # React开发服务器
    "http://127.0.0.1:3000",
]

CORS_ALLOW_CREDENTIALS = True

# AWR分析器特定配置
AWR_SETTINGS = {
    'MAX_FILE_SIZE': 50 * 1024 * 1024,  # 50MB
    'ALLOWED_FILE_TYPES': ['.html', '.htm'],
    'SUPPORTED_ORACLE_VERSIONS': ['11g', '12c', '19c', '21c'],
    'PARSER_TIMEOUT': 300,  # 5分钟
    'MAX_CONCURRENT_PARSERS': 3,
}

# 文件上传配置
FILE_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024  # 10MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024

# P2-LD-013: 限流配置
RATE_LIMITS = {
    'default': {'requests': 60, 'window': 60},      # 60请求/分钟
    'upload': {'requests': 10, 'window': 300},      # 10请求/5分钟  
    'parsing': {'requests': 5, 'window': 600},      # 5请求/10分钟
    'anonymous': {'requests': 30, 'window': 60},    # 匿名用户30请求/分钟
}

# API Key限流配置（可选）
API_KEY_RATE_LIMITS = {
    'free': {'requests': 100, 'window': 3600},      # 免费版：100请求/小时
    'basic': {'requests': 1000, 'window': 3600},    # 基础版：1000请求/小时
    'premium': {'requests': 10000, 'window': 3600}, # 高级版：10000请求/小时
}

# P2-LD-013: 日志配置
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
        'json': {
            'format': '{"level": "{levelname}", "time": "{asctime}", "module": "{module}", "message": "{message}"}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'awr_analysis.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'error_file': {
            'level': 'ERROR',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'errors.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
        'performance_file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': BASE_DIR / 'logs' / 'performance.log',
            'maxBytes': 1024 * 1024 * 5,   # 5MB
            'backupCount': 3,
            'formatter': 'json',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['console', 'file'],
            'level': 'INFO',
            'propagate': True,
        },
        'awr.parser': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'awr.analyzer': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
        'awr.errors': {
            'handlers': ['error_file', 'console'],
            'level': 'WARNING',
            'propagate': False,
        },
        'awr.performance': {
            'handlers': ['performance_file'],
            'level': 'INFO',
            'propagate': False,
        },
        'analyzer.middleware': {
            'handlers': ['file', 'console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
}

# 确保日志目录存在
LOG_DIR = BASE_DIR / 'logs'
LOG_DIR.mkdir(exist_ok=True)

# 缓存配置（生产环境建议使用Redis）
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'unique-snowflake',
        'TIMEOUT': 300,  # 5分钟
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

# 会话配置
SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
SESSION_CACHE_ALIAS = 'default'
SESSION_COOKIE_AGE = 1800  # 30分钟

# 安全配置
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'

# P2-LD-013: 性能监控配置
PERFORMANCE_MONITORING = {
    'SLOW_REQUEST_THRESHOLD': 5.0,  # 慢请求阈值（秒）
    'ENABLE_DETAILED_LOGGING': DEBUG,
    'TRACK_USER_ACTIONS': True,
    'TRACK_API_USAGE': True,
}

# 开发环境特定配置
if DEBUG:
    # 开发时允许所有主机
    ALLOWED_HOSTS = ['*']
    
    # 开发时禁用某些安全检查
    SECURE_SSL_REDIRECT = False
    
    # 开发时的额外中间件
    MIDDLEWARE.insert(0, 'django.middleware.security.SecurityMiddleware')
    
    # 开发时的详细日志
    LOGGING['loggers']['django.request'] = {
        'handlers': ['console'],
        'level': 'DEBUG',
        'propagate': False,
    }
    
# 生产环境配置（待部署时启用）
# if not DEBUG:
#     SECURE_SSL_REDIRECT = True
#     SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
#     SECURE_HSTS_SECONDS = 31536000
#     SECURE_HSTS_INCLUDE_SUBDOMAINS = True
#     SECURE_HSTS_PRELOAD = True
#     
#     # 生产环境使用PostgreSQL
#     DATABASES['default'] = {
#         'ENGINE': 'django.db.backends.postgresql',
#         'NAME': os.getenv('DB_NAME', 'awranalyzor'),
#         'USER': os.getenv('DB_USER', 'postgres'),
#         'PASSWORD': os.getenv('DB_PASSWORD'),
#         'HOST': os.getenv('DB_HOST', 'localhost'),
#         'PORT': os.getenv('DB_PORT', '5432'),
#     }
#     
#     # 生产环境使用Redis缓存
#     CACHES = {
#         'default': {
#             'BACKEND': 'django.core.cache.backends.redis.RedisCache',
#             'LOCATION': os.getenv('REDIS_URL', 'redis://127.0.0.1:6379/1'),
#         }
#     } 