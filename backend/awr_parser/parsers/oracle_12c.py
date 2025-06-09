"""
Oracle 12c AWR解析器
{{CHENGQI: P2-TE-006 解析器测试套件 - Oracle 12c解析器补全 - 2025-06-02T19:35:00}}

实现Oracle 12c版本AWR报告的专业解析
支持标准AWR、RAC、CDB/PDB等多种格式
基于Oracle19cParser和Oracle11gParser的成熟架构，进行12c特定的适配
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


class Oracle12cParser(AbstractAWRParser):
    """
    Oracle 12c AWR解析器
    
    遵循开闭原则，继承AbstractAWRParser抽象基类
    专门处理Oracle 12c版本的AWR报告格式和特殊情况
    基于Oracle 19c和11g解析器的成熟实现，进行12c特定的适配
    """
    
    def __init__(self):
        super().__init__()
        self.logger.info("检测到Oracle 12c AWR格式")
        self.version = OracleVersion.ORACLE_12C
        
        # Oracle 12c特有的锚点映射（与19c基本相同）
        self.anchor_mapping = {
            'db_info': ['dbinfo', 'db_information', 'database_information'],
            'snapshot_info': ['snapshot', 'snap_info', 'snapshot_information'],
            'load_profile': ['loadprofile', 'load_profile', 'system_load'],
            'wait_events': ['topevents', 'wait_events', 'top_events'],
            'sql_statistics': ['topsql', 'sql_statistics', 'top_sql'],
            'instance_activity': ['sysstat', 'instance_activity', 'system_statistics']
        }
        
        # Oracle 12c表格标题模式（与19c基本相同）
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
            bool: 是否支持解析Oracle 12c格式
        """
        try:
            # 检查Oracle 12c版本标识
            version_patterns = [
                r'Oracle\s+Database\s+12c',
                r'Release\s+12\.',
                r'12\.\d+\.\d+\.\d+',
                r'version["\s]*12\.'
            ]
            
            for pattern in version_patterns:
                if re.search(pattern, html_content, re.IGNORECASE):
                    self.logger.info("检测到Oracle 12c AWR格式")
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
                self.logger.info(f"找到 {found_anchors} 个AWR锚点，尝试作为Oracle 12c解析")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查Oracle 12c兼容性时出错: {e}")
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
        
        # 检测实例类型（12c支持CDB/PDB）
        instance_type = self._detect_instance_type(db_data)
        is_rac = instance_type == InstanceType.RAC
        container_name = self._extract_container_name(db_data) if instance_type in [InstanceType.CDB, InstanceType.PDB] else None
        
        # 提取实例编号（用于RAC）
        instance_number = self._extract_instance_number(db_data)
        
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
        
        if analysis['structure_type'] == 'key_value':
            # 键值对形式的快照信息
            snapshot_data = parser.parse_key_value_table(snapshot_table)
            return self._parse_snapshot_from_dict(snapshot_data)
        else:
            # 表格形式的快照信息
            headers, rows = parser.parse_data_table(snapshot_table)
            return self._parse_snapshot_from_table(headers, rows)
    
    def parse_load_profile(self, soup: BeautifulSoup) -> LoadProfile:
        """
        解析Load Profile（复用19c逻辑，结构相同）
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            LoadProfile: 负载概要对象
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
        解析等待事件（复用19c逻辑，结构相同）
        
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
    
    # =================== 辅助方法（复用19c和11g的成熟实现） ===================
    
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
        patterns = ['Platform', 'Platform Name', 'OS']
        return self._get_value_by_patterns(db_data, patterns, None)
    
    def _extract_startup_time(self, db_data: Dict[str, str]) -> Optional[datetime]:
        """提取启动时间"""
        patterns = ['Startup Time', 'Started', 'Instance Started']
        for pattern in patterns:
            if pattern in db_data:
                try:
                    time_str = db_data[pattern].strip()
                    return datetime.strptime(time_str, '%d-%b-%y %H:%M:%S')
                except ValueError:
                    continue
        return None
    
    def _detect_instance_type(self, db_data: Dict[str, str]) -> InstanceType:
        """
        检测实例类型（12c支持CDB/PDB）
        
        Args:
            db_data: 数据库信息字典
            
        Returns:
            InstanceType: 实例类型
        """
        # 检查是否为RAC
        rac_indicators = ['RAC', 'Cluster', 'Instance Number', 'Inst#']
        for key, value in db_data.items():
            if any(indicator.lower() in key.lower() for indicator in rac_indicators):
                return InstanceType.RAC
            if any(indicator.lower() in value.lower() for indicator in ['rac', 'cluster']):
                return InstanceType.RAC
        
        # 检查是否为CDB/PDB（12c支持）
        container_indicators = ['CDB', 'PDB', 'Container']
        for key, value in db_data.items():
            if any(indicator.lower() in key.lower() for indicator in container_indicators):
                if 'pdb' in value.lower():
                    return InstanceType.PDB
                elif 'cdb' in value.lower():
                    return InstanceType.CDB
        
        return InstanceType.SINGLE
    
    def _extract_container_name(self, db_data: Dict[str, str]) -> Optional[str]:
        """提取容器名称（用于CDB/PDB）"""
        patterns = ['Container Name', 'PDB Name', 'Con Name']
        for pattern in patterns:
            if pattern in db_data:
                return db_data[pattern].strip()
        return None
    
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
        instance_type = self._detect_instance_type(db_data)
        if instance_type == InstanceType.RAC:
            return 1
        
        return None
    
    def _parse_snapshot_from_dict(self, snapshot_data: Dict[str, str]) -> SnapshotInfo:
        """从字典数据解析快照信息"""
        begin_snap_id = self._safe_int(
            self._get_value_by_patterns(snapshot_data, ['Begin Snap Id', 'Snap Id'], "0")
        )
        end_snap_id = self._safe_int(
            self._get_value_by_patterns(snapshot_data, ['End Snap Id'], str(begin_snap_id + 1))
        )
        
        elapsed_time = self._safe_float(
            self._get_value_by_patterns(snapshot_data, ['Elapsed Time', 'Duration'], "0")
        )
        
        db_time = self._safe_float(
            self._get_value_by_patterns(snapshot_data, ['DB Time', 'Database Time'], "0")
        )
        
        return SnapshotInfo(
            begin_snap_id=begin_snap_id,
            end_snap_id=end_snap_id,
            begin_time=datetime.now(),
            end_time=datetime.now(),
            elapsed_time_minutes=elapsed_time,
            db_time_minutes=db_time
        )
    
    def _parse_snapshot_from_table(self, headers: List[str], rows: List[Dict[str, str]]) -> SnapshotInfo:
        """从表格数据解析快照信息"""
        if not rows:
            return self._create_default_snapshot_info()
        
        row = rows[0]
        
        begin_snap_id = self._safe_int(
            self._get_value_by_patterns(row, ['Snap Id', 'Begin Snap Id'], "0")
        )
        end_snap_id = self._safe_int(
            self._get_value_by_patterns(row, ['End Snap Id'], str(begin_snap_id + 1))
        )
        
        elapsed_time = self._safe_float(
            self._get_value_by_patterns(row, ['Elapsed Time', 'Duration'], "0")
        )
        
        db_time = self._safe_float(
            self._get_value_by_patterns(row, ['DB Time', 'Database Time'], "0")
        )
        
        return SnapshotInfo(
            begin_snap_id=begin_snap_id,
            end_snap_id=end_snap_id,
            begin_time=datetime.now(),
            end_time=datetime.now(),
            elapsed_time_minutes=elapsed_time,
            db_time_minutes=db_time
        )
    
    def _extract_load_metrics(self, headers: List[str], rows: List[Dict[str, str]]) -> LoadProfile:
        """提取Load Profile指标"""
        metrics = {}
        
        for row in rows:
            # 提取指标名称（通常在第一列）
            metric_name = ""
            for header in headers:
                if header and row.get(header):
                    metric_name = row[header].lower().strip()
                    break
            
            if not metric_name:
                continue
            
            # 提取Per Second和Per Transaction值
            per_sec_value = 0.0
            per_txn_value = 0.0
            
            for header in headers[1:]:  # 跳过第一列（指标名称）
                header_lower = header.lower()
                value = row.get(header, "0")
                
                if 'second' in header_lower or 'sec' in header_lower:
                    per_sec_value = self._safe_float(value)
                elif 'transaction' in header_lower or 'txn' in header_lower:
                    per_txn_value = self._safe_float(value)
            
            # 映射到LoadProfile字段
            if 'db time' in metric_name:
                metrics['db_time_per_sec'] = per_sec_value
                metrics['db_time_per_txn'] = per_txn_value
            elif 'logical read' in metric_name:
                metrics['logical_reads_per_sec'] = per_sec_value
                metrics['logical_reads_per_txn'] = per_txn_value
            elif 'physical read' in metric_name:
                metrics['physical_reads_per_sec'] = per_sec_value
            elif 'physical write' in metric_name:
                metrics['physical_writes_per_sec'] = per_sec_value
            elif 'user call' in metric_name:
                metrics['user_calls_per_sec'] = per_sec_value
            elif 'parse' in metric_name and 'hard' not in metric_name:
                metrics['parses_per_sec'] = per_sec_value
            elif 'hard parse' in metric_name:
                metrics['hard_parses_per_sec'] = per_sec_value
            elif 'sort' in metric_name:
                metrics['sorts_per_sec'] = per_sec_value
            elif 'logon' in metric_name:
                metrics['logons_per_sec'] = per_sec_value
            elif 'execute' in metric_name:
                metrics['executes_per_sec'] = per_sec_value
            elif 'rollback' in metric_name:
                metrics['rollbacks_per_sec'] = per_sec_value
            elif 'transaction' in metric_name:
                metrics['transactions_per_sec'] = per_sec_value
        
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
        """转换为等待事件列表"""
        wait_events = []
        
        for i, row in enumerate(rows, 1):
            event_name = self._get_value_by_patterns(
                row, ['Event', 'Wait Event', 'Event Name'], f"Unknown Event {i}"
            )
            
            waits = self._safe_int(
                self._get_value_by_patterns(row, ['Waits', 'Wait Count'], "0")
            )
            
            time_waited = self._safe_float(
                self._get_value_by_patterns(row, ['Time(s)', 'Time Waited', 'Total Wait Time'], "0")
            )
            
            avg_wait = self._safe_float(
                self._get_value_by_patterns(row, ['Avg wait (ms)', 'Average Wait', 'Avg Wait Time'], "0")
            )
            
            pct_total = self._safe_float(
                self._get_value_by_patterns(row, ['%Total', '% Total', 'Percentage'], "0")
            )
            
            wait_class = self._get_value_by_patterns(
                row, ['Wait Class', 'Class'], ""
            )
            
            wait_event = WaitEvent(
                event_name=event_name,
                waits=waits,
                total_wait_time_sec=time_waited,
                avg_wait_ms=avg_wait,
                percent_db_time=pct_total,
                wait_class=wait_class
            )
            
            wait_events.append(wait_event)
        
        return wait_events
    
    def _convert_to_sql_statistics(self, headers: List[str], rows: List[Dict[str, str]]) -> List[SQLStatistic]:
        """转换为SQL统计列表"""
        sql_statistics = []
        
        for i, row in enumerate(rows, 1):
            sql_id = self._get_value_by_patterns(
                row, ['SQL Id', 'SQL ID', 'Id'], f"Unknown_{i}"
            )
            
            sql_text = self._get_value_by_patterns(
                row, ['SQL Text', 'Text', 'Statement'], ""
            )
            
            executions = self._safe_int(
                self._get_value_by_patterns(row, ['Executions', 'Exec', 'Execute Count'], "0")
            )
            
            cpu_time = self._safe_float(
                self._get_value_by_patterns(row, ['CPU Time (s)', 'CPU Time', 'Total CPU'], "0")
            )
            
            elapsed_time = self._safe_float(
                self._get_value_by_patterns(row, ['Elapsed Time (s)', 'Elapsed Time', 'Total Time'], "0")
            )
            
            buffer_gets = self._safe_int(
                self._get_value_by_patterns(row, ['Buffer Gets', 'Gets', 'Logical Reads'], "0")
            )
            
            disk_reads = self._safe_int(
                self._get_value_by_patterns(row, ['Disk Reads', 'Physical Reads', 'Reads'], "0")
            )
            
            sql_stat = SQLStatistic(
                sql_id=sql_id,
                sql_text=sql_text,
                executions=executions,
                elapsed_time_sec=elapsed_time,
                cpu_time_sec=cpu_time,
                io_time_sec=elapsed_time - cpu_time if elapsed_time > cpu_time else 0.0,
                gets=buffer_gets,
                reads=disk_reads
            )
            
            sql_statistics.append(sql_stat)
        
        return sql_statistics
    
    def _convert_to_instance_activities(self, headers: List[str], rows: List[Dict[str, str]]) -> List[InstanceActivity]:
        """转换为实例活动统计列表"""
        activities = []
        
        for row in rows:
            statistic_name = self._get_value_by_patterns(
                row, ['Statistic', 'Statistic Name', 'Name'], ""
            )
            
            if not statistic_name:
                continue
            
            total = self._safe_float(
                self._get_value_by_patterns(row, ['Total', 'Value', 'Count'], "0")
            )
            
            per_second = self._safe_float(
                self._get_value_by_patterns(row, ['Per Second', '/Sec', 'Per Sec'], "0")
            )
            
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
        """根据模式列表从字典中获取值"""
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
        """安全转换为整数"""
        if not value:
            return default
        
        try:
            cleaned = re.sub(r'[,\s]', '', str(value))
            return int(float(cleaned))
        except (ValueError, TypeError):
            return default

    @staticmethod
    def _safe_float(value: str, default: float = 0.0) -> float:
        """安全转换为浮点数"""
        if not value:
            return default
        
        try:
            cleaned = re.sub(r'[,\s]', '', str(value))
            return float(cleaned)
        except (ValueError, TypeError):
            return default

    def get_supported_version(self) -> OracleVersion:
        """返回支持的Oracle版本"""
        return OracleVersion.ORACLE_12C 