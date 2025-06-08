"""
Oracle AWR报告分析软件 - URL配置
{{CHENGQI: P1-LD-002 配置项目主URL路由，包含API和各应用路由 - 2025-06-01 23:04:00 +08:00}}
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Django管理后台
    path('admin/', admin.site.urls),
    
    # DRF API根路径
    path('api/auth/', include('rest_framework.urls')),
    
    # AWR分析器核心API路由
    path('api/v1/accounts/', include('accounts.urls')),
    path('api/v1/upload/', include('awr_upload.urls')),
    path('api/v1/parser/', include('awr_parser.urls')),
    path('api/v1/performance/', include('performance.urls')),
    path('api/v1/diagnostics/', include('diagnostics.urls')),
    path('api/v1/reports/', include('reports.urls')),
    path('api/v1/comparisons/', include('comparisons.urls')),
    path('api/v1/exports/', include('exports.urls')),
]

# 开发环境静态文件服务
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
