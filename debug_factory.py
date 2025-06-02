#!/usr/bin/env python3
"""
调试factory.py中的'str' object has no attribute 'value'错误
"""

from apps.awr_parser.parsers.factory import create_parser, get_parser_factory
from apps.awr_parser.parsers.utils import VersionDetector
from apps.awr_parser.parsers.base import OracleVersion
import traceback
import logging

# 开启详细日志
logging.basicConfig(level=logging.DEBUG)

def debug_factory_error():
    # 读取一个AWR文件进行测试
    with open('awrrpt/19c/awrrpt_1_17676_17677.html', 'r', encoding='utf-8') as f:
        content = f.read()
    
    print("=== 调试步骤分解 ===")
    
    # 步骤1: 版本检测
    detector = VersionDetector()
    detected_version = detector.detect_version(content)
    print(f"1. 检测版本: {detected_version} (类型: {type(detected_version)})")
    
    # 步骤2: 获取工厂
    factory = get_parser_factory()
    print(f"2. 工厂获取成功")
    
    # 步骤3: 获取解析器类
    try:
        parser_class = factory._registry.get_parser_class(detected_version)
        print(f"3. 解析器类获取: {parser_class}")
    except Exception as e:
        print(f"3. 解析器类获取失败: {e}")
        traceback.print_exc()
        return
    
    # 步骤4: 创建解析器实例
    try:
        parser_instance = parser_class()
        print(f"4. 解析器实例创建: {parser_instance}")
    except Exception as e:
        print(f"4. 解析器实例创建失败: {e}")
        traceback.print_exc()
        return
    
    # 步骤5: 直接调用工厂方法
    try:
        parser = factory.create_parser(html_content=content)
        print(f"5. 工厂create_parser: {parser}")
    except Exception as e:
        print(f"5. 工厂create_parser失败: {e}")
        traceback.print_exc()
        return

if __name__ == "__main__":
    debug_factory_error() 