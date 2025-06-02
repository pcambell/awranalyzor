"""
Oracle AWR解析器模块
{{CHENGQI: P2-AR-001 AWR解析器架构最终化设计 - 2025-06-02 11:05:00 +08:00}}
{{CHENGQI: P2-LD-002 BeautifulSoup解析基础工具类 - 2025-06-02 11:15:00 +08:00}}
{{CHENGQI: P2-LD-004 Oracle 11g解析器模块导出 - 2025-06-02 11:58:05 +08:00}}

提供多版本Oracle AWR报告解析功能
支持11g, 12c, 19c版本，以及RAC和CDB/PDB格式
"""

from .base import AbstractAWRParser, ParseResult, ParseError, OracleVersion, InstanceType
from .factory import AWRParserFactory, get_parser_factory, create_parser, parse_awr
from .utils import HTMLSectionExtractor, VersionDetector, DataCleaner, AWRStructureAnalyzer
from .html_parser import HTMLTableParser, AnchorNavigator, TableStructureAnalyzer
from .oracle_19c import Oracle19cParser
from .oracle_11g import Oracle11gParser

__all__ = [
    'AbstractAWRParser',
    'ParseResult', 
    'ParseError',
    'OracleVersion',
    'InstanceType',
    'AWRParserFactory',
    'get_parser_factory',
    'create_parser',
    'parse_awr',
    'HTMLSectionExtractor',
    'VersionDetector',
    'DataCleaner',
    'AWRStructureAnalyzer',
    'HTMLTableParser',
    'AnchorNavigator', 
    'TableStructureAnalyzer',
    'Oracle19cParser',
    'Oracle11gParser'
] 