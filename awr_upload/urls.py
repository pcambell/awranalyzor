"""
Oracle AWR分析器 - 文件上传模块URL配置
{{CHENGQI: P1-LD-002 创建awr_upload应用URL配置 - 2025-06-01 23:04:00 +08:00}}
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'awr_upload'

# DRF路由器配置
router = DefaultRouter()
# router.register(r'files', views.AWRFileUploadViewSet)

urlpatterns = [
    # DRF ViewSet路由
    path('', include(router.urls)),
    
    # 文件上传相关路由
    # path('upload/', views.FileUploadView.as_view(), name='file_upload'),
    # path('validate/', views.FileValidateView.as_view(), name='file_validate'),
    # path('progress/<str:upload_id>/', views.UploadProgressView.as_view(), name='upload_progress'),
] 