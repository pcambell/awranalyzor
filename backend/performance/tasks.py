"""
性能分析异步任务
使用Celery实现异步性能分析和优化建议生成
"""

import logging
import traceback
from typing import Dict, Any, List
from celery import shared_task
from django.utils import timezone

from awr_upload.models import AWRReport
from .models import PerformanceMetrics, PerformanceAlert, OptimizationRecommendation
from .services.performance_analyzer import PerformanceAnalyzer
from .services.alert_generator import AlertGenerator
from .services.recommendation_engine import RecommendationEngine

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
        
        # 创建性能分析器
        analyzer = PerformanceAnalyzer(awr_report)
        
        # 执行性能分析
        analysis_result = analyzer.analyze()
        
        # 保存性能指标
        metrics_saved = _save_performance_metrics(awr_report, analysis_result)
        
        # 生成性能告警
        alerts_generated = _generate_performance_alerts(awr_report, analysis_result)
        
        # 生成优化建议
        recommendations_generated = _generate_optimization_recommendations(awr_report, analysis_result)
        
        # 更新报告状态为完成
        awr_report.status = 'completed'
        awr_report.updated_at = timezone.now()
        awr_report.save(update_fields=['status', 'updated_at'])
        
        logger.info(f"性能分析完成: {awr_report.id}")
        
        # 触发报告生成任务
        from reports.tasks import generate_analysis_report
        generate_analysis_report.delay(report_id)
        
        return {
            'status': 'success',
            'report_id': report_id,
            'metrics_count': metrics_saved,
            'alerts_count': alerts_generated,
            'recommendations_count': recommendations_generated,
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


@shared_task(bind=True, name='performance.generate_alerts')
def generate_alerts(self, report_id: int, force_regenerate: bool = False) -> Dict[str, Any]:
    """
    生成性能告警
    
    Args:
        report_id: AWR报告ID
        force_regenerate: 是否强制重新生成
    """
    try:
        awr_report = AWRReport.objects.get(id=report_id)
        
        # 检查是否已有告警且不强制重新生成
        if not force_regenerate and PerformanceAlert.objects.filter(awr_report=awr_report).exists():
            logger.info(f"告警已存在，跳过生成: {report_id}")
            return {'status': 'skipped', 'message': '告警已存在'}
        
        logger.info(f"开始生成告警: {report_id}")
        
        # 获取性能指标
        metrics = PerformanceMetrics.objects.filter(awr_report=awr_report)
        if not metrics.exists():
            raise Exception("缺少性能指标数据")
        
        # 创建告警生成器
        alert_generator = AlertGenerator(awr_report)
        
        # 生成告警
        alerts = alert_generator.generate_alerts(metrics)
        
        # 保存告警
        alerts_saved = 0
        for alert_data in alerts:
            alert, created = PerformanceAlert.objects.get_or_create(
                awr_report=awr_report,
                alert_type=alert_data['type'],
                metric_name=alert_data['metric_name'],
                defaults={
                    'severity': alert_data['severity'],
                    'message': alert_data['message'],
                    'threshold_value': alert_data.get('threshold'),
                    'actual_value': alert_data.get('actual_value'),
                    'recommendation': alert_data.get('recommendation', ''),
                }
            )
            if created:
                alerts_saved += 1
        
        logger.info(f"告警生成完成: {report_id}, 新增{alerts_saved}个告警")
        
        return {
            'status': 'success',
            'report_id': report_id,
            'alerts_generated': alerts_saved,
            'total_alerts': len(alerts)
        }
        
    except Exception as e:
        logger.error(f"告警生成失败 - 报告ID: {report_id}, 错误: {str(e)}")
        raise self.retry(countdown=60, max_retries=2, exc=e)


@shared_task(bind=True, name='performance.generate_recommendations')
def generate_recommendations(self, report_id: int, force_regenerate: bool = False) -> Dict[str, Any]:
    """
    生成优化建议
    
    Args:
        report_id: AWR报告ID
        force_regenerate: 是否强制重新生成
    """
    try:
        awr_report = AWRReport.objects.get(id=report_id)
        
        # 检查是否已有建议且不强制重新生成
        if not force_regenerate and OptimizationRecommendation.objects.filter(awr_report=awr_report).exists():
            logger.info(f"优化建议已存在，跳过生成: {report_id}")
            return {'status': 'skipped', 'message': '优化建议已存在'}
        
        logger.info(f"开始生成优化建议: {report_id}")
        
        # 获取性能指标和告警
        metrics = PerformanceMetrics.objects.filter(awr_report=awr_report)
        alerts = PerformanceAlert.objects.filter(awr_report=awr_report)
        
        if not metrics.exists():
            raise Exception("缺少性能指标数据")
        
        # 创建建议引擎
        recommendation_engine = RecommendationEngine(awr_report)
        
        # 生成建议
        recommendations = recommendation_engine.generate_recommendations(metrics, alerts)
        
        # 保存建议
        recommendations_saved = 0
        for rec_data in recommendations:
            recommendation, created = OptimizationRecommendation.objects.get_or_create(
                awr_report=awr_report,
                category=rec_data['category'],
                title=rec_data['title'],
                defaults={
                    'priority': rec_data['priority'],
                    'description': rec_data['description'],
                    'implementation_steps': rec_data.get('implementation_steps', ''),
                    'expected_impact': rec_data.get('expected_impact', ''),
                    'risk_level': rec_data.get('risk_level', 'LOW'),
                    'estimated_effort': rec_data.get('estimated_effort', ''),
                }
            )
            if created:
                recommendations_saved += 1
        
        logger.info(f"优化建议生成完成: {report_id}, 新增{recommendations_saved}个建议")
        
        return {
            'status': 'success',
            'report_id': report_id,
            'recommendations_generated': recommendations_saved,
            'total_recommendations': len(recommendations)
        }
        
    except Exception as e:
        logger.error(f"优化建议生成失败 - 报告ID: {report_id}, 错误: {str(e)}")
        raise self.retry(countdown=60, max_retries=2, exc=e)


@shared_task(bind=True, name='performance.trend_analysis')
def trend_analysis(self, time_period_days: int = 30) -> Dict[str, Any]:
    """
    趋势分析
    
    分析指定时间段内的性能趋势
    
    Args:
        time_period_days: 分析时间段（天）
    """
    try:
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=time_period_days)
        
        # 获取指定时间段内的完成报告
        reports = AWRReport.objects.filter(
            status='completed',
            created_at__gte=cutoff_date
        ).order_by('created_at')
        
        if reports.count() < 2:
            logger.info(f"数据不足，无法进行趋势分析: {reports.count()}个报告")
            return {'status': 'insufficient_data', 'report_count': reports.count()}
        
        logger.info(f"开始趋势分析: {reports.count()}个报告, {time_period_days}天")
        
        # 执行趋势分析
        trend_data = _analyze_performance_trends(reports)
        
        # 生成趋势告警
        trend_alerts = _generate_trend_alerts(trend_data)
        
        logger.info(f"趋势分析完成: {len(trend_alerts)}个趋势告警")
        
        return {
            'status': 'success',
            'report_count': reports.count(),
            'trend_alerts': len(trend_alerts),
            'analysis_period_days': time_period_days,
            'message': '趋势分析完成'
        }
        
    except Exception as e:
        logger.error(f"趋势分析失败: {str(e)}")
        raise self.retry(countdown=300, max_retries=1, exc=e)


@shared_task(bind=True, name='performance.cleanup_old_metrics')
def cleanup_old_metrics(self, retention_days: int = 90) -> Dict[str, Any]:
    """
    清理过期的性能指标数据
    
    Args:
        retention_days: 保留天数
    """
    try:
        from datetime import timedelta
        
        cutoff_date = timezone.now() - timedelta(days=retention_days)
        
        # 查找过期的报告
        old_reports = AWRReport.objects.filter(created_at__lt=cutoff_date)
        
        cleaned_metrics = 0
        cleaned_alerts = 0
        cleaned_recommendations = 0
        
        for report in old_reports:
            # 清理性能指标
            metrics_count = PerformanceMetrics.objects.filter(awr_report=report).count()
            PerformanceMetrics.objects.filter(awr_report=report).delete()
            cleaned_metrics += metrics_count
            
            # 清理告警
            alerts_count = PerformanceAlert.objects.filter(awr_report=report).count()
            PerformanceAlert.objects.filter(awr_report=report).delete()
            cleaned_alerts += alerts_count
            
            # 清理建议
            recommendations_count = OptimizationRecommendation.objects.filter(awr_report=report).count()
            OptimizationRecommendation.objects.filter(awr_report=report).delete()
            cleaned_recommendations += recommendations_count
        
        logger.info(f"性能数据清理完成: 指标{cleaned_metrics}个, 告警{cleaned_alerts}个, 建议{cleaned_recommendations}个")
        
        return {
            'status': 'success',
            'cleaned_reports': old_reports.count(),
            'cleaned_metrics': cleaned_metrics,
            'cleaned_alerts': cleaned_alerts,
            'cleaned_recommendations': cleaned_recommendations,
            'retention_days': retention_days
        }
        
    except Exception as e:
        logger.error(f"性能数据清理失败: {str(e)}")
        raise


def _save_performance_metrics(awr_report: AWRReport, analysis_result: Dict[str, Any]) -> int:
    """保存性能指标"""
    metrics_saved = 0
    
    try:
        metrics_data = analysis_result.get('metrics', {})
        
        for category, metrics in metrics_data.items():
            for metric_name, metric_value in metrics.items():
                if isinstance(metric_value, dict):
                    # 复合指标
                    for sub_name, sub_value in metric_value.items():
                        PerformanceMetrics.objects.create(
                            awr_report=awr_report,
                            category=category,
                            metric_name=f"{metric_name}.{sub_name}",
                            metric_value=str(sub_value),
                            unit=metrics.get('unit', ''),
                            description=f"{metric_name} - {sub_name}"
                        )
                        metrics_saved += 1
                else:
                    # 简单指标
                    PerformanceMetrics.objects.create(
                        awr_report=awr_report,
                        category=category,
                        metric_name=metric_name,
                        metric_value=str(metric_value),
                        unit=metrics.get('unit', ''),
                        description=metric_name
                    )
                    metrics_saved += 1
                    
    except Exception as e:
        logger.error(f"保存性能指标失败: {str(e)}")
    
    return metrics_saved


def _generate_performance_alerts(awr_report: AWRReport, analysis_result: Dict[str, Any]) -> int:
    """生成性能告警"""
    try:
        alert_generator = AlertGenerator(awr_report)
        alerts = alert_generator.generate_alerts_from_analysis(analysis_result)
        
        alerts_saved = 0
        for alert_data in alerts:
            PerformanceAlert.objects.create(
                awr_report=awr_report,
                alert_type=alert_data['type'],
                severity=alert_data['severity'],
                metric_name=alert_data['metric_name'],
                message=alert_data['message'],
                threshold_value=alert_data.get('threshold'),
                actual_value=alert_data.get('actual_value'),
                recommendation=alert_data.get('recommendation', '')
            )
            alerts_saved += 1
            
        return alerts_saved
        
    except Exception as e:
        logger.error(f"生成性能告警失败: {str(e)}")
        return 0


def _generate_optimization_recommendations(awr_report: AWRReport, analysis_result: Dict[str, Any]) -> int:
    """生成优化建议"""
    try:
        recommendation_engine = RecommendationEngine(awr_report)
        recommendations = recommendation_engine.generate_recommendations_from_analysis(analysis_result)
        
        recommendations_saved = 0
        for rec_data in recommendations:
            OptimizationRecommendation.objects.create(
                awr_report=awr_report,
                category=rec_data['category'],
                title=rec_data['title'],
                priority=rec_data['priority'],
                description=rec_data['description'],
                implementation_steps=rec_data.get('implementation_steps', ''),
                expected_impact=rec_data.get('expected_impact', ''),
                risk_level=rec_data.get('risk_level', 'LOW'),
                estimated_effort=rec_data.get('estimated_effort', '')
            )
            recommendations_saved += 1
            
        return recommendations_saved
        
    except Exception as e:
        logger.error(f"生成优化建议失败: {str(e)}")
        return 0


def _analyze_performance_trends(reports) -> Dict[str, Any]:
    """分析性能趋势"""
    trend_data = {
        'cpu_trend': [],
        'memory_trend': [],
        'io_trend': [],
        'wait_events_trend': []
    }
    
    # 这里可以实现具体的趋势分析逻辑
    # 例如计算各种指标的变化趋势、异常检测等
    
    return trend_data


def _generate_trend_alerts(trend_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """生成趋势告警"""
    alerts = []
    
    # 这里可以实现趋势告警生成逻辑
    # 例如检测性能恶化、异常波动等
    
    return alerts 