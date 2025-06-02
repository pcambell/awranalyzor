"""
Oracle AWR分析器 - 用户管理模块URL配置
{{CHENGQI: P1-LD-002 创建accounts应用URL配置 - 2025-06-01 23:04:00 +08:00}}
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

app_name = 'accounts'

# DRF路由器配置
router = DefaultRouter()
# router.register(r'users', views.UserViewSet)
# router.register(r'profiles', views.UserProfileViewSet)

urlpatterns = [
    # DRF ViewSet路由
    path('', include(router.urls)),
    
    # 自定义认证相关路由
    # path('login/', views.LoginView.as_view(), name='login'),
    # path('logout/', views.LogoutView.as_view(), name='logout'),
    # path('register/', views.RegisterView.as_view(), name='register'),
    # path('profile/', views.UserProfileView.as_view(), name='profile'),
] 