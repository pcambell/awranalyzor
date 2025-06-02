"""
Oracle 11g AWR解析器
{{CHENGQI: P2-LD-004 Oracle 11g解析器实现 - 2025-06-02 11:58:05 +08:00}}

实现Oracle 11g版本AWR报告的专业解析
支持标准AWR、RAC等多种格式（不支持CDB/PDB，因为11g没有此功能）
基于Oracle19cParser的成熟架构，进行版本特定的适配
"""

import re
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from bs4 import BeautifulSoup

from .base import (
    AbstractAWRParser, DBInfo, SnapshotInfo, LoadProfile, 
    WaitEvent, SQLStatistic, InstanceActivity,
    OracleVersion, InstanceType, ParseStatus
)
from .html_parser import HTMLTableParser, AnchorNavigator, TableStructureAnalyzer
from .utils import DataCleaner


logger = logging.getLogger(__name__)


class Oracle11gParser(AbstractAWRParser):
    """
    Oracle 11g AWR解析器
    
    遵循开闭原则，继承AbstractAWRParser抽象基类
    专门处理Oracle 11g版本的AWR报告格式和特殊情况
    基于Oracle 19c解析器的成熟实现，进行11g特定的适配
    """
    
    def __init__(self):
        super().__init__()
        self.logger.info("检测到Oracle 11g AWR格式")
        self.version = OracleVersion.ORACLE_11G
        
        # Oracle 11g特有的锚点映射（与19c基本相同，但可能有细微差异）
        self.anchor_mapping = {
            'db_info': ['dbinfo', 'db_information', 'database_information'],
            'snapshot_info': ['snapshot', 'snap_info', 'snapshot_information'],
            'load_profile': ['loadprofile', 'load_profile', 'system_load'],
            'wait_events': ['topevents', 'wait_events', 'top_events'],
            'sql_statistics': ['topsql', 'sql_statistics', 'top_sql'],
            'instance_activity': ['sysstat', 'instance_activity', 'system_statistics']
        }
        
        # Oracle 11g表格标题模式（与19c相似）
        self.table_patterns = {
            'db_info': [
                r'Database\s+Information',
                r'DB\s+Info',
                r'Instance\s+Information'
            ],
            'load_profile': [
                r'Load\s+Profile',
                r'System\s+Load\s+Profile',
                r'Per\s+Second\s+Per\s+Transaction'
            ],
            'wait_events': [
                r'Top\s+\d+\s+Timed\s+Events',
                r'Wait\s+Events',
                r'Top\s+Wait\s+Events'
            ],
            'sql_statistics': [
                r'SQL\s+ordered\s+by',
                r'Top\s+SQL',
                r'SQL\s+Statistics'
            ]
        }
    
    def can_parse(self, html_content: str) -> bool:
        """
        检查是否能解析给定的AWR内容
        
        Args:
            html_content: AWR HTML内容
            
        Returns:
            bool: 是否支持解析Oracle 11g格式
        """
        try:
            # 检查Oracle 11g版本标识
            version_patterns = [
                r'Oracle\s+Database\s+11g',
                r'Release\s+11\.',
                r'11\.\d+\.\d+\.\d+',
                r'version["\s]*11\.'
            ]
            
            for pattern in version_patterns:
                if re.search(pattern, html_content, re.IGNORECASE):
                    self.logger.info("检测到Oracle 11g AWR格式")
                    return True
            
            # 检查AWR报告结构特征
            soup = BeautifulSoup(html_content, 'html.parser')
            
            # 检查是否包含AWR特有的锚点
            awr_anchors = ['dbinfo', 'loadprofile', 'topevents', 'topsql']
            found_anchors = 0
            
            for anchor in awr_anchors:
                if soup.find('a', {'name': anchor}) or soup.find(attrs={'id': anchor}):
                    found_anchors += 1
            
            # 如果找到大部分AWR锚点，认为可以解析
            if found_anchors >= 2:
                self.logger.info(f"找到 {found_anchors} 个AWR锚点，尝试作为Oracle 11g解析")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查Oracle 11g兼容性时出错: {e}")
            return False
    
    def parse_db_info(self, soup: BeautifulSoup) -> DBInfo:
        """
        解析数据库基本信息
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            DBInfo: 数据库信息对象
        """
        navigator = AnchorNavigator(soup)
        parser = HTMLTableParser(soup)
        
        # 查找数据库信息表格
        db_table = None
        for anchor in self.anchor_mapping['db_info']:
            db_table = navigator.get_table_after_anchor(anchor)
            if db_table:
                break
        
        if not db_table:
            # 尝试通过标题查找
            for pattern in self.table_patterns['db_info']:
                db_table = parser.find_table_by_caption(pattern)
                if db_table:
                    break
        
        if not db_table:
            self.logger.warning("未找到数据库信息表格")
            return self._create_default_db_info()
        
        # 解析键值对表格
        db_data = parser.parse_key_value_table(db_table)
        
        if not db_data:
            self.logger.warning("数据库信息表格解析为空")
            return self._create_default_db_info()
        
        # 提取关键信息
        db_name = self._extract_db_name(db_data)
        instance_name = self._extract_instance_name(db_data)
        host_name = self._extract_host_name(db_data)
        platform = self._extract_platform(db_data)
        startup_time = self._extract_startup_time(db_data)
        
        # 检测实例类型（11g不支持CDB/PDB）
        instance_type = self._detect_instance_type_11g(db_data)
        is_rac = instance_type == InstanceType.RAC
        
        # 提取实例编号（用于RAC）
        instance_number = self._extract_instance_number(db_data)
        
        # 11g不支持容器数据库
        container_name = None
        
        return DBInfo(
            db_name=db_name,
            instance_name=instance_name,
            version=self.version,
            instance_type=instance_type,
            host_name=host_name,
            platform=platform,
            startup_time=startup_time,
            is_rac=is_rac,
            container_name=container_name,
            instance_number=instance_number
        )
    
    def parse_snapshot_info(self, soup: BeautifulSoup) -> SnapshotInfo:
        """
        解析快照信息（复用19c的逻辑，因为结构基本相同）
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            SnapshotInfo: 快照信息对象
        """
        navigator = AnchorNavigator(soup)
        parser = HTMLTableParser(soup)
        
        # 查找快照信息，通常在AWR报告开头
        snapshot_table = None
        
        # 首先尝试查找专门的快照信息表格
        for anchor in self.anchor_mapping['snapshot_info']:
            snapshot_table = navigator.get_table_after_anchor(anchor)
            if snapshot_table:
                break
        
        if not snapshot_table:
            # 尝试在报告开头查找包含Snap Id的表格
            tables = soup.find_all('table')
            for table in tables[:5]:  # 只检查前5个表格
                analyzer = TableStructureAnalyzer(table)
                if analyzer.has_columns(['Snap Id', 'Instance', 'Begin Snap Time', 'End Snap Time']):
                    snapshot_table = table
                    break
        
        if not snapshot_table:
            self.logger.warning("未找到快照信息表格")
            return self._create_default_snapshot_info()
        
        # 分析表格结构
        analyzer = TableStructureAnalyzer(snapshot_table)
        analysis = analyzer.analyze()
        
        # 优先尝试解析为标准数据表格（如果有表头）
        if analysis.get('has_header', False) or analysis.get('structure_type') == 'header_data':
            headers, rows = parser.parse_data_table(snapshot_table)
            if headers and rows:
                return self._parse_snapshot_from_table(headers, rows)
        
        # 如果不是标准表格，尝试解析为键值对表格
        snapshot_data = parser.parse_key_value_table(snapshot_table)
        if snapshot_data and len(snapshot_data) > 2:  # 确保有足够的键值对
            return self._parse_snapshot_from_kv(snapshot_data)
        
        # 最后尝试标准表格解析（作为备选方案）
        headers, rows = parser.parse_data_table(snapshot_table)
        if headers and rows:
            return self._parse_snapshot_from_table(headers, rows)
        
        self.logger.warning("快照信息表格解析失败")
        return self._create_default_snapshot_info()
    
    def parse_load_profile(self, soup: BeautifulSoup) -> LoadProfile:
        """
        解析Load Profile（复用19c逻辑，字段结构基本相同）
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            LoadProfile: Load Profile对象
        """
        navigator = AnchorNavigator(soup)
        parser = HTMLTableParser(soup)
        
        # 查找Load Profile表格
        load_table = None
        for anchor in self.anchor_mapping['load_profile']:
            load_table = navigator.get_table_after_anchor(anchor)
            if load_table:
                break
        
        if not load_table:
            # 尝试通过标题查找
            for pattern in self.table_patterns['load_profile']:
                load_table = parser.find_table_by_caption(pattern)
                if load_table:
                    break
        
        if not load_table:
            self.logger.warning("未找到Load Profile表格")
            return self._create_default_load_profile()
        
        # 解析表格数据
        headers, rows = parser.parse_data_table(load_table)
        
        if not headers or not rows:
            self.logger.warning("Load Profile表格解析为空")
            return self._create_default_load_profile()
        
        return self._extract_load_metrics(headers, rows)
    
    def parse_wait_events(self, soup: BeautifulSoup) -> List[WaitEvent]:
        """
        解析等待事件统计（复用19c逻辑，结构相同）
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            List[WaitEvent]: 等待事件列表
        """
        navigator = AnchorNavigator(soup)
        parser = HTMLTableParser(soup)
        
        # 查找等待事件表格
        wait_table = None
        for anchor in self.anchor_mapping['wait_events']:
            wait_table = navigator.get_table_after_anchor(anchor)
            if wait_table:
                break
        
        if not wait_table:
            # 尝试通过标题查找
            for pattern in self.table_patterns['wait_events']:
                wait_table = parser.find_table_by_caption(pattern)
                if wait_table:
                    break
        
        if not wait_table:
            self.logger.warning("未找到等待事件表格")
            return []
        
        # 解析表格数据
        headers, rows = parser.parse_data_table(wait_table)
        
        if not headers or not rows:
            self.logger.warning("等待事件表格解析为空")
            return []
        
        return self._convert_to_wait_events(headers, rows)
    
    def parse_sql_statistics(self, soup: BeautifulSoup) -> List[SQLStatistic]:
        """
        解析SQL统计信息（复用19c逻辑，结构相同）
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            List[SQLStatistic]: SQL统计列表
        """
        navigator = AnchorNavigator(soup)
        parser = HTMLTableParser(soup)
        
        # 查找SQL统计表格
        sql_table = None
        for anchor in self.anchor_mapping['sql_statistics']:
            sql_table = navigator.get_table_after_anchor(anchor)
            if sql_table:
                break
        
        if not sql_table:
            # 尝试通过标题查找
            for pattern in self.table_patterns['sql_statistics']:
                sql_table = parser.find_table_by_caption(pattern)
                if sql_table:
                    break
        
        if not sql_table:
            self.logger.warning("未找到SQL统计表格")
            return []
        
        # 解析表格数据
        headers, rows = parser.parse_data_table(sql_table)
        
        if not headers or not rows:
            self.logger.warning("SQL统计表格解析为空")
            return []
        
        return self._convert_to_sql_statistics(headers, rows)
    
    def parse_instance_activity(self, soup: BeautifulSoup) -> List[InstanceActivity]:
        """
        解析实例活动统计（复用19c逻辑，结构相同）
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            List[InstanceActivity]: 实例活动统计列表
        """
        navigator = AnchorNavigator(soup)
        parser = HTMLTableParser(soup)
        
        # 查找实例活动统计表格
        activity_table = None
        for anchor in self.anchor_mapping['instance_activity']:
            activity_table = navigator.get_table_after_anchor(anchor)
            if activity_table:
                break
        
        if not activity_table:
            self.logger.warning("未找到实例活动统计表格")
            return []
        
        # 解析表格数据
        headers, rows = parser.parse_data_table(activity_table)
        
        if not headers or not rows:
            self.logger.warning("实例活动统计表格解析为空")
            return []
        
        return self._convert_to_instance_activities(headers, rows)
    
    # =================== 辅助方法（部分复用19c，部分11g特定） ===================
    
    def _create_default_db_info(self) -> DBInfo:
        """创建默认的数据库信息"""
        return DBInfo(
            db_name="UNKNOWN",
            instance_name="UNKNOWN",
            version=self.version,
            instance_type=InstanceType.SINGLE,
            host_name=None,
            platform=None,
            startup_time=None,
            is_rac=False,
            container_name=None,
            instance_number=1  # 默认实例编号为1
        )
    
    def _create_default_snapshot_info(self) -> SnapshotInfo:
        """创建默认的快照信息"""
        return SnapshotInfo(
            begin_snap_id=0,
            end_snap_id=0,
            begin_time=datetime.now(),
            end_time=datetime.now(),
            elapsed_time_minutes=0.0,
            db_time_minutes=0.0
        )
    
    def _create_default_load_profile(self) -> LoadProfile:
        """创建默认的Load Profile"""
        return LoadProfile(
            db_time_per_second=0.0,
            db_time_per_transaction=0.0,
            logical_reads_per_second=0.0,
            logical_reads_per_transaction=0.0,
            physical_reads_per_second=0.0,
            physical_writes_per_second=0.0,
            user_calls_per_second=0.0,
            parses_per_second=0.0,
            hard_parses_per_second=0.0,
            sorts_per_second=0.0,
            logons_per_second=0.0,
            executes_per_second=0.0,
            rollbacks_per_second=0.0,
            transactions_per_second=0.0
        )
    
    def _extract_db_name(self, db_data: Dict[str, str]) -> str:
        """提取数据库名称"""
        patterns = ['DB Name', 'Database Name', 'DB_NAME', 'name']
        return self._get_value_by_patterns(db_data, patterns, "UNKNOWN")
    
    def _extract_instance_name(self, db_data: Dict[str, str]) -> str:
        """提取实例名称"""
        patterns = ['Instance', 'Instance Name', 'INSTANCE_NAME']
        return self._get_value_by_patterns(db_data, patterns, "UNKNOWN")
    
    def _extract_host_name(self, db_data: Dict[str, str]) -> Optional[str]:
        """提取主机名"""
        patterns = ['Host Name', 'Host', 'HOST_NAME']
        return self._get_value_by_patterns(db_data, patterns, None)
    
    def _extract_platform(self, db_data: Dict[str, str]) -> Optional[str]:
        """提取平台信息"""
        patterns = ['Platform', 'Platform Name', 'PLATFORM_NAME']
        return self._get_value_by_patterns(db_data, patterns, None)
    
    def _extract_startup_time(self, db_data: Dict[str, str]) -> Optional[datetime]:
        """提取启动时间"""
        patterns = ['Startup Time', 'Started', 'STARTUP_TIME']
        time_str = self._get_value_by_patterns(db_data, patterns, None)
        
        if not time_str:
            return None
        
        # 尝试多种时间格式解析
        time_formats = [
            "%d-%b-%y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%m/%d/%Y %H:%M:%S"
        ]
        
        for fmt in time_formats:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                continue
        
        self.logger.warning(f"无法解析启动时间: {time_str}")
        return None
    
    def _detect_instance_type_11g(self, db_data: Dict[str, str]) -> InstanceType:
        """
        检测实例类型（11g特定版本，不支持CDB/PDB）
        
        Args:
            db_data: 数据库信息字典
            
        Returns:
            InstanceType: 实例类型
        """
        # 检查RAC标识
        rac_patterns = ['RAC', 'Real Application Clusters', 'Parallel Server']
        
        for key, value in db_data.items():
            key_lower = key.lower()
            value_lower = value.lower() if value else ""
            
            # 检查键名
            if any(pattern.lower() in key_lower for pattern in rac_patterns):
                if 'yes' in value_lower or 'true' in value_lower or 'enabled' in value_lower:
                    return InstanceType.RAC
            
            # 检查值内容
            if any(pattern.lower() in value_lower for pattern in rac_patterns):
                return InstanceType.RAC
        
        # 11g默认为单实例
        return InstanceType.SINGLE
    
    def _extract_instance_number(self, db_data: Dict[str, str]) -> Optional[int]:
        """提取实例编号（用于RAC）"""
        patterns = ['Instance Number', 'Instance', 'Inst Num', 'INSTANCE_NUMBER']
        
        # 首先尝试直接匹配
        instance_str = self._get_value_by_patterns(db_data, patterns, None)
        if instance_str:
            instance_num = self._safe_int(instance_str, 0)
            if instance_num > 0:
                return instance_num
        
        # 如果没有找到直接的实例编号，尝试从实例名中提取
        instance_name = self._extract_instance_name(db_data)
        if instance_name and instance_name != "UNKNOWN":
            # 尝试从实例名末尾提取数字（如ORCL1, ORCL2等）
            import re
            match = re.search(r'(\d+)$', instance_name)
            if match:
                return int(match.group(1))
        
        # 如果检测到是RAC，默认返回1，否则返回None
        instance_type = self._detect_instance_type_11g(db_data)
        if instance_type == InstanceType.RAC:
            return 1
        
        return None
    
    # =================== 复用19c的核心解析方法 ===================
    
    def _parse_snapshot_from_kv(self, snapshot_data: Dict[str, str]) -> SnapshotInfo:
        """从键值对数据解析快照信息（复用19c逻辑）"""
        # 提取快照ID
        begin_snap_id = self._safe_int(
            self._get_value_by_patterns(snapshot_data, ['Begin Snap', 'Begin Snap Id'], "0")
        )
        end_snap_id = self._safe_int(
            self._get_value_by_patterns(snapshot_data, ['End Snap', 'End Snap Id'], "0")
        )
        
        # 提取时间信息
        begin_time_str = self._get_value_by_patterns(
            snapshot_data, ['Begin Snap Time', 'Begin Time'], ""
        )
        end_time_str = self._get_value_by_patterns(
            snapshot_data, ['End Snap Time', 'End Time'], ""
        )
        
        # 解析时间
        begin_time = self._parse_snapshot_time(begin_time_str)
        end_time = self._parse_snapshot_time(end_time_str)
        
        # 计算时长
        elapsed_time = self._parse_time_duration(
            self._get_value_by_patterns(snapshot_data, ['Elapsed Time', 'Duration'], "0")
        )
        
        db_time = self._parse_time_duration(
            self._get_value_by_patterns(snapshot_data, ['DB Time', 'Database Time'], "0")
        )
        
        return SnapshotInfo(
            begin_snap_id=begin_snap_id,
            end_snap_id=end_snap_id,
            begin_time=begin_time,
            end_time=end_time,
            elapsed_time_minutes=elapsed_time,
            db_time_minutes=db_time
        )
    
    def _parse_snapshot_from_table(self, headers: List[str], rows: List[Dict[str, str]]) -> SnapshotInfo:
        """从表格数据解析快照信息（复用19c逻辑）"""
        if not rows:
            return self._create_default_snapshot_info()
        
        # 通常使用第一行数据
        row = rows[0]
        
        begin_snap_id = self._safe_int(
            self._get_value_by_patterns(row, ['Snap Id', 'Snapshot Id', 'Begin Snap Id'], "0")
        )
        end_snap_id = self._safe_int(
            self._get_value_by_patterns(row, ['End Snap Id', 'Snapshot Id'], str(begin_snap_id + 1))
        )
        
        # 解析快照时间
        begin_time_str = self._get_value_by_patterns(
            row, ['Begin Snap Time', 'Snap Time', 'Begin Time'], ""
        )
        end_time_str = self._get_value_by_patterns(
            row, ['End Snap Time', 'End Time'], ""
        )
        
        begin_time = self._parse_snapshot_time(begin_time_str)
        end_time = self._parse_snapshot_time(end_time_str)
        
        # 计算时长
        elapsed_time = self._safe_float(
            self._get_value_by_patterns(row, ['Elapsed Time', 'Duration'], "0")
        )
        
        db_time = self._safe_float(
            self._get_value_by_patterns(row, ['DB Time', 'Database Time'], "0")
        )
        
        return SnapshotInfo(
            begin_snap_id=begin_snap_id,
            end_snap_id=end_snap_id,
            begin_time=begin_time,
            end_time=end_time,
            elapsed_time_minutes=elapsed_time,
            db_time_minutes=db_time
        )
    
    def _parse_snapshot_time(self, time_str: str) -> datetime:
        """解析快照时间字符串"""
        if not time_str:
            return datetime.now()
        
        # 尝试多种时间格式
        time_formats = [
            "%d-%b-%y %H:%M:%S",
            "%Y-%m-%d %H:%M:%S",
            "%d-%m-%Y %H:%M:%S",
            "%m/%d/%Y %H:%M:%S",
            "%d-%b-%Y %H:%M:%S"
        ]
        
        for fmt in time_formats:
            try:
                return datetime.strptime(time_str.strip(), fmt)
            except ValueError:
                continue
        
        self.logger.warning(f"无法解析快照时间: {time_str}")
        return datetime.now()
    
    def _parse_time_duration(self, time_str: str) -> float:
        """解析时间持续时间（复用19c逻辑）"""
        if not time_str:
            return 0.0
        
        try:
            # 移除逗号和多余空格
            cleaned = re.sub(r'[,\s]+', '', time_str)
            
            # 尝试直接转换为浮点数（分钟）
            if '.' in cleaned or cleaned.isdigit():
                return float(cleaned)
            
            # 解析时:分:秒格式
            if ':' in time_str:
                parts = time_str.split(':')
                if len(parts) == 3:
                    hours = float(parts[0])
                    minutes = float(parts[1])
                    seconds = float(parts[2])
                    return hours * 60 + minutes + seconds / 60
                elif len(parts) == 2:
                    minutes = float(parts[0])
                    seconds = float(parts[1])
                    return minutes + seconds / 60
            
            return 0.0
            
        except (ValueError, IndexError) as e:
            self.logger.warning(f"解析时间持续时间失败: {time_str}, 错误: {e}")
            return 0.0
    
    def _extract_load_metrics(self, headers: List[str], rows: List[Dict[str, str]]) -> LoadProfile:
        """提取Load Profile指标（复用19c逻辑）"""
        metrics = {}
        
        # 定义指标映射（Per Second和Per Transaction）
        metric_patterns = {
            'user_calls_per_sec': ['User calls', 'User Calls'],
            'logical_reads_per_sec': ['Logical reads', 'Logical Reads'],
            'block_changes_per_sec': ['Block changes', 'Block Changes'],
            'physical_reads_per_sec': ['Physical reads', 'Physical Reads'],
            'physical_writes_per_sec': ['Physical writes', 'Physical Writes'],
            'redo_size_per_sec': ['Redo size', 'Redo Size'],
            'user_calls_per_txn': ['User calls', 'User Calls'],
            'logical_reads_per_txn': ['Logical reads', 'Logical Reads'],
            'block_changes_per_txn': ['Block changes', 'Block Changes'],
            'physical_reads_per_txn': ['Physical reads', 'Physical Reads'],
            'physical_writes_per_txn': ['Physical writes', 'Physical Writes'],
            'redo_size_per_txn': ['Redo size', 'Redo Size']
        }
        
        # 查找Per Second和Per Transaction列
        per_sec_col = None
        per_txn_col = None
        
        for header in headers:
            if 'per second' in header.lower() or '/sec' in header.lower():
                per_sec_col = header
            elif 'per transaction' in header.lower() or '/txn' in header.lower():
                per_txn_col = header
        
        # 解析每一行数据
        for row in rows:
            metric_name = self._get_value_by_patterns(row, ['Metric', 'Load Profile'], "").strip()
            
            if not metric_name:
                continue
            
            # 提取Per Second值
            if per_sec_col and per_sec_col in row:
                for key, patterns in metric_patterns.items():
                    if key.endswith('_per_sec') and any(pattern.lower() in metric_name.lower() for pattern in patterns):
                        metrics[key] = self._safe_float(row[per_sec_col])
                        break
            
            # 提取Per Transaction值
            if per_txn_col and per_txn_col in row:
                for key, patterns in metric_patterns.items():
                    if key.endswith('_per_txn') and any(pattern.lower() in metric_name.lower() for pattern in patterns):
                        metrics[key] = self._safe_float(row[per_txn_col])
                        break
        
        # 创建LoadProfile对象
        return LoadProfile(
            db_time_per_second=metrics.get('db_time_per_sec', 0.0),
            db_time_per_transaction=metrics.get('db_time_per_txn', 0.0),
            logical_reads_per_second=metrics.get('logical_reads_per_sec', 0.0),
            logical_reads_per_transaction=metrics.get('logical_reads_per_txn', 0.0),
            physical_reads_per_second=metrics.get('physical_reads_per_sec', 0.0),
            physical_writes_per_second=metrics.get('physical_writes_per_sec', 0.0),
            user_calls_per_second=metrics.get('user_calls_per_sec', 0.0),
            parses_per_second=metrics.get('parses_per_sec', 0.0),
            hard_parses_per_second=metrics.get('hard_parses_per_sec', 0.0),
            sorts_per_second=metrics.get('sorts_per_sec', 0.0),
            logons_per_second=metrics.get('logons_per_sec', 0.0),
            executes_per_second=metrics.get('executes_per_sec', 0.0),
            rollbacks_per_second=metrics.get('rollbacks_per_sec', 0.0),
            transactions_per_second=metrics.get('transactions_per_sec', 0.0)
        )
    
    def _convert_to_wait_events(self, headers: List[str], rows: List[Dict[str, str]]) -> List[WaitEvent]:
        """转换为等待事件列表（复用19c逻辑）"""
        wait_events = []
        
        for i, row in enumerate(rows, 1):
            # 提取等待事件名称
            event_name = self._get_value_by_patterns(
                row, ['Event', 'Wait Event', 'Event Name'], f"Unknown Event {i}"
            )
            
            # 提取等待次数
            waits = self._safe_int(
                self._get_value_by_patterns(row, ['Waits', 'Wait Count'], "0")
            )
            
            # 提取总等待时间（秒）
            time_waited = self._safe_float(
                self._get_value_by_patterns(row, ['Time(s)', 'Time Waited', 'Total Wait Time'], "0")
            )
            
            # 提取平均等待时间（毫秒）
            avg_wait = self._safe_float(
                self._get_value_by_patterns(row, ['Avg wait (ms)', 'Average Wait', 'Avg Wait Time'], "0")
            )
            
            # 提取占比
            pct_total = self._safe_float(
                self._get_value_by_patterns(row, ['%Total', '% Total', 'Percentage'], "0")
            )
            
            wait_event = WaitEvent(
                event_name=event_name,
                waits=waits,
                total_wait_time_sec=time_waited,
                avg_wait_ms=avg_wait,
                percent_db_time=pct_total,
                wait_class=""  # 11g AWR可能没有wait_class信息，设为空字符串
            )
            
            wait_events.append(wait_event)
        
        return wait_events
    
    def _convert_to_sql_statistics(self, headers: List[str], rows: List[Dict[str, str]]) -> List[SQLStatistic]:
        """转换为SQL统计列表（复用19c逻辑）"""
        sql_statistics = []
        
        for i, row in enumerate(rows, 1):
            # 提取SQL ID
            sql_id = self._get_value_by_patterns(
                row, ['SQL Id', 'SQL ID', 'Id'], f"Unknown_{i}"
            )
            
            # 提取SQL文本（可能不完整）
            sql_text = self._get_value_by_patterns(
                row, ['SQL Text', 'Text', 'Statement'], ""
            )
            
            # 提取执行次数
            executions = self._safe_int(
                self._get_value_by_patterns(row, ['Executions', 'Exec', 'Execute Count'], "0")
            )
            
            # 提取总CPU时间
            cpu_time = self._safe_float(
                self._get_value_by_patterns(row, ['CPU Time (s)', 'CPU Time', 'Total CPU'], "0")
            )
            
            # 提取总等待时间
            elapsed_time = self._safe_float(
                self._get_value_by_patterns(row, ['Elapsed Time (s)', 'Elapsed Time', 'Total Time'], "0")
            )
            
            # 提取缓冲区获取数
            buffer_gets = self._safe_int(
                self._get_value_by_patterns(row, ['Buffer Gets', 'Gets', 'Logical Reads'], "0")
            )
            
            # 提取物理读
            disk_reads = self._safe_int(
                self._get_value_by_patterns(row, ['Disk Reads', 'Physical Reads', 'Reads'], "0")
            )
            
            sql_stat = SQLStatistic(
                sql_id=sql_id,
                sql_text=sql_text,
                executions=executions,
                elapsed_time_sec=elapsed_time,
                cpu_time_sec=cpu_time,
                io_time_sec=0.0,  # 11g AWR可能没有单独的IO时间，设为0
                gets=buffer_gets,
                reads=disk_reads
            )
            
            sql_statistics.append(sql_stat)
        
        return sql_statistics
    
    def _convert_to_instance_activities(self, headers: List[str], rows: List[Dict[str, str]]) -> List[InstanceActivity]:
        """转换为实例活动统计列表（复用19c逻辑）"""
        activities = []
        
        for row in rows:
            # 提取统计名称
            statistic_name = self._get_value_by_patterns(
                row, ['Statistic', 'Statistic Name', 'Name'], ""
            )
            
            if not statistic_name:
                continue
            
            # 提取统计值
            total = self._safe_float(
                self._get_value_by_patterns(row, ['Total', 'Value', 'Count'], "0")
            )
            
            # 提取每秒值
            per_second = self._safe_float(
                self._get_value_by_patterns(row, ['Per Second', '/Sec', 'Per Sec'], "0")
            )
            
            # 提取每事务值
            per_txn = self._safe_float(
                self._get_value_by_patterns(row, ['Per Transaction', '/Txn', 'Per Txn'], "0")
            )
            
            activity = InstanceActivity(
                statistic_name=statistic_name,
                total_value=total,
                per_second=per_second,
                per_transaction=per_txn
            )
            
            activities.append(activity)
        
        return activities

    # =================== 静态工具方法 ===================

    @staticmethod
    def _get_value_by_patterns(data: Dict[str, str], patterns: List[str], default: Any = None) -> Any:
        """
        根据模式列表从字典中获取值
        
        Args:
            data: 数据字典
            patterns: 匹配模式列表
            default: 默认值
            
        Returns:
            匹配到的值或默认值
        """
        if not data:
            return default
        
        for pattern in patterns:
            # 精确匹配
            if pattern in data:
                return data[pattern]
            
            # 大小写不敏感匹配
            pattern_lower = pattern.lower()
            for key, value in data.items():
                if key.lower() == pattern_lower:
                    return value
            
            # 部分匹配
            for key, value in data.items():
                if pattern_lower in key.lower():
                    return value
        
        return default

    @staticmethod
    def _safe_int(value: str, default: int = 0) -> int:
        """
        安全转换为整数
        
        Args:
            value: 字符串值
            default: 默认值
            
        Returns:
            转换后的整数或默认值
        """
        if not value:
            return default
        
        try:
            # 移除逗号和空格
            cleaned = re.sub(r'[,\s]', '', str(value))
            return int(float(cleaned))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_float(value: str, default: float = 0.0) -> float:
        """
        安全转换为浮点数
        
        Args:
            value: 字符串值
            default: 默认值
            
        Returns:
            转换后的浮点数或默认值
        """
        if not value:
            return default
        
        try:
            # 移除逗号和空格
            cleaned = re.sub(r'[,\s]', '', str(value))
            return float(cleaned)
        except (ValueError, TypeError):
            return default

    def get_supported_version(self) -> OracleVersion:
        """返回支持的Oracle版本"""
        return OracleVersion.ORACLE_11G 