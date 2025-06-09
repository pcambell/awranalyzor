#!/usr/bin/env python3
"""
AWR上传视图层
{{CHENGQI: P2-LD-005 解析器工厂和集成 - Django REST API集成 - 2025-06-02T14:45:00}}

提供AWR文件上传、状态查询等REST API接口
"""

import logging
from typing import Dict, Any

from django.contrib.auth.models import User
from django.http import JsonResponse
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.serializers import ModelSerializer, ValidationError
from rest_framework.views import APIView

from .models import AWRReport
from .services import AWRUploadService, AWRParsingService, AWRFileValidationError

logger = logging.getLogger(__name__)


class AWRReportSerializer(ModelSerializer):
    """AWR报告序列化器"""
    
    class Meta:
        model = AWRReport
        fields = [
            'id', 'name', 'description', 'original_filename', 
            'file_size', 'oracle_version', 'instance_name', 
            'host_name', 'database_id', 'instance_number',
            'snapshot_begin_time', 'snapshot_end_time', 
            'snapshot_duration_minutes', 'status', 'error_message',
            'tags', 'category', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'original_filename', 'file_size', 
            'oracle_version', 'instance_name', 'host_name', 
            'database_id', 'instance_number', 'snapshot_begin_time', 
            'snapshot_end_time', 'snapshot_duration_minutes', 
            'status', 'error_message', 'created_at', 'updated_at'
        ]


class AWRUploadView(APIView):
    """
    AWR文件上传API视图
    
    支持multipart/form-data文件上传
    """
    
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [AllowAny]
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.upload_service = AWRUploadService()
        self.parsing_service = AWRParsingService()
    
    def post(self, request, *args, **kwargs) -> Response:
        """
        处理AWR文件上传
        
        请求参数:
        - file: AWR文件 (required)
        - name: 报告名称 (optional)
        - description: 报告描述 (optional)
        - category: 环境分类 (optional)
        - tags: 标签列表，逗号分隔 (optional)
        
        返回:
        - 成功: AWR报告信息
        - 失败: 错误信息
        """
        try:
            # 获取上传的文件
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response(
                    {'error': '请选择要上传的AWR文件'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 获取其他参数
            name = request.data.get('name', '').strip()
            description = request.data.get('description', '').strip()
            category = request.data.get('category', '').strip()
            tags_str = request.data.get('tags', '').strip()
            tags = [tag.strip() for tag in tags_str.split(',') if tag.strip()] if tags_str else []
            
            # 处理用户认证问题 - 为未认证用户创建默认用户
            if request.user.is_authenticated:
                user = request.user
            else:
                # 创建或获取默认匿名用户
                user, created = User.objects.get_or_create(
                    username='anonymous_user',
                    defaults={
                        'email': 'anonymous@example.com',
                        'first_name': 'Anonymous',
                        'last_name': 'User'
                    }
                )
            
            # 创建AWR报告
            awr_report = self.upload_service.create_awr_report(
                uploaded_file=uploaded_file,
                user=user,
                name=name,
                description=description,
                category=category or None,
                tags=tags
            )
            
            # 调度解析任务
            parsing_scheduled = self.upload_service.schedule_parsing(awr_report)
            
            # 序列化响应数据
            serializer = AWRReportSerializer(awr_report)
            response_data = serializer.data
            response_data['parsing_scheduled'] = parsing_scheduled
            
            logger.info(f"AWR文件上传成功: {awr_report.id} - 用户: {user.username}")
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except AWRFileValidationError as e:
            user_name = request.user.username if request.user.is_authenticated else 'anonymous'
            logger.warning(f"AWR文件验证失败: {str(e)} - 用户: {user_name}")
            return Response(
                {'error': f'文件验证失败: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        except Exception as e:
            user_name = request.user.username if request.user.is_authenticated else 'anonymous'
            logger.error(f"AWR文件上传失败: {str(e)} - 用户: {user_name}")
            return Response(
                {'error': f'上传处理失败: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AWRReportViewSet(viewsets.ModelViewSet):
    """
    AWR报告ViewSet
    
    提供报告列表、详情查询、删除等功能
    {{CHENGQI: 启用删除功能 - 2025-06-09 19:29:13 +08:00 - 
    Action: Modified; Reason: 将ReadOnlyModelViewSet改为ModelViewSet以支持删除重复文件; Principle_Applied: 用户体验优化}}
    """
    
    serializer_class = AWRReportSerializer
    permission_classes = [IsAuthenticated]
    http_method_names = ['get', 'delete', 'head', 'options']  # 只允许GET和DELETE操作
    
    def get_queryset(self):
        """返回当前用户的AWR报告"""
        return AWRReport.objects.filter(uploaded_by=self.request.user).order_by('-created_at')
    
    def perform_destroy(self, instance):
        """删除报告时同时删除关联的文件"""
        try:
            # 删除文件
            if instance.file_path:
                instance.file_path.delete(save=False)
            
            # 删除数据库记录
            instance.delete()
            logger.info(f"AWR报告 {instance.id} 及关联文件已删除")
            
        except Exception as e:
            logger.error(f"删除AWR报告 {instance.id} 时出错: {e}")
            raise
    
    @action(detail=True, methods=['get'])
    def status(self, request, pk=None) -> Response:
        """
        获取报告处理状态
        
        返回:
        - 报告的当前状态和相关信息
        """
        try:
            report = self.get_object()
            
            return Response({
                'id': report.id,
                'status': report.status,
                'status_display': report.get_status_display(),
                'error_message': report.error_message,
                'is_processing': report.is_processing(),
                'is_completed': report.is_completed(),
                'is_failed': report.is_failed(),
                'updated_at': report.updated_at
            })
            
        except Exception as e:
            logger.error(f"获取报告状态失败: {str(e)}")
            return Response(
                {'error': '获取状态失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def reparse(self, request, pk=None) -> Response:
        """
        重新解析报告
        
        用于处理失败的报告重新解析
        """
        try:
            report = self.get_object()
            
            # 检查报告状态
            if report.is_processing():
                return Response(
                    {'error': '报告正在处理中，无法重新解析'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 重置状态并调度解析
            upload_service = AWRUploadService()
            parsing_scheduled = upload_service.schedule_parsing(report)
            
            return Response({
                'message': '重新解析任务已调度',
                'parsing_scheduled': parsing_scheduled,
                'status': report.status
            })
            
        except Exception as e:
            logger.error(f"重新解析失败: {str(e)}")
            return Response(
                {'error': '重新解析失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


@method_decorator(csrf_exempt, name='dispatch')
class AWRFileValidationView(APIView):
    """
    AWR文件验证API
    
    用于在实际上传前验证文件
    """
    
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs) -> Response:
        """
        验证AWR文件
        
        请求参数:
        - file: 要验证的AWR文件
        
        返回:
        - 验证结果和基础信息
        """
        try:
            uploaded_file = request.FILES.get('file')
            if not uploaded_file:
                return Response(
                    {'error': '请选择要验证的文件'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            upload_service = AWRUploadService()
            
            # 文件验证
            validation_info = upload_service.validate_file(uploaded_file)
            
            # 提取基础信息
            uploaded_file.seek(0)
            content = uploaded_file.read().decode('utf-8', errors='ignore')
            basic_info = upload_service.extract_basic_info(content)
            
            response_data = {
                'valid': True,
                'file_info': validation_info,
                'awr_info': basic_info,
                'message': '文件验证通过'
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
            
        except AWRFileValidationError as e:
            return Response({
                'valid': False,
                'error': str(e),
                'message': '文件验证失败'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        except Exception as e:
            logger.error(f"文件验证失败: {str(e)}")
            return Response({
                'valid': False,
                'error': '验证过程出错',
                'message': '验证过程出错'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class AWRParsingProgressView(APIView):
    """
    AWR解析进度查询API
    
    用于实时查询解析进度（为后续Celery集成做准备）
    """
    
    permission_classes = [IsAuthenticated]
    
    def get(self, request, report_id: int) -> Response:
        """
        查询指定报告的解析进度
        
        Args:
            report_id: 报告ID
            
        返回:
        - 解析进度信息
        """
        try:
            # 验证报告归属
            report = AWRReport.objects.filter(
                id=report_id, 
                uploaded_by=request.user
            ).first()
            
            if not report:
                return Response(
                    {'error': '报告不存在或无权限访问'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # TODO: 集成Celery后，这里将查询实际的任务进度
            progress_data = {
                'report_id': report.id,
                'status': report.status,
                'progress_percentage': self._calculate_progress_percentage(report.status),
                'current_stage': self._get_current_stage(report.status),
                'error_message': report.error_message,
                'updated_at': report.updated_at
            }
            
            return Response(progress_data, status=status.HTTP_200_OK)
            
        except Exception as e:
            logger.error(f"查询解析进度失败: {str(e)}")
            return Response(
                {'error': '查询进度失败'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _calculate_progress_percentage(self, status: str) -> int:
        """根据状态计算进度百分比"""
        progress_map = {
            'uploaded': 10,
            'validating': 20,
            'validated': 30,
            'parsing': 50,
            'parsed': 80,
            'analyzing': 90,
            'completed': 100,
            'failed': 0,
        }
        return progress_map.get(status, 0)
    
    def _get_current_stage(self, status: str) -> str:
        """根据状态获取当前阶段描述"""
        stage_map = {
            'uploaded': '文件已上传',
            'validating': '正在验证文件',
            'validated': '文件验证完成',
            'parsing': '正在解析AWR内容',
            'parsed': '解析完成',
            'analyzing': '正在进行性能分析',
            'completed': '处理完成',
            'failed': '处理失败',
        }
        return stage_map.get(status, '未知状态')
