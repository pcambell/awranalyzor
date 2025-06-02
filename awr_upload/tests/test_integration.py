#!/usr/bin/env python3
"""
AWR上传模块集成测试
{{CHENGQI: P2-LD-005 解析器工厂和集成 - Django集成测试 - 2025-06-02T15:00:00}}

测试文件上传、解析调度、结果存储的完整集成流程
"""

import os
import tempfile
from django.test import TestCase, override_settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APITestCase
from rest_framework import status

from ..models import AWRReport
from ..services import AWRUploadService, AWRParsingService, AWRFileValidationError
from ..tasks import parse_awr_report_async, schedule_awr_parsing


class AWRServiceIntegrationTestCase(TestCase):
    """AWR服务层集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass123',
            email='test@example.com'
        )
        self.upload_service = AWRUploadService()
        self.parsing_service = AWRParsingService()
    
    def create_mock_awr_file(self, content: str = None) -> SimpleUploadedFile:
        """创建模拟AWR文件"""
        if content is None:
            content = """
            <html>
            <head><title>Oracle Database 19c Enterprise Edition Release 19.0.0.0.0 AWR Report</title></head>
            <body>
            <h1>WORKLOAD REPOSITORY report for</h1>
            <h2>Oracle Database 19c Enterprise Edition Release 19.0.0.0.0</h2>
            <table>
                <tr><td>Instance Name:</td><td>TESTDB1</td></tr>
                <tr><td>DB Name:</td><td>TESTDB</td></tr>
            </table>
            </body>
            </html>
            """
        
        return SimpleUploadedFile(
            "test_awr.html",
            content.encode('utf-8'),
            content_type="text/html"
        )
    
    def test_complete_upload_and_parsing_flow(self):
        """测试完整的上传和解析流程"""
        # 1. 创建AWR文件
        uploaded_file = self.create_mock_awr_file()
        
        # 2. 创建AWR报告
        awr_report = self.upload_service.create_awr_report(
            uploaded_file=uploaded_file,
            user=self.user,
            name="测试AWR报告",
            description="集成测试用报告",
            category="test"
        )
        
        # 验证报告创建
        self.assertIsNotNone(awr_report)
        self.assertEqual(awr_report.name, "测试AWR报告")
        self.assertEqual(awr_report.status, 'uploaded')
        self.assertEqual(awr_report.uploaded_by, self.user)
        
        # 3. 调度解析任务
        scheduling_success = self.upload_service.schedule_parsing(awr_report)
        self.assertTrue(scheduling_success)
        
        # 4. 刷新报告状态
        awr_report.refresh_from_db()
        
        # 验证解析完成
        self.assertIn(awr_report.status, ['parsed', 'completed'])
        self.assertIsNotNone(awr_report.oracle_version)
        
    def test_file_validation_error(self):
        """测试文件验证错误处理"""
        # 创建无效文件
        invalid_file = SimpleUploadedFile(
            "invalid.txt",
            b"This is not an AWR report",
            content_type="text/plain"
        )
        
        # 应该抛出验证错误
        with self.assertRaises(AWRFileValidationError):
            self.upload_service.create_awr_report(
                uploaded_file=invalid_file,
                user=self.user
            )
    
    def test_duplicate_file_handling(self):
        """测试重复文件处理"""
        uploaded_file1 = self.create_mock_awr_file()
        uploaded_file2 = self.create_mock_awr_file()  # 相同内容
        
        # 第一次上传成功
        awr_report1 = self.upload_service.create_awr_report(
            uploaded_file=uploaded_file1,
            user=self.user,
            name="第一次上传"
        )
        self.assertIsNotNone(awr_report1)
        
        # 第二次上传应该失败（重复文件）
        with self.assertRaises(AWRFileValidationError) as context:
            self.upload_service.create_awr_report(
                uploaded_file=uploaded_file2,
                user=self.user,
                name="第二次上传"
            )
        
        self.assertIn("文件已存在", str(context.exception))
    
    def test_basic_info_extraction(self):
        """测试基础信息提取"""
        content = """
        <html>
        <head><title>Oracle Database 11g Enterprise Edition Release 11.2.0.4.0 AWR Report</title></head>
        <body>
        <h1>WORKLOAD REPOSITORY report for</h1>
        <table>
            <tr><td>Instance Name:</td><td>PROD1</td></tr>
            <tr><td>DB Name:</td><td>PRODDB</td></tr>
        </table>
        </body>
        </html>
        """
        
        basic_info = self.upload_service.extract_basic_info(content)
        
        # 根据工厂解析器的能力，可能提取到一些信息
        self.assertIsInstance(basic_info, dict)


class AWRTaskIntegrationTestCase(TestCase):
    """AWR任务集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='taskuser',
            password='testpass123'
        )
    
    def create_test_report(self) -> AWRReport:
        """创建测试报告"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""
            <html>
            <head><title>Oracle Database 19c AWR Report</title></head>
            <body>
            <h1>WORKLOAD REPOSITORY report for</h1>
            <h2>Oracle Database 19c Enterprise Edition</h2>
            </body>
            </html>
            """)
            temp_path = f.name
        
        # 创建AWR报告记录
        report = AWRReport.objects.create(
            name="任务测试报告",
            original_filename="test.html",
            file_path=temp_path,
            file_size=1024,
            file_hash="test_hash_123",
            uploaded_by=self.user,
            status='uploaded'
        )
        
        return report
    
    def test_async_parsing_task(self):
        """测试异步解析任务"""
        report = self.create_test_report()
        
        # 执行解析任务
        result = parse_awr_report_async(report.id)
        
        # 验证任务结果
        self.assertIsInstance(result, dict)
        self.assertEqual(result['report_id'], report.id)
        self.assertIsNotNone(result['started_at'])
        self.assertIsNotNone(result['completed_at'])
        
        # 验证报告状态更新
        report.refresh_from_db()
        self.assertIn(report.status, ['parsed', 'completed', 'failed'])
    
    def test_task_scheduling(self):
        """测试任务调度"""
        report = self.create_test_report()
        
        # 调度任务
        success = schedule_awr_parsing(report.id)
        
        # 验证调度结果
        self.assertTrue(success)
        
        # 验证报告状态更新
        report.refresh_from_db()
        self.assertNotEqual(report.status, 'uploaded')
    
    def tearDown(self):
        """测试后清理"""
        # 清理临时文件
        for report in AWRReport.objects.filter(uploaded_by=self.user):
            if report.file_path and os.path.exists(report.file_path.path):
                try:
                    os.unlink(report.file_path.path)
                except OSError:
                    pass


class AWRAPIIntegrationTestCase(APITestCase):
    """AWR API集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='apiuser',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
    
    def test_file_upload_api(self):
        """测试文件上传API"""
        # 准备上传文件
        content = """
        <html>
        <head><title>Oracle Database 19c AWR Report</title></head>
        <body>
        <h1>WORKLOAD REPOSITORY report for</h1>
        </body>
        </html>
        """
        uploaded_file = SimpleUploadedFile(
            "api_test.html",
            content.encode('utf-8'),
            content_type="text/html"
        )
        
        # 发送上传请求
        response = self.client.post('/awr_upload/api/upload/', {
            'file': uploaded_file,
            'name': 'API测试报告',
            'description': '通过API上传的测试报告',
            'category': 'test',
            'tags': 'api,test,integration'
        }, format='multipart')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('id', response.data)
        self.assertEqual(response.data['name'], 'API测试报告')
        self.assertTrue(response.data['parsing_scheduled'])
        
        # 验证数据库记录
        report = AWRReport.objects.get(id=response.data['id'])
        self.assertEqual(report.uploaded_by, self.user)
        self.assertEqual(report.tags, ['api', 'test', 'integration'])
    
    def test_file_validation_api(self):
        """测试文件验证API"""
        content = """
        <html>
        <head><title>Oracle Database 19c AWR Report</title></head>
        <body>
        <h1>WORKLOAD REPOSITORY report for</h1>
        </body>
        </html>
        """
        uploaded_file = SimpleUploadedFile(
            "validate_test.html",
            content.encode('utf-8'),
            content_type="text/html"
        )
        
        # 发送验证请求
        response = self.client.post('/awr_upload/api/validate/', {
            'file': uploaded_file
        }, format='multipart')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(response.data['valid'])
        self.assertIn('file_info', response.data)
        self.assertIn('awr_info', response.data)
    
    def test_report_list_api(self):
        """测试报告列表API"""
        # 创建测试报告
        AWRReport.objects.create(
            name="测试报告1",
            original_filename="test1.html",
            file_path="dummy/path1.html",
            file_size=1024,
            file_hash="hash1",
            uploaded_by=self.user,
            status='completed'
        )
        
        AWRReport.objects.create(
            name="测试报告2",
            original_filename="test2.html",
            file_path="dummy/path2.html",
            file_size=2048,
            file_hash="hash2",
            uploaded_by=self.user,
            status='parsing'
        )
        
        # 获取报告列表
        response = self.client.get('/awr_upload/api/reports/')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data['results']), 2)
        
        # 验证只返回当前用户的报告
        for report in response.data['results']:
            self.assertIn('name', report)
            self.assertIn('status', report)
    
    def test_report_status_api(self):
        """测试报告状态查询API"""
        # 创建测试报告
        report = AWRReport.objects.create(
            name="状态测试报告",
            original_filename="status_test.html",
            file_path="dummy/status_path.html",
            file_size=1024,
            file_hash="status_hash",
            uploaded_by=self.user,
            status='parsing'
        )
        
        # 查询状态
        response = self.client.get(f'/awr_upload/api/reports/{report.id}/status/')
        
        # 验证响应
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], report.id)
        self.assertEqual(response.data['status'], 'parsing')
        self.assertIn('status_display', response.data)
        self.assertIn('is_processing', response.data)


@override_settings(
    MEDIA_ROOT=tempfile.mkdtemp(),
    AWR_SETTINGS={
        'MAX_FILE_SIZE': 1024 * 1024,  # 1MB for testing
        'ALLOWED_FILE_TYPES': ['.html', '.htm'],
    }
)
class AWRFullIntegrationTestCase(TestCase):
    """AWR完整集成测试"""
    
    def setUp(self):
        """测试前准备"""
        self.user = User.objects.create_user(
            username='fulluser',
            password='testpass123'
        )
    
    def test_end_to_end_workflow(self):
        """测试端到端工作流程"""
        # 1. 创建服务实例
        upload_service = AWRUploadService()
        
        # 2. 准备AWR文件
        awr_content = """
        <html>
        <head><title>Oracle Database 19c Enterprise Edition Release 19.0.0.0.0 AWR Report</title></head>
        <body>
        <h1>WORKLOAD REPOSITORY report for</h1>
        <h2>Oracle Database 19c Enterprise Edition Release 19.0.0.0.0</h2>
        <table>
            <tr><td>Instance Name:</td><td>E2ETEST</td></tr>
            <tr><td>DB Name:</td><td>E2EDB</td></tr>
        </table>
        </body>
        </html>
        """
        
        uploaded_file = SimpleUploadedFile(
            "e2e_test.html",
            awr_content.encode('utf-8'),
            content_type="text/html"
        )
        
        # 3. 文件上传和基础信息提取
        awr_report = upload_service.create_awr_report(
            uploaded_file=uploaded_file,
            user=self.user,
            name="端到端测试报告",
            description="完整工作流程测试",
            category="test",
            tags=["e2e", "integration"]
        )
        
        # 验证报告创建
        self.assertIsNotNone(awr_report)
        self.assertEqual(awr_report.status, 'uploaded')
        
        # 4. 调度解析任务
        parsing_success = upload_service.schedule_parsing(awr_report)
        self.assertTrue(parsing_success)
        
        # 5. 验证最终状态
        awr_report.refresh_from_db()
        self.assertIn(awr_report.status, ['parsed', 'completed', 'failed'])
        
        # 如果解析成功，验证提取的信息
        if awr_report.status in ['parsed', 'completed']:
            # 可能提取到的基础信息
            self.assertIsNotNone(awr_report.file_hash)
            self.assertTrue(len(awr_report.file_hash) > 0)
        
        # 6. 清理
        if awr_report.file_path:
            try:
                os.unlink(awr_report.file_path.path)
            except OSError:
                pass 