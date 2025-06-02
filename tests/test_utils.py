"""
Oracle AWR分析器 - 测试工具模块
{{CHENGQI: P1-TE-004 基础测试框架配置 - 2025-06-01 23:45:00 +08:00}}

这个模块包含测试中常用的工具函数和辅助类
"""
import os
import tempfile
import json
from typing import Dict, Any, Optional
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APITestCase


class BaseTestCase(TestCase):
    """
    基础测试用例类
    为所有Django TestCase提供通用功能
    """
    
    def setUp(self):
        """测试前设置"""
        super().setUp()
        self.temp_files = []
    
    def tearDown(self):
        """测试后清理"""
        # 清理临时文件
        for temp_file in self.temp_files:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        super().tearDown()
    
    def create_temp_file(self, content: str, suffix: str = '.html') -> str:
        """
        创建临时文件
        
        Args:
            content: 文件内容
            suffix: 文件后缀
        
        Returns:
            临时文件路径
        """
        with tempfile.NamedTemporaryFile(mode='w', suffix=suffix, delete=False) as f:
            f.write(content)
            self.temp_files.append(f.name)
            return f.name


class BaseAPITestCase(APITestCase):
    """
    基础API测试用例类
    为所有DRF API测试提供通用功能
    """
    
    def setUp(self):
        """测试前设置"""
        super().setUp()
        self.base_url = '/api/v1'
    
    def get_url(self, endpoint: str) -> str:
        """
        获取完整的API URL
        
        Args:
            endpoint: API端点
        
        Returns:
            完整URL
        """
        return f"{self.base_url}{endpoint}"
    
    def assert_response_status(self, response, expected_status: int):
        """
        断言响应状态码
        
        Args:
            response: HTTP响应
            expected_status: 期望状态码
        """
        self.assertEqual(
            response.status_code, 
            expected_status,
            f"Expected status {expected_status}, got {response.status_code}. "
            f"Response: {getattr(response, 'data', response.content)}"
        )
    
    def assert_response_contains(self, response, key: str, value: Any = None):
        """
        断言响应包含指定键值
        
        Args:
            response: HTTP响应
            key: 键名
            value: 期望值（可选）
        """
        self.assertIn(key, response.data)
        if value is not None:
            self.assertEqual(response.data[key], value)


def create_test_awr_file(
    content: str = None, 
    filename: str = "test_awr.html",
    content_type: str = "text/html"
) -> SimpleUploadedFile:
    """
    创建测试用的AWR文件
    
    Args:
        content: 文件内容
        filename: 文件名
        content_type: 内容类型
    
    Returns:
        Django上传文件对象
    """
    if content is None:
        content = """
        <html>
        <head><title>AWR Report for DB: TEST</title></head>
        <body>
        <h1>AWR Report</h1>
        <table>
            <tr><th>DB Name</th><td>TEST</td></tr>
            <tr><th>Instance</th><td>1</td></tr>
            <tr><th>Begin Time</th><td>01-JAN-24 00:00:00</td></tr>
            <tr><th>End Time</th><td>01-JAN-24 01:00:00</td></tr>
        </table>
        </body>
        </html>
        """
    
    return SimpleUploadedFile(
        filename,
        content.encode('utf-8'),
        content_type=content_type
    )


def create_malicious_file(filename: str = "malicious.html") -> SimpleUploadedFile:
    """
    创建恶意测试文件用于安全测试
    
    Args:
        filename: 文件名
    
    Returns:
        包含恶意内容的上传文件
    """
    malicious_content = """
    <html>
    <head><title>Malicious File</title></head>
    <body>
    <script>alert('XSS');</script>
    <iframe src="javascript:alert('XSS')"></iframe>
    </body>
    </html>
    """
    
    return SimpleUploadedFile(
        filename,
        malicious_content.encode('utf-8'),
        content_type="text/html"
    )


def assert_dict_contains(actual: Dict[str, Any], expected: Dict[str, Any]):
    """
    断言字典包含期望的键值对
    
    Args:
        actual: 实际字典
        expected: 期望包含的键值对
    """
    for key, value in expected.items():
        assert key in actual, f"Key '{key}' not found in {actual}"
        assert actual[key] == value, f"Expected {key}={value}, got {actual[key]}"


def load_test_data(filename: str) -> Dict[str, Any]:
    """
    加载测试数据文件
    
    Args:
        filename: 测试数据文件名（相对于tests目录）
    
    Returns:
        测试数据字典
    """
    test_dir = os.path.dirname(__file__)
    file_path = os.path.join(test_dir, 'data', filename)
    
    if not os.path.exists(file_path):
        return {}
    
    with open(file_path, 'r', encoding='utf-8') as f:
        return json.load(f)


class MockAWRParser:
    """
    模拟AWR解析器，用于测试
    """
    
    def __init__(self, should_fail: bool = False):
        self.should_fail = should_fail
    
    def parse(self, file_content: str) -> Dict[str, Any]:
        """
        模拟解析AWR文件
        
        Args:
            file_content: 文件内容
        
        Returns:
            解析结果字典
        """
        if self.should_fail:
            raise ValueError("Parse failed")
        
        return {
            'database_info': {
                'name': 'TEST',
                'instance': '1',
                'version': '19c'
            },
            'time_range': {
                'begin': '2024-01-01 00:00:00',
                'end': '2024-01-01 01:00:00'
            },
            'metrics': {
                'cpu_usage': 85.5,
                'memory_usage': 92.1,
                'io_wait': 12.3
            }
        }


def skip_if_no_playwright():
    """
    如果没有安装Playwright则跳过测试的装饰器
    """
    import pytest
    
    try:
        import playwright
        return lambda func: func
    except ImportError:
        return pytest.mark.skip(reason="Playwright not installed")


class AWRTestDataMixin:
    """
    AWR测试数据混入类
    提供常用的AWR测试数据
    """
    
    @classmethod
    def get_sample_awr_content(cls, oracle_version: str = '19c') -> str:
        """
        获取示例AWR内容
        
        Args:
            oracle_version: Oracle版本
        
        Returns:
            AWR HTML内容
        """
        templates = {
            '11g': cls._get_11g_template(),
            '12c': cls._get_12c_template(), 
            '19c': cls._get_19c_template()
        }
        
        return templates.get(oracle_version, templates['19c'])
    
    @staticmethod
    def _get_11g_template() -> str:
        """Oracle 11g AWR模板"""
        return """
        <html>
        <head><title>AWR Report for DB: TEST11G</title></head>
        <body>
        <h1>Oracle 11g AWR Report</h1>
        <table>
            <tr><th>DB Name</th><td>TEST11G</td></tr>
            <tr><th>DB Id</th><td>1234567890</td></tr>
            <tr><th>Instance</th><td>1</td></tr>
            <tr><th>Release</th><td>11.2.0.4.0</td></tr>
        </table>
        </body>
        </html>
        """
    
    @staticmethod
    def _get_12c_template() -> str:
        """Oracle 12c AWR模板"""
        return """
        <html>
        <head><title>AWR Report for PDB: TESTPDB</title></head>
        <body>
        <h1>Oracle 12c AWR Report</h1>
        <table>
            <tr><th>Container Name</th><td>TESTPDB</td></tr>
            <tr><th>Container Id</th><td>3</td></tr>
            <tr><th>DB Name</th><td>TEST12C</td></tr>
            <tr><th>Release</th><td>12.2.0.1.0</td></tr>
        </table>
        </body>
        </html>
        """
    
    @staticmethod
    def _get_19c_template() -> str:
        """Oracle 19c AWR模板"""
        return """
        <html>
        <head><title>AWR Report for DB: TEST19C</title></head>
        <body>
        <h1>Oracle 19c AWR Report</h1>
        <table>
            <tr><th>DB Name</th><td>TEST19C</td></tr>
            <tr><th>DB Id</th><td>9876543210</td></tr>
            <tr><th>Instance</th><td>1</td></tr>
            <tr><th>Release</th><td>19.12.0.0.0</td></tr>
        </table>
        </body>
        </html>
        """ 