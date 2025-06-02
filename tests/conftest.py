"""
Oracle AWR分析器 - pytest配置文件
{{CHENGQI: P1-TE-004 基础测试框架配置 - 2025-06-01 23:45:00 +08:00}}

这个文件包含了所有测试共享的fixture和配置
"""
import os
import sys
import pytest
from django.conf import settings
from django.contrib.auth.models import User
from django.test import Client
from django.core.management import call_command


# 确保Django项目在Python路径中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope='session')
def django_db_setup():
    """
    数据库配置fixture
    确保测试使用独立的数据库配置
    """
    settings.DATABASES['default'] = {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': ':memory:',
        'TEST': {
            'NAME': ':memory:',
        },
    }


# 为E2E测试禁用自动数据库访问
def pytest_collection_modifyitems(config, items):
    """
    修改测试项目，为E2E测试添加特殊标记
    """
    for item in items:
        # 如果是E2E测试且没有明确标记django_db，则添加no_db标记
        if "e2e" in item.keywords and "django_db" not in item.keywords:
            item.add_marker(pytest.mark.no_db)


@pytest.fixture(autouse=True)
def enable_db_access_for_all_tests(request):
    """
    自动为所有测试启用数据库访问，除了标记为no_db的测试
    """
    if "no_db" in request.keywords:
        # 跳过数据库设置
        return
    # 其他测试正常使用数据库
    from django.test import TransactionTestCase
    if hasattr(request, 'instance') and isinstance(request.instance, TransactionTestCase):
        request.instance._pre_setup()


@pytest.fixture(autouse=True) 
def clear_cache_and_mail():
    """
    每个测试前清理缓存和邮件
    """
    from django.core.cache import cache
    from django.core import mail
    
    cache.clear()
    mail.outbox.clear()


@pytest.fixture
def api_client():
    """
    API客户端fixture
    """
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def authenticated_client(api_client, test_user):
    """
    已认证的API客户端
    """
    api_client.force_authenticate(user=test_user)
    return api_client


@pytest.fixture
def test_user():
    """
    测试用户fixture
    """
    return User.objects.create_user(
        username='testuser',
        email='test@example.com',
        password='testpass123'
    )


@pytest.fixture
def admin_user():
    """
    管理员用户fixture
    """
    return User.objects.create_superuser(
        username='admin',
        email='admin@example.com',
        password='adminpass123'
    )


@pytest.fixture
def authenticated_admin_client(api_client, admin_user):
    """
    已认证的管理员API客户端
    """
    api_client.force_authenticate(user=admin_user)
    return api_client


@pytest.fixture
def sample_awr_file_path():
    """
    示例AWR文件路径
    返回测试用的AWR文件路径
    """
    # 暂时返回None，后续实现AWR解析时会添加实际文件
    return None


@pytest.fixture
def temp_uploaded_file():
    """
    临时上传文件fixture，用于测试文件上传功能
    """
    from django.core.files.uploadedfile import SimpleUploadedFile
    
    # 创建一个简单的测试文件
    content = b"<html><head><title>Test AWR Report</title></head><body>Test Content</body></html>"
    return SimpleUploadedFile("test_awr.html", content, content_type="text/html")


@pytest.fixture(autouse=True)
def set_test_settings(settings):
    """
    设置测试环境的Django配置
    """
    # 禁用缓存
    settings.CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.dummy.DummyCache',
        }
    }
    
    # 测试环境使用同步邮件后端
    settings.EMAIL_BACKEND = 'django.core.mail.backends.locmem.EmailBackend'
    
    # 禁用Celery的eager模式用于测试
    settings.CELERY_TASK_ALWAYS_EAGER = True
    settings.CELERY_TASK_EAGER_PROPAGATES = True
    
    # 设置媒体文件目录
    settings.MEDIA_ROOT = '/tmp/test_media'
    
    # 禁用调试模式
    settings.DEBUG = False
    
    # 设置密钥
    settings.SECRET_KEY = 'test-secret-key-for-testing-only'


@pytest.fixture(scope='session')
def celery_config():
    """
    Celery测试配置
    """
    return {
        'broker_url': 'memory://',
        'result_backend': 'cache+memory://',
        'task_always_eager': True,
        'task_eager_propagates': True,
    }


# E2E测试专用fixture
@pytest.fixture
def e2e_live_server(live_server):
    """
    E2E测试专用的live server
    """
    return live_server


# 测试标记定义 - 移除自动django_db标记
# pytestmark = [
#     pytest.mark.django_db,
# ] 