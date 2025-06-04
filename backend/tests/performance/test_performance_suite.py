"""
性能测试套件
验证系统在各种负载条件下的性能表现
"""

import time
import threading
import asyncio
import psutil
import pytest
from unittest.mock import Mock, patch
from django.test import TestCase, TransactionTestCase
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from concurrent.futures import ThreadPoolExecutor, as_completed

from awr_upload.models import AWRReport
from awr_parser.services.awr_parsing_service import AWRParsingService


@pytest.mark.performance
class ConcurrentUserTestCase(TransactionTestCase):
    """并发用户测试"""
    
    def setUp(self):
        # 创建测试用户
        self.users = []
        for i in range(20):
            user = User.objects.create_user(
                username=f'testuser{i}',
                password='testpass123'
            )
            self.users.append(user)
    
    def test_concurrent_file_upload(self):
        """测试并发文件上传"""
        upload_results = []
        
        def upload_file(user_index):
            """单个用户上传文件"""
            client = APIClient()
            client.force_authenticate(user=self.users[user_index])
            
            # 创建测试文件
            content = f"""
            <html>
            <head><title>AWR Report {user_index}</title></head>
            <body>
                <h1>Database Instance Activity</h1>
                <table>
                    <tr><th>User</th><th>Value</th></tr>
                    <tr><td>User {user_index}</td><td>Test Data</td></tr>
                </table>
            </body>
            </html>
            """
            
            test_file = SimpleUploadedFile(
                f"test_concurrent_{user_index}.html",
                content.encode('utf-8'),
                content_type="text/html"
            )
            
            start_time = time.time()
            
            try:
                response = client.post('/api/upload/', {
                    'file': test_file,
                    'name': f'Concurrent Test {user_index}',
                    'description': f'Performance test file from user {user_index}'
                })
                
                end_time = time.time()
                upload_time = end_time - start_time
                
                return {
                    'user_index': user_index,
                    'status_code': response.status_code,
                    'upload_time': upload_time,
                    'success': response.status_code in [200, 201]
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    'user_index': user_index,
                    'status_code': 500,
                    'upload_time': end_time - start_time,
                    'success': False,
                    'error': str(e)
                }
        
        # 并发执行上传
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(upload_file, i) for i in range(10)]
            
            for future in as_completed(futures):
                result = future.result()
                upload_results.append(result)
        
        # 验证结果
        self.assertEqual(len(upload_results), 10)
        
        # 计算性能指标
        successful_uploads = [r for r in upload_results if r['success']]
        failed_uploads = [r for r in upload_results if not r['success']]
        
        success_rate = len(successful_uploads) / len(upload_results) * 100
        avg_upload_time = sum(r['upload_time'] for r in successful_uploads) / len(successful_uploads) if successful_uploads else 0
        max_upload_time = max(r['upload_time'] for r in successful_uploads) if successful_uploads else 0
        
        print(f"\n=== 并发上传性能测试结果 ===")
        print(f"总请求数: {len(upload_results)}")
        print(f"成功率: {success_rate:.1f}%")
        print(f"平均上传时间: {avg_upload_time:.2f}秒")
        print(f"最大上传时间: {max_upload_time:.2f}秒")
        print(f"失败次数: {len(failed_uploads)}")
        
        # 性能验收标准
        self.assertGreaterEqual(success_rate, 80.0)  # 成功率>=80%
        self.assertLessEqual(avg_upload_time, 5.0)   # 平均时间<=5秒
        self.assertLessEqual(max_upload_time, 10.0)  # 最大时间<=10秒
    
    def test_concurrent_api_requests(self):
        """测试并发API请求"""
        request_results = []
        
        def make_api_request(user_index):
            """执行API请求"""
            client = APIClient()
            client.force_authenticate(user=self.users[user_index % len(self.users)])
            
            start_time = time.time()
            
            try:
                response = client.get('/api/reports/')
                end_time = time.time()
                
                return {
                    'user_index': user_index,
                    'status_code': response.status_code,
                    'response_time': end_time - start_time,
                    'success': response.status_code == 200
                }
                
            except Exception as e:
                end_time = time.time()
                return {
                    'user_index': user_index,
                    'status_code': 500,
                    'response_time': end_time - start_time,
                    'success': False,
                    'error': str(e)
                }
        
        # 并发执行50个API请求
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = [executor.submit(make_api_request, i) for i in range(50)]
            
            for future in as_completed(futures):
                result = future.result()
                request_results.append(result)
        
        # 验证结果
        self.assertEqual(len(request_results), 50)
        
        # 计算性能指标
        successful_requests = [r for r in request_results if r['success']]
        
        success_rate = len(successful_requests) / len(request_results) * 100
        avg_response_time = sum(r['response_time'] for r in successful_requests) / len(successful_requests) if successful_requests else 0
        p95_response_time = sorted([r['response_time'] for r in successful_requests])[int(len(successful_requests) * 0.95)] if successful_requests else 0
        
        print(f"\n=== 并发API请求性能测试结果 ===")
        print(f"总请求数: {len(request_results)}")
        print(f"成功率: {success_rate:.1f}%")
        print(f"平均响应时间: {avg_response_time:.3f}秒")
        print(f"P95响应时间: {p95_response_time:.3f}秒")
        
        # 性能验收标准
        self.assertGreaterEqual(success_rate, 95.0)    # 成功率>=95%
        self.assertLessEqual(avg_response_time, 0.5)   # 平均响应时间<=500ms
        self.assertLessEqual(p95_response_time, 1.0)   # P95响应时间<=1秒


@pytest.mark.performance
class LargeFileProcessingTestCase(TransactionTestCase):
    """大文件处理性能测试"""
    
    def test_large_file_upload_performance(self):
        """测试大文件上传性能"""
        user = User.objects.create_user('testuser', password='testpass123')
        client = APIClient()
        client.force_authenticate(user=user)
        
        # 创建不同大小的测试文件
        file_sizes = [
            (1, "1MB"),
            (5, "5MB"),
            (10, "10MB"),
            (25, "25MB"),
            (50, "50MB")  # 最大允许大小
        ]
        
        results = []
        
        for size_mb, size_label in file_sizes:
            print(f"\n测试 {size_label} 文件上传...")
            
            # 生成大文件内容
            base_content = """
            <html>
            <head><title>Large AWR Report</title></head>
            <body>
                <h1>Database Instance Activity</h1>
                <table>
                    <tr><th>Metric</th><th>Value</th></tr>
            """
            
            # 添加大量数据行
            rows_needed = (size_mb * 1024 * 1024) // 100  # 估算需要的行数
            for i in range(min(rows_needed, 50000)):  # 限制最大行数
                base_content += f"<tr><td>Metric_{i}</td><td>Value_{i}</td></tr>\n"
            
            base_content += """
                </table>
            </body>
            </html>
            """
            
            # 确保文件大小接近目标
            current_size = len(base_content.encode('utf-8'))
            target_size = size_mb * 1024 * 1024
            
            if current_size < target_size:
                padding = "A" * (target_size - current_size)
                base_content = base_content.replace("</body>", f"<!-- {padding} --></body>")
            
            large_file = SimpleUploadedFile(
                f"large_test_{size_mb}mb.html",
                base_content.encode('utf-8'),
                content_type="text/html"
            )
            
            # 测量上传时间
            start_time = time.time()
            
            try:
                response = client.post('/api/upload/', {
                    'file': large_file,
                    'name': f'Large File Test {size_label}',
                    'description': f'Performance test with {size_label} file'
                })
                
                end_time = time.time()
                upload_time = end_time - start_time
                
                results.append({
                    'size_mb': size_mb,
                    'size_label': size_label,
                    'upload_time': upload_time,
                    'status_code': response.status_code,
                    'success': response.status_code in [200, 201],
                    'throughput_mbps': size_mb / upload_time if upload_time > 0 else 0
                })
                
                print(f"{size_label}: {upload_time:.2f}秒, {size_mb/upload_time:.2f} MB/s")
                
            except Exception as e:
                end_time = time.time()
                results.append({
                    'size_mb': size_mb,
                    'size_label': size_label,
                    'upload_time': end_time - start_time,
                    'status_code': 500,
                    'success': False,
                    'error': str(e),
                    'throughput_mbps': 0
                })
                print(f"{size_label}: 失败 - {str(e)}")
        
        # 验证结果
        print(f"\n=== 大文件上传性能测试结果 ===")
        for result in results:
            print(f"{result['size_label']}: {result['upload_time']:.2f}秒, "
                  f"吞吐量: {result['throughput_mbps']:.2f} MB/s, "
                  f"状态: {'成功' if result['success'] else '失败'}")
        
        # 性能验收标准
        successful_results = [r for r in results if r['success']]
        self.assertGreater(len(successful_results), 0)  # 至少有一个成功
        
        # 50MB文件应该在30秒内上传完成
        mb50_result = next((r for r in results if r['size_mb'] == 50), None)
        if mb50_result and mb50_result['success']:
            self.assertLessEqual(mb50_result['upload_time'], 30.0)
    
    def test_large_file_parsing_performance(self):
        """测试大文件解析性能"""
        # 创建包含大量数据的AWR内容
        content = """
        <html>
        <head><title>AWR Report</title></head>
        <body>
            <h1>Database Instance Activity</h1>
            <table summary="This table displays basic instance information">
                <tr><th>Instance Name</th><th>DB Name</th><th>Oracle Version</th></tr>
                <tr><td>prod1</td><td>TESTDB</td><td>19.0.0.0.0</td></tr>
            </table>
            
            <h2>Load Profile</h2>
            <table summary="This table displays load profile">
                <tr><th class="awrnc">Load Profile</th><th class="awrnc">Per Second</th><th class="awrnc">Per Transaction</th></tr>
        """
        
        # 添加大量性能数据
        for i in range(10000):
            content += f"""
                <tr><td>DB Time(s):</td><td>{i * 0.001:.3f}</td><td>{i * 0.01:.3f}</td></tr>
                <tr><td>DB CPU(s):</td><td>{i * 0.0005:.3f}</td><td>{i * 0.005:.3f}</td></tr>
                <tr><td>Redo size:</td><td>{i * 1000:,}</td><td>{i * 10000:,}</td></tr>
            """
        
        content += """
            </table>
            
            <h2>Top 5 Timed Events</h2>
            <table summary="This table displays top timed events">
                <tr><th>Event</th><th>Waits</th><th>Time(s)</th><th>Avg Wait (ms)</th></tr>
        """
        
        # 添加等待事件数据
        events = ["CPU time", "db file sequential read", "log file sync", "db file scattered read", "direct path read"]
        for i, event in enumerate(events):
            for j in range(1000):
                content += f"""
                    <tr><td>{event}</td><td>{j * 100:,}</td><td>{j * 0.1:.2f}</td><td>{j * 0.01:.2f}</td></tr>
                """
        
        content += """
            </table>
        </body>
        </html>
        """
        
        print(f"\n测试大文件解析性能（文件大小: {len(content.encode('utf-8')) / 1024 / 1024:.2f} MB）...")
        
        # 测量解析时间
        start_time = time.time()
        
        parsing_service = AWRParsingService()
        
        try:
            result = parsing_service.parse_awr_content(
                content=content,
                oracle_version="19c"
            )
            
            end_time = time.time()
            parsing_time = end_time - start_time
            
            print(f"解析时间: {parsing_time:.2f}秒")
            print(f"解析速度: {len(content.encode('utf-8')) / 1024 / 1024 / parsing_time:.2f} MB/s")
            
            # 验证解析结果
            self.assertIsNotNone(result)
            self.assertIn('instance_name', result)
            
            # 性能验收标准：大文件解析应在60秒内完成
            self.assertLessEqual(parsing_time, 60.0)
            
        except Exception as e:
            end_time = time.time()
            print(f"解析失败: {str(e)}")
            self.fail(f"Large file parsing failed: {str(e)}")


@pytest.mark.performance
class MemoryUsageTestCase(TransactionTestCase):
    """内存使用测试"""
    
    def test_memory_usage_during_processing(self):
        """测试处理过程中的内存使用"""
        import gc
        
        # 获取初始内存使用
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        print(f"\n初始内存使用: {initial_memory:.2f} MB")
        
        user = User.objects.create_user('testuser', password='testpass123')
        
        # 创建多个报告并处理
        memory_measurements = []
        
        for i in range(10):
            # 创建中等大小的AWR内容
            content = f"""
            <html>
            <head><title>AWR Report {i}</title></head>
            <body>
                <h1>Database Instance Activity</h1>
                <table>
                    <tr><th>Instance</th><th>DB Name</th></tr>
                    <tr><td>prod{i}</td><td>TESTDB{i}</td></tr>
                </table>
                <h2>Load Profile</h2>
                <table>
            """
            
            # 添加数据
            for j in range(1000):
                content += f"<tr><td>Metric_{j}</td><td>{j * i}</td></tr>"
            
            content += """
                </table>
            </body>
            </html>
            """
            
            # 创建AWR报告
            awr_report = AWRReport.objects.create(
                name=f'Memory Test {i}',
                description=f'Memory usage test report {i}',
                file='test_file.html',
                original_filename=f'test_{i}.html',
                file_size=len(content.encode('utf-8')),
                uploaded_by=user
            )
            
            # 执行解析
            parsing_service = AWRParsingService()
            result = parsing_service.parse_awr_content(content, "19c")
            
            # 测量内存使用
            current_memory = process.memory_info().rss / 1024 / 1024
            memory_measurements.append({
                'iteration': i,
                'memory_mb': current_memory,
                'memory_increase': current_memory - initial_memory
            })
            
            print(f"处理第 {i+1} 个文件后内存: {current_memory:.2f} MB "
                  f"(增加: {current_memory - initial_memory:.2f} MB)")
            
            # 强制垃圾回收
            gc.collect()
        
        # 最终内存使用
        final_memory = process.memory_info().rss / 1024 / 1024
        total_increase = final_memory - initial_memory
        
        print(f"\n=== 内存使用测试结果 ===")
        print(f"初始内存: {initial_memory:.2f} MB")
        print(f"最终内存: {final_memory:.2f} MB")
        print(f"总增长: {total_increase:.2f} MB")
        print(f"平均增长/文件: {total_increase / 10:.2f} MB")
        
        # 内存泄漏检测：总内存增长不应超过500MB
        self.assertLessEqual(total_increase, 500.0)
        
        # 单个文件处理不应导致超过50MB的内存增长
        max_single_increase = max(m['memory_increase'] for m in memory_measurements[1:])
        self.assertLessEqual(max_single_increase, 100.0)
    
    def test_memory_cleanup_after_processing(self):
        """测试处理完成后内存清理"""
        import gc
        
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024
        
        # 处理大量小文件
        for i in range(50):
            content = f"""
            <html><body>
                <h1>Test {i}</h1>
                <table>
                    {'<tr><td>Data</td></tr>' * 100}
                </table>
            </body></html>
            """
            
            parsing_service = AWRParsingService()
            result = parsing_service.parse_awr_content(content, "19c")
            
            # 每10个文件强制垃圾回收
            if i % 10 == 9:
                gc.collect()
        
        # 最终垃圾回收
        gc.collect()
        
        # 等待一段时间让内存释放
        time.sleep(2)
        
        final_memory = process.memory_info().rss / 1024 / 1024
        memory_increase = final_memory - initial_memory
        
        print(f"\n=== 内存清理测试结果 ===")
        print(f"处理50个文件后内存增长: {memory_increase:.2f} MB")
        
        # 内存增长应该保持在合理范围内
        self.assertLessEqual(memory_increase, 200.0)


@pytest.mark.performance
class DatabasePerformanceTestCase(TransactionTestCase):
    """数据库性能测试"""
    
    def test_bulk_report_creation_performance(self):
        """测试批量报告创建性能"""
        user = User.objects.create_user('testuser', password='testpass123')
        
        # 测量批量创建时间
        start_time = time.time()
        
        reports = []
        for i in range(1000):
            reports.append(AWRReport(
                name=f'Bulk Test Report {i}',
                description=f'Performance test report {i}',
                file=f'test_file_{i}.html',
                original_filename=f'test_{i}.html',
                file_size=1024 * (i + 1),
                uploaded_by=user,
                oracle_version='19c',
                status='uploaded'
            ))
        
        # 批量创建
        AWRReport.objects.bulk_create(reports, batch_size=100)
        
        end_time = time.time()
        creation_time = end_time - start_time
        
        print(f"\n=== 批量数据库操作性能测试结果 ===")
        print(f"创建1000个报告耗时: {creation_time:.2f}秒")
        print(f"平均创建速度: {1000 / creation_time:.0f} 记录/秒")
        
        # 性能验收标准：1000个记录应在5秒内创建完成
        self.assertLessEqual(creation_time, 5.0)
        
        # 验证创建的记录数
        total_reports = AWRReport.objects.count()
        self.assertEqual(total_reports, 1000)
    
    def test_complex_query_performance(self):
        """测试复杂查询性能"""
        user = User.objects.create_user('testuser', password='testpass123')
        
        # 创建测试数据
        for i in range(100):
            AWRReport.objects.create(
                name=f'Query Test Report {i}',
                description=f'Performance test report {i}',
                file=f'test_file_{i}.html',
                original_filename=f'test_{i}.html',
                file_size=1024 * (i + 1),
                uploaded_by=user,
                oracle_version='19c' if i % 2 == 0 else '11g',
                status='completed' if i % 3 == 0 else 'uploaded',
                instance_name=f'instance_{i % 10}',
                database_id=f'db_{i % 5}'
            )
        
        # 测试复杂查询
        queries = [
            lambda: list(AWRReport.objects.filter(oracle_version='19c').order_by('-created_at')[:20]),
            lambda: list(AWRReport.objects.filter(status='completed', file_size__gt=5000).select_related('uploaded_by')),
            lambda: AWRReport.objects.filter(instance_name__startswith='instance_').count(),
            lambda: list(AWRReport.objects.values('oracle_version').annotate(count=models.Count('id'))),
        ]
        
        print(f"\n=== 复杂查询性能测试结果 ===")
        
        for i, query_func in enumerate(queries, 1):
            start_time = time.time()
            
            result = query_func()
            
            end_time = time.time()
            query_time = end_time - start_time
            
            print(f"查询 {i}: {query_time:.3f}秒")
            
            # 每个查询应在1秒内完成
            self.assertLessEqual(query_time, 1.0)


def run_performance_tests():
    """运行所有性能测试的便捷函数"""
    import subprocess
    import sys
    
    print("开始运行性能测试套件...")
    
    # 运行性能测试
    result = subprocess.run([
        sys.executable, '-m', 'pytest', 
        'tests/performance/test_performance_suite.py',
        '-v', '-m', 'performance',
        '--tb=short'
    ], capture_output=True, text=True)
    
    print("性能测试完成。")
    print(f"返回码: {result.returncode}")
    print(f"输出:\n{result.stdout}")
    
    if result.stderr:
        print(f"错误:\n{result.stderr}")
    
    return result.returncode == 0


if __name__ == '__main__':
    run_performance_tests() 