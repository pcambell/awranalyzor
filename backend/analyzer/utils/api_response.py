"""
标准化API响应工具
实现DRY原则：避免重复的响应格式代码
"""

import time
from typing import Any, Dict, Optional, Union, List
from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework import status


class APIResponse:
    """
    标准化API响应工具类
    
    提供统一的成功和错误响应格式，确保API响应的一致性
    """
    
    @staticmethod
    def success(
        data: Any = None,
        message: str = "操作成功",
        status_code: int = 200,
        pagination: Dict = None,
        extra: Dict = None
    ) -> Response:
        """
        创建成功响应
        
        Args:
            data: 响应数据
            message: 成功消息
            status_code: HTTP状态码
            pagination: 分页信息
            extra: 额外信息
            
        Returns:
            Response: DRF响应对象
        """
        response_data = {
            'success': True,
            'message': message,
            'data': data,
            'timestamp': time.time()
        }
        
        if pagination:
            response_data['pagination'] = pagination
            
        if extra:
            response_data.update(extra)
        
        return Response(response_data, status=status_code)
    
    @staticmethod
    def error(
        message: str,
        code: str = 'ERROR',
        details: Dict = None,
        status_code: int = 400,
        request_id: str = None
    ) -> Response:
        """
        创建错误响应
        
        Args:
            message: 错误消息
            code: 错误代码
            details: 错误详情
            status_code: HTTP状态码
            request_id: 请求ID
            
        Returns:
            Response: DRF响应对象
        """
        response_data = {
            'success': False,
            'error': {
                'code': code,
                'message': message,
                'details': details or {},
                'timestamp': time.time()
            }
        }
        
        if request_id:
            response_data['error']['request_id'] = request_id
        
        return Response(response_data, status=status_code)
    
    @staticmethod
    def validation_error(
        errors: Union[Dict, List, str],
        message: str = "数据验证失败"
    ) -> Response:
        """
        创建验证错误响应
        
        Args:
            errors: 验证错误详情
            message: 错误消息
            
        Returns:
            Response: DRF响应对象
        """
        details = {}
        
        if isinstance(errors, dict):
            details['field_errors'] = errors
        elif isinstance(errors, list):
            details['errors'] = errors
        else:
            details['error'] = str(errors)
        
        return APIResponse.error(
            message=message,
            code='VALIDATION_ERROR',
            details=details,
            status_code=400
        )
    
    @staticmethod
    def not_found(
        message: str = "请求的资源不存在",
        resource_type: str = None
    ) -> Response:
        """
        创建资源未找到响应
        
        Args:
            message: 错误消息
            resource_type: 资源类型
            
        Returns:
            Response: DRF响应对象
        """
        details = {}
        if resource_type:
            details['resource_type'] = resource_type
        
        return APIResponse.error(
            message=message,
            code='NOT_FOUND',
            details=details,
            status_code=404
        )
    
    @staticmethod
    def forbidden(
        message: str = "权限不足",
        required_permission: str = None
    ) -> Response:
        """
        创建权限不足响应
        
        Args:
            message: 错误消息
            required_permission: 所需权限
            
        Returns:
            Response: DRF响应对象
        """
        details = {}
        if required_permission:
            details['required_permission'] = required_permission
        
        return APIResponse.error(
            message=message,
            code='PERMISSION_DENIED',
            details=details,
            status_code=403
        )
    
    @staticmethod
    def server_error(
        message: str = "服务器内部错误",
        debug_info: Dict = None
    ) -> Response:
        """
        创建服务器错误响应
        
        Args:
            message: 错误消息
            debug_info: 调试信息（仅在DEBUG模式下包含）
            
        Returns:
            Response: DRF响应对象
        """
        from django.conf import settings
        
        details = {}
        if debug_info and settings.DEBUG:
            details['debug_info'] = debug_info
        
        return APIResponse.error(
            message=message,
            code='INTERNAL_ERROR',
            details=details,
            status_code=500
        )
    
    @staticmethod
    def paginated_success(
        data: List,
        page: int,
        page_size: int,
        total_count: int,
        message: str = "查询成功"
    ) -> Response:
        """
        创建分页成功响应
        
        Args:
            data: 数据列表
            page: 当前页码
            page_size: 每页大小
            total_count: 总记录数
            message: 成功消息
            
        Returns:
            Response: DRF响应对象
        """
        total_pages = (total_count + page_size - 1) // page_size
        
        pagination = {
            'page': page,
            'page_size': page_size,
            'total_count': total_count,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_previous': page > 1
        }
        
        return APIResponse.success(
            data=data,
            message=message,
            pagination=pagination
        )


class APIResponseMixin:
    """
    API响应混入类
    
    为视图类提供便捷的响应方法
    """
    
    def success_response(self, *args, **kwargs) -> Response:
        """成功响应"""
        return APIResponse.success(*args, **kwargs)
    
    def error_response(self, *args, **kwargs) -> Response:
        """错误响应"""
        return APIResponse.error(*args, **kwargs)
    
    def validation_error_response(self, *args, **kwargs) -> Response:
        """验证错误响应"""
        return APIResponse.validation_error(*args, **kwargs)
    
    def not_found_response(self, *args, **kwargs) -> Response:
        """未找到响应"""
        return APIResponse.not_found(*args, **kwargs)
    
    def forbidden_response(self, *args, **kwargs) -> Response:
        """权限不足响应"""
        return APIResponse.forbidden(*args, **kwargs)
    
    def server_error_response(self, *args, **kwargs) -> Response:
        """服务器错误响应"""
        return APIResponse.server_error(*args, **kwargs)
    
    def paginated_response(self, *args, **kwargs) -> Response:
        """分页响应"""
        return APIResponse.paginated_success(*args, **kwargs)


def create_json_response(data: Dict, status_code: int = 200) -> JsonResponse:
    """
    创建原生Django JsonResponse
    
    Args:
        data: 响应数据
        status_code: HTTP状态码
        
    Returns:
        JsonResponse: Django JsonResponse对象
    """
    return JsonResponse(data, status=status_code, json_dumps_params={
        'ensure_ascii': False,  # 支持中文
        'indent': 2 if status_code >= 400 else None  # 错误响应格式化
    }) 