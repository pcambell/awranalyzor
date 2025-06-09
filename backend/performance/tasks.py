"""
Oracle AWR分析器 - 性能分析异步任务
"""

import logging
import traceback
from typing import Dict, Any

from celery import shared_task
from django.utils import timezone

from awr_upload.models import AWRReport
from .models import PerformanceMetric, PerformanceBaseline

logger = logging.getLogger(__name__)


@shared_task(bind=True, name='performance.analyze_performance')
def analyze_performance(self, report_id: int) -> Dict[str, Any]:
    """
    异步性能分析
    
    Args:
        report_id: AWR报告ID
        
    Returns:
        分析结果字典
    """
    try:
        # 获取AWR报告
        try:
            awr_report = AWRReport.objects.get(id=report_id)
        except AWRReport.DoesNotExist:
            raise Exception(f"AWR报告不存在: {report_id}")
        
        # 检查报告状态
        if awr_report.status != 'parsed':
            raise Exception(f"报告尚未解析完成: {awr_report.status}")
        
        # 更新状态为分析中
        awr_report.status = 'analyzing'
        awr_report.updated_at = timezone.now()
        awr_report.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"开始性能分析: {awr_report.id}")
        
        # TODO: 实现实际的性能分析逻辑
        # 这里先做一个简单的示例
        
        # 更新报告状态为完成
        awr_report.status = 'completed'
        awr_report.updated_at = timezone.now()
        awr_report.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"性能分析完成: {awr_report.id}")
        
        return {
            'status': 'success',
            'report_id': report_id,
            'message': '性能分析完成'
        }
        
    except Exception as e:
        # 更新状态为失败
        try:
            awr_report.status = 'failed'
            awr_report.error_message = f"性能分析失败: {str(e)}"
            awr_report.updated_at = timezone.now()
            awr_report.save(update_fields=['status', 'error_message', 'updated_at'])
        except:
            pass
        
        logger.error(f"性能分析失败 - 报告ID: {report_id}, 错误: {str(e)}, 堆栈: {traceback.format_exc()}")
        
        # 重试机制
        raise self.retry(countdown=120, max_retries=2, exc=e)


@shared_task(bind=True, name='performance.cleanup_old_metrics')
def cleanup_old_metrics(self, retention_days: int = 90) -> Dict[str, Any]:
    """
    清理旧的性能指标数据
    
    Args:
        retention_days: 保留天数
    """
    try:
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        # 清理旧的性能指标
        old_metrics = PerformanceMetric.objects.filter(created_at__lt=cutoff_date)
        deleted_count = old_metrics.count()
        old_metrics.delete()
        
        logger.info(f"清理完成，删除了 {deleted_count} 条旧的性能指标记录")
        
        return {
            'status': 'success',
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"清理旧数据失败: {str(e)}")
        raise 