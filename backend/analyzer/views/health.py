"""
健康检查API视图
用于Docker健康检查、负载均衡器监控和系统状态检测
"""

import logging
import psutil
from django.http import JsonResponse
from django.views import View
from django.db import connection
from django.core.cache import cache
from django.conf import settings
from celery import current_app as celery_app

logger = logging.getLogger(__name__)


class HealthCheckView(View):
    """
    系统健康检查视图
    
    返回系统各组件的健康状态
    """
    
    def get(self, request):
        """执行健康检查"""
        health_status = {
            'status': 'healthy',
            'timestamp': self._get_timestamp(),
            'checks': {},
            'version': getattr(settings, 'VERSION', '1.0.0'),
        }
        
        # 执行各项检查
        checks = [
            ('database', self._check_database),
            ('cache', self._check_cache),
            ('celery', self._check_celery),
            ('disk_space', self._check_disk_space),
            ('memory', self._check_memory),
        ]
        
        overall_healthy = True
        
        for check_name, check_func in checks:
            # 检查配置是否启用
            if getattr(settings, 'HEALTH_CHECKS', {}).get(check_name, True):
                try:
                    result = check_func()
                    health_status['checks'][check_name] = result
                    
                    if not result.get('healthy', False):
                        overall_healthy = False
                        
                except Exception as e:
                    logger.error(f"健康检查失败 - {check_name}: {str(e)}")
                    health_status['checks'][check_name] = {
                        'healthy': False,
                        'error': str(e)
                    }
                    overall_healthy = False
            else:
                health_status['checks'][check_name] = {
                    'healthy': True,
                    'status': 'skipped'
                }
        
        # 设置总体状态
        if not overall_healthy:
            health_status['status'] = 'unhealthy'
        
        # 根据状态返回适当的HTTP状态码
        status_code = 200 if overall_healthy else 503
        
        return JsonResponse(health_status, status=status_code)
    
    def _get_timestamp(self):
        """获取当前时间戳"""
        from django.utils import timezone
        return timezone.now().isoformat()
    
    def _check_database(self):
        """检查数据库连接"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
                
            return {
                'healthy': True,
                'status': 'connected',
                'response_time_ms': self._measure_db_response_time()
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'status': 'connection_failed',
                'error': str(e)
            }
    
    def _check_cache(self):
        """检查缓存连接"""
        try:
            # 测试缓存读写
            test_key = 'health_check_test'
            test_value = 'test_value'
            
            cache.set(test_key, test_value, timeout=10)
            cached_value = cache.get(test_key)
            cache.delete(test_key)
            
            if cached_value == test_value:
                return {
                    'healthy': True,
                    'status': 'connected'
                }
            else:
                return {
                    'healthy': False,
                    'status': 'read_write_failed'
                }
                
        except Exception as e:
            return {
                'healthy': False,
                'status': 'connection_failed',
                'error': str(e)
            }
    
    def _check_celery(self):
        """检查Celery连接"""
        try:
            # 检查Celery broker连接
            inspect = celery_app.control.inspect()
            stats = inspect.stats()
            
            if stats:
                active_workers = len(stats)
                return {
                    'healthy': True,
                    'status': 'connected',
                    'active_workers': active_workers
                }
            else:
                return {
                    'healthy': False,
                    'status': 'no_workers'
                }
                
        except Exception as e:
            return {
                'healthy': False,
                'status': 'connection_failed',
                'error': str(e)
            }
    
    def _check_disk_space(self):
        """检查磁盘空间"""
        try:
            disk_usage = psutil.disk_usage('/')
            free_space_gb = disk_usage.free / (1024 ** 3)
            total_space_gb = disk_usage.total / (1024 ** 3)
            usage_percent = (disk_usage.used / disk_usage.total) * 100
            
            # 磁盘使用率超过90%视为不健康
            healthy = usage_percent < 90
            
            return {
                'healthy': healthy,
                'usage_percent': round(usage_percent, 2),
                'free_space_gb': round(free_space_gb, 2),
                'total_space_gb': round(total_space_gb, 2)
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _check_memory(self):
        """检查内存使用情况"""
        try:
            memory = psutil.virtual_memory()
            memory_usage_percent = memory.percent
            available_gb = memory.available / (1024 ** 3)
            total_gb = memory.total / (1024 ** 3)
            
            # 内存使用率超过90%视为不健康
            healthy = memory_usage_percent < 90
            
            return {
                'healthy': healthy,
                'usage_percent': round(memory_usage_percent, 2),
                'available_gb': round(available_gb, 2),
                'total_gb': round(total_gb, 2)
            }
            
        except Exception as e:
            return {
                'healthy': False,
                'error': str(e)
            }
    
    def _measure_db_response_time(self):
        """测量数据库响应时间"""
        import time
        
        try:
            start_time = time.time()
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM django_migrations")
                cursor.fetchone()
            end_time = time.time()
            
            return round((end_time - start_time) * 1000, 2)  # 毫秒
            
        except Exception:
            return None


class ReadinessCheckView(View):
    """
    就绪检查视图
    
    检查应用是否准备好接收流量
    """
    
    def get(self, request):
        """执行就绪检查"""
        readiness_status = {
            'ready': True,
            'timestamp': self._get_timestamp(),
            'checks': {}
        }
        
        # 关键服务检查
        critical_checks = [
            ('database', self._check_database_ready),
            ('migrations', self._check_migrations),
        ]
        
        ready = True
        
        for check_name, check_func in critical_checks:
            try:
                result = check_func()
                readiness_status['checks'][check_name] = result
                
                if not result.get('ready', False):
                    ready = False
                    
            except Exception as e:
                logger.error(f"就绪检查失败 - {check_name}: {str(e)}")
                readiness_status['checks'][check_name] = {
                    'ready': False,
                    'error': str(e)
                }
                ready = False
        
        readiness_status['ready'] = ready
        status_code = 200 if ready else 503
        
        return JsonResponse(readiness_status, status=status_code)
    
    def _get_timestamp(self):
        """获取当前时间戳"""
        from django.utils import timezone
        return timezone.now().isoformat()
    
    def _check_database_ready(self):
        """检查数据库是否就绪"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()
                
            return {
                'ready': True,
                'status': 'connected'
            }
            
        except Exception as e:
            return {
                'ready': False,
                'error': str(e)
            }
    
    def _check_migrations(self):
        """检查数据库迁移是否完成"""
        try:
            from django.db.migrations.executor import MigrationExecutor
            
            executor = MigrationExecutor(connection)
            plan = executor.migration_plan(executor.loader.graph.leaf_nodes())
            
            if plan:
                return {
                    'ready': False,
                    'status': 'pending_migrations',
                    'pending_count': len(plan)
                }
            else:
                return {
                    'ready': True,
                    'status': 'up_to_date'
                }
                
        except Exception as e:
            return {
                'ready': False,
                'error': str(e)
            }


class LivenessCheckView(View):
    """
    存活检查视图
    
    简单的存活检查，用于确认应用进程正在运行
    """
    
    def get(self, request):
        """执行存活检查"""
        return JsonResponse({
            'alive': True,
            'timestamp': self._get_timestamp(),
            'version': getattr(settings, 'VERSION', '1.0.0')
        })
    
    def _get_timestamp(self):
        """获取当前时间戳"""
        from django.utils import timezone
        return timezone.now().isoformat() 