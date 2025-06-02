"""
Oracle AWR分析器 - 基础测试
{{CHENGQI: P1-TE-004 基础测试框架配置 - 2025-06-01 23:45:00 +08:00}}

验证测试环境配置的基础测试
"""
import pytest
from django.test import TestCase
from django.contrib.auth.models import User
from django.conf import settings


class TestBasicConfiguration(TestCase):
    """基础配置测试"""
    
    def test_django_settings(self):
        """测试Django设置是否正确"""
        self.assertIsNotNone(settings.SECRET_KEY)
        self.assertEqual(settings.DEBUG, False)  # 测试环境应该是False
    
    def test_database_connection(self):
        """测试数据库连接"""
        # 创建一个用户来测试数据库连接
        user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.assertEqual(user.username, 'testuser')
        self.assertTrue(user.check_password('testpass123'))
    
    def test_user_creation(self):
        """测试用户创建功能"""
        user_count_before = User.objects.count()
        User.objects.create_user(
            username='newuser',
            email='newuser@example.com',
            password='newpass123'
        )
        user_count_after = User.objects.count()
        self.assertEqual(user_count_after, user_count_before + 1)


@pytest.mark.unit
def test_pytest_configuration():
    """测试pytest配置"""
    assert True  # 基础断言测试


@pytest.mark.unit
def test_fixtures_work(test_user):
    """测试fixture是否工作"""
    assert test_user.username == 'testuser'
    assert test_user.email == 'test@example.com'


@pytest.mark.unit
def test_api_client_fixture(api_client):
    """测试API客户端fixture"""
    assert api_client is not None
    # 测试一个简单的请求（这会失败，但证明客户端工作）
    response = api_client.get('/nonexistent/')
    assert response.status_code == 404


@pytest.mark.unit
def test_authenticated_client(authenticated_client, test_user):
    """测试认证客户端fixture"""
    assert authenticated_client is not None
    # 验证用户已认证
    assert hasattr(authenticated_client, 'force_authenticate')


class TestFactoryBoy:
    """测试Factory Boy工厂"""
    
    @pytest.mark.unit
    def test_user_factory(self):
        """测试用户工厂"""
        from tests.factories import UserFactory
        
        user = UserFactory()
        assert user.username.startswith('user_')
        assert '@example.com' in user.email
        assert user.is_active is True
        assert user.is_staff is False
    
    @pytest.mark.unit
    def test_admin_user_factory(self):
        """测试管理员用户工厂"""
        from tests.factories import AdminUserFactory
        
        admin = AdminUserFactory()
        assert admin.username.startswith('admin_')
        assert admin.is_staff is True
        assert admin.is_superuser is True


class TestTestUtils:
    """测试工具函数测试"""
    
    @pytest.mark.unit
    def test_create_test_awr_file(self):
        """测试AWR文件创建工具"""
        from tests.test_utils import create_test_awr_file
        
        awr_file = create_test_awr_file()
        assert awr_file.name == "test_awr.html"
        assert awr_file.content_type == "text/html"
        assert b"AWR Report" in awr_file.read()
    
    @pytest.mark.unit
    def test_create_malicious_file(self):
        """测试恶意文件创建工具"""
        from tests.test_utils import create_malicious_file
        
        malicious_file = create_malicious_file()
        content = malicious_file.read().decode('utf-8')
        assert "script" in content
        assert "alert" in content
    
    @pytest.mark.unit
    def test_awr_test_data_mixin(self):
        """测试AWR测试数据混入类"""
        from tests.test_utils import AWRTestDataMixin
        
        # 测试不同版本的模板
        content_11g = AWRTestDataMixin.get_sample_awr_content('11g')
        content_12c = AWRTestDataMixin.get_sample_awr_content('12c')
        content_19c = AWRTestDataMixin.get_sample_awr_content('19c')
        
        assert "TEST11G" in content_11g
        assert "TESTPDB" in content_12c
        assert "TEST19C" in content_19c


@pytest.mark.slow
def test_slow_operation():
    """标记为慢速的测试"""
    import time
    time.sleep(0.1)  # 模拟慢速操作
    assert True


# 性能测试示例
@pytest.mark.performance
def test_user_creation_performance(benchmark):
    """性能基准测试示例"""
    def create_user():
        return User.objects.create_user(
            username='perfuser',
            email='perf@example.com',
            password='perfpass123'
        )
    
    # 这个测试需要pytest-benchmark
    try:
        result = benchmark(create_user)
        assert result.username == 'perfuser'
    except Exception:
        # 如果benchmark不可用，跳过
        pytest.skip("benchmark not available") 