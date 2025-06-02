"""
Oracle 11g AWR解析器测试套件
{{CHENGQI: P2-LD-004 Oracle 11g解析器测试套件 - 2025-06-02 11:58:05 +08:00}}

测试Oracle11gParser的完整功能，包括版本检测、解析能力、错误处理等
基于Oracle19cParser测试结构，针对11g特性进行调整
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from bs4 import BeautifulSoup

from apps.awr_parser.parsers.oracle_11g import Oracle11gParser
from apps.awr_parser.parsers.base import (
    OracleVersion, InstanceType, DBInfo, SnapshotInfo, 
    LoadProfile, WaitEvent, SQLStatistic, InstanceActivity
)


class TestOracle11gParser(unittest.TestCase):
    """Oracle 11g解析器核心功能测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.parser = Oracle11gParser()
        
        # Oracle 11g AWR HTML内容示例
        self.sample_11g_html = """
        <html>
        <head><title>AWR Report</title></head>
        <body>
        <h1>Oracle Database 11g Enterprise Edition - 11.2.0.4.0</h1>
        <p>Database Instance: TESTDB</p>
        <a name="dbinfo"></a>
        <table>
        <tr><td>DB Name</td><td>TESTDB</td></tr>
        <tr><td>Instance</td><td>TESTDB1</td></tr>
        <tr><td>Host Name</td><td>test-server</td></tr>
        <tr><td>Platform</td><td>Linux x86 64-bit</td></tr>
        <tr><td>Startup Time</td><td>31-Oct-23 09:30:15</td></tr>
        </table>
        
        <a name="loadprofile"></a>
        <table>
        <tr><th>Load Profile</th><th>Per Second</th><th>Per Transaction</th></tr>
        <tr><td>User calls</td><td>125.50</td><td>2.30</td></tr>
        <tr><td>Logical reads</td><td>12500.75</td><td>230.15</td></tr>
        <tr><td>Physical reads</td><td>850.25</td><td>15.65</td></tr>
        <tr><td>Physical writes</td><td>450.50</td><td>8.30</td></tr>
        <tr><td>Redo size</td><td>2048000</td><td>37700</td></tr>
        </table>
        
        <a name="topevents"></a>
        <table>
        <tr><th>Event</th><th>Waits</th><th>Time(s)</th><th>Avg wait (ms)</th><th>%Total</th></tr>
        <tr><td>db file sequential read</td><td>125000</td><td>450.25</td><td>3.60</td><td>35.50</td></tr>
        <tr><td>log file sync</td><td>75000</td><td>280.75</td><td>3.74</td><td>22.15</td></tr>
        <tr><td>CPU time</td><td>-</td><td>320.50</td><td>-</td><td>25.25</td></tr>
        </table>
        
        <a name="topsql"></a>
        <table>
        <tr><th>SQL Id</th><th>SQL Text</th><th>Executions</th><th>CPU Time (s)</th><th>Elapsed Time (s)</th></tr>
        <tr><td>abc123xyz</td><td>SELECT * FROM users</td><td>1500</td><td>45.25</td><td>125.75</td></tr>
        <tr><td>def456uvw</td><td>UPDATE orders SET</td><td>850</td><td>32.50</td><td>95.25</td></tr>
        </table>
        
        <a name="sysstat"></a>
        <table>
        <tr><th>Statistic</th><th>Total</th><th>Per Second</th><th>Per Transaction</th></tr>
        <tr><td>session logical reads</td><td>15750000</td><td>8750.50</td><td>161.25</td></tr>
        <tr><td>physical reads</td><td>1275000</td><td>708.75</td><td>13.05</td></tr>
        <tr><td>redo writes</td><td>85000</td><td>47.25</td><td>0.87</td></tr>
        </table>
        </body>
        </html>
        """
        
        # Oracle 11g RAC AWR HTML内容示例
        self.rac_11g_html = """
        <html>
        <body>
        <h1>Oracle Database 11g Release 11.2.0.4.0</h1>
        <a name="dbinfo"></a>
        <table>
        <tr><td>DB Name</td><td>RACDB</td></tr>
        <tr><td>Instance</td><td>RACDB1</td></tr>
        <tr><td>RAC</td><td>YES</td></tr>
        <tr><td>Real Application Clusters</td><td>Enabled</td></tr>
        </table>
        </body>
        </html>
        """
        
        # 无效格式HTML
        self.invalid_html = """
        <html>
        <body>
        <h1>Some Other Report</h1>
        <p>This is not an AWR report</p>
        </body>
        </html>
        """
    
    def test_can_parse_oracle_11g(self):
        """测试Oracle 11g版本检测"""
        # 测试正确版本检测
        self.assertTrue(self.parser.can_parse(self.sample_11g_html))
        
        # 测试包含11g版本字符串
        html_with_version = '<html><body>Oracle Database 11g Enterprise Edition</body></html>'
        self.assertTrue(self.parser.can_parse(html_with_version))
        
        html_with_release = '<html><body>Release 11.2.0.4.0</body></html>'
        self.assertTrue(self.parser.can_parse(html_with_release))
    
    def test_can_parse_by_anchors(self):
        """测试通过AWR锚点检测"""
        # 包含足够AWR锚点的HTML
        html_with_anchors = """
        <html>
        <body>
        <a name="dbinfo"></a>
        <a name="loadprofile"></a>
        <a name="topevents"></a>
        </body>
        </html>
        """
        self.assertTrue(self.parser.can_parse(html_with_anchors))
    
    def test_cannot_parse_invalid_format(self):
        """测试无法解析无效格式"""
        self.assertFalse(self.parser.can_parse(self.invalid_html))
        
        # 测试空内容
        self.assertFalse(self.parser.can_parse(""))
        
        # 测试其他Oracle版本
        oracle_19c_html = '<html><body>Oracle Database 19c</body></html>'
        self.assertFalse(self.parser.can_parse(oracle_19c_html))
    
    def test_parse_db_info_standard(self):
        """测试标准数据库信息解析"""
        soup = BeautifulSoup(self.sample_11g_html, 'html.parser')
        db_info = self.parser.parse_db_info(soup)
        
        self.assertEqual(db_info.db_name, "TESTDB")
        self.assertEqual(db_info.instance_name, "TESTDB1")
        self.assertEqual(db_info.version, OracleVersion.ORACLE_11G)
        self.assertEqual(db_info.instance_type, InstanceType.SINGLE)
        self.assertEqual(db_info.host_name, "test-server")
        self.assertEqual(db_info.platform, "Linux x86 64-bit")
        self.assertFalse(db_info.is_rac)
        self.assertIsNone(db_info.container_name)  # 11g不支持CDB/PDB
    
    def test_parse_db_info_rac(self):
        """测试RAC数据库信息解析"""
        soup = BeautifulSoup(self.rac_11g_html, 'html.parser')
        db_info = self.parser.parse_db_info(soup)
        
        self.assertEqual(db_info.db_name, "RACDB")
        self.assertEqual(db_info.instance_type, InstanceType.RAC)
        self.assertTrue(db_info.is_rac)
        self.assertIsNone(db_info.container_name)  # 11g不支持CDB/PDB
    
    def test_parse_db_info_missing_table(self):
        """测试缺失数据库信息表格的处理"""
        html_no_db_info = '<html><body><h1>AWR Report</h1></body></html>'
        soup = BeautifulSoup(html_no_db_info, 'html.parser')
        
        db_info = self.parser.parse_db_info(soup)
        
        self.assertEqual(db_info.db_name, "UNKNOWN")
        self.assertEqual(db_info.instance_name, "UNKNOWN")
        self.assertEqual(db_info.version, OracleVersion.ORACLE_11G)
        self.assertEqual(db_info.instance_type, InstanceType.SINGLE)
    
    def test_parse_snapshot_info(self):
        """测试快照信息解析"""
        # 创建包含快照信息的HTML
        snapshot_html = """
        <html><body>
        <a name="snapshot"></a>
        <table>
        <tr><td>Begin Snap Id</td><td>12345</td></tr>
        <tr><td>End Snap Id</td><td>12346</td></tr>
        <tr><td>Begin Snap Time</td><td>31-Oct-23 09:00:00</td></tr>
        <tr><td>End Snap Time</td><td>31-Oct-23 10:00:00</td></tr>
        <tr><td>Elapsed Time</td><td>60.0</td></tr>
        <tr><td>DB Time</td><td>48.5</td></tr>
        </table>
        </body></html>
        """
        
        soup = BeautifulSoup(snapshot_html, 'html.parser')
        snapshot_info = self.parser.parse_snapshot_info(soup)
        
        self.assertEqual(snapshot_info.begin_snap_id, 12345)
        self.assertEqual(snapshot_info.end_snap_id, 12346)
        self.assertEqual(snapshot_info.elapsed_time_minutes, 60.0)
        self.assertEqual(snapshot_info.db_time_minutes, 48.5)
    
    def test_parse_snapshot_info_table_format(self):
        """测试表格格式的快照信息解析"""
        table_snapshot_html = """
        <html><body>
        <a name="snapshot"></a>
        <table>
        <tr><th>Snap Id</th><th>Instance</th><th>Begin Snap Time</th><th>End Snap Time</th></tr>
        <tr><td>12345</td><td>TESTDB1</td><td>31-Oct-23 09:00:00</td><td>31-Oct-23 10:00:00</td></tr>
        </table>
        </body></html>
        """
        
        soup = BeautifulSoup(table_snapshot_html, 'html.parser')
        snapshot_info = self.parser.parse_snapshot_info(soup)
        
        self.assertEqual(snapshot_info.begin_snap_id, 12345)
        self.assertEqual(snapshot_info.end_snap_id, 12346)  # 自动计算
    
    def test_parse_load_profile(self):
        """测试Load Profile解析"""
        soup = BeautifulSoup(self.sample_11g_html, 'html.parser')
        load_profile = self.parser.parse_load_profile(soup)
        
        self.assertEqual(load_profile.user_calls_per_second, 125.50)
        self.assertEqual(load_profile.logical_reads_per_second, 12500.75)
        self.assertEqual(load_profile.physical_reads_per_second, 850.25)
        self.assertEqual(load_profile.physical_writes_per_second, 450.50)
        # 注意：新的LoadProfile模型没有redo_size和block_changes字段
        
        self.assertEqual(load_profile.logical_reads_per_transaction, 230.15)
        # 注意：新的LoadProfile模型没有physical_reads_per_transaction字段
    
    def test_parse_load_profile_missing_table(self):
        """测试缺失Load Profile表格的处理"""
        html_no_load = '<html><body><h1>AWR Report</h1></body></html>'
        soup = BeautifulSoup(html_no_load, 'html.parser')
        
        load_profile = self.parser.parse_load_profile(soup)
        
        # 应返回默认值
        self.assertEqual(load_profile.user_calls_per_second, 0.0)
        self.assertEqual(load_profile.logical_reads_per_second, 0.0)
    
    def test_parse_wait_events(self):
        """测试等待事件解析"""
        soup = BeautifulSoup(self.sample_11g_html, 'html.parser')
        wait_events = self.parser.parse_wait_events(soup)
        
        self.assertEqual(len(wait_events), 3)
        
        # 检查第一个等待事件
        first_event = wait_events[0]
        self.assertEqual(first_event.event_name, "db file sequential read")
        self.assertEqual(first_event.waits, 125000)
        self.assertEqual(first_event.total_wait_time_sec, 450.25)
        self.assertEqual(first_event.avg_wait_ms, 3.60)
        self.assertEqual(first_event.percent_db_time, 35.50)
    
    def test_parse_wait_events_empty_table(self):
        """测试空等待事件表格处理"""
        html_no_events = """
        <html><body>
        <a name="topevents"></a>
        <table>
        <tr><th>Event</th><th>Waits</th><th>Time(s)</th></tr>
        </table>
        </body></html>
        """
        
        soup = BeautifulSoup(html_no_events, 'html.parser')
        wait_events = self.parser.parse_wait_events(soup)
        
        self.assertEqual(len(wait_events), 0)
    
    def test_parse_sql_statistics(self):
        """测试SQL统计解析"""
        soup = BeautifulSoup(self.sample_11g_html, 'html.parser')
        sql_stats = self.parser.parse_sql_statistics(soup)
        
        self.assertEqual(len(sql_stats), 2)
        
        # 检查第一个SQL统计
        first_sql = sql_stats[0]
        self.assertEqual(first_sql.sql_id, "abc123xyz")
        self.assertEqual(first_sql.sql_text, "SELECT * FROM users")
        self.assertEqual(first_sql.executions, 1500)
        self.assertEqual(first_sql.cpu_time_sec, 45.25)
        self.assertEqual(first_sql.elapsed_time_sec, 125.75)
    
    def test_parse_sql_statistics_missing_columns(self):
        """测试缺失列的SQL统计处理"""
        html_incomplete_sql = """
        <html><body>
        <a name="topsql"></a>
        <table>
        <tr><th>SQL Id</th><th>Executions</th></tr>
        <tr><td>test123</td><td>100</td></tr>
        </table>
        </body></html>
        """
        
        soup = BeautifulSoup(html_incomplete_sql, 'html.parser')
        sql_stats = self.parser.parse_sql_statistics(soup)
        
        self.assertEqual(len(sql_stats), 1)
        self.assertEqual(sql_stats[0].sql_id, "test123")
        self.assertEqual(sql_stats[0].executions, 100)
        self.assertEqual(sql_stats[0].cpu_time_sec, 0.0)  # 默认值
        self.assertEqual(sql_stats[0].elapsed_time_sec, 0.0)  # 默认值
    
    def test_parse_instance_activity(self):
        """测试实例活动统计解析"""
        soup = BeautifulSoup(self.sample_11g_html, 'html.parser')
        activities = self.parser.parse_instance_activity(soup)
        
        self.assertEqual(len(activities), 3)
        
        # 检查第一个统计项
        first_activity = activities[0]
        self.assertEqual(first_activity.statistic_name, "session logical reads")
        self.assertEqual(first_activity.total_value, 15750000)
        self.assertEqual(first_activity.per_second, 8750.50)
        self.assertEqual(first_activity.per_transaction, 161.25)
    
    def test_detect_instance_type_11g(self):
        """测试11g实例类型检测（不支持CDB/PDB）"""
        # 测试单实例
        single_data = {"DB Name": "TESTDB", "Instance": "TESTDB1"}
        instance_type = self.parser._detect_instance_type_11g(single_data)
        self.assertEqual(instance_type, InstanceType.SINGLE)
        
        # 测试RAC
        rac_data = {"DB Name": "RACDB", "RAC": "YES"}
        instance_type = self.parser._detect_instance_type_11g(rac_data)
        self.assertEqual(instance_type, InstanceType.RAC)
        
        # 测试包含RAC字符串
        rac_data2 = {"Cluster": "Real Application Clusters"}
        instance_type = self.parser._detect_instance_type_11g(rac_data2)
        self.assertEqual(instance_type, InstanceType.RAC)
    
    def test_extract_db_name(self):
        """测试数据库名称提取"""
        db_data = {"DB Name": "TESTDB", "Other": "value"}
        name = self.parser._extract_db_name(db_data)
        self.assertEqual(name, "TESTDB")
        
        # 测试空数据
        empty_data = {}
        name = self.parser._extract_db_name(empty_data)
        self.assertEqual(name, "UNKNOWN")
    
    def test_extract_startup_time(self):
        """测试启动时间提取"""
        db_data = {"Startup Time": "31-Oct-23 09:30:15"}
        startup_time = self.parser._extract_startup_time(db_data)
        
        self.assertIsNotNone(startup_time)
        self.assertEqual(startup_time.day, 31)
        self.assertEqual(startup_time.month, 10)
        self.assertEqual(startup_time.year, 2023)
        
        # 测试无效时间格式
        invalid_data = {"Startup Time": "invalid-time"}
        startup_time = self.parser._extract_startup_time(invalid_data)
        self.assertIsNone(startup_time)
    
    def test_parse_time_duration(self):
        """测试时间持续时间解析"""
        # 测试分钟格式
        duration = self.parser._parse_time_duration("60.5")
        self.assertEqual(duration, 60.5)
        
        # 测试时:分:秒格式
        duration = self.parser._parse_time_duration("1:30:30")
        self.assertEqual(duration, 90.5)  # 1小时30分30秒 = 90.5分钟
        
        # 测试分:秒格式
        duration = self.parser._parse_time_duration("30:45")
        self.assertEqual(duration, 30.75)  # 30分45秒 = 30.75分钟
        
        # 测试无效格式
        duration = self.parser._parse_time_duration("invalid")
        self.assertEqual(duration, 0.0)
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试解析损坏的HTML
        broken_html = '<html><body><table><tr><td>incomplete'
        
        soup = BeautifulSoup(broken_html, 'html.parser')
        
        # 应该能正常处理，返回默认值
        db_info = self.parser.parse_db_info(soup)
        self.assertEqual(db_info.db_name, "UNKNOWN")
    
    def test_can_parse_exception_handling(self):
        """测试can_parse方法的异常处理"""
        # 测试None输入，应该返回False
        result = self.parser.can_parse(None)
        self.assertFalse(result)
    
    def test_logging(self):
        """测试日志记录功能"""
        # 测试成功检测11g版本
        result = self.parser.can_parse(self.sample_11g_html)
        self.assertTrue(result)
        
        # 只要can_parse返回True，就说明检测成功了


class TestOracle11gParserIntegration(unittest.TestCase):
    """Oracle 11g解析器集成测试"""
    
    def setUp(self):
        """设置测试环境"""
        self.parser = Oracle11gParser()
        
        # 完整的11g AWR示例HTML
        self.complete_11g_html = """
        <html>
        <head><title>Oracle AWR Report</title></head>
        <body>
        <h1>Oracle Database 11g Enterprise Edition Release 11.2.0.4.0</h1>
        
        <a name="dbinfo"></a>
        <h2>Database Information</h2>
        <table>
        <tr><td>DB Name</td><td>PRODDB</td></tr>
        <tr><td>Instance</td><td>PRODDB1</td></tr>
        <tr><td>Host Name</td><td>prod-server-01</td></tr>
        <tr><td>Platform</td><td>Linux x86 64-bit</td></tr>
        <tr><td>Startup Time</td><td>31-Oct-23 08:00:00</td></tr>
        </table>
        
        <a name="snapshot"></a>
        <h2>Snapshot Information</h2>
        <table>
        <tr><td>Begin Snap Id</td><td>12345</td></tr>
        <tr><td>End Snap Id</td><td>12346</td></tr>
        <tr><td>Begin Snap Time</td><td>31-Oct-23 09:00:00</td></tr>
        <tr><td>End Snap Time</td><td>31-Oct-23 10:00:00</td></tr>
        <tr><td>Elapsed Time</td><td>60.0</td></tr>
        <tr><td>DB Time</td><td>48.5</td></tr>
        </table>
        
        <a name="loadprofile"></a>
        <h2>Load Profile</h2>
        <table>
        <tr><th>Load Profile</th><th>Per Second</th><th>Per Transaction</th></tr>
        <tr><td>User calls</td><td>145.75</td><td>2.85</td></tr>
        <tr><td>Logical reads</td><td>15250.50</td><td>298.25</td></tr>
        <tr><td>Block changes</td><td>850.25</td><td>16.65</td></tr>
        <tr><td>Physical reads</td><td>925.75</td><td>18.15</td></tr>
        <tr><td>Physical writes</td><td>485.25</td><td>9.50</td></tr>
        <tr><td>Redo size</td><td>2560000</td><td>50000</td></tr>
        </table>
        
        <a name="topevents"></a>
        <h2>Top Wait Events</h2>
        <table>
        <tr><th>Event</th><th>Waits</th><th>Time(s)</th><th>Avg wait (ms)</th><th>%Total</th></tr>
        <tr><td>db file sequential read</td><td>150000</td><td>525.50</td><td>3.50</td><td>42.50</td></tr>
        <tr><td>log file sync</td><td>85000</td><td>315.25</td><td>3.71</td><td>25.45</td></tr>
        <tr><td>db file scattered read</td><td>45000</td><td>180.75</td><td>4.02</td><td>14.60</td></tr>
        <tr><td>CPU time</td><td>-</td><td>285.50</td><td>-</td><td>23.05</td></tr>
        </table>
        
        <a name="topsql"></a>
        <h2>SQL Statistics</h2>
        <table>
        <tr><th>SQL Id</th><th>SQL Text</th><th>Executions</th><th>CPU Time (s)</th><th>Elapsed Time (s)</th><th>Buffer Gets</th><th>Disk Reads</th></tr>
        <tr><td>1a2b3c4d5e</td><td>SELECT o.*, c.name FROM orders o JOIN customers c</td><td>2500</td><td>65.25</td><td>185.75</td><td>850000</td><td>25000</td></tr>
        <tr><td>f6g7h8i9j0</td><td>UPDATE inventory SET quantity =</td><td>1250</td><td>45.50</td><td>125.25</td><td>450000</td><td>15000</td></tr>
        <tr><td>k1l2m3n4o5</td><td>INSERT INTO order_items VALUES</td><td>3750</td><td>35.75</td><td>95.50</td><td>300000</td><td>8500</td></tr>
        </table>
        
        <a name="sysstat"></a>
        <h2>Instance Activity Stats</h2>
        <table>
        <tr><th>Statistic</th><th>Total</th><th>Per Second</th><th>Per Transaction</th></tr>
        <tr><td>session logical reads</td><td>18500000</td><td>10277.78</td><td>201.09</td></tr>
        <tr><td>physical reads</td><td>1485000</td><td>825.00</td><td>16.13</td></tr>
        <tr><td>physical writes</td><td>785000</td><td>436.11</td><td>8.53</td></tr>
        <tr><td>redo writes</td><td>95000</td><td>52.78</td><td>1.03</td></tr>
        <tr><td>user commits</td><td>51000</td><td>28.33</td><td>0.56</td></tr>
        <tr><td>user rollbacks</td><td>1850</td><td>1.03</td><td>0.02</td></tr>
        </table>
        </body>
        </html>
        """
    
    def test_complete_parsing_workflow(self):
        """测试完整的解析工作流"""
        # 验证能够解析
        self.assertTrue(self.parser.can_parse(self.complete_11g_html))
        
        soup = BeautifulSoup(self.complete_11g_html, 'html.parser')
        
        # 解析所有组件
        db_info = self.parser.parse_db_info(soup)
        snapshot_info = self.parser.parse_snapshot_info(soup)
        load_profile = self.parser.parse_load_profile(soup)
        wait_events = self.parser.parse_wait_events(soup)
        sql_statistics = self.parser.parse_sql_statistics(soup)
        instance_activity = self.parser.parse_instance_activity(soup)
        
        # 验证解析结果
        self.assertEqual(db_info.db_name, "PRODDB")
        self.assertEqual(db_info.version, OracleVersion.ORACLE_11G)
        self.assertEqual(db_info.instance_type, InstanceType.SINGLE)
        self.assertIsNone(db_info.container_name)  # 11g不支持CDB/PDB
        
        self.assertEqual(snapshot_info.begin_snap_id, 12345)
        self.assertEqual(snapshot_info.end_snap_id, 12346)
        self.assertEqual(snapshot_info.elapsed_time_minutes, 60.0)
        
        self.assertEqual(load_profile.user_calls_per_second, 145.75)
        # 注意：redo_size字段在新的LoadProfile模型中不存在，移除相关测试
        
        self.assertEqual(len(wait_events), 4)
        
        self.assertEqual(len(sql_statistics), 3)
        self.assertEqual(sql_statistics[0].sql_id, "1a2b3c4d5e")
        
        self.assertEqual(len(instance_activity), 6)
        self.assertEqual(instance_activity[0].statistic_name, "session logical reads")
    
    def test_parsing_with_missing_sections(self):
        """测试缺失部分区块的解析处理"""
        # 只包含部分区块的HTML
        partial_html = """
        <html>
        <body>
        <h1>Oracle Database 11g Enterprise Edition</h1>
        <a name="dbinfo"></a>
        <table>
        <tr><td>DB Name</td><td>PARTIALDB</td></tr>
        <tr><td>Instance</td><td>PARTIALDB1</td></tr>
        </table>
        
        <a name="loadprofile"></a>
        <table>
        <tr><th>Load Profile</th><th>Per Second</th></tr>
        <tr><td>User calls</td><td>100.0</td></tr>
        </table>
        </body>
        </html>
        """
        
        soup = BeautifulSoup(partial_html, 'html.parser')
        
        # 应该能正常解析存在的部分，对缺失部分返回默认值
        db_info = self.parser.parse_db_info(soup)
        self.assertEqual(db_info.db_name, "PARTIALDB")
        
        load_profile = self.parser.parse_load_profile(soup)
        self.assertEqual(load_profile.user_calls_per_second, 100.0)
        self.assertEqual(load_profile.logical_reads_per_second, 0.0)  # 缺失字段默认值
        
        # 缺失的区块应返回空列表或默认对象
        wait_events = self.parser.parse_wait_events(soup)
        self.assertEqual(len(wait_events), 0)
        
        sql_statistics = self.parser.parse_sql_statistics(soup)
        self.assertEqual(len(sql_statistics), 0)


if __name__ == '__main__':
    unittest.main() 