"""
AWR解析器抽象基类
{{CHENGQI: P2-AR-001 AWR解析器架构最终化设计 - 2025-06-02 11:05:00 +08:00}}

定义AWR解析器的标准接口，遵循SOLID原则中的开闭原则和接口隔离原则
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, Union
from enum import Enum
import logging
from datetime import datetime


logger = logging.getLogger(__name__)


class OracleVersion(Enum):
    """Oracle版本枚举"""
    ORACLE_11G = "11g"
    ORACLE_12C = "12c" 
    ORACLE_19C = "19c"
    ORACLE_21C = "21c"
    UNKNOWN = "unknown"


class InstanceType(Enum):
    """实例类型枚举"""
    SINGLE = "single"
    RAC = "rac"
    CDB = "cdb"
    PDB = "pdb"


class ParseStatus(Enum):
    """解析状态枚举"""
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"
    WARNING = "warning"


@dataclass
class ParseError:
    """解析错误信息"""
    section: str
    error_type: str
    message: str
    details: Optional[str] = None
    is_critical: bool = False


@dataclass
class DBInfo:
    """数据库基本信息"""
    db_name: str
    instance_name: str
    version: OracleVersion
    instance_type: InstanceType
    host_name: Optional[str] = None
    platform: Optional[str] = None
    startup_time: Optional[datetime] = None
    is_rac: bool = False
    container_name: Optional[str] = None  # CDB/PDB


@dataclass
class SnapshotInfo:
    """快照信息"""
    begin_snap_id: int
    end_snap_id: int
    begin_time: datetime
    end_time: datetime
    elapsed_time_minutes: float
    db_time_minutes: float
    instance_id: Optional[int] = None


@dataclass
class LoadProfile:
    """负载概要"""
    db_time_per_second: float
    db_time_per_transaction: float
    logical_reads_per_second: float
    logical_reads_per_transaction: float
    physical_reads_per_second: float
    physical_writes_per_second: float
    user_calls_per_second: float
    parses_per_second: float
    hard_parses_per_second: float
    sorts_per_second: float
    logons_per_second: float
    executes_per_second: float
    rollbacks_per_second: float
    transactions_per_second: float


@dataclass
class WaitEvent:
    """等待事件"""
    event_name: str
    waits: int
    total_wait_time_sec: float
    avg_wait_ms: float
    percent_db_time: float
    wait_class: str


@dataclass
class SQLStatistic:
    """SQL统计"""
    sql_id: str
    sql_text: str
    executions: int
    elapsed_time_sec: float
    cpu_time_sec: float
    io_time_sec: float
    gets: int
    reads: int
    module: Optional[str] = None
    parsing_schema: Optional[str] = None


@dataclass
class InstanceActivity:
    """实例活动统计"""
    statistic_name: str
    total_value: Union[int, float]
    per_second: float
    per_transaction: float


@dataclass
class ParseResult:
    """
    解析结果数据结构
    遵循单一职责原则，仅包含解析后的结构化数据
    """
    # 基本信息
    db_info: DBInfo
    snapshot_info: SnapshotInfo
    
    # 核心性能数据
    load_profile: LoadProfile
    wait_events: List[WaitEvent] = field(default_factory=list)
    sql_statistics: List[SQLStatistic] = field(default_factory=list)
    instance_activities: List[InstanceActivity] = field(default_factory=list)
    
    # 解析元信息
    parse_status: ParseStatus = ParseStatus.SUCCESS
    errors: List[ParseError] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    parsed_sections: List[str] = field(default_factory=list)
    raw_data: Optional[Dict[str, Any]] = None
    
    def add_error(self, section: str, error_type: str, message: str, 
                  details: Optional[str] = None, is_critical: bool = False):
        """添加解析错误"""
        error = ParseError(
            section=section,
            error_type=error_type, 
            message=message,
            details=details,
            is_critical=is_critical
        )
        self.errors.append(error)
        
        if is_critical and self.parse_status == ParseStatus.SUCCESS:
            self.parse_status = ParseStatus.FAILED
        elif not is_critical and self.parse_status == ParseStatus.SUCCESS:
            self.parse_status = ParseStatus.PARTIAL
    
    def add_warning(self, message: str):
        """添加解析警告"""
        self.warnings.append(message)
        if self.parse_status == ParseStatus.SUCCESS:
            self.parse_status = ParseStatus.WARNING
    
    def is_successful(self) -> bool:
        """是否解析成功（包括部分成功）"""
        return self.parse_status in [ParseStatus.SUCCESS, ParseStatus.PARTIAL, ParseStatus.WARNING]


class AbstractAWRParser(ABC):
    """
    AWR解析器抽象基类
    
    遵循SOLID原则：
    - 单一职责：专注于AWR解析
    - 开闭原则：对扩展开放，对修改关闭
    - 里氏替换：所有子类都可以替换基类
    - 接口隔离：提供最小必要接口
    - 依赖倒置：依赖抽象而非具体实现
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @abstractmethod
    def can_parse(self, html_content: str) -> bool:
        """
        检查是否能解析给定的AWR内容
        
        Args:
            html_content: AWR HTML内容
            
        Returns:
            bool: 是否支持解析
        """
        pass
    
    @abstractmethod
    def parse_db_info(self, soup) -> DBInfo:
        """解析数据库基本信息"""
        pass
    
    @abstractmethod
    def parse_snapshot_info(self, soup) -> SnapshotInfo:
        """解析快照信息"""
        pass
    
    @abstractmethod
    def parse_load_profile(self, soup) -> LoadProfile:
        """解析负载概要"""
        pass
    
    @abstractmethod
    def parse_wait_events(self, soup) -> List[WaitEvent]:
        """解析等待事件"""
        pass
    
    @abstractmethod
    def parse_sql_statistics(self, soup) -> List[SQLStatistic]:
        """解析SQL统计"""
        pass
    
    @abstractmethod
    def parse_instance_activity(self, soup) -> List[InstanceActivity]:
        """解析实例活动统计"""
        pass
    
    def parse(self, html_content: str) -> ParseResult:
        """
        模板方法模式：定义解析流程
        
        Args:
            html_content: AWR HTML内容
            
        Returns:
            ParseResult: 解析结果
        """
        from bs4 import BeautifulSoup
        
        result = ParseResult(
            db_info=DBInfo("", "", OracleVersion.UNKNOWN, InstanceType.SINGLE),
            snapshot_info=SnapshotInfo(0, 0, datetime.now(), datetime.now(), 0, 0),
            load_profile=LoadProfile(0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0)
        )
        
        try:
            # 检查是否支持解析
            if not self.can_parse(html_content):
                result.add_error("parser", "unsupported", "不支持的AWR格式", is_critical=True)
                return result
            
            # 解析HTML
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 按顺序解析各个区块
            self._parse_section(result, "db_info", lambda: self.parse_db_info(soup))
            self._parse_section(result, "snapshot_info", lambda: self.parse_snapshot_info(soup))
            self._parse_section(result, "load_profile", lambda: self.parse_load_profile(soup))
            self._parse_section(result, "wait_events", lambda: self.parse_wait_events(soup))
            self._parse_section(result, "sql_statistics", lambda: self.parse_sql_statistics(soup))
            self._parse_section(result, "instance_activity", lambda: self.parse_instance_activity(soup))
            
            # 设置解析后的数据
            if hasattr(result, '_temp_db_info'):
                result.db_info = result._temp_db_info
                del result._temp_db_info
            if hasattr(result, '_temp_snapshot_info'):
                result.snapshot_info = result._temp_snapshot_info
                del result._temp_snapshot_info
            if hasattr(result, '_temp_load_profile'):
                result.load_profile = result._temp_load_profile
                del result._temp_load_profile
            
            self.logger.info(f"AWR解析完成，状态: {result.parse_status.value}, "
                           f"解析区块: {len(result.parsed_sections)}, "
                           f"错误: {len(result.errors)}")
            
        except Exception as e:
            self.logger.error(f"AWR解析失败: {e}", exc_info=True)
            result.add_error("parser", "exception", f"解析异常: {str(e)}", is_critical=True)
        
        return result
    
    def _parse_section(self, result: ParseResult, section_name: str, parse_func):
        """
        解析区块的通用方法，包含错误处理
        """
        try:
            parsed_data = parse_func()
            if parsed_data is not None:
                # 使用临时属性存储数据，在主流程中设置
                setattr(result, f'_temp_{section_name}', parsed_data)
                result.parsed_sections.append(section_name)
                self.logger.debug(f"成功解析区块: {section_name}")
            else:
                result.add_warning(f"区块 {section_name} 解析为空")
                
        except Exception as e:
            self.logger.warning(f"解析区块 {section_name} 失败: {e}")
            result.add_error(
                section=section_name,
                error_type="parse_error", 
                message=f"解析失败: {str(e)}",
                details=None,
                is_critical=False  # 单个区块失败不影响整体
            ) 