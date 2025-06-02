#!/usr/bin/env python3
"""
AWR解析器性能基准测试套件
{{CHENGQI: P2-TE-006 解析器测试套件 - 性能基准测试 - 2025-06-02T15:23:28}}

验证解析器性能指标：
1. 解析速度基准
2. 内存使用基准
3. 并发处理基准
4. 大文件处理基准
5. 资源泄漏检测
"""

import gc
import logging
import os
import time
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import List, Dict, Any
import statistics

from ..parsers.factory import create_parser, parse_awr
from ..parsers.base import ParseStatus


class AWRPerformanceBenchmarkTestCase(unittest.TestCase):
    """AWR解析器性能基准测试"""
    
    @classmethod
    def setUpClass(cls):
        """设置基准测试环境"""
        # 性能基准目标
        cls.PERFORMANCE_TARGETS = {
            'small_file_time': 2.0,      # 小文件(<1MB) 解析时间 < 2秒
            'medium_file_time': 5.0,     # 中文件(1-5MB) 解析时间 < 5秒
            'large_file_time': 30.0,     # 大文件(>5MB) 解析时间 < 30秒
            'memory_increase_mb': 200,   # 内存增长 < 200MB
            'concurrent_threads': 10,    # 支持10并发解析
            'memory_leak_threshold': 50, # 内存泄漏阈值 < 50MB
        }
        
        # 收集测试文件
        cls.test_files = cls._collect_test_files()
        
        # 性能统计
        cls.performance_stats = {
            'parsing_times': [],
            'memory_usage': [],
            'concurrent_results': [],
            'error_rates': [],
        }
    
    @classmethod
    def _collect_test_files(cls) -> Dict[str, List[Path]]:
        """收集并分类测试文件"""
        awrrpt_dir = Path("awrrpt")
        files_by_size = {
            'small': [],    # < 1MB
            'medium': [],   # 1-5MB
            'large': [],    # > 5MB
        }
        
        if awrrpt_dir.exists():
            for awr_file in awrrpt_dir.glob("**/*.html"):
                file_size_mb = awr_file.stat().st_size / (1024 * 1024)
                
                if file_size_mb < 1:
                    files_by_size['small'].append(awr_file)
                elif file_size_mb < 5:
                    files_by_size['medium'].append(awr_file)
                else:
                    files_by_size['large'].append(awr_file)
        
        return files_by_size
    
    def setUp(self):
        """设置单个测试"""
        # 强制垃圾回收
        gc.collect()
        
        # 记录初始内存状态
        self.initial_memory = self._get_memory_usage()
    
    def _get_memory_usage(self) -> float:
        """获取当前内存使用量(MB)"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024
        except ImportError:
            return 0.0  # psutil不可用时返回0
    
    def _create_synthetic_awr(self, size_mb: float) -> str:
        """创建指定大小的合成AWR内容"""
        base_content = """
        <html>
        <head><title>WORKLOAD REPOSITORY report for DB: PERF</title></head>
        <body>
        <h1>ORACLE Database 19c Enterprise Edition</h1>
        <a name="summary"></a>
        <table summary="Performance Test Data">
        <tr><th>Metric</th><th>Value</th><th>Description</th></tr>
        """
        
        # 计算需要的行数以达到目标大小
        target_bytes = size_mb * 1024 * 1024
        current_size = len(base_content.encode('utf-8'))
        
        # 每行大约100字节
        rows_needed = (target_bytes - current_size) // 100
        
        for i in range(int(rows_needed)):
            base_content += f"""
            <tr>
            <td>Performance Metric {i:06d}</td>
            <td>{i * 1.234567:.6f}</td>
            <td>Generated metric for performance testing purposes - iteration {i}</td>
            </tr>
            """
        
        base_content += """
        </table>
        </body>
        </html>
        """
        
        return base_content
    
    def test_small_file_parsing_benchmark(self):
        """小文件解析性能基准测试"""
        if not self.test_files['small']:
            # 如果没有小文件，创建合成文件
            synthetic_content = self._create_synthetic_awr(0.5)  # 0.5MB
            test_files = [('synthetic_small.html', synthetic_content)]
        else:
            test_files = [(f.name, open(f, 'r', encoding='utf-8').read()) 
                         for f in self.test_files['small'][:3]]
        
        parsing_times = []
        
        for filename, content in test_files:
            with self.subTest(file=filename):
                start_time = time.time()
                
                parser = create_parser(content)
                if parser:
                    result = parser.parse(content)
                    self.assertIn(result.parse_status, [ParseStatus.SUCCESS, ParseStatus.PARTIAL])
                
                end_time = time.time()
                parsing_time = end_time - start_time
                parsing_times.append(parsing_time)
                
                # 验证小文件性能目标
                self.assertLess(parsing_time, self.PERFORMANCE_TARGETS['small_file_time'],
                              f"Small file {filename} parsing took {parsing_time:.2f}s, "
                              f"expected < {self.PERFORMANCE_TARGETS['small_file_time']}s")
        
        # 记录统计
        if parsing_times:
            avg_time = statistics.mean(parsing_times)
            self.performance_stats['parsing_times'].extend(parsing_times)
            print(f"Small files average parsing time: {avg_time:.2f}s")
    
    def test_medium_file_parsing_benchmark(self):
        """中文件解析性能基准测试"""
        if not self.test_files['medium']:
            # 创建合成中等大小文件
            synthetic_content = self._create_synthetic_awr(2.5)  # 2.5MB
            test_files = [('synthetic_medium.html', synthetic_content)]
        else:
            test_files = [(f.name, open(f, 'r', encoding='utf-8').read()) 
                         for f in self.test_files['medium'][:2]]
        
        parsing_times = []
        
        for filename, content in test_files:
            with self.subTest(file=filename):
                start_time = time.time()
                
                parser = create_parser(content)
                if parser:
                    result = parser.parse(content)
                
                end_time = time.time()
                parsing_time = end_time - start_time
                parsing_times.append(parsing_time)
                
                # 验证中文件性能目标
                self.assertLess(parsing_time, self.PERFORMANCE_TARGETS['medium_file_time'],
                              f"Medium file {filename} parsing took {parsing_time:.2f}s, "
                              f"expected < {self.PERFORMANCE_TARGETS['medium_file_time']}s")
        
        # 记录统计
        if parsing_times:
            avg_time = statistics.mean(parsing_times)
            self.performance_stats['parsing_times'].extend(parsing_times)
            print(f"Medium files average parsing time: {avg_time:.2f}s")
    
    def test_large_file_parsing_benchmark(self):
        """大文件解析性能基准测试"""
        if not self.test_files['large']:
            # 创建合成大文件
            synthetic_content = self._create_synthetic_awr(8.0)  # 8MB
            test_files = [('synthetic_large.html', synthetic_content)]
        else:
            test_files = [(f.name, open(f, 'r', encoding='utf-8').read()) 
                         for f in self.test_files['large'][:1]]  # 只测试1个大文件
        
        for filename, content in test_files:
            with self.subTest(file=filename):
                file_size_mb = len(content.encode('utf-8')) / (1024 * 1024)
                
                start_time = time.time()
                
                parser = create_parser(content)
                if parser:
                    result = parser.parse(content)
                
                end_time = time.time()
                parsing_time = end_time - start_time
                
                # 验证大文件性能目标
                self.assertLess(parsing_time, self.PERFORMANCE_TARGETS['large_file_time'],
                              f"Large file {filename} ({file_size_mb:.1f}MB) parsing took "
                              f"{parsing_time:.2f}s, expected < {self.PERFORMANCE_TARGETS['large_file_time']}s")
                
                print(f"Large file {filename} ({file_size_mb:.1f}MB): {parsing_time:.2f}s")
    
    def test_memory_usage_benchmark(self):
        """内存使用基准测试"""
        if not hasattr(self, 'initial_memory') or self.initial_memory == 0:
            self.skipTest("Memory monitoring not available (psutil required)")
        
        # 创建中等大小的测试内容
        test_content = self._create_synthetic_awr(3.0)  # 3MB
        
        # 解析前内存
        gc.collect()
        mem_before = self._get_memory_usage()
        
        # 执行解析
        parser = create_parser(test_content)
        if parser:
            result = parser.parse(test_content)
        
        # 解析后内存
        mem_after = self._get_memory_usage()
        memory_increase = mem_after - mem_before
        
        # 记录内存使用
        self.performance_stats['memory_usage'].append(memory_increase)
        
        # 验证内存使用目标
        self.assertLess(memory_increase, self.PERFORMANCE_TARGETS['memory_increase_mb'],
                       f"Memory increase {memory_increase:.1f}MB exceeds target "
                       f"{self.PERFORMANCE_TARGETS['memory_increase_mb']}MB")
        
        print(f"Memory usage: +{memory_increase:.1f}MB")
    
    def test_concurrent_parsing_benchmark(self):
        """并发解析性能基准测试"""
        # 创建测试内容
        test_contents = [
            self._create_synthetic_awr(1.0) for _ in range(10)
        ]
        
        def parse_content(content_index):
            """单个解析任务"""
            content = test_contents[content_index]
            start_time = time.time()
            
            try:
                parser = create_parser(content)
                if parser:
                    result = parser.parse(content)
                    success = result.parse_status in [ParseStatus.SUCCESS, ParseStatus.PARTIAL]
                else:
                    success = False
            except Exception as e:
                success = False
            
            end_time = time.time()
            return {
                'index': content_index,
                'success': success,
                'time': end_time - start_time,
                'thread_id': threading.current_thread().ident
            }
        
        # 并发执行
        start_time = time.time()
        
        with ThreadPoolExecutor(max_workers=self.PERFORMANCE_TARGETS['concurrent_threads']) as executor:
            futures = [executor.submit(parse_content, i) for i in range(10)]
            results = [future.result() for future in as_completed(futures)]
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # 分析结果
        successful_parses = sum(1 for r in results if r['success'])
        avg_parse_time = statistics.mean([r['time'] for r in results])
        unique_threads = len(set(r['thread_id'] for r in results))
        
        # 记录统计
        self.performance_stats['concurrent_results'].extend(results)
        
        # 验证并发性能
        success_rate = successful_parses / len(results)
        self.assertGreater(success_rate, 0.9, f"Concurrent parsing success rate {success_rate:.1%} too low")
        
        # 并发应该比串行快
        expected_serial_time = avg_parse_time * 10
        speedup = expected_serial_time / total_time
        self.assertGreater(speedup, 2.0, f"Concurrent speedup {speedup:.1f}x is too low")
        
        print(f"Concurrent parsing: {successful_parses}/10 successful, "
              f"total time: {total_time:.2f}s, speedup: {speedup:.1f}x, "
              f"threads used: {unique_threads}")
    
    def test_memory_leak_detection(self):
        """内存泄漏检测"""
        if self._get_memory_usage() == 0:
            self.skipTest("Memory monitoring not available")
        
        # 创建测试内容
        test_content = self._create_synthetic_awr(1.0)
        
        # 基线内存测量
        gc.collect()
        baseline_memory = self._get_memory_usage()
        
        # 执行多次解析
        for i in range(50):  # 50次解析
            parser = create_parser(test_content)
            if parser:
                result = parser.parse(test_content)
            
            # 每10次检查一次内存
            if i % 10 == 9:
                gc.collect()
                current_memory = self._get_memory_usage()
                memory_growth = current_memory - baseline_memory
                
                # 如果内存增长过多，可能有泄漏
                if memory_growth > self.PERFORMANCE_TARGETS['memory_leak_threshold']:
                    self.fail(f"Potential memory leak detected: "
                             f"{memory_growth:.1f}MB growth after {i+1} iterations")
        
        # 最终内存检查
        gc.collect()
        final_memory = self._get_memory_usage()
        total_growth = final_memory - baseline_memory
        
        self.assertLess(total_growth, self.PERFORMANCE_TARGETS['memory_leak_threshold'],
                       f"Memory leak detected: {total_growth:.1f}MB growth after 50 iterations")
        
        print(f"Memory leak test: {total_growth:.1f}MB growth (threshold: "
              f"{self.PERFORMANCE_TARGETS['memory_leak_threshold']}MB)")
    
    def test_parser_creation_overhead(self):
        """解析器创建开销测试"""
        # 测试内容
        test_content = """
        <html>
        <head><title>WORKLOAD REPOSITORY report</title></head>
        <body>
        <h1>ORACLE Database 19c Enterprise Edition</h1>
        </body>
        </html>
        """
        
        # 测试解析器创建时间
        creation_times = []
        
        for _ in range(100):
            start_time = time.time()
            parser = create_parser(test_content)
            end_time = time.time()
            
            creation_times.append(end_time - start_time)
        
        avg_creation_time = statistics.mean(creation_times)
        max_creation_time = max(creation_times)
        
        # 解析器创建应该很快
        self.assertLess(avg_creation_time, 0.01, 
                       f"Parser creation too slow: {avg_creation_time:.4f}s average")
        
        self.assertLess(max_creation_time, 0.05,
                       f"Parser creation too slow: {max_creation_time:.4f}s max")
        
        print(f"Parser creation: avg {avg_creation_time:.4f}s, max {max_creation_time:.4f}s")
    
    @classmethod
    def tearDownClass(cls):
        """输出性能统计摘要"""
        print(f"\n=== AWR Parser Performance Benchmark Summary ===")
        
        if cls.performance_stats['parsing_times']:
            times = cls.performance_stats['parsing_times']
            print(f"Parsing times: avg {statistics.mean(times):.2f}s, "
                  f"min {min(times):.2f}s, max {max(times):.2f}s")
        
        if cls.performance_stats['memory_usage']:
            memory = cls.performance_stats['memory_usage']
            print(f"Memory usage: avg +{statistics.mean(memory):.1f}MB, "
                  f"max +{max(memory):.1f}MB")
        
        if cls.performance_stats['concurrent_results']:
            concurrent = cls.performance_stats['concurrent_results']
            success_rate = sum(1 for r in concurrent if r['success']) / len(concurrent)
            print(f"Concurrent success rate: {success_rate:.1%}")
        
        print(f"Performance targets: {cls.PERFORMANCE_TARGETS}")


class AWRScalabilityTestCase(unittest.TestCase):
    """AWR解析器可扩展性测试"""
    
    def test_file_size_scalability(self):
        """文件大小可扩展性测试"""
        # 测试不同大小文件的解析时间
        sizes_mb = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
        parse_times = []
        
        for size_mb in sizes_mb:
            # 创建指定大小的内容
            content = self._create_scalability_content(size_mb)
            
            start_time = time.time()
            parser = create_parser(content)
            if parser:
                result = parser.parse(content)
            end_time = time.time()
            
            parse_time = end_time - start_time
            parse_times.append(parse_time)
            
            print(f"Size: {size_mb}MB, Time: {parse_time:.2f}s, "
                  f"Rate: {size_mb/parse_time:.2f}MB/s")
        
        # 分析可扩展性
        # 解析时间应该大致与文件大小成正比
        for i in range(1, len(sizes_mb)):
            size_ratio = sizes_mb[i] / sizes_mb[i-1]
            time_ratio = parse_times[i] / parse_times[i-1]
            
            # 时间比例不应该远大于大小比例（允许一些开销）
            self.assertLess(time_ratio, size_ratio * 2.0,
                           f"Poor scalability: {size_ratio:.1f}x size increase "
                           f"caused {time_ratio:.1f}x time increase")
    
    def _create_scalability_content(self, size_mb: float) -> str:
        """创建可扩展性测试内容"""
        base_content = """
        <html>
        <head><title>WORKLOAD REPOSITORY report for DB: SCALE</title></head>
        <body>
        <h1>ORACLE Database 19c Enterprise Edition</h1>
        <a name="summary"></a>
        <table>
        <tr><th>ID</th><th>SQL Text</th><th>Executions</th><th>Elapsed Time</th></tr>
        """
        
        # 计算需要的行数
        target_bytes = size_mb * 1024 * 1024
        current_size = len(base_content.encode('utf-8'))
        
        # 每行约200字节
        rows_needed = (target_bytes - current_size) // 200
        
        for i in range(int(rows_needed)):
            base_content += f"""
            <tr>
            <td>{i:08d}</td>
            <td>SELECT * FROM large_table_{i % 100} WHERE id = {i} AND status = 'ACTIVE' ORDER BY created_date DESC</td>
            <td>{i * 123}</td>
            <td>{i * 0.456:.3f}</td>
            </tr>
            """
        
        base_content += """
        </table>
        </body>
        </html>
        """
        
        return base_content


if __name__ == '__main__':
    # 配置性能测试日志
    logging.basicConfig(level=logging.WARNING,  # 减少日志噪音
                       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # 运行性能基准测试
    unittest.main(verbosity=2) 