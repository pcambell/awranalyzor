"""
简单的健康检查视图
"""
from django.http import JsonResponse
from django.views import View
from django.db import connection
from django.utils import timezone


class HealthCheckView(View):
    """简单健康检查视图"""
    
    def get(self, request):
        """GET请求处理"""
        health_status = {
            'status': 'healthy',
            'timestamp': timezone.now().isoformat(),
            'checks': {}
        }
        
        # 数据库检查
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
            health_status['checks']['database'] = {'status': 'healthy'}
        except Exception as e:
            health_status['checks']['database'] = {'status': 'unhealthy', 'error': str(e)}
            health_status['status'] = 'unhealthy'
        
        # 整体状态确定
        status_code = 200 if health_status['status'] == 'healthy' else 503
        
        return JsonResponse(health_status, status=status_code) 