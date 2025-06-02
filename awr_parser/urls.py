"""
Oracle AWR分析器 - 解析器模块URL配置
{{CHENGQI: P1-LD-002 创建awr_parser应用URL配置 - 2025-06-01 23:04:00 +08:00}}
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'awr_parser'

# DRF路由器配置
router = DefaultRouter()
# router.register(r'parsers', views.AWRParserViewSet)
# router.register(r'results', views.ParseResultViewSet)

urlpatterns = [
    # DRF ViewSet路由
    path('', include(router.urls)),
    
    # 解析器相关路由
    # path('parse/', views.ParseAWRView.as_view(), name='parse_awr'),
    # path('parse/status/<str:task_id>/', views.ParseStatusView.as_view(), name='parse_status'),
    # path('versions/', views.SupportedVersionsView.as_view(), name='supported_versions'),
] 