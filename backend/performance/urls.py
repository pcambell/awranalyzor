"""
Oracle AWR分析器 - 性能分析模块URL配置
{{CHENGQI: P1-LD-002 创建performance应用URL配置 - 2025-06-01 23:04:00 +08:00}}
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'performance'

# DRF路由器配置
router = DefaultRouter()
# router.register(r'metrics', views.PerformanceMetricViewSet)
# router.register(r'analysis', views.PerformanceAnalysisViewSet)

urlpatterns = [
    # DRF ViewSet路由
    path('', include(router.urls)),
    
    # 性能分析相关路由
    # path('analyze/', views.PerformanceAnalyzeView.as_view(), name='analyze'),
    # path('summary/<int:report_id>/', views.PerformanceSummaryView.as_view(), name='summary'),
    # path('trends/', views.PerformanceTrendsView.as_view(), name='trends'),
] 