#!/usr/bin/env python
"""
Debug script for AWR parser factory version issue
调试解析器工厂的版本字符串问题
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'awranalyzor.settings')
django.setup()

from apps.awr_parser.parsers.base import OracleVersion
from apps.awr_parser.parsers.factory import get_parser_factory
from pathlib import Path
import logging

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_factory_versions():
    """测试工厂版本处理"""
    print("=== AWR Parser Factory Debug ===\n")
    
    # 1. 测试工厂初始化
    print("1. 测试工厂初始化:")
    factory = get_parser_factory()
    print(f"   工厂实例: {factory}")
    
    # 2. 检查支持的版本
    print("\n2. 检查支持的版本:")
    versions = factory.get_supported_versions()
    print(f"   支持的版本数量: {len(versions)}")
    for i, version in enumerate(versions):
        print(f"   版本 {i+1}: {version} (类型: {type(version)})")
        if hasattr(version, 'value'):
            print(f"            值: {version.value}")
        else:
            print(f"            无.value属性! 原始值: {repr(version)}")
    
    # 3. 测试版本枚举
    print("\n3. 测试版本枚举:")
    print(f"   ORACLE_11G: {OracleVersion.ORACLE_11G} (类型: {type(OracleVersion.ORACLE_11G)})")
    print(f"   ORACLE_12C: {OracleVersion.ORACLE_12C} (类型: {type(OracleVersion.ORACLE_12C)})")
    print(f"   ORACLE_19C: {OracleVersion.ORACLE_19C} (类型: {type(OracleVersion.ORACLE_19C)})")
    
    # 4. 测试注册状态
    print("\n4. 测试注册状态:")
    registry = factory._registry
    print(f"   注册表解析器数量: {len(registry._parsers)}")
    for version, parser_class in registry._parsers.items():
        print(f"   {version} (类型: {type(version)}) -> {parser_class}")
    
    # 5. 测试AWR文件
    print("\n5. 测试AWR文件解析器创建:")
    awrrpt_dir = Path("awrrpt")
    if awrrpt_dir.exists():
        html_files = list(awrrpt_dir.rglob("*.html"))[:3]  # 只测试前3个文件
        for html_file in html_files:
            print(f"\n   测试文件: {html_file}")
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()[:1000]  # 只读取前1000字符
                
                parser = factory.create_parser(html_content=content)
                print(f"   解析器: {parser}")
                
                if parser is None:
                    # 尝试版本检测
                    detected_version = factory._version_detector.detect_version(content)
                    print(f"   检测到版本: {detected_version} (类型: {type(detected_version)})")
                    
            except Exception as e:
                print(f"   错误: {e}")
    else:
        print("   awrrpt目录不存在")

if __name__ == "__main__":
    test_factory_versions() 