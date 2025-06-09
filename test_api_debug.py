#!/usr/bin/env python
"""
调试API上传失败的原因
"""
import os
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'awranalyzor.settings')
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile, InMemoryUploadedFile
from awr_upload.services import AWRUploadService
from io import BytesIO
import logging

# 设置日志级别
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def test_api_upload():
    """测试API上传"""
    service = AWRUploadService()
    
    # 读取19c AWR文件
    file_path = '/app/awrrpt/19c/awrrpt_1_17676_17677.html'
    
    with open(file_path, 'rb') as f:
        content = f.read()
    
    print(f"文件大小: {len(content)} 字节")
    
    # 模拟multipart/form-data上传
    file_obj = BytesIO(content)
    uploaded_file = InMemoryUploadedFile(
        file=file_obj,
        field_name='file',
        name='awrrpt_1_17676_17677.html',
        content_type='text/html',
        size=len(content),
        charset=None
    )
    
    print("开始手动验证过程...")
    
    # 手动验证过程
    errors = []
    
    # 文件大小检查
    max_size = 50 * 1024 * 1024
    if uploaded_file.size > max_size:
        errors.append(f"文件大小 {uploaded_file.size} 字节超过限制 {max_size} 字节")
        print(f"文件大小检查: 失败 - {errors[-1]}")
    else:
        print(f"文件大小检查: 通过 ({uploaded_file.size} 字节)")
    
    # 文件扩展名检查
    file_ext = os.path.splitext(uploaded_file.name)[1].lower()
    allowed_extensions = ['.html', '.htm']
    if file_ext not in allowed_extensions:
        errors.append(f"不支持的文件类型 {file_ext}，仅支持 {', '.join(allowed_extensions)}")
        print(f"文件扩展名检查: 失败 - {errors[-1]}")
    else:
        print(f"文件扩展名检查: 通过 ({file_ext})")
    
    # 内容检查
    try:
        uploaded_file.seek(0)
        raw_content = uploaded_file.read(16384)
        content_sample = raw_content.decode('utf-8', errors='ignore')
        uploaded_file.seek(0)
        
        content_lower = content_sample.lower()
        
        # AWR报告检测
        is_awr_report = (
            'workload repository' in content_lower or
            'awr report' in content_lower or
            ('automatic workload repository' in content_lower)
        )
        
        # ASH报告检测
        is_ash_report = (
            'ash report' in content_lower or
            'active session history' in content_lower or
            ('ash report for' in content_lower)
        )
        
        # 通用Oracle报告检测
        is_oracle_report = (
            'oracle' in content_lower and (
                'report' in content_lower or 
                'database' in content_lower or
                'instance' in content_lower
            )
        )
        
        # 进一步的Oracle特征检测
        oracle_features = (
            'db name' in content_lower or
            'db id' in content_lower or
            'instance name' in content_lower or
            'host name' in content_lower or
            'snap id' in content_lower or
            'begin snap' in content_lower or
            'end snap' in content_lower or
            'oracle database' in content_lower
        )
        
        print(f"内容检测结果:")
        print(f"  AWR报告: {is_awr_report}")
        print(f"  ASH报告: {is_ash_report}")
        print(f"  Oracle通用: {is_oracle_report}")
        print(f"  Oracle特征: {oracle_features}")
        
        overall_pass = is_awr_report or is_ash_report or is_oracle_report or oracle_features
        print(f"  总体通过: {overall_pass}")
        
        if not overall_pass:
            errors.append("文件内容不像是Oracle AWR/ASH报告")
            print(f"内容检查: 失败 - {errors[-1]}")
        else:
            print("内容检查: 通过")
            
    except Exception as e:
        error_msg = f"读取文件内容时出错: {str(e)}"
        errors.append(error_msg)
        print(f"内容检查: 异常 - {error_msg}")
    
    print(f"\n手动验证结果: {'成功' if not errors else '失败'}")
    if errors:
        print("错误列表:")
        for error in errors:
            print(f"  - {error}")
    
    # 现在用原服务验证
    print("\n=== 使用AWRUploadService验证 ===")
    try:
        uploaded_file.seek(0)
        result = service.validate_file(uploaded_file)
        print("✓ 服务验证成功:", result)
    except Exception as e:
        print("✗ 服务验证失败:", str(e))

if __name__ == '__main__':
    test_api_upload() 