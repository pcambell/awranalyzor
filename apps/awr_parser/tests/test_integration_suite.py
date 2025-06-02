#!/usr/bin/env python3
"""
AWR解析器Django集成测试套件
{{CHENGQI: P2-TE-006 解析器测试套件 - Django集成测试 - 2025-06-02T15:23:28}}

测试解析器与Django框架的完整集成，包括：
1. 文件上传与解析流程
2. 数据库存储与查询
3. API接口集成
4. 任务调度集成
5. 错误处理和日志记录
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch, MagicMock

from django.test import TestCase, TransactionTestCase
from django.core.files.uploadedfile import SimpleUploadedFile
from django.contrib.auth.models import User
from django.db import transaction

from awr_upload.models import AWRReport
from awr_upload.services import AWRUploadService, AWRParsingService, AWRFileValidationError
from awr_upload.tasks import parse_awr_report_async, schedule_awr_parsing, AWRParsingProgress
from ..parsers.factory import create_parser, parse_awr
from ..parsers.base import ParseStatus, OracleVersion


class AWRServiceIntegrationTestCase(TestCase):
    """AWR服务集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.upload_service = AWRUploadService()
        self.parsing_service = AWRParsingService()
        
        # 创建测试用的AWR内容
        self.sample_awr_content = """
        <html>
        <head><title>WORKLOAD REPOSITORY report for DB: ORCL</title></head>
        <body>
        <h1>ORACLE Database 19c Enterprise Edition Release 19.0.0.0.0</h1>
        <table summary="Database and Instance Information">
        <tr><th>Database Id</th><th>Database Name</th><th>Instance Name</th></tr>
        <tr><td>1234567890</td><td>ORCL</td><td>orcl1</td></tr>
        </table>
        <table summary="Host Information">
        <tr><th>Host Name</th><th>Platform</th></tr>
        <tr><td>testhost</td><td>Linux x86 64-bit</td></tr>
        </table>
        <a name="summary"></a>
        <table summary="Report Summary">
        <tr><th>Begin Snap</th><th>End Snap</th><th>Elapsed Time</th></tr>
        <tr><td>100</td><td>101</td><td>60.0 (mins)</td></tr>
        </table>
        <a name="load_profile"></a>
        <table summary="Load Profile">
        <tr><th>Load Profile</th><th>Per Second</th><th>Per Transaction</th></tr>
        <tr><td>DB Time(s):</td><td>1.5</td><td>3.2</td></tr>
        <tr><td>DB CPU(s):</td><td>0.8</td><td>1.7</td></tr>
        </table>
        </body>
        </html>
        """
    
    def create_mock_awr_file(self, content: str = None) -> SimpleUploadedFile:
        """创建模拟AWR文件"""
        content = content or self.sample_awr_content
        return SimpleUploadedFile(
            "test_awr.html",
            content.encode('utf-8'),
            content_type="text/html"
        )
    
    def test_complete_upload_and_parsing_workflow(self):
        """测试完整的上传和解析工作流"""
        # 1. 文件上传
        uploaded_file = self.create_mock_awr_file()
        
        awr_report = self.upload_service.create_awr_report(
            uploaded_file=uploaded_file,
            user=self.user,
            name="Test AWR Report",
            description="Integration test report",
            category="TEST",
            tags=["integration", "test"]
        )
        
        # 验证报告创建
        self.assertIsNotNone(awr_report.id)
        self.assertEqual(awr_report.name, "Test AWR Report")
        self.assertEqual(awr_report.uploaded_by, self.user)
        self.assertEqual(awr_report.status, 'uploaded')
        
        # 2. 解析调度
        parsing_scheduled = self.upload_service.schedule_parsing(awr_report)
        self.assertTrue(parsing_scheduled)
        
        # 3. 解析执行
        result = self.parsing_service.parse_report(awr_report)
        
        # 验证解析结果
        self.assertIn(result.parse_status, [ParseStatus.SUCCESS, ParseStatus.PARTIAL])
        self.assertIsNotNone(result.db_info)
        self.assertIsNotNone(result.snapshot_info)
        
        # 4. 结果存储
        success = self.parsing_service.store_parse_result(awr_report, result)
        self.assertTrue(success)
        
        # 5. 验证数据库状态
        awr_report.refresh_from_db()
        self.assertEqual(awr_report.status, 'parsed')
        self.assertIsNotNone(awr_report.oracle_version)
        self.assertIsNotNone(awr_report.instance_name)
    
    def test_file_validation_errors(self):
        """测试文件验证错误处理"""
        # 测试空文件
        empty_file = SimpleUploadedFile("empty.html", b"", content_type="text/html")
        
        with self.assertRaises(AWRFileValidationError):
            self.upload_service.create_awr_report(
                uploaded_file=empty_file,
                user=self.user
            )
        
        # 测试非AWR文件
        non_awr_file = SimpleUploadedFile(
            "not_awr.html", 
            b"<html><body>Not an AWR report</body></html>",
            content_type="text/html"
        )
        
        with self.assertRaises(AWRFileValidationError):
            self.upload_service.create_awr_report(
                uploaded_file=non_awr_file,
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
            name="First Report"
        )
        self.assertIsNotNone(awr_report1.id)
        
        # 第二次上传应该失败（重复文件）
        with self.assertRaises(AWRFileValidationError) as context:
            self.upload_service.create_awr_report(
                uploaded_file=uploaded_file2,
                user=self.user,
                name="Duplicate Report"
            )
        
        self.assertIn("文件已存在", str(context.exception))
    
    def test_basic_info_extraction(self):
        """测试基础信息提取"""
        uploaded_file = self.create_mock_awr_file()
        
        awr_report = self.upload_service.create_awr_report(
            uploaded_file=uploaded_file,
            user=self.user
        )
        
        # 验证基础信息被正确提取
        self.assertEqual(awr_report.oracle_version, 'oracle_19c')
        self.assertEqual(awr_report.instance_name, 'orcl1')
        self.assertEqual(awr_report.database_id, 'ORCL')
        self.assertIsNotNone(awr_report.snapshot_duration_minutes)


class AWRTaskIntegrationTestCase(TransactionTestCase):
    """AWR任务系统集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.user = User.objects.create_user(
            username='taskuser',
            email='task@example.com',
            password='taskpass123'
        )
    
    def create_test_report(self) -> AWRReport:
        """创建测试报告"""
        # 创建临时文件
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("""
            <html>
            <head><title>WORKLOAD REPOSITORY report for DB: TEST</title></head>
            <body>
            <h1>ORACLE Database 19c Enterprise Edition</h1>
            <table>
            <tr><th>Database Id</th><th>Instance Name</th></tr>
            <tr><td>9876543210</td><td>test1</td></tr>
            </table>
            <a name="summary"></a>
            <table>
            <tr><th>Begin Snap</th><th>End Snap</th></tr>
            <tr><td>200</td><td>201</td></tr>
            </table>
            </body>
            </html>
            """)
            temp_file_path = f.name
        
        # 创建AWR报告记录
        awr_report = AWRReport.objects.create(
            name="Task Test Report",
            original_filename="task_test.html",
            file_path=temp_file_path,
            file_size=1000,
            file_hash="test_hash_123",
            uploaded_by=self.user,
            status='uploaded'
        )
        
        return awr_report
    
    def test_async_parsing_task(self):
        """测试异步解析任务"""
        awr_report = self.create_test_report()
        
        # 执行异步解析任务
        result = parse_awr_report_async(awr_report.id)
        
        # 验证任务执行结果
        self.assertIsNotNone(result)
        self.assertIn('status', result)
        
        # 验证报告状态更新
        awr_report.refresh_from_db()
        self.assertIn(awr_report.status, ['parsed', 'failed'])
    
    def test_task_scheduling(self):
        """测试任务调度"""
        awr_report = self.create_test_report()
        
        # 调度解析任务
        success = schedule_awr_parsing(awr_report.id)
        self.assertTrue(success)
    
    def test_parsing_progress_tracking(self):
        """测试解析进度跟踪"""
        awr_report = self.create_test_report()
        
        # 创建进度跟踪器
        progress = AWRParsingProgress(awr_report.id)
        
        # 测试进度更新
        progress.update_progress(10, "验证文件")
        progress.update_progress(50, "解析内容")
        progress.update_progress(100, "完成")
        
        # 获取最终进度
        final_progress = progress.get_progress()
        self.assertEqual(final_progress['progress'], 100)
        self.assertEqual(final_progress['stage'], "完成")
    
    def tearDown(self):
        """清理测试数据"""
        # 删除临时文件
        for report in AWRReport.objects.filter(uploaded_by=self.user):
            if os.path.exists(report.file_path):
                os.unlink(report.file_path)


class AWRAPIIntegrationTestCase(TestCase):
    """AWR API集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.user = User.objects.create_user(
            username='apiuser',
            email='api@example.com',
            password='apipass123'
        )
        self.client.force_login(self.user)
    
    def test_file_upload_api(self):
        """测试文件上传API"""
        awr_content = """
        <html>
        <head><title>WORKLOAD REPOSITORY report for DB: API</title></head>
        <body>
        <h1>ORACLE Database 19c Enterprise Edition</h1>
        <table>
        <tr><th>Database Id</th><th>Instance Name</th></tr>
        <tr><td>1111111111</td><td>api1</td></tr>
        </table>
        </body>
        </html>
        """
        
        uploaded_file = SimpleUploadedFile(
            "api_test.html",
            awr_content.encode('utf-8'),
            content_type="text/html"
        )
        
        response = self.client.post('/awr_upload/api/upload/', {
            'file': uploaded_file,
            'name': 'API Test Report',
            'description': 'Test via API',
            'category': 'API_TEST',
            'tags': 'api,test'
        })
        
        self.assertEqual(response.status_code, 201)
        
        response_data = response.json()
        self.assertIn('id', response_data)
        self.assertEqual(response_data['name'], 'API Test Report')
        self.assertTrue(response_data['parsing_scheduled'])
    
    def test_file_validation_api(self):
        """测试文件验证API"""
        valid_awr = SimpleUploadedFile(
            "valid.html",
            b"<html><title>WORKLOAD REPOSITORY report</title></html>",
            content_type="text/html"
        )
        
        response = self.client.post('/awr_upload/api/validate/', {
            'file': valid_awr
        })
        
        self.assertEqual(response.status_code, 200)
        
        response_data = response.json()
        self.assertTrue(response_data['valid'])
        self.assertIn('file_info', response_data)
    
    def test_report_list_api(self):
        """测试报告列表API"""
        # 先创建一些报告
        for i in range(3):
            AWRReport.objects.create(
                name=f"Test Report {i}",
                original_filename=f"test_{i}.html",
                file_path=f"/tmp/test_{i}.html",
                file_size=1000 + i,
                file_hash=f"hash_{i}",
                uploaded_by=self.user,
                status='parsed'
            )
        
        response = self.client.get('/awr_upload/api/reports/')
        
        self.assertEqual(response.status_code, 200)
        
        response_data = response.json()
        self.assertEqual(len(response_data['results']), 3)
    
    def test_report_status_api(self):
        """测试报告状态API"""
        awr_report = AWRReport.objects.create(
            name="Status Test Report",
            original_filename="status_test.html",
            file_path="/tmp/status_test.html",
            file_size=1000,
            file_hash="status_hash",
            uploaded_by=self.user,
            status='parsing'
        )
        
        response = self.client.get(f'/awr_upload/api/reports/{awr_report.id}/status/')
        
        self.assertEqual(response.status_code, 200)
        
        response_data = response.json()
        self.assertEqual(response_data['status'], 'parsing')
        self.assertTrue(response_data['is_processing'])


class AWRRealFilesIntegrationTestCase(TestCase):
    """真实AWR文件集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.user = User.objects.create_user(
            username='realuser',
            email='real@example.com',
            password='realpass123'
        )
        self.upload_service = AWRUploadService()
        self.parsing_service = AWRParsingService()
        
        # 查找真实AWR文件
        self.awrrpt_dir = Path("awrrpt")
        self.real_awr_files = []
        
        if self.awrrpt_dir.exists():
            self.real_awr_files = list(self.awrrpt_dir.glob("**/*.html"))[:5]  # 限制测试文件数量
    
    def test_real_files_integration_workflow(self):
        """测试真实文件的完整集成工作流"""
        if not self.real_awr_files:
            self.skipTest("No real AWR files found for integration testing")
        
        successful_files = []
        failed_files = []
        
        for awr_file in self.real_awr_files:
            with self.subTest(file=str(awr_file)):
                try:
                    # 读取真实文件
                    with open(awr_file, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 创建Django文件对象
                    django_file = SimpleUploadedFile(
                        awr_file.name,
                        content.encode('utf-8'),
                        content_type="text/html"
                    )
                    
                    # 1. 上传
                    awr_report = self.upload_service.create_awr_report(
                        uploaded_file=django_file,
                        user=self.user,
                        name=f"Real File Test - {awr_file.name}",
                        category="REAL_FILE_TEST"
                    )
                    
                    # 2. 解析
                    result = self.parsing_service.parse_report(awr_report)
                    
                    # 3. 存储结果
                    success = self.parsing_service.store_parse_result(awr_report, result)
                    
                    if success and result.parse_status in [ParseStatus.SUCCESS, ParseStatus.PARTIAL]:
                        successful_files.append(awr_file.name)
                        
                        # 验证数据完整性
                        awr_report.refresh_from_db()
                        self.assertIsNotNone(awr_report.oracle_version)
                        self.assertIsNotNone(awr_report.instance_name)
                    else:
                        failed_files.append((awr_file.name, "Parse or store failed"))
                        
                except Exception as e:
                    failed_files.append((awr_file.name, str(e)))
        
        # 验证成功率
        total_files = len(self.real_awr_files)
        success_rate = len(successful_files) / total_files if total_files > 0 else 0
        
        print(f"\n=== Real Files Integration Test Summary ===")
        print(f"Total files: {total_files}")
        print(f"Successful: {len(successful_files)}")
        print(f"Failed: {len(failed_files)}")
        print(f"Success rate: {success_rate:.2%}")
        
        if failed_files:
            print(f"Failed files: {failed_files}")
        
        # 期望至少90%的成功率
        self.assertGreater(success_rate, 0.90, 
                          f"Integration success rate {success_rate:.2%} is below 90%")


class AWRErrorHandlingIntegrationTestCase(TestCase):
    """错误处理集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.user = User.objects.create_user(
            username='erroruser',
            email='error@example.com',
            password='errorpass123'
        )
    
    def test_parsing_error_handling(self):
        """测试解析错误处理"""
        # 创建会导致解析错误的报告
        with tempfile.NamedTemporaryFile(mode='w', suffix='.html', delete=False) as f:
            f.write("<html><body>Invalid AWR content</body></html>")
            temp_file_path = f.name
        
        awr_report = AWRReport.objects.create(
            name="Error Test Report",
            original_filename="error_test.html",
            file_path=temp_file_path,
            file_size=100,
            file_hash="error_hash",
            uploaded_by=self.user,
            status='uploaded'
        )
        
        # 尝试解析
        parsing_service = AWRParsingService()
        
        try:
            result = parsing_service.parse_report(awr_report)
            # 应该返回失败状态而不是抛出异常
            self.assertEqual(result.parse_status, ParseStatus.FAILED)
        except Exception:
            # 如果抛出异常，验证报告状态被正确更新
            awr_report.refresh_from_db()
            self.assertEqual(awr_report.status, 'failed')
            self.assertIsNotNone(awr_report.error_message)
        
        # 清理
        os.unlink(temp_file_path)
    
    def test_database_transaction_rollback(self):
        """测试数据库事务回滚"""
        upload_service = AWRUploadService()
        
        # 模拟数据库错误
        with patch('awr_upload.models.AWRReport.objects.create') as mock_create:
            mock_create.side_effect = Exception("Database error")
            
            uploaded_file = SimpleUploadedFile(
                "transaction_test.html",
                b"<html><title>WORKLOAD REPOSITORY</title></html>",
                content_type="text/html"
            )
            
            with self.assertRaises(Exception):
                upload_service.create_awr_report(
                    uploaded_file=uploaded_file,
                    user=self.user
                )
            
            # 验证没有创建不完整的记录
            self.assertFalse(
                AWRReport.objects.filter(original_filename="transaction_test.html").exists()
            )
    
    @patch('apps.awr_parser.parsers.factory.logger')
    def test_logging_integration(self, mock_logger):
        """测试日志记录集成"""
        # 触发会记录日志的操作
        parser = create_parser("invalid content")
        
        # 验证日志记录
        self.assertTrue(mock_logger.called or parser is None)


if __name__ == '__main__':
    unittest.main(verbosity=2) 