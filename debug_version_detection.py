#!/usr/bin/env python
"""
Debug script for AWR version detection
调试AWR版本检测问题
"""

import os
import sys
import django

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'awranalyzor.settings')
django.setup()

from apps.awr_parser.parsers.utils import VersionDetector
from apps.awr_parser.parsers.base import OracleVersion
from pathlib import Path
import logging
import re

# Setup logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def analyze_version_detection():
    """分析版本检测问题"""
    print("=== AWR Version Detection Debug ===\n")
    
    detector = VersionDetector()
    
    # 1. 检查版本模式
    print("1. 版本检测模式:")
    for version, patterns in detector.version_patterns:
        print(f"   {version.value}:")
        for pattern in patterns:
            print(f"      {pattern}")
    
    # 2. 测试文件
    print("\n2. 测试AWR文件:")
    awrrpt_dir = Path("awrrpt")
    if awrrpt_dir.exists():
        html_files = list(awrrpt_dir.rglob("*.html"))[:2]  # 测试前2个文件
        for html_file in html_files:
            print(f"\n--- 文件: {html_file} ---")
            try:
                with open(html_file, 'r', encoding='utf-8') as f:
                    content = f.read()[:10000]  # 读取前10000字符，增加范围
                
                print(f"文件大小: {len(content)} 字符")
                
                # 检查ASH报告
                is_ash = detector._is_ash_report(content)
                print(f"是否ASH报告: {is_ash}")
                
                if not is_ash:
                    # 逐个测试版本模式
                    print("模式匹配测试:")
                    for version, patterns in detector.version_patterns:
                        matched = False
                        for pattern in patterns:
                            if re.search(pattern, content, re.IGNORECASE):
                                print(f"   ✓ {version.value}: 匹配模式 '{pattern}'")
                                matched = True
                                break
                        if not matched:
                            print(f"   ✗ {version.value}: 无匹配")
                    
                    # 检查标题
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(content, 'html.parser')
                    title = soup.find('title')
                    if title:
                        print(f"HTML标题: '{title.get_text()}'")
                        version_from_title = detector._extract_version_from_title(title.get_text())
                        print(f"从标题检测版本: {version_from_title}")
                    
                    # 检查H1
                    h1 = soup.find('h1')
                    if h1:
                        print(f"H1标题: '{h1.get_text()}'")
                        version_from_h1 = detector._extract_version_from_title(h1.get_text())
                        print(f"从H1检测版本: {version_from_h1}")
                    
                    # 显示文件开头内容
                    print(f"文件开头内容 (前500字符):")
                    print(content[:500])
                    print("..." if len(content) > 500 else "")
                
                # 最终检测结果
                detected = detector.detect_version(content)
                print(f"最终检测结果: {detected}")
                
            except Exception as e:
                print(f"错误: {e}")
    else:
        print("awrrpt目录不存在")

if __name__ == "__main__":
    analyze_version_detection() 