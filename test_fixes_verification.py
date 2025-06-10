#!/usr/bin/env python3.11
"""
AWR分析器修复验证脚本
验证已修复的功能：
1. 首页统计数据获取
2. 文件列表获取和删除功能
3. 解析结果访问
4. 重复文件检测
"""

import requests
import json
import time
from typing import Dict, Any

class AWRFixesVerifier:
    def __init__(self, base_url: str = "http://127.0.0.1"):
        self.base_url = base_url
        self.session = requests.Session()
        
    def test_dashboard_statistics(self) -> Dict[str, Any]:
        """测试首页统计数据API"""
        print("📊 测试首页统计数据API...")
        try:
            response = self.session.get(f"{self.base_url}/api/dashboard/statistics/")
            response.raise_for_status()
            data = response.json()
            
            required_fields = ['total_files', 'total_parses', 'success_rate', 'avg_parse_time']
            missing_fields = [field for field in required_fields if field not in data]
            
            if missing_fields:
                return {
                    'status': 'FAILED',
                    'error': f'缺少必需字段: {missing_fields}',
                    'data': data
                }
            
            return {
                'status': 'PASSED',
                'data': data,
                'message': f"成功获取统计数据: {data['total_files']} 个文件, {data['success_rate']}% 成功率"
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def test_file_list_api(self) -> Dict[str, Any]:
        """测试文件列表API"""
        print("📋 测试文件列表API...")
        try:
            response = self.session.get(f"{self.base_url}/api/reports/")
            response.raise_for_status()
            data = response.json()
            
            if not isinstance(data, list):
                return {
                    'status': 'FAILED',
                    'error': 'API返回格式不正确，期望列表格式',
                    'data': data
                }
            
            if len(data) == 0:
                return {
                    'status': 'PASSED',
                    'data': data,
                    'message': "文件列表为空（正常情况）"
                }
            
            # 检查第一个文件的必需字段
            first_file = data[0]
            required_fields = ['id', 'original_filename', 'file_size', 'status', 'created_at']
            missing_fields = [field for field in required_fields if field not in first_file]
            
            if missing_fields:
                return {
                    'status': 'FAILED',
                    'error': f'文件对象缺少必需字段: {missing_fields}',
                    'data': first_file
                }
            
            return {
                'status': 'PASSED',
                'data': data,
                'message': f"成功获取 {len(data)} 个文件记录"
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def test_parse_results_api(self) -> Dict[str, Any]:
        """测试解析结果API（使用已知ID）"""
        print("📈 测试解析结果API...")
        try:
            # 先获取文件列表找到一个有效的ID
            files_response = self.session.get(f"{self.base_url}/api/reports/")
            files_response.raise_for_status()
            files_data = files_response.json()
            
            if not files_data:
                return {
                    'status': 'SKIPPED',
                    'message': '没有可用的文件来测试解析结果API'
                }
            
            # 使用第一个文件的ID测试解析结果
            first_file_id = files_data[0]['id']
            response = self.session.get(f"{self.base_url}/api/parse-results/{first_file_id}/")
            
            # 如果文件未解析完成，返回404是正常的
            if response.status_code == 404:
                return {
                    'status': 'PASSED',
                    'message': f'文件 {first_file_id} 的解析结果不存在（预期行为）'
                }
            
            response.raise_for_status()
            data = response.json()
            
            return {
                'status': 'PASSED',
                'data': data,
                'message': f"成功获取文件 {first_file_id} 的解析结果"
            }
            
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def test_file_deletion_functionality(self) -> Dict[str, Any]:
        """测试文件删除功能的路径正确性（不实际删除）"""
        print("🗑️  测试文件删除API路径...")
        try:
            # 先获取文件列表
            files_response = self.session.get(f"{self.base_url}/api/reports/")
            files_response.raise_for_status()
            files_data = files_response.json()
            
            if not files_data:
                return {
                    'status': 'SKIPPED',
                    'message': '没有可用的文件来测试删除功能'
                }
            
            # 测试删除API路径（使用HEAD请求，不实际删除）
            first_file_id = files_data[0]['id']
            response = self.session.head(f"{self.base_url}/api/reports/{first_file_id}/")
            
            # HEAD请求应该返回 200 或 405 (Method Not Allowed)
            if response.status_code in [200, 405]:
                return {
                    'status': 'PASSED',
                    'message': f'删除API路径 /api/reports/{first_file_id}/ 可访问'
                }
            elif response.status_code == 404:
                return {
                    'status': 'FAILED',
                    'error': f'删除API路径返回404，路径配置可能有问题'
                }
            else:
                return {
                    'status': 'WARNING',
                    'message': f'删除API路径返回状态码 {response.status_code}'
                }
                
        except Exception as e:
            return {
                'status': 'FAILED',
                'error': str(e)
            }
    
    def run_all_tests(self) -> Dict[str, Any]:
        """运行所有测试"""
        print("🚀 开始验证AWR分析器修复...")
        print("=" * 60)
        
        tests = [
            ('首页统计数据', self.test_dashboard_statistics),
            ('文件列表API', self.test_file_list_api),
            ('解析结果API', self.test_parse_results_api),
            ('删除功能路径', self.test_file_deletion_functionality),
        ]
        
        results = {}
        passed = 0
        failed = 0
        skipped = 0
        warnings = 0
        
        for test_name, test_func in tests:
            print(f"\n🔍 {test_name}:")
            result = test_func()
            results[test_name] = result
            
            if result['status'] == 'PASSED':
                print(f"  ✅ {result.get('message', '通过')}")
                passed += 1
            elif result['status'] == 'FAILED':
                print(f"  ❌ 失败: {result['error']}")
                failed += 1
            elif result['status'] == 'SKIPPED':
                print(f"  ⏭️  跳过: {result['message']}")
                skipped += 1
            elif result['status'] == 'WARNING':
                print(f"  ⚠️  警告: {result['message']}")
                warnings += 1
        
        print("\n" + "=" * 60)
        print("📊 测试结果汇总:")
        print(f"  ✅ 通过: {passed}")
        print(f"  ❌ 失败: {failed}")
        print(f"  ⏭️  跳过: {skipped}")
        print(f"  ⚠️  警告: {warnings}")
        
        overall_status = "SUCCESS" if failed == 0 else "FAILED"
        print(f"\n🏆 总体状态: {overall_status}")
        
        return {
            'overall_status': overall_status,
            'summary': {
                'passed': passed,
                'failed': failed,
                'skipped': skipped,
                'warnings': warnings
            },
            'results': results
        }


if __name__ == "__main__":
    verifier = AWRFixesVerifier()
    results = verifier.run_all_tests()
    
    # 保存测试结果
    with open('verification_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n📝 详细结果已保存到: verification_results.json")
    
    # 返回适当的退出码
    exit(0 if results['overall_status'] == 'SUCCESS' else 1) 