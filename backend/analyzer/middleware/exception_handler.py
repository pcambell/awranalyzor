"""
全局异常处理中间件
实现SOLID原则：单一职责 - 专注于异常处理和错误响应标准化
"""

import logging
import traceback
import time
from typing import Any, Dict, Optional, Callable
from uuid import uuid4

from django.http import JsonResponse, HttpRequest, HttpResponse
from django.conf import settings
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError, OperationalError
from django.utils.deprecation import MiddlewareMixin
from rest_framework.views import exception_handler as drf_exception_handler
from rest_framework.response import Response
from rest_framework import status
from rest_framework.exceptions import (
    ValidationError as DRFValidationError,
    AuthenticationFailed,
    PermissionDenied as DRFPermissionDenied,
    NotFound,
    MethodNotAllowed,
    Throttled
)

logger = logging.getLogger(__name__)
error_logger = logging.getLogger('awr.errors')
performance_logger = logging.getLogger('awr.performance')


class AWRAnalysisError(Exception):
    """AWR分析基础异常"""
    def __init__(self, message: str, code: str = 'ANALYSIS_ERROR', details: Dict = None):
        super().__init__(message)
        self.code = code
        self.details = details or {}


class ParsingError(AWRAnalysisError):
    """解析异常"""
    def __init__(self, message: str, oracle_version: str = None, **kwargs):
        super().__init__(message, code='PARSING_ERROR', **kwargs)
        if oracle_version:
            self.details['oracle_version'] = oracle_version


class ValidationError(AWRAnalysisError):
    """校验异常"""
    def __init__(self, message: str, field: str = None, **kwargs):
        super().__init__(message, code='VALIDATION_ERROR', **kwargs)
        if field:
            self.details['field'] = field


class UnsupportedVersionError(AWRAnalysisError):
    """不支持的版本异常"""
    def __init__(self, message: str, version: str = None, **kwargs):
        super().__init__(message, code='UNSUPPORTED_VERSION', **kwargs)
        if version:
            self.details['version'] = version


class SecurityError(AWRAnalysisError):
    """安全异常"""
    def __init__(self, message: str, **kwargs):
        super().__init__(message, code='SECURITY_ERROR', **kwargs)


class ExceptionHandlerMiddleware(MiddlewareMixin):
    """
    全局异常处理中间件
    
    功能：
    1. 捕获并处理所有未处理的异常
    2. 标准化错误响应格式
    3. 记录详细的错误日志
    4. 性能监控和统计
    """
    
    def __init__(self, get_response: Callable):
        super().__init__(get_response)
        self.get_response = get_response
        
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """中间件主要处理逻辑"""
        start_time = time.time()
        request_id = str(uuid4())
        request.request_id = request_id
        
        try:
            response = self.get_response(request)
            
            # 记录性能指标
            self._log_performance(request, response, start_time)
            
            return response
            
        except Exception as exc:
            # 记录异常和性能
            self._log_performance(request, None, start_time, exc)
            
            # 处理异常并返回标准化响应
            return self._handle_exception(request, exc)
    
    def _handle_exception(self, request: HttpRequest, exc: Exception) -> JsonResponse:
        """
        处理异常并返回标准化错误响应
        
        Args:
            request: HTTP请求对象
            exc: 异常实例
            
        Returns:
            JsonResponse: 标准化错误响应
        """
        request_id = getattr(request, 'request_id', 'unknown')
        
        # 记录详细异常信息
        error_logger.error(
            f"Request {request_id} failed: {exc.__class__.__name__}: {str(exc)}",
            extra={
                'request_id': request_id,
                'path': request.path,
                'method': request.method,
                'user': str(request.user) if hasattr(request, 'user') else 'anonymous',
                'exception_type': exc.__class__.__name__,
                'traceback': traceback.format_exc()
            }
        )
        
        # 根据异常类型生成响应
        if isinstance(exc, AWRAnalysisError):
            return self._create_error_response(
                code=exc.code,
                message=str(exc),
                details=exc.details,
                status_code=400,
                request_id=request_id
            )
        
        elif isinstance(exc, ValidationError):
            return self._create_error_response(
                code='VALIDATION_ERROR',
                message='数据验证失败',
                details={'validation_errors': str(exc)},
                status_code=400,
                request_id=request_id
            )
        
        elif isinstance(exc, PermissionDenied):
            return self._create_error_response(
                code='PERMISSION_DENIED',
                message='权限不足',
                status_code=403,
                request_id=request_id
            )
        
        elif isinstance(exc, IntegrityError):
            return self._create_error_response(
                code='DATABASE_INTEGRITY_ERROR',
                message='数据完整性错误',
                details={'database_error': str(exc)},
                status_code=409,
                request_id=request_id
            )
        
        elif isinstance(exc, OperationalError):
            return self._create_error_response(
                code='DATABASE_OPERATIONAL_ERROR',
                message='数据库操作错误',
                status_code=503,
                request_id=request_id
            )
        
        else:
            # 未知异常 - 不暴露内部细节
            return self._create_error_response(
                code='INTERNAL_ERROR',
                message='服务器内部错误' if not settings.DEBUG else str(exc),
                details={'traceback': traceback.format_exc()} if settings.DEBUG else {},
                status_code=500,
                request_id=request_id
            )
    
    def _create_error_response(
        self, 
        code: str, 
        message: str, 
        details: Dict = None,
        status_code: int = 400,
        request_id: str = None
    ) -> JsonResponse:
        """
        创建标准化错误响应
        
        Args:
            code: 错误代码
            message: 错误消息
            details: 错误详情
            status_code: HTTP状态码
            request_id: 请求ID
            
        Returns:
            JsonResponse: 标准化错误响应
        """
        response_data = {
            'success': False,
            'error': {
                'code': code,
                'message': message,
                'details': details or {},
                'request_id': request_id,
                'timestamp': time.time()
            }
        }
        
        return JsonResponse(response_data, status=status_code)
    
    def _log_performance(
        self, 
        request: HttpRequest, 
        response: Optional[HttpResponse], 
        start_time: float,
        exception: Exception = None
    ):
        """
        记录性能指标
        
        Args:
            request: HTTP请求
            response: HTTP响应（可能为None）
            start_time: 请求开始时间
            exception: 异常对象（如果有）
        """
        execution_time = time.time() - start_time
        request_id = getattr(request, 'request_id', 'unknown')
        
        log_data = {
            'request_id': request_id,
            'method': request.method,
            'path': request.path,
            'execution_time': round(execution_time, 3),
            'status_code': response.status_code if response else 'error',
            'user': str(request.user) if hasattr(request, 'user') else 'anonymous',
            'exception': exception.__class__.__name__ if exception else None
        }
        
        if execution_time > 5.0:  # 慢查询警告
            performance_logger.warning(f"Slow request detected: {log_data}")
        else:
            performance_logger.info(f"Request completed: {log_data}")


def custom_drf_exception_handler(exc, context):
    """
    DRF自定义异常处理器
    与中间件配合，提供一致的错误响应格式
    """
    request = context.get('request')
    request_id = getattr(request, 'request_id', str(uuid4())) if request else str(uuid4())
    
    # 首先调用DRF默认异常处理器
    response = drf_exception_handler(exc, context)
    
    if response is not None:
        # 标准化DRF异常响应格式
        custom_response_data = {
            'success': False,
            'error': {
                'code': _get_error_code_from_exception(exc),
                'message': _get_error_message_from_exception(exc),
                'details': response.data if isinstance(response.data, dict) else {'errors': response.data},
                'request_id': request_id,
                'timestamp': time.time()
            }
        }
        
        response.data = custom_response_data
        
        # 记录API异常
        error_logger.warning(
            f"DRF API exception: {exc.__class__.__name__}: {str(exc)}",
            extra={
                'request_id': request_id,
                'path': request.path if request else 'unknown',
                'method': request.method if request else 'unknown',
                'exception_type': exc.__class__.__name__,
                'status_code': response.status_code
            }
        )
    
    return response


def _get_error_code_from_exception(exc) -> str:
    """从异常获取错误代码"""
    error_code_map = {
        DRFValidationError: 'VALIDATION_ERROR',
        AuthenticationFailed: 'AUTHENTICATION_FAILED',
        DRFPermissionDenied: 'PERMISSION_DENIED',
        NotFound: 'NOT_FOUND',
        MethodNotAllowed: 'METHOD_NOT_ALLOWED',
        Throttled: 'RATE_LIMITED',
    }
    
    return error_code_map.get(type(exc), 'API_ERROR')


def _get_error_message_from_exception(exc) -> str:
    """从异常获取友好的错误消息"""
    message_map = {
        DRFValidationError: '请求数据验证失败',
        AuthenticationFailed: '身份认证失败',
        DRFPermissionDenied: '权限不足',
        NotFound: '请求的资源不存在',
        MethodNotAllowed: '不支持的HTTP方法',
        Throttled: '请求频率超限',
    }
    
    return message_map.get(type(exc), str(exc)) 