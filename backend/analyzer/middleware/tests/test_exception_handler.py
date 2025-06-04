"""
异常处理中间件测试
验证全局异常处理和标准化响应格式
"""

import json
import time
from unittest.mock import Mock, patch
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError

from analyzer.middleware.exception_handler import (
    ExceptionHandlerMiddleware,
    AWRAnalysisError,
    ParsingError,
    SecurityError,
    custom_drf_exception_handler
)


class ExceptionHandlerMiddlewareTestCase(TestCase):
    """异常处理中间件测试"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
        
        # 创建中间件实例
        self.get_response_mock = Mock()
        self.middleware = ExceptionHandlerMiddleware(self.get_response_mock)
    
    def test_successful_request(self):
        """测试正常请求处理"""
        request = self.factory.get('/api/test/')
        request.user = self.user
        
        # 模拟成功响应
        self.get_response_mock.return_value = JsonResponse({'success': True})
        
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 200)
        self.assertTrue(hasattr(request, 'request_id'))
    
    def test_awr_analysis_error(self):
        """测试AWR分析异常处理"""
        request = self.factory.post('/api/upload/')
        request.user = self.user
        
        # 模拟AWR分析异常
        self.get_response_mock.side_effect = AWRAnalysisError(
            "解析失败", 
            code='PARSING_ERROR',
            details={'file': 'test.html'}
        )
        
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'PARSING_ERROR')
        self.assertEqual(data['error']['message'], '解析失败')
        self.assertIn('file', data['error']['details'])
    
    def test_parsing_error_with_oracle_version(self):
        """测试解析错误（包含Oracle版本信息）"""
        request = self.factory.post('/api/parse/')
        request.user = self.user
        
        self.get_response_mock.side_effect = ParsingError(
            "不支持的Oracle版本",
            oracle_version="10g"
        )
        
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertEqual(data['error']['code'], 'PARSING_ERROR')
        self.assertEqual(data['error']['details']['oracle_version'], '10g')
    
    def test_security_error(self):
        """测试安全异常处理"""
        request = self.factory.post('/api/upload/')
        request.user = self.user
        
        self.get_response_mock.side_effect = SecurityError("检测到恶意文件")
        
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertEqual(data['error']['code'], 'SECURITY_ERROR')
        self.assertEqual(data['error']['message'], '检测到恶意文件')
    
    def test_validation_error(self):
        """测试验证异常处理"""
        request = self.factory.post('/api/reports/')
        request.user = self.user
        
        self.get_response_mock.side_effect = ValidationError("字段验证失败")
        
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 400)
        
        data = json.loads(response.content)
        self.assertEqual(data['error']['code'], 'VALIDATION_ERROR')
        self.assertEqual(data['error']['message'], '数据验证失败')
    
    def test_permission_denied(self):
        """测试权限不足异常"""
        request = self.factory.delete('/api/reports/1/')
        request.user = self.user
        
        self.get_response_mock.side_effect = PermissionDenied("权限不足")
        
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 403)
        
        data = json.loads(response.content)
        self.assertEqual(data['error']['code'], 'PERMISSION_DENIED')
    
    def test_integrity_error(self):
        """测试数据完整性异常"""
        request = self.factory.post('/api/reports/')
        request.user = self.user
        
        self.get_response_mock.side_effect = IntegrityError("UNIQUE constraint failed")
        
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 409)
        
        data = json.loads(response.content)
        self.assertEqual(data['error']['code'], 'DATABASE_INTEGRITY_ERROR')
    
    def test_unknown_exception(self):
        """测试未知异常处理"""
        request = self.factory.get('/api/test/')
        request.user = self.user
        
        self.get_response_mock.side_effect = ValueError("意外错误")
        
        response = self.middleware(request)
        
        self.assertEqual(response.status_code, 500)
        
        data = json.loads(response.content)
        self.assertEqual(data['error']['code'], 'INTERNAL_ERROR')
        self.assertEqual(data['error']['message'], '服务器内部错误')
    
    def test_unknown_exception_with_debug(self):
        """测试调试模式下的未知异常处理"""
        with self.settings(DEBUG=True):
            request = self.factory.get('/api/test/')
            request.user = self.user
            
            self.get_response_mock.side_effect = ValueError("意外错误")
            
            response = self.middleware(request)
            
            data = json.loads(response.content)
            self.assertEqual(data['error']['message'], '意外错误')
            self.assertIn('traceback', data['error']['details'])
    
    @patch('analyzer.middleware.exception_handler.performance_logger')
    def test_performance_logging(self, mock_logger):
        """测试性能日志记录"""
        request = self.factory.get('/api/test/')
        request.user = self.user
        
        self.get_response_mock.return_value = JsonResponse({'success': True})
        
        response = self.middleware(request)
        
        # 验证性能日志被调用
        mock_logger.info.assert_called_once()
        
        # 验证日志内容
        log_call_args = mock_logger.info.call_args[0][0]
        self.assertIn('Request completed', log_call_args)
    
    @patch('analyzer.middleware.exception_handler.performance_logger')
    def test_slow_request_warning(self, mock_logger):
        """测试慢请求警告"""
        request = self.factory.get('/api/test/')
        request.user = self.user
        
        # 模拟慢响应
        def slow_response(req):
            time.sleep(0.1)  # 模拟延迟
            return JsonResponse({'success': True})
        
        self.get_response_mock.side_effect = slow_response
        
        # 修改慢请求阈值以便测试
        original_threshold = 5.0
        with patch.object(self.middleware, '_log_performance') as mock_log_perf:
            response = self.middleware(request)
            mock_log_perf.assert_called_once()
    
    def test_request_id_generation(self):
        """测试请求ID生成"""
        request = self.factory.get('/api/test/')
        request.user = self.user
        
        self.get_response_mock.return_value = JsonResponse({'success': True})
        
        response = self.middleware(request)
        
        self.assertTrue(hasattr(request, 'request_id'))
        self.assertIsInstance(request.request_id, str)
        self.assertEqual(len(request.request_id), 36)  # UUID格式
    
    def test_error_response_format(self):
        """测试错误响应格式标准化"""
        request = self.factory.post('/api/upload/')
        request.user = self.user
        
        self.get_response_mock.side_effect = AWRAnalysisError(
            "测试错误",
            code='TEST_ERROR',
            details={'key': 'value'}
        )
        
        response = self.middleware(request)
        
        data = json.loads(response.content)
        
        # 验证响应格式
        self.assertIn('success', data)
        self.assertIn('error', data)
        self.assertFalse(data['success'])
        
        error = data['error']
        self.assertIn('code', error)
        self.assertIn('message', error)
        self.assertIn('details', error)
        self.assertIn('request_id', error)
        self.assertIn('timestamp', error)
        
        # 验证具体内容
        self.assertEqual(error['code'], 'TEST_ERROR')
        self.assertEqual(error['message'], '测试错误')
        self.assertEqual(error['details']['key'], 'value')


class DRFExceptionHandlerTestCase(TestCase):
    """DRF异常处理器测试"""
    
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            password='testpass'
        )
    
    def test_drf_validation_error(self):
        """测试DRF验证错误处理"""
        from rest_framework.exceptions import ValidationError as DRFValidationError
        
        request = self.factory.post('/api/test/')
        request.user = self.user
        request.request_id = 'test-request-id'
        
        context = {'request': request}
        exc = DRFValidationError({'field': ['This field is required.']})
        
        response = custom_drf_exception_handler(exc, context)
        
        self.assertIsNotNone(response)
        self.assertEqual(response.status_code, 400)
        
        data = response.data
        self.assertFalse(data['success'])
        self.assertEqual(data['error']['code'], 'VALIDATION_ERROR')
        self.assertEqual(data['error']['message'], '请求数据验证失败')
        self.assertEqual(data['error']['request_id'], 'test-request-id')
    
    def test_drf_not_found_error(self):
        """测试DRF资源未找到错误"""
        from rest_framework.exceptions import NotFound
        
        request = self.factory.get('/api/reports/999/')
        request.user = self.user
        request.request_id = 'test-request-id'
        
        context = {'request': request}
        exc = NotFound('Report not found')
        
        response = custom_drf_exception_handler(exc, context)
        
        self.assertEqual(response.status_code, 404)
        
        data = response.data
        self.assertEqual(data['error']['code'], 'NOT_FOUND')
        self.assertEqual(data['error']['message'], '请求的资源不存在')
    
    def test_drf_authentication_failed(self):
        """测试DRF认证失败错误"""
        from rest_framework.exceptions import AuthenticationFailed
        
        request = self.factory.post('/api/upload/')
        context = {'request': request}
        exc = AuthenticationFailed('Invalid token')
        
        response = custom_drf_exception_handler(exc, context)
        
        self.assertEqual(response.status_code, 401)
        
        data = response.data
        self.assertEqual(data['error']['code'], 'AUTHENTICATION_FAILED')
        self.assertEqual(data['error']['message'], '身份认证失败')
    
    def test_drf_throttled_error(self):
        """测试DRF限流错误"""
        from rest_framework.exceptions import Throttled
        
        request = self.factory.post('/api/upload/')
        request.user = self.user
        
        context = {'request': request}
        exc = Throttled(wait=60)
        
        response = custom_drf_exception_handler(exc, context)
        
        self.assertEqual(response.status_code, 429)
        
        data = response.data
        self.assertEqual(data['error']['code'], 'RATE_LIMITED')
        self.assertEqual(data['error']['message'], '请求频率超限')
    
    def test_non_drf_exception(self):
        """测试非DRF异常不处理"""
        request = self.factory.get('/api/test/')
        context = {'request': request}
        exc = ValueError('Custom error')
        
        response = custom_drf_exception_handler(exc, context)
        
        # 非DRF异常应该返回None，由Django处理
        self.assertIsNone(response) 