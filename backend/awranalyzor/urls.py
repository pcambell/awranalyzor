"""
Oracle AWR报告分析软件 - URL配置
{{CHENGQI: P1-LD-002 配置项目主URL路由，包含API和各应用路由 - 2025-06-01 23:04:00 +08:00}}
{{CHENGQI: 修复上传路由映射 - 2025-06-09 18:43:53 +08:00 - 
Action: Modified; Reason: 调整awr_upload路由映射到/api/以匹配前端请求路径; Principle_Applied: KISS-保持路由简洁}}
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from .views import HealthCheckView

urlpatterns = [
    # 健康检查端点
    path('api/health/', HealthCheckView.as_view(), name='health_check'),
    
    # Django管理后台
    path('admin/', admin.site.urls),
    
    # DRF API根路径
    path('api/auth/', include('rest_framework.urls')),
    
    # AWR分析器核心API路由
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/parser/', include('awr_parser.urls')),
    path('api/v1/performance/', include('performance.urls')),
    path('api/v1/diagnostics/', include('diagnostics.urls')),
    path('api/v1/reports/', include('reports.urls')),
    path('api/v1/comparisons/', include('comparisons.urls')),
    path('api/v1/exports/', include('exports.urls')),
    
    # 上传模块专用路由 - 直接映射到/api/以匹配前端请求
    path('api/', include('awr_upload.urls')),
]

# 开发环境静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
