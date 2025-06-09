#!/usr/bin/env python
"""
容器内测试文件上传验证逻辑
"""
from django.core.files.uploadedfile import SimpleUploadedFile
from awr_upload.services import AWRUploadService
import os

def test_file_validation():
    """测试文件验证逻辑"""
    service = AWRUploadService()
    
    test_files = [
        ('/app/awrrpt/19c/awrrpt_1_17676_17677.html', '19c AWR'),
        ('/app/awrrpt/11g/awrrpt_1_36008_36009.html', '11g AWR'),
        ('/app/awrrpt/11g/ashrpt_1_1212_2037.html', '11g ASH'),
    ]
    
    for file_path, description in test_files:
        print(f"\n测试文件: {description} ({file_path})")
        print("=" * 60)
        
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
            
            uploaded_file = SimpleUploadedFile(
                name=os.path.basename(file_path),
                content=content,
                content_type='text/html'
            )
            
            result = service.validate_file(uploaded_file)
            print(f"✓ 验证成功: {result}")
            
        except Exception as e:
            print(f"✗ 验证失败: {str(e)}")

if __name__ == '__main__':
    test_file_validation() 