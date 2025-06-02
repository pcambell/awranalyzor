"""
Oracle AWR分析器 - 诊断规则模块URL配置
{{CHENGQI: P1-LD-002 创建diagnostics应用URL配置 - 2025-06-01 23:04:00 +08:00}}
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'diagnostics'

# DRF路由器配置
router = DefaultRouter()
# router.register(r'rules', views.DiagnosticRuleViewSet)
# router.register(r'results', views.DiagnosticResultViewSet)

urlpatterns = [
    # DRF ViewSet路由
    path('', include(router.urls)),
    
    # 诊断分析相关路由
    # path('diagnose/', views.DiagnoseView.as_view(), name='diagnose'),
    # path('rules/config/', views.RuleConfigView.as_view(), name='rule_config'),
    # path('results/<int:report_id>/', views.DiagnosticResultsView.as_view(), name='results'),
] 