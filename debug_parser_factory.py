#!/usr/bin/env python
"""
调试解析器工厂问题的脚本
"""
import os
import sys
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'awranalyzor.settings')
django.setup()

from apps.awr_parser.parsers.factory import get_parser_factory, create_parser
from apps.awr_parser.parsers.oracle_11g import Oracle11gParser
from apps.awr_parser.parsers.oracle_19c import Oracle19cParser

def test_single_file():
    """测试单个文件的解析器创建"""
    awr_files = list(Path("awrrpt").glob("**/*.html"))
    
    if not awr_files:
        print("没有找到AWR文件")
        return
    
    # 测试前几个文件
    for i, awr_file in enumerate(awr_files[:3]):
        print(f"\n=== 测试文件 {i+1}: {awr_file} ===")
        
        try:
            with open(awr_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            print(f"文件大小: {len(content)} 字符")
            
            # 测试Oracle11gParser直接能否识别
            oracle_11g = Oracle11gParser()
            can_parse_11g = oracle_11g.can_parse(content)
            print(f"Oracle11gParser.can_parse(): {can_parse_11g}")
            
            # 测试Oracle19cParser直接能否识别
            oracle_19c = Oracle19cParser()
            can_parse_19c = oracle_19c.can_parse(content)
            print(f"Oracle19cParser.can_parse(): {can_parse_19c}")
            
            # 测试工厂方法
            factory = get_parser_factory()
            print(f"支持的版本: {[v.value for v in factory.get_supported_versions()]}")
            
            # 测试版本检测器
            detected_version = factory._version_detector.detect_version(content)
            print(f"检测到的版本: {detected_version}")
            
            # 测试创建解析器
            parser = create_parser(content)
            print(f"工厂创建的解析器: {parser}")
            
            if parser:
                print(f"解析器类型: {type(parser).__name__}")
            else:
                print("解析器创建失败")
                
                # 手动测试get_parser_for_content
                result_parser = factory.get_parser_for_content(content)
                print(f"get_parser_for_content结果: {result_parser}")
            
        except Exception as e:
            print(f"测试文件 {awr_file} 时出错: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_single_file() 