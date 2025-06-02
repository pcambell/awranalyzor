#!/usr/bin/env python3
"""
AWR解析器工厂测试套件
{{CHENGQI: P2-LD-005 解析器工厂和集成 - 2025-06-02 13:45:00 +08:00}}

测试解析器工厂模式、注册机制、自动版本检测和解析器选择
"""

import unittest
from unittest.mock import patch, MagicMock
from typing import Optional
from datetime import datetime

from apps.awr_parser.parsers.base import (
    AbstractAWRParser, OracleVersion, ParseResult,
    DBInfo, SnapshotInfo, LoadProfile, InstanceType
)
from apps.awr_parser.parsers.factory import (
    ParserRegistry, 
    AWRParserFactory, 
    get_parser_factory,
    create_parser,
    parse_awr
)


class MockParser(AbstractAWRParser):
    """测试用的模拟解析器"""
    
    def __init__(self, version: OracleVersion = OracleVersion.ORACLE_11G, can_parse_result: bool = True):
        super().__init__()
        self._version = version
        self._can_parse_result = can_parse_result
    
    def can_parse(self, html_content: str) -> bool:
        return self._can_parse_result
    
    def parse_db_info(self, soup):
        return DBInfo(
            db_name="TESTDB",
            instance_name="TESTDB1", 
            version=self._version,
            instance_type=InstanceType.SINGLE
        )
    
    def parse_snapshot_info(self, soup):
        return SnapshotInfo(
            begin_snap_id=1000,
            end_snap_id=1001,
            begin_time=datetime.now(),
            end_time=datetime.now(),
            elapsed_time_minutes=60.0,
            db_time_minutes=45.0
        )
    
    def parse_load_profile(self, soup):
        return LoadProfile(
            db_time_per_second=10.0,
            db_time_per_transaction=5.0,
            logical_reads_per_second=1000.0,
            logical_reads_per_transaction=500.0,
            physical_reads_per_second=100.0,
            physical_writes_per_second=50.0,
            user_calls_per_second=200.0,
            parses_per_second=100.0,
            hard_parses_per_second=10.0,
            sorts_per_second=50.0,
            logons_per_second=5.0,
            executes_per_second=150.0,
            rollbacks_per_second=2.0,
            transactions_per_second=20.0
        )
    
    def parse_wait_events(self, soup):
        return []
    
    def parse_sql_statistics(self, soup):
        return []
    
    def parse_instance_activity(self, soup):
        return []
    
    def parse(self, html_content: str) -> ParseResult:
        return ParseResult(
            db_info=self._create_default_db_info(),
            snapshot_info=self._create_default_snapshot_info(),
            load_profile=self._create_default_load_profile(),
            wait_events=[],
            sql_statistics=[],
            instance_activities=[]
        )


class TestParserRegistry(unittest.TestCase):
    """测试解析器注册表"""
    
    def setUp(self):
        self.registry = ParserRegistry()
    
    def test_register_parser_success(self):
        """测试成功注册解析器"""
        mock_parser_class = MockParser
        
        self.registry.register_parser(OracleVersion.ORACLE_11G, mock_parser_class)
        
        # 验证注册成功
        self.assertTrue(self.registry.is_version_supported(OracleVersion.ORACLE_11G))
        self.assertEqual(
            self.registry.get_parser_class(OracleVersion.ORACLE_11G),
            mock_parser_class
        )
    
    def test_register_parser_invalid_class(self):
        """测试注册无效解析器类"""
        class InvalidParser:
            pass
        
        with self.assertRaises(ValueError):
            self.registry.register_parser(OracleVersion.ORACLE_11G, InvalidParser)
    
    def test_get_parser_instance_singleton(self):
        """测试解析器实例的单例模式"""
        mock_parser_class = MockParser
        self.registry.register_parser(OracleVersion.ORACLE_19C, mock_parser_class)
        
        # 多次获取应该返回同一实例
        parser1 = self.registry.get_parser(OracleVersion.ORACLE_19C)
        parser2 = self.registry.get_parser(OracleVersion.ORACLE_19C)
        
        self.assertIsNotNone(parser1)
        self.assertIsNotNone(parser2)
        self.assertIs(parser1, parser2)  # 同一个实例
    
    def test_get_parser_not_registered(self):
        """测试获取未注册的解析器"""
        parser = self.registry.get_parser(OracleVersion.ORACLE_12C)
        self.assertIsNone(parser)
    
    def test_get_supported_versions(self):
        """测试获取支持的版本列表"""
        mock_parser_class = MockParser
        
        self.registry.register_parser(OracleVersion.ORACLE_11G, mock_parser_class)
        self.registry.register_parser(OracleVersion.ORACLE_19C, mock_parser_class)
        
        supported_versions = self.registry.get_supported_versions()
        
        self.assertEqual(len(supported_versions), 2)
        self.assertIn(OracleVersion.ORACLE_11G, supported_versions)
        self.assertIn(OracleVersion.ORACLE_19C, supported_versions)


class TestAWRParserFactory(unittest.TestCase):
    """测试AWR解析器工厂"""
    
    def setUp(self):
        """每次测试前创建新的工厂实例"""
        self.factory = AWRParserFactory()
    
    def test_create_parser_by_version(self):
        """测试通过版本创建解析器"""
        # 注册模拟解析器
        mock_parser_class = MockParser
        self.factory.register_parser(OracleVersion.ORACLE_11G, mock_parser_class)
        
        parser = self.factory.create_parser(version=OracleVersion.ORACLE_11G)
        
        self.assertIsNotNone(parser)
        self.assertIsInstance(parser, MockParser)
    
    def test_create_parser_unsupported_version(self):
        """测试创建不支持版本的解析器"""
        parser = self.factory.create_parser(version=OracleVersion.ORACLE_12C)
        self.assertIsNone(parser)
    
    @patch('apps.awr_parser.parsers.factory.VersionDetector')
    def test_create_parser_by_content_detection(self, mock_detector_class):
        """测试通过内容检测创建解析器"""
        # 设置模拟版本检测器
        mock_detector = mock_detector_class.return_value
        mock_detector.detect_version.return_value = OracleVersion.ORACLE_19C
        
        # 创建新的工厂实例避免默认注册干扰
        clean_factory = AWRParserFactory.__new__(AWRParserFactory)
        clean_factory._registry = ParserRegistry()
        clean_factory._version_detector = mock_detector
        
        # 绑定必要的方法
        clean_factory.register_parser = AWRParserFactory.register_parser.__get__(clean_factory, AWRParserFactory)
        clean_factory.create_parser = AWRParserFactory.create_parser.__get__(clean_factory, AWRParserFactory)
        
        # 注册模拟解析器
        mock_parser_class = MockParser
        clean_factory.register_parser(OracleVersion.ORACLE_19C, mock_parser_class)
        
        html_content = "<html>Oracle 19c AWR Report</html>"
        parser = clean_factory.create_parser(html_content=html_content)
        
        self.assertIsNotNone(parser)
        self.assertIsInstance(parser, MockParser)
        mock_detector.detect_version.assert_called_once_with(html_content)
    
    def test_get_parser_for_content_auto_detection(self):
        """测试内容自动检测选择解析器"""
        # 创建两个不同的解析器类，一个可以解析，一个不能
        class CannotParseParser(MockParser):
            def __init__(self):
                super().__init__(OracleVersion.ORACLE_11G, False)
                
        class CanParseParser(MockParser):
            def __init__(self):
                super().__init__(OracleVersion.ORACLE_19C, True)
        
        self.factory.register_parser(OracleVersion.ORACLE_11G, CannotParseParser)
        self.factory.register_parser(OracleVersion.ORACLE_19C, CanParseParser)
        
        html_content = "<html>Some AWR content</html>"
        parser = self.factory.get_parser_for_content(html_content)
        
        self.assertIsNotNone(parser)
        # 应该选择能解析的那个
        self.assertIsInstance(parser, CanParseParser)
    
    def test_get_parser_for_content_no_match(self):
        """测试内容无法匹配任何解析器"""
        # 创建一个不能解析的解析器类
        class CannotParseParser(MockParser):
            def __init__(self):
                super().__init__(OracleVersion.ORACLE_11G, False)
        
        self.factory.register_parser(OracleVersion.ORACLE_11G, CannotParseParser)
        
        html_content = "<html>Unsupported content</html>"
        parser = self.factory.get_parser_for_content(html_content)
        
        self.assertIsNone(parser)
    
    def test_create_parser_invalid_params(self):
        """测试无效参数调用"""
        parser = self.factory.create_parser()  # 既没有version也没有html_content
        self.assertIsNone(parser)
    
    def test_get_supported_versions(self):
        """测试获取支持的版本"""
        supported = self.factory.get_supported_versions()
        
        # 应该包含默认注册的版本
        self.assertIsInstance(supported, list)
        # 如果默认解析器注册成功，应该包含对应版本
        
    def test_is_version_supported(self):
        """测试版本支持检查"""
        # 注册一个解析器
        mock_parser_class = MockParser
        self.factory.register_parser(OracleVersion.ORACLE_11G, mock_parser_class)
        
        self.assertTrue(self.factory.is_version_supported(OracleVersion.ORACLE_11G))
        self.assertFalse(self.factory.is_version_supported(OracleVersion.ORACLE_12C))


class TestFactoryFunctions(unittest.TestCase):
    """测试工厂模块级函数"""
    
    def test_get_parser_factory_singleton(self):
        """测试工厂单例模式"""
        factory1 = get_parser_factory()
        factory2 = get_parser_factory()
        
        self.assertIsNotNone(factory1)
        self.assertIsNotNone(factory2)
        self.assertIs(factory1, factory2)  # 应该是同一个实例
    
    @patch('apps.awr_parser.parsers.factory.get_parser_factory')
    def test_create_parser_function(self, mock_get_factory):
        """测试create_parser函数"""
        mock_factory = MagicMock()
        mock_parser = MockParser(OracleVersion.ORACLE_11G)
        mock_factory.create_parser.return_value = mock_parser
        mock_get_factory.return_value = mock_factory
        
        html_content = "<html>Test content</html>"
        result = create_parser(html_content)
        
        self.assertEqual(result, mock_parser)
        # 模块级create_parser函数实际调用工厂的create_parser方法，传入html_content作为位置参数
        mock_factory.create_parser.assert_called_once_with(html_content)
    
    @patch('apps.awr_parser.parsers.factory.create_parser')
    def test_parse_awr_function(self, mock_create_parser):
        """测试parse_awr函数"""
        mock_parser = MagicMock()
        mock_report = MagicMock()
        mock_parser.parse.return_value = mock_report
        mock_create_parser.return_value = mock_parser
        
        html_content = "<html>Test content</html>"
        result = parse_awr(html_content)
        
        self.assertEqual(result, mock_report)
        mock_create_parser.assert_called_once_with(html_content)
        mock_parser.parse.assert_called_once_with(html_content)
    
    @patch('apps.awr_parser.parsers.factory.create_parser')
    def test_parse_awr_no_parser(self, mock_create_parser):
        """测试无解析器情况下的parse_awr函数"""
        mock_create_parser.return_value = None
        
        html_content = "<html>Unsupported content</html>"
        result = parse_awr(html_content)
        
        # 期望返回失败的ParseResult而不是None
        self.assertIsNotNone(result)
        self.assertEqual(result.parse_status.value, 'failed')
        self.assertTrue(any(error.error_type == 'no_parser' for error in result.errors))
        mock_create_parser.assert_called_once_with(html_content)


class TestFactoryIntegration(unittest.TestCase):
    """解析器工厂集成测试"""
    
    def test_real_parsers_registration(self):
        """测试真实解析器的注册"""
        factory = AWRParserFactory()
        
        supported_versions = factory.get_supported_versions()
        
        # 应该自动注册11g和19c解析器
        self.assertIn(OracleVersion.ORACLE_11G, supported_versions)
        self.assertIn(OracleVersion.ORACLE_19C, supported_versions)
    
    def test_real_parser_creation(self):
        """测试真实解析器的创建"""
        factory = AWRParserFactory()
        
        # 测试创建11g解析器
        parser_11g = factory.create_parser(version=OracleVersion.ORACLE_11G)
        self.assertIsNotNone(parser_11g)
        self.assertEqual(parser_11g.__class__.__name__, 'Oracle11gParser')
        
        # 测试创建19c解析器
        parser_19c = factory.create_parser(version=OracleVersion.ORACLE_19C)
        self.assertIsNotNone(parser_19c)
        self.assertEqual(parser_19c.__class__.__name__, 'Oracle19cParser')
    
    def test_oracle_11g_content_parsing(self):
        """测试Oracle 11g内容解析"""
        factory = AWRParserFactory()
        
        # Oracle 11g AWR内容示例
        oracle_11g_content = """
        <html>
        <head><title>Oracle Database 11g Enterprise Edition Release 11.2.0.4.0 AWR Report</title></head>
        <body>
        <h1>WORKLOAD REPOSITORY report for</h1>
        <h2>Oracle Database 11g Enterprise Edition Release 11.2.0.4.0</h2>
        </body>
        </html>
        """
        
        parser = factory.get_parser_for_content(oracle_11g_content)
        self.assertIsNotNone(parser)
        self.assertEqual(parser.__class__.__name__, 'Oracle11gParser')
    
    def test_oracle_19c_content_parsing(self):
        """测试Oracle 19c内容解析"""
        factory = AWRParserFactory()
        
        # Oracle 19c AWR内容示例
        oracle_19c_content = """
        <html>
        <head><title>Oracle Database 19c Enterprise Edition Release 19.0.0.0.0 AWR Report</title></head>
        <body>
        <h1>WORKLOAD REPOSITORY report for</h1>
        <h2>Oracle Database 19c Enterprise Edition Release 19.0.0.0.0</h2>
        </body>
        </html>
        """
        
        parser = factory.get_parser_for_content(oracle_19c_content)
        self.assertIsNotNone(parser)
        self.assertEqual(parser.__class__.__name__, 'Oracle19cParser')


if __name__ == '__main__':
    unittest.main() 