"""
AWR解析器工厂类
{{CHENGQI: P2-AR-001 AWR解析器架构最终化设计 - 2025-06-02 11:05:00 +08:00}}

实现工厂模式，根据AWR版本自动选择合适的解析器
遵循开闭原则，支持新版本解析器的无缝添加
"""

import re
import logging
from typing import Optional, Dict, Type, List
from .base import AbstractAWRParser, OracleVersion
from .utils import VersionDetector


logger = logging.getLogger(__name__)


class ParserRegistry:
    """
    解析器注册表
    遵循单一职责原则，专门管理解析器的注册和获取
    """
    
    def __init__(self):
        self._parsers: Dict[OracleVersion, Type[AbstractAWRParser]] = {}
        self._parser_instances: Dict[OracleVersion, AbstractAWRParser] = {}
    
    def register_parser(self, version: OracleVersion, parser_class: Type[AbstractAWRParser]):
        """
        注册解析器类
        
        Args:
            version: Oracle版本
            parser_class: 解析器类
        """
        if not issubclass(parser_class, AbstractAWRParser):
            raise ValueError(f"解析器类必须继承自AbstractAWRParser: {parser_class}")
        
        self._parsers[version] = parser_class
        logger.info(f"注册解析器: {version.value} -> {parser_class.__name__}")
    
    def get_parser(self, version: OracleVersion) -> Optional[AbstractAWRParser]:
        """
        获取解析器实例（单例模式）
        
        Args:
            version: Oracle版本
            
        Returns:
            解析器实例或None
        """
        if version not in self._parsers:
            return None
        
        # 单例模式：每个版本只创建一个解析器实例
        if version not in self._parser_instances:
            parser_class = self._parsers[version]
            self._parser_instances[version] = parser_class()
            logger.debug(f"创建解析器实例: {version.value}")
        
        return self._parser_instances[version]
    
    def get_supported_versions(self) -> List[OracleVersion]:
        """获取支持的Oracle版本列表"""
        return list(self._parsers.keys())
    
    def is_version_supported(self, version: OracleVersion) -> bool:
        """检查是否支持指定版本"""
        return version in self._parsers


class AWRParserFactory:
    """
    AWR解析器工厂
    
    实现工厂模式，提供统一的解析器创建接口
    遵循开闭原则：添加新版本解析器时无需修改现有代码
    """
    
    def __init__(self):
        self._registry = ParserRegistry()
        self._version_detector = VersionDetector()
        self._register_default_parsers()
    
    def _register_default_parsers(self):
        """
        注册默认解析器
        采用延迟导入避免循环依赖
        """
        try:
            # 动态导入解析器类，避免循环依赖
            from .oracle_19c import Oracle19cParser
            self._registry.register_parser(OracleVersion.ORACLE_19C, Oracle19cParser)
        except ImportError:
            logger.warning("Oracle 19c解析器未找到，跳过注册")
        
        try:
            from .oracle_11g import Oracle11gParser  
            self._registry.register_parser(OracleVersion.ORACLE_11G, Oracle11gParser)
        except ImportError:
            logger.warning("Oracle 11g解析器未找到，跳过注册")
        
        try:
            from .oracle_12c import Oracle12cParser
            self._registry.register_parser(OracleVersion.ORACLE_12C, Oracle12cParser)
        except ImportError:
            logger.warning("Oracle 12c解析器未找到，跳过注册")
    
    def register_parser(self, version: OracleVersion, parser_class: Type[AbstractAWRParser]):
        """
        注册自定义解析器
        
        Args:
            version: Oracle版本
            parser_class: 解析器类
        """
        self._registry.register_parser(version, parser_class)
    
    def create_parser(self, html_content: str) -> Optional[AbstractAWRParser]:
        """
        根据AWR内容自动创建合适的解析器
        
        Args:
            html_content: AWR HTML内容
            
        Returns:
            解析器实例或None（如果无法识别版本）
        """
        # 检测Oracle版本
        version = self._version_detector.detect_version(html_content)
        
        if version == OracleVersion.UNKNOWN:
            logger.warning("无法识别Oracle版本")
            return None
        
        # 获取对应的解析器
        parser = self._registry.get_parser(version)
        
        if parser is None:
            logger.error(f"未找到 {version.value} 版本的解析器")
            return None
        
        # 二次验证：确保解析器可以处理该内容
        if not parser.can_parse(html_content):
            logger.warning(f"{version.value} 解析器无法处理该AWR内容")
            return None
        
        logger.info(f"选择解析器: {parser.__class__.__name__} for {version.value}")
        return parser
    
    def create_parser_by_version(self, version: OracleVersion) -> Optional[AbstractAWRParser]:
        """
        根据指定版本创建解析器
        
        Args:
            version: Oracle版本
            
        Returns:
            解析器实例或None
        """
        return self._registry.get_parser(version)
    
    def get_supported_versions(self) -> List[OracleVersion]:
        """获取当前支持的Oracle版本"""
        return self._registry.get_supported_versions()
    
    def is_version_supported(self, version: OracleVersion) -> bool:
        """检查是否支持指定的Oracle版本"""
        return self._registry.is_version_supported(version)


# 全局工厂实例（单例）
_factory_instance: Optional[AWRParserFactory] = None


def get_parser_factory() -> AWRParserFactory:
    """
    获取全局解析器工厂实例（单例模式）
    
    Returns:
        AWRParserFactory实例
    """
    global _factory_instance
    if _factory_instance is None:
        _factory_instance = AWRParserFactory()
        logger.info("初始化AWR解析器工厂")
    return _factory_instance


def create_parser(html_content: str) -> Optional[AbstractAWRParser]:
    """
    便捷函数：根据AWR内容创建解析器
    
    Args:
        html_content: AWR HTML内容
        
    Returns:
        解析器实例或None
    """
    factory = get_parser_factory()
    return factory.create_parser(html_content)


def parse_awr(html_content: str):
    """
    便捷函数：直接解析AWR内容
    
    Args:
        html_content: AWR HTML内容
        
    Returns:
        ParseResult: 解析结果
    """
    parser = create_parser(html_content)
    if parser is None:
        from .base import ParseResult, DBInfo, SnapshotInfo, LoadProfile, OracleVersion, InstanceType
        from datetime import datetime
        
        result = ParseResult(
            db_info=DBInfo("", "", OracleVersion.UNKNOWN, InstanceType.SINGLE),
            snapshot_info=SnapshotInfo(0, 0, datetime.now(), datetime.now(), 0, 0),
            load_profile=LoadProfile(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        )
        result.add_error("factory", "no_parser", "无法找到合适的解析器", is_critical=True)
        return result
    
    return parser.parse(html_content) 