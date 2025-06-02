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
    
    def get_parser_class(self, version: OracleVersion) -> Optional[Type[AbstractAWRParser]]:
        """
        获取解析器类
        
        Args:
            version: Oracle版本
            
        Returns:
            解析器类或None
        """
        return self._parsers.get(version)
    
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
            logger.info("Oracle 19c解析器注册成功")
        except ImportError as e:
            logger.warning(f"Oracle 19c解析器未找到，跳过注册: {e}")
        
        try:
            from .oracle_11g import Oracle11gParser  
            self._registry.register_parser(OracleVersion.ORACLE_11G, Oracle11gParser)
            logger.info("Oracle 11g解析器注册成功")
        except ImportError as e:
            logger.warning(f"Oracle 11g解析器未找到，跳过注册: {e}")
        
        try:
            from .oracle_12c import Oracle12cParser
            self._registry.register_parser(OracleVersion.ORACLE_12C, Oracle12cParser)
            logger.info("Oracle 12c解析器注册成功")
        except ImportError as e:
            logger.warning(f"Oracle 12c解析器未找到，跳过注册: {e}")
    
    def register_parser(self, version: OracleVersion, parser_class: Type[AbstractAWRParser]):
        """
        注册自定义解析器
        
        Args:
            version: Oracle版本
            parser_class: 解析器类
        """
        self._registry.register_parser(version, parser_class)
    
    def create_parser(self, version: OracleVersion = None, html_content: str = None) -> Optional[AbstractAWRParser]:
        """
        创建指定版本的解析器
        
        Args:
            version: Oracle版本（如果指定，则直接创建该版本解析器）
            html_content: AWR HTML内容（如果version未指定，则用于自动检测版本）
            
        Returns:
            解析器实例或None
        """
        try:
            # 如果直接指定了版本，则创建对应解析器
            if version is not None:
                if isinstance(version, str):
                    # 如果传入的是字符串，尝试转换为枚举
                    logger.warning(f"传入的版本是字符串: {version}，尝试转换为枚举")
                    try:
                        # 尝试通过值查找枚举
                        for oracle_version in OracleVersion:
                            if oracle_version.value == version:
                                version = oracle_version
                                break
                        else:
                            logger.error(f"无法识别的版本字符串: {version}")
                            return None
                    except Exception as e:
                        logger.error(f"版本转换失败: {e}")
                        return None
                
                parser = self._registry.get_parser(version)
                if parser:
                    logger.info(f"创建指定版本解析器: {version.value}")
                    return parser
                else:
                    logger.error(f"未找到Oracle {version.value}解析器")
                    return None
            
            # 如果未指定版本，则从HTML内容中检测
            if html_content is not None:
                detected_version = self._version_detector.detect_version(html_content)
                logger.info(f"检测到的版本: {detected_version}, 类型: {type(detected_version)}")
                
                if detected_version and detected_version != OracleVersion.UNKNOWN:
                    parser = self._registry.get_parser(detected_version)
                    if parser:
                        logger.info(f"基于检测版本创建解析器: {detected_version.value}")
                        return parser
                    else:
                        logger.warning(f"检测到版本 {detected_version.value} 但未找到对应解析器")
                
                logger.warning("无法确定Oracle版本，尝试自动检测解析器")
                return self.get_parser_for_content(html_content)
            
            logger.error("必须指定version或html_content参数")
            return None
            
        except Exception as e:
            logger.error(f"创建解析器时出错: {e}", exc_info=True)
            return None
    
    def get_parser_for_content(self, html_content: str) -> Optional[AbstractAWRParser]:
        """
        根据内容自动选择合适的解析器
        
        Args:
            html_content: AWR HTML内容
            
        Returns:
            解析器实例或None
        """
        # 首先尝试版本检测
        detected_version = self._version_detector.detect_version(html_content)
        if detected_version and detected_version != OracleVersion.UNKNOWN:
            parser = self._registry.get_parser(detected_version)
            if parser:
                logger.info(f"通过版本检测找到解析器: {detected_version.value}")
                return parser
        
        # 如果版本检测失败，尝试所有已注册的解析器
        supported_versions = self._registry.get_supported_versions()
        logger.debug(f"支持的版本列表: {[v.value for v in supported_versions]}")
        
        for version in supported_versions:
            try:
                # 确保version是OracleVersion枚举
                if not isinstance(version, OracleVersion):
                    logger.error(f"注册表中的版本不是OracleVersion枚举: {version}, 类型: {type(version)}")
                    continue
                    
                logger.debug(f"测试版本: {version.value}")
                
                parser = self._registry.get_parser(version)
                if parser and parser.can_parse(html_content):
                    logger.info(f"自动检测选择解析器: {parser.__class__.__name__} for {version.value}")
                    return parser
                    
            except Exception as e:
                logger.error(f"测试解析器时出错 - 版本: {version.value if hasattr(version, 'value') else version}, 错误: {e}")
                continue
        
        logger.error("未找到合适的解析器")
        return None
    
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
    return factory.create_parser(html_content=html_content)


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