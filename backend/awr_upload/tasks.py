#!/usr/bin/env python3
"""
AWR上传模块异步任务
{{CHENGQI: P2-LD-005 解析器工厂和集成 - Celery异步任务 - 2025-06-02T14:55:00}}

使用Celery处理AWR文件解析等耗时操作
"""

import logging
from typing import Dict, Any

# TODO: 集成Celery后取消注释
# from celery import shared_task
# from celery.exceptions import Retry

from django.db import transaction
from django.utils import timezone

from .models import AWRReport
from .services import AWRParsingService, AWRParsingError

logger = logging.getLogger(__name__)


# TODO: 集成Celery后，添加@shared_task装饰器
# @shared_task(bind=True, max_retries=3, default_retry_delay=60)
def parse_awr_report_async(report_id: int) -> Dict[str, Any]:
    """
    异步解析AWR报告任务
    
    Args:
        report_id: AWR报告ID
        
    Returns:
        Dict包含任务执行结果
    """
    result = {
        'report_id': report_id,
        'success': False,
        'message': '',
        'parse_result': None,
        'started_at': timezone.now(),
        'completed_at': None
    }
    
    parsing_service = AWRParsingService()
    
    try:
        # 获取报告实例
        with transaction.atomic():
            report = AWRReport.objects.select_for_update().get(id=report_id)
            
            # 检查状态，避免重复处理
            if report.status not in ['uploaded', 'validated', 'failed']:
                result['message'] = f'报告状态为 {report.status}，无法处理'
                logger.warning(f"报告 {report_id} 状态为 {report.status}，跳过处理")
                return result
            
            # 更新状态为解析中
            report.status = 'parsing'
            report.save(update_fields=['status', 'updated_at'])
            
            logger.info(f"开始解析AWR报告: {report_id}")
        
        # 执行解析
        parse_result = parsing_service.parse_report(report)
        
        # 存储解析结果
        storage_success = parsing_service.store_parse_result(report, parse_result)
        
        if storage_success:
            result.update({
                'success': True,
                'message': '解析完成',
                'parse_result': {
                    'status': parse_result.parse_status.value,
                    'db_info': {
                        'version': parse_result.db_info.version.value if parse_result.db_info else None,
                        'instance_name': parse_result.db_info.instance_name if parse_result.db_info else None,
                        'db_name': parse_result.db_info.db_name if parse_result.db_info else None,
                    } if parse_result.db_info else None,
                    'snapshot_info': {
                        'begin_time': parse_result.snapshot_info.begin_time if parse_result.snapshot_info else None,
                        'end_time': parse_result.snapshot_info.end_time if parse_result.snapshot_info else None,
                        'elapsed_minutes': parse_result.snapshot_info.elapsed_time_minutes if parse_result.snapshot_info else None,
                    } if parse_result.snapshot_info else None,
                    'metrics_count': {
                        'wait_events': len(parse_result.wait_events),
                        'sql_statistics': len(parse_result.sql_statistics),
                        'instance_activities': len(parse_result.instance_activities),
                    }
                }
            })
            logger.info(f"AWR报告 {report_id} 解析并存储成功")
        else:
            result['message'] = '解析成功但存储失败'
            logger.error(f"AWR报告 {report_id} 解析成功但存储失败")
        
    except AWRReport.DoesNotExist:
        result['message'] = f'报告 {report_id} 不存在'
        logger.error(f"AWR报告 {report_id} 不存在")
        
    except AWRParsingError as e:
        result['message'] = f'解析失败: {str(e)}'
        logger.error(f"AWR报告 {report_id} 解析失败: {e}")
        
        # 更新报告状态为失败
        try:
            report = AWRReport.objects.get(id=report_id)
            report.status = 'failed'
            report.error_message = str(e)
            report.save(update_fields=['status', 'error_message', 'updated_at'])
        except AWRReport.DoesNotExist:
            pass
    
    except Exception as e:
        result['message'] = f'处理异常: {str(e)}'
        logger.error(f"AWR报告 {report_id} 处理异常: {e}")
        
        # 更新报告状态为失败
        try:
            report = AWRReport.objects.get(id=report_id)
            report.status = 'failed'
            report.error_message = f'处理异常: {str(e)}'
            report.save(update_fields=['status', 'error_message', 'updated_at'])
        except AWRReport.DoesNotExist:
            pass
        
        # TODO: 集成Celery后，可以实现重试逻辑
        # if self.request.retries < self.max_retries:
        #     logger.info(f"重试解析AWR报告: {report_id} (第{self.request.retries + 1}次)")
        #     raise self.retry(countdown=60, exc=e)
    
    finally:
        result['completed_at'] = timezone.now()
    
    return result


def schedule_awr_parsing(report_id: int) -> bool:
    """
    调度AWR解析任务
    
    Args:
        report_id: AWR报告ID
        
    Returns:
        是否成功调度任务
    """
    try:
        # TODO: 集成Celery后，使用异步任务
        # task = parse_awr_report_async.delay(report_id)
        # logger.info(f"AWR解析任务已调度: {report_id}, 任务ID: {task.id}")
        
        # 目前使用同步执行（开发阶段）
        logger.info(f"同步执行AWR解析任务: {report_id}")
        result = parse_awr_report_async(report_id)
        
        if result['success']:
            logger.info(f"AWR解析任务完成: {report_id}")
            return True
        else:
            logger.error(f"AWR解析任务失败: {report_id} - {result['message']}")
            return False
            
    except Exception as e:
        logger.error(f"调度AWR解析任务失败: {report_id} - {str(e)}")
        return False


class AWRParsingProgress:
    """
    AWR解析进度跟踪器
    
    用于跟踪和更新解析进度（为Celery集成做准备）
    """
    
    def __init__(self, report_id: int):
        self.report_id = report_id
        self.current_progress = 0
        self.current_stage = "初始化"
    
    def update_progress(self, progress: int, stage: str, details: str = None):
        """
        更新解析进度
        
        Args:
            progress: 进度百分比 (0-100)
            stage: 当前阶段描述
            details: 详细信息
        """
        self.current_progress = min(100, max(0, progress))
        self.current_stage = stage
        
        # TODO: 集成Celery后，这里将更新任务进度
        # if hasattr(self, 'task'):
        #     self.task.update_state(
        #         state='PROGRESS',
        #         meta={
        #             'current': progress,
        #             'total': 100,
        #             'stage': stage,
        #             'details': details
        #         }
        #     )
        
        logger.info(f"报告 {self.report_id} 解析进度: {progress}% - {stage}")
        
        # 更新数据库中的状态
        try:
            report = AWRReport.objects.get(id=self.report_id)
            
            # 根据进度更新状态
            if progress < 30:
                status = 'parsing'
            elif progress < 90:
                status = 'parsed'
            elif progress < 100:
                status = 'analyzing'
            else:
                status = 'completed'
            
            if report.status != status:
                report.status = status
                report.save(update_fields=['status', 'updated_at'])
                
        except AWRReport.DoesNotExist:
            logger.warning(f"更新进度时报告 {self.report_id} 不存在")
    
    def get_progress(self) -> Dict[str, Any]:
        """
        获取当前进度信息
        
        Returns:
            Dict包含进度信息
        """
        return {
            'report_id': self.report_id,
            'progress': self.current_progress,
            'stage': self.current_stage,
            'updated_at': timezone.now()
        }


# TODO: 集成Celery后，添加更多异步任务
# @shared_task
def cleanup_failed_reports():
    """
    清理失败的报告（定期任务）
    
    删除超过一定时间的失败报告及其文件
    """
    from datetime import timedelta
    
    cutoff_date = timezone.now() - timedelta(days=7)  # 7天前的失败报告
    
    failed_reports = AWRReport.objects.filter(
        status='failed',
        updated_at__lt=cutoff_date
    )
    
    cleanup_count = 0
    for report in failed_reports:
        try:
            # 删除文件
            if report.file_path and report.file_path.storage.exists(report.file_path.name):
                report.file_path.delete(save=False)
            
            # 删除记录
            report.delete()
            cleanup_count += 1
            
        except Exception as e:
            logger.error(f"清理失败报告 {report.id} 时出错: {e}")
    
    logger.info(f"清理了 {cleanup_count} 个失败的AWR报告")
    return cleanup_count


# @shared_task
def generate_parsing_statistics():
    """
    生成解析统计信息（定期任务）
    
    统计各种状态的报告数量、解析成功率等
    """
    from django.db.models import Count
    
    stats = AWRReport.objects.values('status').annotate(count=Count('id'))
    
    statistics = {
        'total_reports': AWRReport.objects.count(),
        'status_breakdown': {item['status']: item['count'] for item in stats},
        'success_rate': 0,
        'generated_at': timezone.now()
    }
    
    # 计算成功率
    total = statistics['total_reports']
    completed = statistics['status_breakdown'].get('completed', 0)
    
    if total > 0:
        statistics['success_rate'] = round((completed / total) * 100, 2)
    
    logger.info(f"解析统计: {statistics}")
    return statistics 