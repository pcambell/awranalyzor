"""
Oracle 19c AWR解析器
{{CHENGQI: P2-LD-003 Oracle 19c解析器实现 - 2025-06-02 11:25:00 +08:00}}

实现Oracle 19c版本AWR报告的专业解析
支持标准AWR、RAC、CDB/PDB等多种格式
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


class Oracle19cParser(AbstractAWRParser):
    """
    Oracle 19c AWR解析器
    
    遵循开闭原则，继承AbstractAWRParser抽象基类
    专门处理Oracle 19c版本的AWR报告格式和特殊情况
    """
    
    def __init__(self):
        super().__init__()
        self.version = OracleVersion.ORACLE_19C
        
        # Oracle 19c特有的锚点映射
        self.anchor_mapping = {
            'db_info': ['dbinfo', 'db_information', 'database_information'],
            'snapshot_info': ['snapshot', 'snap_info', 'snapshot_information'],
            'load_profile': ['loadprofile', 'load_profile', 'system_load'],
            'wait_events': ['topevents', 'wait_events', 'top_events'],
            'sql_statistics': ['topsql', 'sql_statistics', 'top_sql'],
            'instance_activity': ['sysstat', 'instance_activity', 'system_statistics']
        }
        
        # Oracle 19c表格标题模式
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
            bool: 是否支持解析Oracle 19c格式
        """
        try:
            # 检查Oracle版本标识
            version_patterns = [
                r'Oracle\s+Database\s+19c',
                r'Release\s+19\.',
                r'19\.\d+\.\d+\.\d+',
                r'version["\s]*19\.'
            ]
            
            for pattern in version_patterns:
                if re.search(pattern, html_content, re.IGNORECASE):
                    self.logger.info("检测到Oracle 19c AWR格式")
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
                self.logger.info(f"找到 {found_anchors} 个AWR锚点，尝试作为Oracle 19c解析")
                return True
            
            return False
            
        except Exception as e:
            self.logger.error(f"检查Oracle 19c兼容性时出错: {e}")
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
        
        # 检测实例类型
        instance_type = self._detect_instance_type(db_data)
        is_rac = instance_type == InstanceType.RAC
        container_name = self._extract_container_name(db_data) if instance_type in [InstanceType.CDB, InstanceType.PDB] else None
        
        return DBInfo(
            db_name=db_name,
            instance_name=instance_name,
            version=self.version,
            instance_type=instance_type,
            host_name=host_name,
            platform=platform,
            startup_time=startup_time,
            is_rac=is_rac,
            container_name=container_name
        )
    
    def parse_snapshot_info(self, soup: BeautifulSoup) -> SnapshotInfo:
        """
        解析快照信息
        
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
        
        # 如果没找到，尝试查找包含"Snap"的表格
        if not snapshot_table:
            for table in soup.find_all('table'):
                # 检查表格内容是否包含快照信息
                table_text = table.get_text().lower()
                if any(keyword in table_text for keyword in ['snap id', 'begin snap', 'end snap', 'elapsed']):
                    snapshot_table = table
                    break
        
        if not snapshot_table:
            self.logger.warning("未找到快照信息表格")
            return self._create_default_snapshot_info()
        
        # 分析表格结构
        analyzer = TableStructureAnalyzer(snapshot_table)
        structure = analyzer.analyze()
        
        if structure.get('is_key_value', False):
            # 键值对格式
            snapshot_data = parser.parse_key_value_table(snapshot_table)
            return self._parse_snapshot_from_kv(snapshot_data)
        else:
            # 表头数据格式
            headers, rows = parser.parse_table_with_headers(snapshot_table)
            return self._parse_snapshot_from_table(headers, rows)
    
    def parse_load_profile(self, soup: BeautifulSoup) -> LoadProfile:
        """
        解析负载概要
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            LoadProfile: 负载概要对象
        """
        navigator = AnchorNavigator(soup)
        parser = HTMLTableParser(soup)
        
        # 查找负载概要表格
        load_table = None
        for anchor in self.anchor_mapping['load_profile']:
            load_table = navigator.get_table_after_anchor(anchor)
            if load_table:
                break
        
        if not load_table:
            # 尝试通过标题模式查找
            for pattern in self.table_patterns['load_profile']:
                load_table = parser.find_table_by_caption(pattern)
                if load_table:
                    break
        
        if not load_table:
            self.logger.warning("未找到负载概要表格")
            return self._create_default_load_profile()
        
        # 解析表格数据
        headers, rows = parser.parse_table_with_headers(load_table)
        
        if not rows:
            self.logger.warning("负载概要表格无数据行")
            return self._create_default_load_profile()
        
        # 提取负载指标
        return self._extract_load_metrics(headers, rows)
    
    def parse_wait_events(self, soup: BeautifulSoup) -> List[WaitEvent]:
        """
        解析等待事件
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            List[WaitEvent]: 等待事件列表
        """
        navigator = AnchorNavigator(soup)
        parser = HTMLTableParser(soup)
        
        # 查找等待事件表格
        events_table = None
        for anchor in self.anchor_mapping['wait_events']:
            events_table = navigator.get_table_after_anchor(anchor)
            if events_table:
                break
        
        if not events_table:
            # 尝试通过标题模式查找
            for pattern in self.table_patterns['wait_events']:
                events_table = parser.find_table_by_caption(pattern)
                if events_table:
                    break
        
        if not events_table:
            self.logger.warning("未找到等待事件表格")
            return []
        
        # 解析表格数据
        headers, rows = parser.parse_table_with_headers(events_table)
        
        if not rows:
            self.logger.warning("等待事件表格无数据行")
            return []
        
        # 转换为WaitEvent对象列表
        return self._convert_to_wait_events(headers, rows)
    
    def parse_sql_statistics(self, soup: BeautifulSoup) -> List[SQLStatistic]:
        """
        解析SQL统计
        
        Args:
            soup: BeautifulSoup解析对象
            
        Returns:
            List[SQLStatistic]: SQL统计列表
        """
        navigator = AnchorNavigator(soup)
        parser = HTMLTableParser(soup)
        
        sql_statistics = []
        
        # 查找各种SQL统计表格
        for anchor in self.anchor_mapping['sql_statistics']:
            sql_table = navigator.get_table_after_anchor(anchor)
            if sql_table:
                headers, rows = parser.parse_table_with_headers(sql_table)
                if rows:
                    sql_stats = self._convert_to_sql_statistics(headers, rows)
                    sql_statistics.extend(sql_stats)
        
        # 如果没通过锚点找到，尝试通过标题查找
        if not sql_statistics:
            for pattern in self.table_patterns['sql_statistics']:
                sql_table = parser.find_table_by_caption(pattern)
                if sql_table:
                    headers, rows = parser.parse_table_with_headers(sql_table)
                    if rows:
                        sql_stats = self._convert_to_sql_statistics(headers, rows)
                        sql_statistics.extend(sql_stats)
                        break
        
        if not sql_statistics:
            self.logger.warning("未找到SQL统计数据")
        
        return sql_statistics[:50]  # 限制返回数量，避免数据过多
    
    def parse_instance_activity(self, soup: BeautifulSoup) -> List[InstanceActivity]:
        """
        解析实例活动统计
        
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
        headers, rows = parser.parse_table_with_headers(activity_table)
        
        if not rows:
            self.logger.warning("实例活动统计表格无数据行")
            return []
        
        # 转换为InstanceActivity对象列表
        return self._convert_to_instance_activities(headers, rows)
    
    # ===== 私有辅助方法 =====
    
    def _create_default_db_info(self) -> DBInfo:
        """创建默认数据库信息"""
        return DBInfo(
            db_name="UNKNOWN",
            instance_name="UNKNOWN", 
            version=self.version,
            instance_type=InstanceType.SINGLE
        )
    
    def _create_default_snapshot_info(self) -> SnapshotInfo:
        """创建默认快照信息"""
        now = datetime.now()
        return SnapshotInfo(
            begin_snap_id=0,
            end_snap_id=0,
            begin_time=now,
            end_time=now,
            elapsed_time_minutes=0.0,
            db_time_minutes=0.0
        )
    
    def _create_default_load_profile(self) -> LoadProfile:
        """创建默认负载概要"""
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
        """从数据库信息中提取数据库名"""
        keys = ['DB Name', 'Database Name', 'DB_NAME', 'Name']
        for key in keys:
            if key in db_data:
                return db_data[key].strip()
        return "UNKNOWN"
    
    def _extract_instance_name(self, db_data: Dict[str, str]) -> str:
        """从数据库信息中提取实例名"""
        keys = ['Instance', 'Instance Name', 'INSTANCE_NAME', 'Inst Name']
        for key in keys:
            if key in db_data:
                return db_data[key].strip()
        return "UNKNOWN"
    
    def _extract_host_name(self, db_data: Dict[str, str]) -> Optional[str]:
        """从数据库信息中提取主机名"""
        keys = ['Host Name', 'Hostname', 'HOST_NAME', 'Host']
        for key in keys:
            if key in db_data:
                return db_data[key].strip()
        return None
    
    def _extract_platform(self, db_data: Dict[str, str]) -> Optional[str]:
        """从数据库信息中提取平台信息"""
        keys = ['Platform', 'Platform Name', 'OS']
        for key in keys:
            if key in db_data:
                return db_data[key].strip()
        return None
    
    def _extract_startup_time(self, db_data: Dict[str, str]) -> Optional[datetime]:
        """从数据库信息中提取启动时间"""
        keys = ['Startup Time', 'Started', 'Instance Started']
        for key in keys:
            if key in db_data:
                try:
                    # 尝试解析时间格式
                    time_str = db_data[key].strip()
                    # Oracle时间格式通常是：DD-MON-YY HH24:MI:SS
                    return datetime.strptime(time_str, '%d-%b-%y %H:%M:%S')
                except ValueError:
                    continue
        return None
    
    def _detect_instance_type(self, db_data: Dict[str, str]) -> InstanceType:
        """检测实例类型"""
        # 检查是否为RAC
        rac_indicators = ['RAC', 'Cluster', 'Instance Number', 'Inst#']
        for key, value in db_data.items():
            if any(indicator.lower() in key.lower() for indicator in rac_indicators):
                return InstanceType.RAC
            if any(indicator.lower() in value.lower() for indicator in ['rac', 'cluster']):
                return InstanceType.RAC
        
        # 检查是否为CDB/PDB
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
        keys = ['Container Name', 'PDB Name', 'Con Name']
        for key in keys:
            if key in db_data:
                return db_data[key].strip()
        return None
    
    def _parse_snapshot_from_kv(self, snapshot_data: Dict[str, str]) -> SnapshotInfo:
        """从键值对数据解析快照信息"""
        # 提取快照ID
        begin_snap_id = 0
        end_snap_id = 0
        
        for key, value in snapshot_data.items():
            if 'begin snap' in key.lower():
                begin_snap_id = DataCleaner.clean_number(value) or 0
            elif 'end snap' in key.lower():
                end_snap_id = DataCleaner.clean_number(value) or 0
        
        # 提取时间信息
        begin_time = datetime.now()
        end_time = datetime.now()
        elapsed_minutes = 0.0
        db_time_minutes = 0.0
        
        for key, value in snapshot_data.items():
            if 'elapsed' in key.lower():
                elapsed_minutes = self._parse_time_duration(value)
            elif 'db time' in key.lower():
                db_time_minutes = self._parse_time_duration(value)
        
        return SnapshotInfo(
            begin_snap_id=int(begin_snap_id),
            end_snap_id=int(end_snap_id),
            begin_time=begin_time,
            end_time=end_time,
            elapsed_time_minutes=elapsed_minutes,
            db_time_minutes=db_time_minutes
        )
    
    def _parse_snapshot_from_table(self, headers: List[str], rows: List[Dict[str, str]]) -> SnapshotInfo:
        """从表格数据解析快照信息"""
        if not rows:
            return self._create_default_snapshot_info()
        
        # 假设第一行包含Begin快照信息，第二行包含End快照信息
        begin_row = rows[0] if len(rows) > 0 else {}
        end_row = rows[1] if len(rows) > 1 else rows[0]
        
        # 查找Snap ID列
        snap_id_col = None
        for header in headers:
            if 'snap' in header.lower() and 'id' in header.lower():
                snap_id_col = header
                break
        
        begin_snap_id = 0
        end_snap_id = 0
        
        if snap_id_col:
            begin_snap_id = DataCleaner.clean_number(begin_row.get(snap_id_col, '0')) or 0
            end_snap_id = DataCleaner.clean_number(end_row.get(snap_id_col, '0')) or 0
        
        return SnapshotInfo(
            begin_snap_id=int(begin_snap_id),
            end_snap_id=int(end_snap_id),
            begin_time=datetime.now(),  # 实际应从数据中解析
            end_time=datetime.now(),
            elapsed_time_minutes=0.0,   # 实际应从数据中解析
            db_time_minutes=0.0
        )
    
    def _parse_time_duration(self, time_str: str) -> float:
        """解析时间duration为分钟数"""
        if not time_str:
            return 0.0
        
        try:
            # 尝试解析各种时间格式
            time_str = time_str.strip().lower()
            
            # 格式：123.45 mins
            if 'min' in time_str:
                match = re.search(r'([\d.]+)', time_str)
                if match:
                    return float(match.group(1))
            
            # 格式：1.23 hrs
            if 'hr' in time_str:
                match = re.search(r'([\d.]+)', time_str)
                if match:
                    return float(match.group(1)) * 60
            
            # 格式：12345 secs
            if 'sec' in time_str:
                match = re.search(r'([\d.]+)', time_str)
                if match:
                    return float(match.group(1)) / 60
            
            # 纯数字，假设为分钟
            match = re.search(r'([\d.]+)', time_str)
            if match:
                return float(match.group(1))
                
        except (ValueError, AttributeError):
            pass
        
        return 0.0
    
    def _extract_load_metrics(self, headers: List[str], rows: List[Dict[str, str]]) -> LoadProfile:
        """从负载概要表格提取指标"""
        # 初始化默认值
        metrics = {
            'db_time_per_second': 0.0,
            'db_time_per_transaction': 0.0,
            'logical_reads_per_second': 0.0,
            'logical_reads_per_transaction': 0.0,
            'physical_reads_per_second': 0.0,
            'physical_writes_per_second': 0.0,
            'user_calls_per_second': 0.0,
            'parses_per_second': 0.0,
            'hard_parses_per_second': 0.0,
            'sorts_per_second': 0.0,
            'logons_per_second': 0.0,
            'executes_per_second': 0.0,
            'rollbacks_per_second': 0.0,
            'transactions_per_second': 0.0
        }
        
        # 查找Per Second和Per Transaction列
        per_second_col = None
        per_trans_col = None
        
        for header in headers:
            if 'per second' in header.lower() or 'per sec' in header.lower():
                per_second_col = header
            elif 'per transaction' in header.lower() or 'per txn' in header.lower():
                per_trans_col = header
        
        if not per_second_col:
            self.logger.warning("未找到Per Second列")
            return self._create_default_load_profile()
        
        # 提取各行指标
        for row in rows:
            metric_name = ''
            for header in headers:
                if header not in [per_second_col, per_trans_col]:
                    metric_name = row.get(header, '').strip().lower()
                    break
            
            if not metric_name:
                continue
            
            per_second_value = DataCleaner.clean_number(row.get(per_second_col, '0')) or 0.0
            per_trans_value = DataCleaner.clean_number(row.get(per_trans_col, '0')) or 0.0 if per_trans_col else 0.0
            
            # 映射到LoadProfile字段
            if 'db time' in metric_name:
                metrics['db_time_per_second'] = per_second_value
                metrics['db_time_per_transaction'] = per_trans_value
            elif 'logical read' in metric_name:
                metrics['logical_reads_per_second'] = per_second_value
                metrics['logical_reads_per_transaction'] = per_trans_value
            elif 'physical read' in metric_name:
                metrics['physical_reads_per_second'] = per_second_value
            elif 'physical write' in metric_name:
                metrics['physical_writes_per_second'] = per_second_value
            elif 'user call' in metric_name:
                metrics['user_calls_per_second'] = per_second_value
            elif 'parse' in metric_name and 'hard' not in metric_name:
                metrics['parses_per_second'] = per_second_value
            elif 'hard parse' in metric_name:
                metrics['hard_parses_per_second'] = per_second_value
            elif 'sort' in metric_name:
                metrics['sorts_per_second'] = per_second_value
            elif 'logon' in metric_name:
                metrics['logons_per_second'] = per_second_value
            elif 'execute' in metric_name:
                metrics['executes_per_second'] = per_second_value
            elif 'rollback' in metric_name:
                metrics['rollbacks_per_second'] = per_second_value
            elif 'transaction' in metric_name:
                metrics['transactions_per_second'] = per_second_value
        
        return LoadProfile(**metrics)
    
    def _convert_to_wait_events(self, headers: List[str], rows: List[Dict[str, str]]) -> List[WaitEvent]:
        """转换表格数据为WaitEvent对象列表"""
        wait_events = []
        
        # 查找关键列
        event_col = None
        waits_col = None
        time_col = None
        pct_col = None
        class_col = None
        
        for header in headers:
            header_lower = header.lower()
            if 'event' in header_lower and not event_col:
                event_col = header
            elif 'wait' in header_lower and ('count' in header_lower or 'waits' in header_lower):
                waits_col = header
            elif 'time' in header_lower and 'total' in header_lower:
                time_col = header
            elif '%' in header and ('db time' in header_lower or 'total' in header_lower):
                pct_col = header
            elif 'class' in header_lower:
                class_col = header
        
        if not event_col:
            self.logger.warning("等待事件表格缺少事件名称列")
            return []
        
        for row in rows:
            event_name = row.get(event_col, '').strip()
            if not event_name or event_name.lower() in ['total', 'other']:
                continue
            
            waits = int(DataCleaner.clean_number(row.get(waits_col, '0')) or 0)
            total_time = float(DataCleaner.clean_number(row.get(time_col, '0')) or 0.0)
            pct_db_time = DataCleaner.clean_percentage(row.get(pct_col, '0%')) or 0.0
            wait_class = row.get(class_col, 'Unknown').strip() if class_col else 'Unknown'
            
            # 计算平均等待时间（毫秒）
            avg_wait_ms = (total_time * 1000 / waits) if waits > 0 else 0.0
            
            wait_event = WaitEvent(
                event_name=DataCleaner.standardize_event_name(event_name),
                waits=waits,
                total_wait_time_sec=total_time,
                avg_wait_ms=avg_wait_ms,
                percent_db_time=pct_db_time,
                wait_class=wait_class
            )
            
            wait_events.append(wait_event)
        
        return wait_events
    
    def _convert_to_sql_statistics(self, headers: List[str], rows: List[Dict[str, str]]) -> List[SQLStatistic]:
        """转换表格数据为SQLStatistic对象列表"""
        sql_statistics = []
        
        # 查找关键列
        sql_id_col = None
        sql_text_col = None
        executions_col = None
        elapsed_col = None
        cpu_col = None
        gets_col = None
        reads_col = None
        
        for header in headers:
            header_lower = header.lower()
            if 'sql id' in header_lower:
                sql_id_col = header
            elif 'sql text' in header_lower or 'command' in header_lower:
                sql_text_col = header
            elif 'execution' in header_lower:
                executions_col = header
            elif 'elapsed' in header_lower:
                elapsed_col = header
            elif 'cpu' in header_lower:
                cpu_col = header
            elif 'gets' in header_lower or 'buffer get' in header_lower:
                gets_col = header
            elif 'reads' in header_lower or 'disk read' in header_lower:
                reads_col = header
        
        if not sql_id_col:
            self.logger.warning("SQL统计表格缺少SQL ID列")
            return []
        
        for row in rows:
            sql_id = row.get(sql_id_col, '').strip()
            if not sql_id:
                continue
            
            sql_text = row.get(sql_text_col, '').strip()[:500] if sql_text_col else ''  # 限制长度
            executions = int(DataCleaner.clean_number(row.get(executions_col, '0')) or 0)
            elapsed_time = float(DataCleaner.clean_number(row.get(elapsed_col, '0')) or 0.0)
            cpu_time = float(DataCleaner.clean_number(row.get(cpu_col, '0')) or 0.0)
            gets = int(DataCleaner.clean_number(row.get(gets_col, '0')) or 0)
            reads = int(DataCleaner.clean_number(row.get(reads_col, '0')) or 0)
            
            sql_stat = SQLStatistic(
                sql_id=sql_id,
                sql_text=sql_text,
                executions=executions,
                elapsed_time_sec=elapsed_time,
                cpu_time_sec=cpu_time,
                io_time_sec=elapsed_time - cpu_time if elapsed_time > cpu_time else 0.0,
                gets=gets,
                reads=reads
            )
            
            sql_statistics.append(sql_stat)
        
        return sql_statistics
    
    def _convert_to_instance_activities(self, headers: List[str], rows: List[Dict[str, str]]) -> List[InstanceActivity]:
        """转换表格数据为InstanceActivity对象列表"""
        activities = []
        
        # 查找关键列
        statistic_col = None
        total_col = None
        per_second_col = None
        per_trans_col = None
        
        for header in headers:
            header_lower = header.lower()
            if 'statistic' in header_lower or 'name' in header_lower:
                statistic_col = header
            elif 'total' in header_lower:
                total_col = header
            elif 'per second' in header_lower:
                per_second_col = header
            elif 'per transaction' in header_lower:
                per_trans_col = header
        
        if not statistic_col:
            self.logger.warning("实例活动统计表格缺少统计名称列")
            return []
        
        for row in rows:
            statistic_name = row.get(statistic_col, '').strip()
            if not statistic_name:
                continue
            
            total_value = DataCleaner.clean_number(row.get(total_col, '0')) or 0
            per_second = float(DataCleaner.clean_number(row.get(per_second_col, '0')) or 0.0)
            per_transaction = float(DataCleaner.clean_number(row.get(per_trans_col, '0')) or 0.0)
            
            activity = InstanceActivity(
                statistic_name=statistic_name,
                total_value=total_value,
                per_second=per_second,
                per_transaction=per_transaction
            )
            
            activities.append(activity)
        
        return activities 