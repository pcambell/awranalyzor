"""
接口限流中间件
实现基于用户和IP的请求频率限制，保护系统免受恶意请求攻击
"""

import time
import json
from typing import Dict, Optional, Tuple
from collections import defaultdict, deque

from django.http import JsonResponse, HttpRequest, HttpResponse
from django.conf import settings
from django.core.cache import cache
from django.utils.deprecation import MiddlewareMixin
from django.contrib.auth.models import AnonymousUser

import logging

logger = logging.getLogger(__name__)


class RateLimitExceeded(Exception):
    """请求频率超限异常"""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after


class RateLimitingMiddleware(MiddlewareMixin):
    """
    接口限流中间件
    
    支持多种限流策略：
    1. 基于IP地址的限流
    2. 基于用户的限流
    3. 基于API端点的限流
    4. 滑动窗口算法
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        
        # 从设置中获取限流配置
        self.rate_limits = getattr(settings, 'RATE_LIMITS', {
            'default': {'requests': 60, 'window': 60},  # 60请求/分钟
            'upload': {'requests': 10, 'window': 300},   # 10请求/5分钟
            'parsing': {'requests': 5, 'window': 600},   # 5请求/10分钟
            'anonymous': {'requests': 30, 'window': 60}, # 匿名用户30请求/分钟
        })
        
        # 内存存储（生产环境建议使用Redis）
        self.request_counts = defaultdict(lambda: defaultdict(deque))
        
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """中间件处理逻辑"""
        try:
            # 检查是否需要限流
            if self._should_rate_limit(request):
                self._check_rate_limit(request)
            
            response = self.get_response(request)
            return response
            
        except RateLimitExceeded as e:
            return self._create_rate_limit_response(e)
    
    def _should_rate_limit(self, request: HttpRequest) -> bool:
        """判断请求是否需要限流"""
        # 跳过某些路径
        skip_paths = ['/admin/', '/static/', '/media/']
        for path in skip_paths:
            if request.path.startswith(path):
                return False
                
        # 只对API请求限流
        return request.path.startswith('/api/')
    
    def _check_rate_limit(self, request: HttpRequest):
        """检查请求是否超过限流阈值"""
        # 获取限流配置
        limit_config = self._get_limit_config(request)
        if not limit_config:
            return
            
        # 获取客户端标识
        client_id = self._get_client_identifier(request)
        endpoint = self._get_endpoint_identifier(request)
        
        # 检查限流
        current_time = time.time()
        window_size = limit_config['window']
        max_requests = limit_config['requests']
        
        # 使用Redis缓存（如果可用）或内存存储
        if self._is_redis_available():
            self._check_rate_limit_redis(client_id, endpoint, current_time, window_size, max_requests)
        else:
            self._check_rate_limit_memory(client_id, endpoint, current_time, window_size, max_requests)
    
    def _get_limit_config(self, request: HttpRequest) -> Optional[Dict]:
        """获取请求对应的限流配置"""
        path = request.path.lower()
        
        # 根据路径匹配限流配置
        if '/upload/' in path:
            return self.rate_limits.get('upload')
        elif '/parsing/' in path or '/parse-progress/' in path:
            return self.rate_limits.get('parsing')
        elif isinstance(request.user, AnonymousUser):
            return self.rate_limits.get('anonymous')
        else:
            return self.rate_limits.get('default')
    
    def _get_client_identifier(self, request: HttpRequest) -> str:
        """获取客户端唯一标识"""
        if hasattr(request, 'user') and request.user.is_authenticated:
            return f"user_{request.user.id}"
        else:
            # 获取真实IP地址
            x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
            if x_forwarded_for:
                ip = x_forwarded_for.split(',')[0].strip()
            else:
                ip = request.META.get('REMOTE_ADDR', 'unknown')
            return f"ip_{ip}"
    
    def _get_endpoint_identifier(self, request: HttpRequest) -> str:
        """获取API端点标识"""
        path = request.path
        # 移除路径参数，只保留端点模式
        # 例如：/api/reports/123/ -> /api/reports/
        import re
        pattern = re.sub(r'/\d+/', '/{id}/', path)
        return f"{request.method}:{pattern}"
    
    def _is_redis_available(self) -> bool:
        """检查Redis是否可用"""
        try:
            cache.get('test_key')
            return True
        except:
            return False
    
    def _check_rate_limit_redis(
        self, 
        client_id: str, 
        endpoint: str, 
        current_time: float,
        window_size: int, 
        max_requests: int
    ):
        """使用Redis检查限流"""
        cache_key = f"rate_limit:{client_id}:{endpoint}"
        
        try:
            # 获取当前窗口内的请求记录
            request_times = cache.get(cache_key, [])
            
            # 清理过期记录
            cutoff_time = current_time - window_size
            request_times = [t for t in request_times if t > cutoff_time]
            
            # 检查是否超限
            if len(request_times) >= max_requests:
                oldest_request = min(request_times)
                retry_after = int(oldest_request + window_size - current_time) + 1
                raise RateLimitExceeded(
                    f"请求频率超限，每{window_size}秒最多{max_requests}个请求",
                    retry_after=retry_after
                )
            
            # 记录当前请求
            request_times.append(current_time)
            cache.set(cache_key, request_times, timeout=window_size + 60)
            
        except Exception as e:
            if isinstance(e, RateLimitExceeded):
                raise
            # Redis异常时降级到内存存储
            logger.warning(f"Redis限流失败，降级到内存存储: {str(e)}")
            self._check_rate_limit_memory(client_id, endpoint, current_time, window_size, max_requests)
    
    def _check_rate_limit_memory(
        self, 
        client_id: str, 
        endpoint: str, 
        current_time: float,
        window_size: int, 
        max_requests: int
    ):
        """使用内存检查限流"""
        request_queue = self.request_counts[client_id][endpoint]
        
        # 清理过期请求
        cutoff_time = current_time - window_size
        while request_queue and request_queue[0] <= cutoff_time:
            request_queue.popleft()
        
        # 检查是否超限
        if len(request_queue) >= max_requests:
            oldest_request = request_queue[0]
            retry_after = int(oldest_request + window_size - current_time) + 1
            raise RateLimitExceeded(
                f"请求频率超限，每{window_size}秒最多{max_requests}个请求",
                retry_after=retry_after
            )
        
        # 记录当前请求
        request_queue.append(current_time)
    
    def _create_rate_limit_response(self, exc: RateLimitExceeded) -> JsonResponse:
        """创建限流响应"""
        response_data = {
            'success': False,
            'error': {
                'code': 'RATE_LIMIT_EXCEEDED',
                'message': str(exc),
                'details': {
                    'retry_after': exc.retry_after
                },
                'timestamp': time.time()
            }
        }
        
        response = JsonResponse(response_data, status=429)
        if exc.retry_after:
            response['Retry-After'] = str(exc.retry_after)
        
        return response


class APIKeyRateLimitingMiddleware(MiddlewareMixin):
    """
    基于API Key的高级限流中间件
    为不同级别的API Key提供不同的限流策略
    """
    
    def __init__(self, get_response):
        super().__init__(get_response)
        self.get_response = get_response
        
        # API Key限流配置
        self.api_key_limits = getattr(settings, 'API_KEY_RATE_LIMITS', {
            'free': {'requests': 100, 'window': 3600},     # 免费版：100请求/小时
            'basic': {'requests': 1000, 'window': 3600},   # 基础版：1000请求/小时
            'premium': {'requests': 10000, 'window': 3600}, # 高级版：10000请求/小时
        })
    
    def __call__(self, request: HttpRequest) -> HttpResponse:
        """处理API Key限流"""
        api_key = self._extract_api_key(request)
        
        if api_key:
            try:
                self._check_api_key_rate_limit(api_key, request)
            except RateLimitExceeded as e:
                return self._create_rate_limit_response(e)
        
        return self.get_response(request)
    
    def _extract_api_key(self, request: HttpRequest) -> Optional[str]:
        """提取API Key"""
        # 从Header中获取
        api_key = request.META.get('HTTP_X_API_KEY')
        if api_key:
            return api_key
            
        # 从查询参数中获取
        return request.GET.get('api_key')
    
    def _check_api_key_rate_limit(self, api_key: str, request: HttpRequest):
        """检查API Key限流"""
        # 这里应该从数据库查询API Key的级别
        # 为了简化，这里假设API Key格式为 level_keystring
        key_level = 'free'  # 默认级别
        
        if api_key.startswith('basic_'):
            key_level = 'basic'
        elif api_key.startswith('premium_'):
            key_level = 'premium'
        
        limit_config = self.api_key_limits.get(key_level, self.api_key_limits['free'])
        
        # 使用类似的限流逻辑
        cache_key = f"api_key_rate_limit:{api_key}"
        current_time = time.time()
        window_size = limit_config['window']
        max_requests = limit_config['requests']
        
        try:
            request_times = cache.get(cache_key, [])
            cutoff_time = current_time - window_size
            request_times = [t for t in request_times if t > cutoff_time]
            
            if len(request_times) >= max_requests:
                oldest_request = min(request_times)
                retry_after = int(oldest_request + window_size - current_time) + 1
                raise RateLimitExceeded(
                    f"API Key请求频率超限，{key_level}级别每{window_size}秒最多{max_requests}个请求",
                    retry_after=retry_after
                )
            
            request_times.append(current_time)
            cache.set(cache_key, request_times, timeout=window_size + 60)
            
        except Exception as e:
            if not isinstance(e, RateLimitExceeded):
                logger.warning(f"API Key限流检查失败: {str(e)}")
    
    def _create_rate_limit_response(self, exc: RateLimitExceeded) -> JsonResponse:
        """创建API Key限流响应"""
        response_data = {
            'success': False,
            'error': {
                'code': 'API_KEY_RATE_LIMIT_EXCEEDED',
                'message': str(exc),
                'details': {
                    'retry_after': exc.retry_after,
                    'suggestion': '考虑升级到更高级别的API Key'
                },
                'timestamp': time.time()
            }
        }
        
        response = JsonResponse(response_data, status=429)
        if exc.retry_after:
            response['Retry-After'] = str(exc.retry_after)
            
        return response 