"""
AWR解析异步任务
使用Celery实现异步AWR文件解析和分析
"""

import logging
import traceback
from typing import Dict, Any, Optional
from celery import shared_task
from django.utils import timezone
from django.core.files.storage import default_storage

from awr_upload.models import AWRReport
from .services.awr_parsing_service import AWRParsingService
from .services.oracle_19c_parser import Oracle19cParser
from .services.oracle_11g_parser import Oracle11gParser
from .exceptions import ParsingError, UnsupportedVersionError

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='awr_parser.parse_awr_file')
def parse_awr_file(self, report_id: int) -> Dict[str, Any]:
    """
    异步解析AWR文件
    
    Args:
        report_id: AWR报告ID
        
    Returns:
        解析结果字典
        
    Raises:
        ParsingError: 解析失败
        UnsupportedVersionError: 不支持的Oracle版本
    """
    try:
        # 获取AWR报告记录
        try:
            awr_report = AWRReport.objects.get(id=report_id)
        except AWRReport.DoesNotExist:
            raise ParsingError(f"AWR报告不存在: {report_id}")
        
        # 更新状态为解析中
        awr_report.status = 'parsing'
        awr_report.updated_at = timezone.now()
        awr_report.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"开始解析AWR文件: {awr_report.id} - {awr_report.original_filename}")
        
        # 读取文件内容
        if not awr_report.file or not default_storage.exists(awr_report.file.name):
            raise ParsingError(f"AWR文件不存在: {awr_report.file.name if awr_report.file else 'None'}")
        
        with default_storage.open(awr_report.file.name, 'r') as file:
            content = file.read()
        
        # 创建解析服务
        parsing_service = AWRParsingService()
        
        # 执行解析
        parsing_result = parsing_service.parse_awr_content(
            content=content,
            oracle_version=awr_report.oracle_version,
            report_id=awr_report.id
        )
        
        # 更新AWR报告信息
        awr_report.status = 'parsed'
        awr_report.instance_name = parsing_result.get('instance_name')
        awr_report.host_name = parsing_result.get('host_name')
        awr_report.database_id = parsing_result.get('database_id')
        awr_report.instance_number = parsing_result.get('instance_number')
        awr_report.snapshot_begin_time = parsing_result.get('snapshot_begin_time')
        awr_report.snapshot_end_time = parsing_result.get('snapshot_end_time')
        awr_report.snapshot_duration_minutes = parsing_result.get('snapshot_duration_minutes')
        awr_report.updated_at = timezone.now()
        awr_report.save()
        
        logger.info(f"AWR文件解析完成: {awr_report.id}")
        
        # 触发性能分析任务
        from performance.tasks import analyze_performance
        analyze_performance.delay(report_id)
        
        return {
            'status': 'success',
            'report_id': report_id,
            'parsing_result': parsing_result,
            'message': 'AWR文件解析成功'
        }
        
    except UnsupportedVersionError as e:
        # 不支持的版本
        awr_report.status = 'failed'
        awr_report.error_message = f"不支持的Oracle版本: {str(e)}"
        awr_report.updated_at = timezone.now()
        awr_report.save(update_fields=['status', 'error_message', 'updated_at'])
        
        logger.error(f"不支持的Oracle版本 - 报告ID: {report_id}, 错误: {str(e)}")
        
        raise self.retry(
            countdown=300,  # 5分钟后重试
            max_retries=1,  # 最多重试1次
            exc=e
        )
        
    except ParsingError as e:
        # 解析错误
        awr_report.status = 'failed'
        awr_report.error_message = f"解析失败: {str(e)}"
        awr_report.updated_at = timezone.now()
        awr_report.save(update_fields=['status', 'error_message', 'updated_at'])
        
        logger.error(f"AWR解析失败 - 报告ID: {report_id}, 错误: {str(e)}")
        
        # 根据错误类型决定是否重试
        if "文件损坏" in str(e) or "格式错误" in str(e):
            # 文件问题不重试
            raise
        else:
            # 其他错误可以重试
            raise self.retry(countdown=60, max_retries=2, exc=e)
            
    except Exception as e:
        # 其他未知错误
        awr_report.status = 'failed'
        awr_report.error_message = f"解析失败: {str(e)}"
        awr_report.updated_at = timezone.now()
        awr_report.save(update_fields=['status', 'error_message', 'updated_at'])
        
        logger.error(f"AWR解析异常 - 报告ID: {report_id}, 错误: {str(e)}, 堆栈: {traceback.format_exc()}")
        
        # 未知错误重试
        raise self.retry(countdown=120, max_retries=3, exc=e)


@shared_task(bind=True, name='awr_parser.validate_awr_file')
def validate_awr_file(self, report_id: int) -> Dict[str, Any]:
    """
    异步验证AWR文件
    
    Args:
        report_id: AWR报告ID
        
    Returns:
        验证结果字典
    """
    try:
        awr_report = AWRReport.objects.get(id=report_id)
        
        # 更新状态为验证中
        awr_report.status = 'validating'
        awr_report.updated_at = timezone.now()
        awr_report.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"开始验证AWR文件: {awr_report.id}")
        
        # 读取文件内容
        with default_storage.open(awr_report.file.name, 'r') as file:
            content = file.read()
        
        # 创建解析服务进行验证
        parsing_service = AWRParsingService()
        
        # 基础验证
        validation_result = parsing_service.validate_awr_content(content)
        
        if validation_result['is_valid']:
            # 验证成功，更新状态并提取基础信息
            awr_report.status = 'validated'
            awr_report.oracle_version = validation_result.get('oracle_version')
            awr_report.updated_at = timezone.now()
            awr_report.save()
            
            logger.info(f"AWR文件验证成功: {awr_report.id}")
            
            # 触发解析任务
            parse_awr_file.delay(report_id)
            
        else:
            # 验证失败
            awr_report.status = 'failed'
            awr_report.error_message = f"文件验证失败: {validation_result.get('error', '未知错误')}"
            awr_report.updated_at = timezone.now()
            awr_report.save()
            
            logger.warning(f"AWR文件验证失败: {awr_report.id}")
        
        return {
            'status': 'success' if validation_result['is_valid'] else 'failed',
            'report_id': report_id,
            'validation_result': validation_result
        }
        
    except AWRReport.DoesNotExist:
        logger.error(f"AWR报告不存在: {report_id}")
        raise
        
    except Exception as e:
        logger.error(f"AWR文件验证异常 - 报告ID: {report_id}, 错误: {str(e)}")
        
        # 更新状态为失败
        try:
            awr_report.status = 'failed'
            awr_report.error_message = f"验证异常: {str(e)}"
            awr_report.updated_at = timezone.now()
            awr_report.save()
        except:
            pass
            
        raise self.retry(countdown=60, max_retries=2, exc=e)


@shared_task(bind=True, name='awr_parser.reparse_failed_reports')
def reparse_failed_reports(self) -> Dict[str, Any]:
    """
    重新解析失败的报告
    
    定期任务，自动重试解析失败的报告
    """
    try:
        # 查找24小时内失败的报告
        from datetime import timedelta
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        failed_reports = AWRReport.objects.filter(
            status='failed',
            updated_at__gte=cutoff_time
        ).exclude(
            error_message__icontains='不支持'
        )[:10]  # 限制每次处理10个
        
        reparse_count = 0
        for report in failed_reports:
            # 重置状态并重新解析
            report.status = 'uploaded'
            report.error_message = ''
            report.save(update_fields=['status', 'error_message'])
            
            # 重新调度验证任务
            validate_awr_file.delay(report.id)
            reparse_count += 1
        
        logger.info(f"重新解析失败报告完成: {reparse_count}个")
        
        return {
            'status': 'success',
            'reparse_count': reparse_count,
            'message': f'已重新调度{reparse_count}个失败报告的解析任务'
        }
        
    except Exception as e:
        logger.error(f"重新解析失败报告异常: {str(e)}")
        raise


@shared_task(bind=True, name='awr_parser.cleanup_temp_files')
def cleanup_temp_files(self) -> Dict[str, Any]:
    """
    清理临时文件
    
    清理解析过程中产生的临时文件
    """
    try:
        import os
        import tempfile
        from datetime import timedelta
        
        temp_dir = tempfile.gettempdir()
        cutoff_time = timezone.now() - timedelta(hours=6)  # 6小时前的临时文件
        
        cleaned_count = 0
        cleaned_size = 0
        
        # 查找AWR相关的临时文件
        for root, dirs, files in os.walk(temp_dir):
            for file in files:
                if file.startswith('awr_') and (file.endswith('.tmp') or file.endswith('.html')):
                    file_path = os.path.join(root, file)
                    try:
                        file_time = timezone.datetime.fromtimestamp(
                            os.path.getmtime(file_path),
                            tz=timezone.get_current_timezone()
                        )
                        
                        if file_time < cutoff_time:
                            file_size = os.path.getsize(file_path)
                            os.remove(file_path)
                            cleaned_count += 1
                            cleaned_size += file_size
                            
                    except OSError:
                        # 文件可能已被删除或无权限
                        pass
        
        logger.info(f"临时文件清理完成: {cleaned_count}个文件, {cleaned_size/1024/1024:.2f}MB")
        
        return {
            'status': 'success',
            'cleaned_count': cleaned_count,
            'cleaned_size_mb': round(cleaned_size / 1024 / 1024, 2),
            'message': f'已清理{cleaned_count}个临时文件'
        }
        
    except Exception as e:
        logger.error(f"临时文件清理异常: {str(e)}")
        raise


@shared_task(bind=True, name='awr_parser.update_parsing_progress')
def update_parsing_progress(self, report_id: int, stage: str, progress: int, message: str = '') -> Dict[str, Any]:
    """
    更新解析进度
    
    Args:
        report_id: 报告ID
        stage: 当前阶段
        progress: 进度百分比
        message: 进度消息
    """
    try:
        from django.core.cache import cache
        
        progress_data = {
            'report_id': report_id,
            'stage': stage,
            'progress': progress,
            'message': message,
            'timestamp': timezone.now().isoformat()
        }
        
        # 缓存进度信息
        cache_key = f"awr_parsing_progress_{report_id}"
        cache.set(cache_key, progress_data, timeout=3600)  # 1小时过期
        
        logger.debug(f"解析进度更新: {report_id} - {stage} - {progress}%")
        
        return progress_data
        
    except Exception as e:
        logger.error(f"更新解析进度失败: {str(e)}")
        raise 