#!/usr/bin/env python3
"""
API修复验证测试脚本
{{CHENGQI: 创建API修复验证测试 - 2025-06-10 12:43:34 +08:00 - 
Action: Added; Reason: 验证解析结果API修复效果; Principle_Applied: 测试驱动}}
"""

import requests
import json
import sys
from datetime import datetime

def test_parse_result_api():
    """测试解析结果API"""
    
    print("=== AWR解析结果API修复验证测试 ===")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 测试参数
    base_url = "http://127.0.0.1"
    report_id = 19
    
    # 1. 测试健康检查
    print("1. 测试后端健康检查...")
    try:
        response = requests.get(f"{base_url}/api/health/", timeout=10)
        if response.status_code == 200:
            print("   ✓ 后端健康检查正常")
        else:
            print(f"   ✗ 后端健康检查失败: {response.status_code}")
            return False
    except Exception as e:
        print(f"   ✗ 后端连接失败: {e}")
        return False
    
    # 2. 测试解析结果API
    print("2. 测试解析结果API...")
    try:
        response = requests.get(f"{base_url}/api/parse-results/{report_id}/", timeout=30)
        
        if response.status_code == 200:
            print(f"   ✓ API响应正常 (状态码: {response.status_code})")
            
            # 解析JSON响应
            try:
                data = response.json()
                print(f"   ✓ JSON解析成功")
                
                # 验证必要字段
                required_fields = ['id', 'status', 'progress', 'data_completeness']
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    print(f"   ✗ 缺少必要字段: {missing_fields}")
                    return False
                else:
                    print(f"   ✓ 包含所有必要字段")
                
                # 显示关键信息
                print(f"   - 报告ID: {data.get('id')}")
                print(f"   - 状态: {data.get('status')}")
                print(f"   - 进度: {data.get('progress')}%")
                print(f"   - 数据完整性: {data.get('data_completeness')}%")
                print(f"   - 解析区块数: {data.get('sections_parsed')}/{data.get('total_sections')}")
                
                # 检查数据内容
                if data.get('db_info'):
                    print(f"   - 数据库版本: {data['db_info'].get('db_version')}")
                    print(f"   - 实例名称: {data['db_info'].get('instance_name')}")
                
                if data.get('snapshot_info'):
                    print(f"   - 快照时间: {data['snapshot_info'].get('begin_time')} - {data['snapshot_info'].get('end_time')}")
                
                wait_events_count = len(data.get('wait_events', []))
                sql_stats_count = len(data.get('sql_statistics', []))
                print(f"   - 等待事件数: {wait_events_count}")
                print(f"   - SQL统计数: {sql_stats_count}")
                
                print("   ✓ 解析结果API测试通过")
                return True
                
            except json.JSONDecodeError as e:
                print(f"   ✗ JSON解析失败: {e}")
                print(f"   响应内容: {response.text[:200]}...")
                return False
                
        elif response.status_code == 404:
            print(f"   ✗ API端点不存在 (404) - 修复可能未生效")
            return False
        elif response.status_code == 400:
            print(f"   ✗ 报告状态不符合要求 (400)")
            print(f"   响应: {response.text}")
            return False
        else:
            print(f"   ✗ API响应异常 (状态码: {response.status_code})")
            print(f"   响应: {response.text}")
            return False
            
    except requests.exceptions.Timeout:
        print(f"   ✗ 请求超时")
        return False
    except Exception as e:
        print(f"   ✗ 请求失败: {e}")
        return False

def test_report_list_api():
    """测试报告列表API"""
    print("3. 测试报告列表API...")
    try:
        # 由于权限问题，这里可能需要认证，我们先测试端点是否存在
        response = requests.get("http://127.0.0.1/api/reports/", timeout=10)
        
        if response.status_code == 403:
            print("   ✓ 报告列表API存在 (需要认证)")
            return True
        elif response.status_code == 200:
            print("   ✓ 报告列表API正常响应")
            return True
        else:
            print(f"   - 报告列表API状态: {response.status_code}")
            return True  # 非关键测试
            
    except Exception as e:
        print(f"   ✗ 报告列表API测试失败: {e}")
        return True  # 非关键测试

if __name__ == "__main__":
    print("开始API修复验证测试...")
    print()
    
    success = test_parse_result_api()
    test_report_list_api()
    
    print()
    print("=== 测试结果汇总 ===")
    if success:
        print("✓ 主要功能测试通过 - API修复成功")
        print("✓ 前端现在应该可以正常显示解析结果")
        sys.exit(0)
    else:
        print("✗ 主要功能测试失败 - 需要进一步调试")
        sys.exit(1) 