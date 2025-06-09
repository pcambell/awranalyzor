#!/usr/bin/env python3
"""
AWR文件验证调试工具
用于诊断AWR文件验证失败的原因
"""

import sys
import os

def debug_awr_file(file_path):
    """调试AWR文件内容"""
    print(f"调试文件: {file_path}")
    print("=" * 60)
    
    if not os.path.exists(file_path):
        print(f"错误: 文件不存在 - {file_path}")
        return
    
    file_size = os.path.getsize(file_path)
    print(f"文件大小: {file_size} 字节")
    
    # 检查文件扩展名
    file_ext = os.path.splitext(file_path)[1].lower()
    print(f"文件扩展名: {file_ext}")
    
    try:
        # 尝试不同的编码方式
        encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
        content_sample = None
        used_encoding = None
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content_sample = f.read(8192)  # 读取更多内容
                used_encoding = encoding
                print(f"成功读取文件，使用编码: {encoding}")
                break
            except Exception as e:
                print(f"编码 {encoding} 失败: {e}")
                continue
        
        if content_sample is None:
            print("错误: 无法用任何编码读取文件")
            return
        
        # 分析内容
        content_lower = content_sample.lower()
        print(f"\n内容长度: {len(content_sample)} 字符")
        print(f"前500字符预览:")
        print("-" * 40)
        print(content_sample[:500])
        print("-" * 40)
        
        # 检测AWR相关关键词
        print(f"\n关键词检测:")
        keywords = {
            'workload repository': 'workload repository' in content_lower,
            'ash report': 'ash report' in content_lower,
            'active session history': 'active session history' in content_lower,
            'oracle': 'oracle' in content_lower,
            'report': 'report' in content_lower,
            'database': 'database' in content_lower,
            'awr': 'awr' in content_lower,
        }
        
        for keyword, found in keywords.items():
            status = "✓" if found else "✗"
            print(f"  {status} '{keyword}': {found}")
        
        # 验证逻辑检查
        is_awr_report = keywords['workload repository']
        is_ash_report = keywords['ash report'] or keywords['active session history']
        is_oracle_report = keywords['oracle'] and (keywords['report'] or keywords['database'])
        
        print(f"\n验证结果:")
        print(f"  AWR报告检测: {is_awr_report}")
        print(f"  ASH报告检测: {is_ash_report}")
        print(f"  通用Oracle报告检测: {is_oracle_report}")
        print(f"  总体通过: {is_awr_report or is_ash_report or is_oracle_report}")
        
        # 查找更多线索
        interesting_phrases = []
        lines = content_sample.split('\n')[:50]  # 检查前50行
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            if any(word in line_lower for word in ['oracle', 'awr', 'repository', 'report', 'database']):
                interesting_phrases.append(f"第{i+1}行: {line.strip()}")
        
        if interesting_phrases:
            print(f"\n相关内容行:")
            for phrase in interesting_phrases[:10]:  # 只显示前10行
                print(f"  {phrase}")
        
    except Exception as e:
        print(f"处理文件时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("用法: python debug_awr_validation.py <AWR文件路径>")
        sys.exit(1)
    
    debug_awr_file(sys.argv[1]) 