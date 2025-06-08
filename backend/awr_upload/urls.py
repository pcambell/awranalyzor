#!/usr/bin/env python3
"""
AWR上传模块URL配置
{{CHENGQI: P2-LD-005 解析器工厂和集成 - URL路由配置 - 2025-06-02T14:50:00}}
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
    path('api/', include(router.urls)),
    path('api/upload/', AWRUploadView.as_view(), name='upload'),
    path('api/validate/', AWRFileValidationView.as_view(), name='validate'),
    path('api/progress/<int:report_id>/', AWRParsingProgressView.as_view(), name='progress'),
] 