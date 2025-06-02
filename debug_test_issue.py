#!/usr/bin/env python
"""
重现测试中的问题
"""

import os
import sys
import django
from pathlib import Path

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'awranalyzor.settings')
django.setup()

# 模拟测试环境
def test_simplified_awr_parsing():
    """简化的AWR解析测试"""
    
    from apps.awr_parser.parsers.factory import get_parser_factory
    from apps.awr_parser.parsers.base import ParseStatus
    
    # 获取AWR文件
    awrrpt_dir = Path('awrrpt')
    all_files = list(awrrpt_dir.rglob("*.html"))
    
    print(f"找到 {len(all_files)} 个HTML文件")
    
    factory = get_parser_factory()
    print(f"工厂创建成功: {factory}")
    
    for i, file_path in enumerate(all_files[:3]):  # 只测试前3个文件
        print(f"\n=== 测试文件 {i+1}: {file_path} ===")
        
        try:
            content = file_path.read_text(encoding='utf-8', errors='replace')
            print(f"文件大小: {len(content)} 字符")
            
            # 检查是否为ASH报告
            is_ash = any(pattern in content for pattern in ['ASH Report', 'Active Session History'])
            if is_ash:
                print("跳过ASH报告")
                continue
            
            print("尝试创建解析器...")
            
            # 这里是问题发生的地方
            parser = factory.create_parser(html_content=content)
            print(f"创建的解析器: {parser}")
            
            if parser is None:
                print("Failed to create parser")
                continue
                
            print("尝试解析...")
            result = parser.parse(content)
            print(f"解析结果: {result}")
            print(f"解析状态: {result.status}")
            
        except Exception as e:
            print(f"处理文件 {file_path} 时出错: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_simplified_awr_parsing() 