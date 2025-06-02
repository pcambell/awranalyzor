"""
Oracle AWR解析器模块
{{CHENGQI: P2-AR-001 AWR解析器架构最终化设计 - 2025-06-02 11:05:00 +08:00}}
{{CHENGQI: P2-LD-002 BeautifulSoup解析基础工具类 - 2025-06-02 11:15:00 +08:00}}

提供多版本Oracle AWR报告解析功能
支持11g, 12c, 19c版本，以及RAC和CDB/PDB格式
"""

from .base import AbstractAWRParser, ParseResult, ParseError
from .factory import AWRParserFactory
from .utils import HTMLSectionExtractor, VersionDetector, DataCleaner, AWRStructureAnalyzer
from .html_parser import HTMLTableParser, AnchorNavigator, TableStructureAnalyzer
from .oracle_19c import Oracle19cParser

__all__ = [
    'AbstractAWRParser',
    'ParseResult', 
    'ParseError',
    'AWRParserFactory',
    'HTMLSectionExtractor',
    'VersionDetector',
    'DataCleaner',
    'AWRStructureAnalyzer',
    'HTMLTableParser',
    'AnchorNavigator', 
    'TableStructureAnalyzer',
    'Oracle19cParser',
] 