#!/usr/bin/env python3
"""
综合修复验证脚本
验证关键修复是否解决了测试失败问题
"""

import os
import sys
import time
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from apps.awr_parser.parsers.factory import create_parser, get_parser_factory
from apps.awr_parser.parsers.base import OracleVersion, ParseStatus
from apps.awr_parser.parsers.utils import VersionDetector

def test_version_detection():
    """测试版本检测修复"""
    print("=== 测试版本检测修复 ===")
    
    # 模拟Oracle 11g AWR内容
    oracle_11g_content = """
    <html>
    <head><title>WORKLOAD REPOSITORY report for DB: TESTDB</title></head>
    <body>
    <h1>ORACLE Database 11g Enterprise Edition Release 11.2.0.4.0 - 64bit Production</h1>
    <table>
    <tr><td>Database Id</td><td>1234567890</td></tr>
    <tr><td>Instance</td><td>TESTDB</td></tr>
    <tr><td>Release</td><td>11.2.0.4.0</td></tr>
    </table>
    </body>
    </html>
    """
    
    try:
        # 测试版本检测
        detector = VersionDetector()
        detected_version = detector.detect_version(oracle_11g_content)
        print(f"检测到的版本: {detected_version}")
        print(f"版本类型: {type(detected_version)}")
        print(f"是否为11g: {detected_version == OracleVersion.ORACLE_11G}")
        
        # 测试工厂创建解析器
        parser = create_parser(oracle_11g_content)
        print(f"创建的解析器: {parser}")
        print(f"解析器类型: {type(parser)}")
        
        if parser:
            # 测试解析
            result = parser.parse(oracle_11g_content)
            print(f"解析状态: {result.parse_status}")
            print(f"解析结果: {result}")
            
            if result.db_info:
                print(f"数据库版本: {result.db_info.version}")
                print(f"实例编号: {result.db_info.instance_number}")
            
        return True
        
    except Exception as e:
        print(f"版本检测测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_factory_registry():
    """测试工厂注册表修复"""
    print("\n=== 测试工厂注册表修复 ===")
    
    try:
        factory = get_parser_factory()
        supported_versions = factory.get_supported_versions()
        
        print(f"支持的版本: {[v.value for v in supported_versions]}")
        
        for version in supported_versions:
            print(f"版本 {version.value} (类型: {type(version)})")
            parser = factory.create_parser_by_version(version)
            print(f"  - 解析器: {parser}")
        
        return True
        
    except Exception as e:
        print(f"工厂注册表测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_error_handling():
    """测试错误处理修复"""
    print("\n=== 测试错误处理修复 ===")
    
    # 测试无效HTML
    invalid_html = "<html><title>Not AWR</title></html>"
    
    try:
        parser = create_parser(invalid_html)
        print(f"无效HTML解析器: {parser}")
        
        if parser:
            result = parser.parse(invalid_html)
            print(f"无效HTML解析状态: {result.parse_status}")
            print(f"解析结果有效: {result is not None}")
        
        return True
        
    except Exception as e:
        print(f"错误处理测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_real_file_parsing():
    """测试真实文件解析"""
    print("\n=== 测试真实文件解析 ===")
    
    awrrpt_dir = Path("awrrpt")
    if not awrrpt_dir.exists():
        print("awrrpt目录不存在，跳过真实文件测试")
        return True
    
    html_files = list(awrrpt_dir.glob("**/*.html"))[:3]  # 只测试前3个文件
    
    success_count = 0
    for html_file in html_files:
        try:
            print(f"测试文件: {html_file}")
            
            with open(html_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            start_time = time.time()
            parser = create_parser(content)
            
            if parser:
                result = parser.parse(content)
                parse_time = time.time() - start_time
                
                print(f"  - 解析器: {type(parser).__name__}")
                print(f"  - 解析状态: {result.parse_status}")
                print(f"  - 解析时间: {parse_time:.2f}s")
                
                if result.db_info:
                    print(f"  - 数据库版本: {result.db_info.version}")
                
                success_count += 1
            else:
                print(f"  - 无法创建解析器")
                
        except Exception as e:
            print(f"  - 解析失败: {e}")
    
    print(f"成功解析文件数: {success_count}/{len(html_files)}")
    return success_count > 0

def main():
    """主函数"""
    print("综合修复验证开始...")
    
    tests = [
        ("版本检测", test_version_detection),
        ("工厂注册表", test_factory_registry),
        ("错误处理", test_error_handling),
        ("真实文件解析", test_real_file_parsing),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'='*50}")
        print(f"运行测试: {test_name}")
        print(f"{'='*50}")
        
        try:
            if test_func():
                print(f"✅ {test_name} 测试通过")
                passed += 1
            else:
                print(f"❌ {test_name} 测试失败")
        except Exception as e:
            print(f"❌ {test_name} 测试异常: {e}")
    
    print(f"\n{'='*50}")
    print(f"测试总结: {passed}/{total} 通过")
    print(f"{'='*50}")
    
    return passed == total

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 