"""
Oracle AWR分析器 - 报告对比模块URL配置
{{CHENGQI: P1-LD-002 创建comparisons应用URL配置 - 2025-06-01 23:04:00 +08:00}}
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'comparisons'

# DRF路由器配置
router = DefaultRouter()
# router.register(r'comparisons', views.ReportComparisonViewSet)

urlpatterns = [
    # DRF ViewSet路由
    path('', include(router.urls)),
    
    # 报告对比相关路由
    # path('compare/', views.CompareReportsView.as_view(), name='compare'),
    # path('results/<int:comparison_id>/', views.ComparisonResultsView.as_view(), name='results'),
    # path('history/', views.ComparisonHistoryView.as_view(), name='history'),
] 