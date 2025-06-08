"""
Oracle AWR分析器 - 报告生成模块URL配置
{{CHENGQI: P1-LD-002 创建reports应用URL配置 - 2025-06-01 23:04:00 +08:00}}
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'reports'

# DRF路由器配置
router = DefaultRouter()
# router.register(r'reports', views.AWRReportViewSet)
# router.register(r'templates', views.ReportTemplateViewSet)

urlpatterns = [
    # DRF ViewSet路由
    path('', include(router.urls)),
    
    # 报告生成相关路由
    # path('generate/', views.GenerateReportView.as_view(), name='generate'),
    # path('preview/<int:report_id>/', views.PreviewReportView.as_view(), name='preview'),
    # path('download/<int:report_id>/', views.DownloadReportView.as_view(), name='download'),
    # path('list/', views.ReportListView.as_view(), name='list'),
] 