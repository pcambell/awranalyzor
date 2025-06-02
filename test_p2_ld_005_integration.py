#!/usr/bin/env python3
"""
P2-LD-005 任务集成验证脚本
{{CHENGQI: P2-LD-005 解析器工厂和集成 - 功能验证 - 2025-06-02T15:10:00}}

验证解析器工厂与Django集成的核心功能
"""

import os
import sys
import django
from pathlib import Path

# 设置Django环境
sys.path.append(str(Path(__file__).parent))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'awranalyzor.settings')
django.setup()

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from awr_upload.models import AWRReport
from awr_upload.services import AWRUploadService, AWRParsingService
from apps.awr_parser.parsers.factory import create_parser, parse_awr


def test_parser_factory_integration():
    """测试解析器工厂集成"""
    print("🧪 测试解析器工厂集成...")
    
    try:
        # 首先测试工厂初始化
        from apps.awr_parser.parsers.factory import get_parser_factory
        factory = get_parser_factory()
        print("✅ 解析器工厂初始化成功")
        
        # 测试支持的版本
        supported_versions = factory.get_supported_versions()
        print(f"✅ 支持的版本: {[v.value for v in supported_versions]}")
        
        # 测试简单的AWR内容
        awr_content = """
        <html>
        <head><title>Oracle Database 19c Enterprise Edition Release 19.0.0.0.0 AWR Report</title></head>
        <body>
        <h1>WORKLOAD REPOSITORY report for</h1>
        <h2>Oracle Database 19c Enterprise Edition Release 19.0.0.0.0</h2>
        <table>
            <tr><td>Instance Name:</td><td>TESTDB1</td></tr>
            <tr><td>DB Name:</td><td>TESTDB</td></tr>
        </table>
        </body>
        </html>
        """
        
        # 测试解析器创建
        parser = factory.get_parser_for_content(awr_content)
        if parser:
            print("✅ 解析器工厂成功创建解析器")
            print(f"   解析器类型: {parser.__class__.__name__}")
            
            # 简单测试can_parse方法
            can_parse = parser.can_parse(awr_content)
            print(f"   can_parse结果: {can_parse}")
            
        else:
            print("❌ 解析器工厂无法创建解析器")
            return False
            
    except Exception as e:
        print(f"❌ 解析器工厂集成测试异常: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_django_services_integration():
    """测试Django服务集成"""
    print("\n🧪 测试Django服务集成...")
    
    try:
        # 创建测试用户
        user, created = User.objects.get_or_create(
            username='test_integration_user',
            defaults={
                'email': 'test@example.com',
                'password': 'test_password'
            }
        )
        print(f"✅ 测试用户创建: {'新建' if created else '已存在'}")
        
        # 创建上传服务
        upload_service = AWRUploadService()
        print("✅ AWR上传服务创建成功")
        
        # 创建模拟文件
        awr_content = """
        <html>
        <head><title>Oracle Database 19c AWR Report</title></head>
        <body>
        <h1>WORKLOAD REPOSITORY report for</h1>
        </body>
        </html>
        """
        
        uploaded_file = SimpleUploadedFile(
            "integration_test.html",
            awr_content.encode('utf-8'),
            content_type="text/html"
        )
        
        # 测试文件验证
        try:
            validation_info = upload_service.validate_file(uploaded_file)
            print("✅ 文件验证通过")
            print(f"   文件大小: {validation_info['size']} 字节")
        except Exception as e:
            print(f"❌ 文件验证失败: {e}")
            return False
        
        # 测试基础信息提取
        uploaded_file.seek(0)
        content = uploaded_file.read().decode('utf-8')
        basic_info = upload_service.extract_basic_info(content)
        print("✅ 基础信息提取完成")
        print(f"   提取信息: {basic_info}")
        
        # 重置文件指针
        uploaded_file.seek(0)
        
        # 测试AWR报告创建
        try:
            awr_report = upload_service.create_awr_report(
                uploaded_file=uploaded_file,
                user=user,
                name="集成测试报告",
                description="P2-LD-005集成测试",
                category="test"
            )
            print("✅ AWR报告创建成功")
            print(f"   报告ID: {awr_report.id}")
            print(f"   报告状态: {awr_report.status}")
            
            # 测试解析调度
            parsing_success = upload_service.schedule_parsing(awr_report)
            if parsing_success:
                print("✅ 解析任务调度成功")
                
                # 检查最终状态
                awr_report.refresh_from_db()
                print(f"   最终状态: {awr_report.status}")
                
                # 清理测试数据
                awr_report.delete()
                print("✅ 测试数据清理完成")
                
            else:
                print("❌ 解析任务调度失败")
                return False
                
        except Exception as e:
            print(f"❌ AWR报告创建失败: {e}")
            return False
        
    except Exception as e:
        print(f"❌ Django服务集成测试失败: {e}")
        return False
    
    return True


def test_task_system():
    """测试任务系统"""
    print("\n🧪 测试任务系统...")
    
    try:
        from awr_upload.tasks import schedule_awr_parsing, AWRParsingProgress
        print("✅ 任务模块导入成功")
        
        # 测试进度跟踪器
        progress = AWRParsingProgress(report_id=999)
        progress.update_progress(50, "测试阶段", "正在进行集成测试")
        
        progress_info = progress.get_progress()
        print("✅ 进度跟踪器测试成功")
        print(f"   当前进度: {progress_info['progress']}%")
        print(f"   当前阶段: {progress_info['stage']}")
        
    except Exception as e:
        print(f"❌ 任务系统测试失败: {e}")
        return False
    
    return True


def main():
    """主测试函数"""
    print("🚀 开始P2-LD-005解析器工厂和集成功能验证\n")
    
    tests = [
        ("解析器工厂集成", test_parser_factory_integration),
        ("Django服务集成", test_django_services_integration), 
        ("任务系统", test_task_system),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"{'='*60}")
        print(f"测试: {test_name}")
        print(f"{'='*60}")
        
        try:
            if test_func():
                print(f"✅ {test_name} - 通过")
                passed += 1
            else:
                print(f"❌ {test_name} - 失败")
        except Exception as e:
            print(f"❌ {test_name} - 异常: {e}")
        
        print()
    
    print(f"{'='*60}")
    print(f"测试结果: {passed}/{total} 通过")
    print(f"{'='*60}")
    
    if passed == total:
        print("🎉 P2-LD-005任务集成验证全部通过！")
        return True
    else:
        print("⚠️  部分测试失败，请检查相关功能")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 