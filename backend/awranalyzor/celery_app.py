"""
Celery应用配置
实现异步任务处理：AWR文件解析、性能分析等
"""

import os
from celery import Celery
from django.conf import settings

# 设置Django设置模块
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'awranalyzor.settings')

# 创建Celery应用实例
app = Celery('awranalyzor')

# 从Django设置中加载配置
app.config_from_object('django.conf:settings', namespace='CELERY')

# 自动发现任务模块
app.autodiscover_tasks()

# Celery配置
app.conf.update(
    # 任务结果后端
    result_backend='redis://localhost:6379/0',
    
    # 消息代理
    broker_url='redis://localhost:6379/0',
    
    # 任务序列化
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    
    # 时区设置
    timezone='Asia/Shanghai',
    enable_utc=True,
    
    # 任务路由
    task_routes={
        'awr_parser.tasks.parse_awr_file': {'queue': 'awr_parsing'},
        'performance.tasks.analyze_performance': {'queue': 'performance_analysis'},
        'reports.tasks.generate_report': {'queue': 'report_generation'},
    },
    
    # 工作进程配置
    worker_prefetch_multiplier=1,  # 防止内存占用过高
    task_acks_late=True,          # 任务完成后才确认
    worker_max_tasks_per_child=1000,  # 防止内存泄漏
    
    # 任务超时配置
    task_soft_time_limit=300,     # 5分钟软超时
    task_time_limit=600,          # 10分钟硬超时
    
    # 任务重试配置
    task_default_retry_delay=60,  # 默认重试延迟
    task_max_retries=3,           # 最大重试次数
    
    # 结果过期时间
    result_expires=3600,          # 1小时后过期
    
    # 监控配置
    worker_send_task_events=True,
    task_send_sent_event=True,
)

# 队列配置
app.conf.task_routes = {
    # AWR解析任务 - 高优先级
    'awr_parser.tasks.*': {
        'queue': 'awr_parsing',
        'routing_key': 'awr_parsing',
    },
    
    # 性能分析任务 - 中优先级
    'performance.tasks.*': {
        'queue': 'performance_analysis',
        'routing_key': 'performance_analysis',
    },
    
    # 报告生成任务 - 低优先级
    'reports.tasks.*': {
        'queue': 'report_generation',
        'routing_key': 'report_generation',
    },
    
    # 清理任务 - 后台执行
    'common.tasks.cleanup_*': {
        'queue': 'cleanup',
        'routing_key': 'cleanup',
    },
}

# 队列声明
app.conf.task_create_missing_queues = True
app.conf.task_default_queue = 'default'
app.conf.task_default_exchange = 'default'
app.conf.task_default_exchange_type = 'direct'
app.conf.task_default_routing_key = 'default'

# 调试模式下的额外配置
if settings.DEBUG:
    app.conf.update(
        task_always_eager=False,  # 异步执行任务
        task_eager_propagates=True,  # 传播异常
        worker_log_level='DEBUG',
    )


@app.task(bind=True)
def debug_task(self):
    """调试任务"""
    print(f'Request: {self.request!r}')


# Celery信号处理
from celery.signals import (
    task_prerun, task_postrun, task_failure, 
    task_retry, worker_ready, worker_shutdown
)

import logging

logger = logging.getLogger(__name__)


@task_prerun.connect
def task_prerun_handler(sender=None, headers=None, body=None, **kwargs):
    """任务开始前的处理"""
    logger.info(f"任务开始: {sender}")


@task_postrun.connect
def task_postrun_handler(sender=None, task_id=None, task=None, args=None, kwargs=None, retval=None, state=None, **kwds):
    """任务完成后的处理"""
    logger.info(f"任务完成: {task.name} - 任务ID: {task_id} - 状态: {state}")


@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, traceback=None, einfo=None, **kwds):
    """任务失败处理"""
    logger.error(f"任务失败: {sender} - 任务ID: {task_id} - 异常: {exception}")


@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwds):
    """任务重试处理"""
    logger.warning(f"任务重试: {sender} - 任务ID: {task_id} - 原因: {reason}")


@worker_ready.connect
def worker_ready_handler(sender=None, **kwargs):
    """Worker准备就绪"""
    logger.info(f"Worker准备就绪: {sender}")


@worker_shutdown.connect
def worker_shutdown_handler(sender=None, **kwargs):
    """Worker关闭"""
    logger.info(f"Worker关闭: {sender}")


# 健康检查任务
@app.task
def health_check():
    """健康检查任务"""
    return {'status': 'healthy', 'timestamp': str(timezone.now())}


if __name__ == '__main__':
    app.start() 