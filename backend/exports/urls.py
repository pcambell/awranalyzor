"""
Oracle AWR分析器 - 导出功能模块URL配置
{{CHENGQI: P1-LD-002 创建exports应用URL配置 - 2025-06-01 23:04:00 +08:00}}
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'exports'

# DRF路由器配置
router = DefaultRouter()
# router.register(r'exports', views.ExportRecordViewSet)

urlpatterns = [
    # DRF ViewSet路由
    path('', include(router.urls)),
    
    # 导出功能相关路由
    # path('pdf/', views.ExportPDFView.as_view(), name='export_pdf'),
    # path('excel/', views.ExportExcelView.as_view(), name='export_excel'),
    # path('csv/', views.ExportCSVView.as_view(), name='export_csv'),
    # path('status/<str:export_id>/', views.ExportStatusView.as_view(), name='export_status'),
] 