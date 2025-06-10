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
from rest_framework.serializers import ModelSerializer, ValidationError, Serializer, CharField, IntegerField, FloatField, DateTimeField, ListField, DictField, SerializerMethodField
from rest_framework.views import APIView

from .models import AWRReport
from .services import AWRUploadService, AWRParsingService, AWRFileValidationError

logger = logging.getLogger(__name__)


class AWRParseResultSerializer(Serializer):
    """
    AWR解析结果序列化器
    {{CHENGQI: 添加解析结果序列化器 - 2025-06-10 12:37:15 +08:00 - 
    Action: Added; Reason: 为解析结果API提供标准化的数据格式; Principle_Applied: 数据一致性}}
    """
    id = CharField()
    file_id = CharField()
    report_id = CharField(required=False, allow_null=True)
    status = CharField()
    progress = IntegerField()
    start_time = DateTimeField()
    estimated_time_remaining = IntegerField(required=False, allow_null=True)
    parser_version = CharField()
    sections_parsed = IntegerField()
    total_sections = IntegerField()
    parse_errors = ListField(required=False, default=list)
    data_completeness = FloatField(required=False, allow_null=True)
    data_quality_score = FloatField(required=False, allow_null=True)
    error_message = CharField(required=False, allow_null=True)
    db_info = DictField(required=False, allow_null=True)
    snapshot_info = DictField(required=False, allow_null=True)
    parse_metadata = DictField(required=False, allow_null=True)
    load_profile = ListField(required=False, default=list)
    wait_events = ListField(required=False, default=list)
    sql_statistics = ListField(required=False, default=list)


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


class AWRParseResultView(APIView):
    """
    AWR解析结果API视图
    {{CHENGQI: 添加解析结果API视图 - 2025-06-10 12:37:15 +08:00 - 
    Action: Added; Reason: 实现解析结果检索功能，修复前端404错误; Principle_Applied: 单一职责原则}}
    
    提供获取详细AWR解析结果的功能
    """
    
    permission_classes = [AllowAny]  # 暂时允许匿名访问，与上传保持一致
    
    def get(self, request, report_id: int) -> Response:
        """
        获取AWR报告的详细解析结果
        
        Args:
            report_id: AWR报告ID
            
        Returns:
            AWR解析结果的详细数据
        """
        try:
            # 处理认证问题 - 与上传视图保持一致的逻辑
            if request.user.is_authenticated:
                user = request.user
                # 验证报告归属
                report = AWRReport.objects.filter(
                    id=report_id, 
                    uploaded_by=user
                ).first()
            else:
                # 对于匿名用户，查找anonymous_user上传的报告
                try:
                    anonymous_user = User.objects.get(username='anonymous_user')
                    report = AWRReport.objects.filter(
                        id=report_id,
                        uploaded_by=anonymous_user
                    ).first()
                except User.DoesNotExist:
                    report = None
            
            if not report:
                return Response(
                    {'error': '报告不存在或无权限访问'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # 检查报告是否已成功解析
            if report.status not in ['parsed', 'completed']:
                return Response(
                    {
                        'error': '报告尚未解析完成',
                        'current_status': report.status,
                        'status_display': report.get_status_display()
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # 重新解析文件获取详细结果
            try:
                parse_result = self._get_parse_result(report)
                
                # 构建响应数据
                result_data = self._build_parse_result_data(report, parse_result)
                
                logger.info(f"成功返回AWR解析结果: 报告 {report_id}")
                return Response(result_data, status=status.HTTP_200_OK)
                
            except Exception as parse_error:
                logger.error(f"重新解析AWR报告 {report_id} 失败: {parse_error}")
                return Response(
                    {'error': f'解析结果获取失败: {str(parse_error)}'},
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
            
        except Exception as e:
            logger.error(f"获取解析结果失败: {str(e)}")
            return Response(
                {'error': '服务器内部错误'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _get_parse_result(self, report: AWRReport):
        """
        获取AWR报告的解析结果
        
        Args:
            report: AWR报告实例
            
        Returns:
            解析结果对象
        """
        # 读取文件内容
        with open(report.file_path.path, 'r', encoding='utf-8', errors='ignore') as file:
            content = file.read()
        
        # 使用解析器进行解析
        from awr_parser.parsers.factory import parse_awr
        result = parse_awr(content)
        
        return result
    
    def _build_parse_result_data(self, report: AWRReport, parse_result) -> Dict[str, Any]:
        """
        构建解析结果响应数据
        
        Args:
            report: AWR报告实例
            parse_result: 解析结果对象
            
        Returns:
            格式化的解析结果数据
        """
        # 基础信息
        result_data = {
            'id': str(report.id),
            'file_id': str(report.id),  # 使用report.id作为file_id
            'report_id': str(report.id),
            'status': 'completed' if parse_result.parse_status.value == 'success' else 'failed',
            'progress': 100,
            'start_time': report.created_at.isoformat(),
            'estimated_time_remaining': None,
            'parser_version': '1.0.0',
            'sections_parsed': len(parse_result.parsed_sections),
            'total_sections': 6,  # 预期的总区块数
            'parse_errors': [
                {
                    'section': error.section,
                    'type': error.error_type,
                    'message': error.message,
                    'details': error.details
                }
                for error in parse_result.errors
            ],
            'data_completeness': self._calculate_data_completeness(parse_result),
            'data_quality_score': self._calculate_data_quality_score(parse_result),
            'error_message': report.error_message
        }
        
        # 数据库信息
        if parse_result.db_info:
            result_data['db_info'] = {
                'db_name': parse_result.db_info.db_name,
                'instance_name': parse_result.db_info.instance_name,
                'db_version': parse_result.db_info.version.value,
                'host_name': report.host_name or 'Unknown',
                'platform': 'Linux x86-64',  # 默认值
                'rac_instances': None,
                'cdb_name': None,
                'pdb_name': None
            }
        
        # 快照信息
        if parse_result.snapshot_info:
            result_data['snapshot_info'] = {
                'begin_snap_id': parse_result.snapshot_info.begin_snap_id,
                'end_snap_id': parse_result.snapshot_info.end_snap_id,
                'begin_time': parse_result.snapshot_info.begin_time.strftime('%Y-%m-%d %H:%M:%S'),
                'end_time': parse_result.snapshot_info.end_time.strftime('%Y-%m-%d %H:%M:%S'),
                'snapshot_duration_minutes': parse_result.snapshot_info.elapsed_time_minutes
            }
        
        # 解析元数据
        result_data['parse_metadata'] = {
            'parse_duration_seconds': 2.5,  # 估算值
            'parser_version': '1.0.0',
            'oracle_version': parse_result.db_info.version.value if parse_result.db_info else 'unknown'
        }
        
        # 负载概要
        if parse_result.load_profile:
            result_data['load_profile'] = self._format_load_profile(parse_result.load_profile)
        
        # 等待事件
        result_data['wait_events'] = [
            {
                'event_name': event.event_name,
                'waits': event.waits,
                'time_waited_seconds': event.time_waited_ms / 1000.0 if event.time_waited_ms else 0,
                'avg_wait_ms': event.avg_wait_ms,
                'percent_db_time': getattr(event, 'percent_db_time', 0)
            }
            for event in parse_result.wait_events
        ]
        
        # SQL统计
        result_data['sql_statistics'] = [
            {
                'sql_id': sql.sql_id,
                'executions': sql.executions,
                'cpu_time_seconds': sql.cpu_time_ms / 1000.0 if sql.cpu_time_ms else 0,
                'elapsed_time_seconds': sql.elapsed_time_ms / 1000.0 if sql.elapsed_time_ms else 0,
                'buffer_gets': sql.buffer_gets,
                'disk_reads': sql.disk_reads,
                'rows_processed': sql.rows_processed
            }
            for sql in parse_result.sql_statistics
        ]
        
        return result_data
    
    def _format_load_profile(self, load_profile) -> list:
        """格式化负载概要数据"""
        if not load_profile:
            return []
        
        # 将LoadProfile对象转换为前端期望的格式
        metrics = []
        
        # DB Time相关指标
        if hasattr(load_profile, 'db_time_minutes') and load_profile.db_time_minutes:
            metrics.append({
                'metric_name': 'DB Time',
                'per_second': round(load_profile.db_time_minutes * 60 / 3600, 2),
                'per_transaction': None,
                'per_exec': None,
                'per_call': None
            })
        
        # CPU Time
        if hasattr(load_profile, 'db_cpu_minutes') and load_profile.db_cpu_minutes:
            metrics.append({
                'metric_name': 'DB CPU',
                'per_second': round(load_profile.db_cpu_minutes * 60 / 3600, 2),
                'per_transaction': None,
                'per_exec': None,
                'per_call': None
            })
        
        # Logical reads
        if hasattr(load_profile, 'logical_reads') and load_profile.logical_reads:
            metrics.append({
                'metric_name': 'Logical reads',
                'per_second': round(load_profile.logical_reads / 3600, 2),
                'per_transaction': None,
                'per_exec': None,
                'per_call': None
            })
        
        # Physical reads
        if hasattr(load_profile, 'physical_reads') and load_profile.physical_reads:
            metrics.append({
                'metric_name': 'Physical reads',
                'per_second': round(load_profile.physical_reads / 3600, 2),
                'per_transaction': None,
                'per_exec': None,
                'per_call': None
            })
        
        return metrics
    
    def _calculate_data_completeness(self, parse_result) -> float:
        """计算数据完整性百分比"""
        total_sections = 6
        parsed_sections = len(parse_result.parsed_sections)
        return round((parsed_sections / total_sections) * 100, 1)
    
    def _calculate_data_quality_score(self, parse_result) -> float:
        """计算数据质量评分"""
        base_score = 100
        
        # 根据错误数量减分
        error_penalty = len(parse_result.errors) * 5
        warning_penalty = len(parse_result.warnings) * 2
        
        score = base_score - error_penalty - warning_penalty
        return max(0, min(100, score))
