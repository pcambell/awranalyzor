#!/usr/bin/env python
"""
在容器中直接测试服务验证
"""
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'awranalyzor.settings')
django.setup()

from django.core.files.uploadedfile import SimpleUploadedFile
from awr_upload.services import AWRUploadService

def test_service():
    # 读取文件
    with open('/app/awrrpt/19c/awrrpt_1_17676_17677.html', 'rb') as f:
        content = f.read()
    
    # 创建上传文件对象
    uploaded_file = SimpleUploadedFile(
        name='awrrpt_1_17676_17677.html',
        content=content,
        content_type='text/html'
    )
    
    # 使用服务验证
    service = AWRUploadService()
    try:
        result = service.validate_file(uploaded_file)
        print('SUCCESS:', result)
    except Exception as e:
        print('ERROR:', str(e))

if __name__ == '__main__':
    test_service() 