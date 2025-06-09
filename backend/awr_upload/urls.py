#!/usr/bin/env python3
"""
AWR上传模块URL配置
{{CHENGQI: P2-LD-005 解析器工厂和集成 - URL路由配置 - 2025-06-02T14:50:00}}
{{CHENGQI: 修复URL路由匹配问题 - 2025-06-09 18:43:53 +08:00 - 
Action: Modified; Reason: 修复前端/api/upload/与后端路由不匹配的404错误; Principle_Applied: KISS-简化路由配置}}
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    AWRUploadView,
    AWRReportViewSet,
    AWRFileValidationView,
    AWRParsingProgressView
)

app_name = 'awr_upload'

# DRF路由器配置
router = DefaultRouter()
router.register(r'reports', AWRReportViewSet, basename='awrreport')

urlpatterns = [
    # API接口
    path('', include(router.urls)),  # DRF路由器直接映射
    path('upload/', AWRUploadView.as_view(), name='upload'),  # 对应 /api/upload/
    path('validate/', AWRFileValidationView.as_view(), name='validate'),  # 对应 /api/validate/
    path('progress/<int:report_id>/', AWRParsingProgressView.as_view(), name='progress'),  # 对应 /api/progress/{id}/
] 