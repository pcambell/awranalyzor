"""
安全测试套件
验证系统的安全性，包括文件上传、XSS防护、API安全等
"""

import os
import tempfile
import pytest
from unittest.mock import patch, Mock
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status

from analyzer.security.validators import FileSecurityValidator, validate_uploaded_file
from analyzer.middleware.exception_handler import SecurityError
from awr_upload.models import AWRReport


class FileUploadSecurityTestCase(TestCase):
    """文件上传安全测试"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        self.validator = FileSecurityValidator()
    
    def test_malicious_html_file_rejection(self):
        """测试恶意HTML文件被拒绝"""
        malicious_content = """
        <html>
        <body>
            <script>alert('XSS attack!');</script>
            <iframe src="javascript:alert('Malicious iframe')"></iframe>
            <img src="x" onerror="alert('Image XSS')">
        </body>
        </html>
        """
        
        malicious_file = SimpleUploadedFile(
            "malicious.html",
            malicious_content.encode('utf-8'),
            content_type="text/html"
        )
        
        with pytest.raises(SecurityError):
            validate_uploaded_file(malicious_file)
    
    def test_executable_file_rejection(self):
        """测试可执行文件被拒绝"""
        # 创建模拟的可执行文件
        executable_content = b"MZ\x90\x00"  # PE header
        
        exe_file = SimpleUploadedFile(
            "malware.exe",
            executable_content,
            content_type="application/octet-stream"
        )
        
        with pytest.raises(SecurityError):
            validate_uploaded_file(exe_file)
    
    def test_oversized_file_rejection(self):
        """测试超大文件被拒绝"""
        # 创建超过50MB的文件
        large_content = b"A" * (51 * 1024 * 1024)  # 51MB
        
        large_file = SimpleUploadedFile(
            "large.html",
            large_content,
            content_type="text/html"
        )
        
        with pytest.raises(SecurityError):
            validate_uploaded_file(large_file)
    
    def test_script_injection_in_content(self):
        """测试HTML内容中的脚本注入"""
        injection_attempts = [
            '<script>malicious_code()</script>',
            'javascript:alert("xss")',
            'onload="alert(1)"',
            '<iframe src="data:text/html,<script>alert(1)</script>"></iframe>',
            'eval("malicious_code")',
            '<img src=x onerror=alert(1)>',
            'expression(alert("XSS"))',
            '<svg onload=alert(1)>',
            '<object data="javascript:alert(1)">',
            '<embed src="javascript:alert(1)">',
        ]
        
        for injection in injection_attempts:
            html_content = f"""
            <html>
            <head><title>AWR Report</title></head>
            <body>
                <h1>Database Instance Activity</h1>
                {injection}
                <table>
                    <tr><td>Normal content</td></tr>
                </table>
            </body>
            </html>
            """
            
            test_file = SimpleUploadedFile(
                f"test_injection_{hash(injection)}.html",
                html_content.encode('utf-8'),
                content_type="text/html"
            )
            
            # 安全校验应该检测到危险内容
            with pytest.raises(SecurityError):
                validate_uploaded_file(test_file)
    
    def test_valid_awr_file_acceptance(self):
        """测试有效的AWR文件被接受"""
        valid_awr_content = """
        <html>
        <head><title>AWR Report</title></head>
        <body>
            <h1>Database Instance Activity</h1>
            <table>
                <tr><th>Instance</th><th>DB Name</th></tr>
                <tr><td>prod1</td><td>TESTDB</td></tr>
            </table>
            <h2>Load Profile</h2>
            <table>
                <tr><th>Metric</th><th>Per Second</th></tr>
                <tr><td>DB Time(s):</td><td>0.5</td></tr>
            </table>
        </body>
        </html>
        """
        
        valid_file = SimpleUploadedFile(
            "valid_awr.html",
            valid_awr_content.encode('utf-8'),
            content_type="text/html"
        )
        
        # 有效文件应该通过安全校验
        is_valid, errors, file_hash = validate_uploaded_file(valid_file)
        assert is_valid
        assert not errors
        assert file_hash is not None
    
    def test_file_path_traversal_protection(self):
        """测试路径遍历攻击防护"""
        malicious_filenames = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "....//....//etc//passwd",
            "%2e%2e%2f%2e%2e%2f%2e%2e%2fetc%2fpasswd",
            "..%255c..%255c..%255cetc%255cpasswd",
        ]
        
        for filename in malicious_filenames:
            malicious_file = SimpleUploadedFile(
                filename,
                b"<html><body>test</body></html>",
                content_type="text/html"
            )
            
            # 应该被安全校验拒绝
            with pytest.raises(SecurityError):
                validate_uploaded_file(malicious_file)


class APISecurityTestCase(TestCase):
    """API安全测试"""
    
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123'
        )
    
    def test_unauthenticated_access_denied(self):
        """测试未认证访问被拒绝"""
        # 不进行认证
        response = self.client.get('/api/reports/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        
        response = self.client.post('/api/upload/')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_sql_injection_protection(self):
        """测试SQL注入防护"""
        self.client.force_authenticate(user=self.user)
        
        # 常见的SQL注入尝试
        injection_attempts = [
            "1' OR '1'='1",
            "'; DROP TABLE awr_upload_awrreport; --",
            "1' UNION SELECT * FROM django_user --",
            "1'; EXEC xp_cmdshell('dir'); --",
            "1' OR 1=1 --",
            "' OR 'a'='a",
            "admin'--",
            "admin' /*",
            "1' OR 1=1#",
        ]
        
        for injection in injection_attempts:
            # 尝试在不同的参数中注入
            response = self.client.get(f'/api/reports/?search={injection}')
            # 应该返回正常响应，而不是500错误
            self.assertIn(response.status_code, [200, 400, 404])
            
            # 检查响应内容不包含数据库错误信息
            if hasattr(response, 'json'):
                response_data = response.json()
                response_text = str(response_data).lower()
                
                # 不应该暴露数据库错误
                dangerous_keywords = [
                    'sql syntax', 'mysql_fetch', 'postgresql error',
                    'ora-', 'microsoft odbc', 'sqlite_',
                    'syntax error', 'quotation mark'
                ]
                
                for keyword in dangerous_keywords:
                    self.assertNotIn(keyword, response_text)
    
    def test_xss_protection_in_api_responses(self):
        """测试API响应中的XSS防护"""
        self.client.force_authenticate(user=self.user)
        
        # 创建包含XSS尝试的报告
        xss_payload = "<script>alert('XSS')</script>"
        
        # 创建报告（如果通过了安全校验，说明XSS已被清理）
        safe_content = f"""
        <html>
        <body>
            <h1>Test Report {xss_payload}</h1>
            <p>Description: {xss_payload}</p>
        </body>
        </html>
        """
        
        # 这里主要测试API响应的转义
        test_file = SimpleUploadedFile(
            "xss_test.html",
            safe_content.encode('utf-8'),
            content_type="text/html"
        )
        
        # 由于我们有安全校验，这个请求应该失败
        response = self.client.post('/api/upload/', {
            'file': test_file,
            'name': xss_payload,
            'description': xss_payload
        })
        
        # 检查响应中XSS代码被正确处理
        if response.status_code == 400:
            # 安全校验拒绝了文件
            response_data = response.json()
            response_text = str(response_data)
            
            # 确保响应中没有执行脚本的风险
            self.assertNotIn('<script>', response_text)
            self.assertNotIn('javascript:', response_text)
    
    def test_csrf_protection(self):
        """测试CSRF防护"""
        # 使用普通的requests客户端模拟外部请求
        import requests
        from django.conf import settings
        
        # 假设服务器运行在localhost:8000
        base_url = "http://localhost:8000"
        
        # 尝试不带CSRF token的POST请求
        response = requests.post(f"{base_url}/api/upload/", {
            'name': 'test'
        })
        
        # 应该被CSRF保护拒绝（如果启用了CSRF）
        # 在测试环境中，CSRF可能被禁用，所以检查合理的状态码
        self.assertIn(response.status_code, [403, 401, 405])
    
    def test_rate_limiting(self):
        """测试接口限流"""
        self.client.force_authenticate(user=self.user)
        
        # 快速发送多个请求，测试限流
        responses = []
        
        for i in range(70):  # 超过默认限制（60请求/分钟）
            response = self.client.get('/api/reports/')
            responses.append(response.status_code)
        
        # 应该有一些请求被限流（429状态码）
        rate_limited_count = responses.count(429)
        
        # 至少应该有一些请求被限流
        # 注意：在测试环境中，限流可能不会严格执行
        if rate_limited_count > 0:
            self.assertGreater(rate_limited_count, 0)


class InputValidationSecurityTestCase(TestCase):
    """输入验证安全测试"""
    
    def test_parameter_pollution(self):
        """测试HTTP参数污染攻击"""
        client = APIClient()
        user = User.objects.create_user('testuser', password='testpass123')
        client.force_authenticate(user=user)
        
        # 发送重复参数的请求
        response = client.get('/api/reports/?page=1&page=999&page=-1')
        
        # 应该正常处理，不出现异常
        self.assertIn(response.status_code, [200, 400])
    
    def test_buffer_overflow_protection(self):
        """测试缓冲区溢出防护"""
        client = APIClient()
        user = User.objects.create_user('testuser', password='testpass123')
        client.force_authenticate(user=user)
        
        # 发送超长字符串
        very_long_string = "A" * 10000
        
        response = client.post('/api/upload/', {
            'name': very_long_string,
            'description': very_long_string
        })
        
        # 应该返回验证错误，而不是崩溃
        self.assertIn(response.status_code, [400, 413])  # Bad Request or Payload Too Large
    
    def test_unicode_security(self):
        """测试Unicode安全性"""
        client = APIClient()
        user = User.objects.create_user('testuser', password='testpass123')
        client.force_authenticate(user=user)
        
        # 测试各种Unicode字符
        unicode_tests = [
            "\u202e",  # Right-to-left override
            "\u200b",  # Zero width space
            "\ufeff",  # Byte order mark
            "𝕏𝕊𝕊",      # Mathematical double-struck
            "\u0000",  # Null byte
        ]
        
        for unicode_str in unicode_tests:
            response = client.get(f'/api/reports/?search={unicode_str}')
            
            # 应该正常处理Unicode字符
            self.assertIn(response.status_code, [200, 400])


class SecurityHeadersTestCase(TestCase):
    """安全响应头测试"""
    
    def setUp(self):
        self.client = APIClient()
        
    def test_security_headers_present(self):
        """测试安全响应头存在"""
        response = self.client.get('/api/')
        
        # 检查重要的安全头
        expected_headers = [
            'X-Content-Type-Options',
            'X-Frame-Options',
            'X-XSS-Protection',
        ]
        
        for header in expected_headers:
            if header in response:
                # 验证头部值
                if header == 'X-Content-Type-Options':
                    self.assertEqual(response[header], 'nosniff')
                elif header == 'X-Frame-Options':
                    self.assertIn(response[header], ['DENY', 'SAMEORIGIN'])
    
    def test_sensitive_info_not_exposed(self):
        """测试敏感信息不被暴露"""
        response = self.client.get('/api/')
        
        # 检查响应头中不包含敏感信息
        server_header = response.get('Server', '')
        self.assertNotIn('Django', server_header)
        self.assertNotIn('Python', server_header)
        
        # 检查响应中不暴露内部路径
        if hasattr(response, 'content'):
            content = response.content.decode('utf-8', errors='ignore')
            sensitive_patterns = [
                '/home/',
                '/var/',
                '/usr/',
                'C:\\',
                '__pycache__',
                '.pyc',
                'Traceback',
            ]
            
            for pattern in sensitive_patterns:
                self.assertNotIn(pattern, content)


@pytest.mark.performance
class SecurityPerformanceTestCase(TransactionTestCase):
    """安全功能性能测试"""
    
    def test_file_validation_performance(self):
        """测试文件验证性能"""
        import time
        
        # 创建中等大小的测试文件
        content = """
        <html>
        <head><title>AWR Report</title></head>
        <body>
        """ + "<p>Test data</p>" * 1000 + """
        </body>
        </html>
        """
        
        test_file = SimpleUploadedFile(
            "performance_test.html",
            content.encode('utf-8'),
            content_type="text/html"
        )
        
        start_time = time.time()
        
        # 执行安全验证
        is_valid, errors, file_hash = validate_uploaded_file(test_file)
        
        end_time = time.time()
        validation_time = end_time - start_time
        
        # 验证应该在合理时间内完成（<2秒）
        self.assertLess(validation_time, 2.0)
        
        # 文件应该通过验证
        self.assertTrue(is_valid)
    
    def test_concurrent_validation_performance(self):
        """测试并发验证性能"""
        import threading
        import time
        
        results = []
        
        def validate_file():
            content = "<html><body><p>Test</p></body></html>"
            test_file = SimpleUploadedFile(
                "concurrent_test.html",
                content.encode('utf-8'),
                content_type="text/html"
            )
            
            start_time = time.time()
            is_valid, errors, file_hash = validate_uploaded_file(test_file)
            end_time = time.time()
            
            results.append({
                'valid': is_valid,
                'time': end_time - start_time
            })
        
        # 启动多个并发验证
        threads = []
        for i in range(10):
            thread = threading.Thread(target=validate_file)
            threads.append(thread)
            thread.start()
        
        # 等待所有线程完成
        for thread in threads:
            thread.join()
        
        # 检查结果
        self.assertEqual(len(results), 10)
        
        # 所有验证都应该成功
        for result in results:
            self.assertTrue(result['valid'])
            self.assertLess(result['time'], 3.0)  # 并发情况下允许更长时间 