#!/usr/bin/env python
"""
调试版本检测和工厂创建问题
"""

import os
import sys
import django
from pathlib import Path

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'awranalyzor.settings')
django.setup()

from apps.awr_parser.parsers.factory import get_parser_factory, create_parser
from apps.awr_parser.parsers.utils import VersionDetector
from apps.awr_parser.parsers.base import OracleVersion

def debug_version_detection():
    """调试版本检测"""
    print("=== 调试版本检测 ===")
    
    # 测试单个AWR文件
    test_file = Path('awrrpt/11g/awrrpt_1_36006_36007.html')
    if not test_file.exists():
        print(f"测试文件不存在: {test_file}")
        return
    
    try:
        with open(test_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        print(f"文件大小: {len(content)} 字符")
        print(f"文件前500字符:\n{content[:500]}")
        
        # 测试版本检测器
        detector = VersionDetector()
        print(f"\n版本检测器创建成功: {detector}")
        print(f"版本模式: {detector.version_patterns}")
        
        detected_version = detector.detect_version(content)
        print(f"检测到的版本: {detected_version}, 类型: {type(detected_version)}")
        
        # 测试工厂
        factory = get_parser_factory()
        print(f"\n工厂创建成功: {factory}")
        
        # 检查支持的版本
        supported_versions = factory.get_supported_versions()
        print(f"支持的版本: {supported_versions}")
        for v in supported_versions:
            print(f"  版本: {v}, 类型: {type(v)}")
        
        # 尝试创建解析器
        parser = factory.create_parser(html_content=content)
        print(f"创建的解析器: {parser}")
        
    except Exception as e:
        print(f"调试时出错: {e}")
        import traceback
        traceback.print_exc()

def debug_factory_directly():
    """直接调试工厂"""
    print("\n=== 直接调试工厂 ===")
    
    try:
        factory = get_parser_factory()
        registry = factory._registry
        
        print(f"注册表类型: {type(registry)}")
        print(f"内部解析器字典: {registry._parsers}")
        
        # 检查字典键的类型
        for key, value in registry._parsers.items():
            print(f"键: {key}, 键类型: {type(key)}, 值: {value}")
            
        # 测试获取支持版本
        versions = registry.get_supported_versions()
        print(f"获取的版本: {versions}")
        for v in versions:
            print(f"  版本: {v}, 类型: {type(v)}")
            if hasattr(v, 'value'):
                print(f"    .value: {v.value}")
            else:
                print(f"    没有.value属性!")
                
    except Exception as e:
        print(f"直接调试工厂时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_version_detection()
    debug_factory_directly() 