"""
Oracle AWR分析器 - URL配置
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from analyzer.views.health import HealthCheckView, ReadinessCheckView, LivenessCheckView

urlpatterns = [
    # 管理后台
    path('admin/', admin.site.urls),
    
    # 健康检查端点
    path('api/health/', HealthCheckView.as_view(), name='health_check'),
    path('api/ready/', ReadinessCheckView.as_view(), name='readiness_check'),
    path('api/live/', LivenessCheckView.as_view(), name='liveness_check'),
    
    # API端点
    path('api/auth/', include('accounts.urls')),
    path('api/upload/', include('awr_upload.urls')),
    path('api/parser/', include('awr_parser.urls')),
    path('api/performance/', include('performance.urls')),
    path('api/reports/', include('reports.urls')),
    path('api/comparisons/', include('comparisons.urls')),
    path('api/exports/', include('exports.urls')),
]

# 开发环境静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 