"""
Oracle 19c解析器单元测试
{{CHENGQI: P2-LD-003 Oracle 19c解析器实现 - 2025-06-02 11:25:00 +08:00}}

测试Oracle19cParser的功能完整性和正确性
确保各个解析方法的稳定性和容错性
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime
from bs4 import BeautifulSoup

from apps.awr_parser.parsers.oracle_19c import Oracle19cParser
from apps.awr_parser.parsers.base import (
    DBInfo, SnapshotInfo, LoadProfile, WaitEvent, 
    SQLStatistic, InstanceActivity, OracleVersion, InstanceType
)


class TestOracle19cParser(unittest.TestCase):
    """Oracle 19c解析器测试类"""
    
    def setUp(self):
        """测试用例初始化"""
        self.parser = Oracle19cParser()
        
        # 创建标准Oracle 19c AWR HTML
        self.oracle_19c_html = """
        <html>
        <head>
            <title>Oracle Database 19c AWR Report</title>
        </head>
        <body>
            <h1>WORKLOAD REPOSITORY report for Oracle Database 19c</h1>
            <p>Release 19.3.0.0.0 - Production on Mon Jun 02 11:25:00 2025</p>
            
            <a name="dbinfo">Database Information</a>
            <table>
                <tr><td>DB Name</td><td>TESTDB</td></tr>
                <tr><td>Instance</td><td>testdb1</td></tr>
                <tr><td>Host Name</td><td>server01</td></tr>
                <tr><td>Platform</td><td>Linux x86 64-bit</td></tr>
                <tr><td>Startup Time</td><td>01-Jun-25 10:00:00</td></tr>
            </table>
            
            <a name="loadprofile">Load Profile</a>
            <table>
                <tr><th>Metric</th><th>Per Second</th><th>Per Transaction</th></tr>
                <tr><td>DB Time(s)</td><td>1.23</td><td>0.56</td></tr>
                <tr><td>Logical reads</td><td>12345</td><td>5678</td></tr>
                <tr><td>Physical reads</td><td>234</td><td>123</td></tr>
                <tr><td>Physical writes</td><td>45</td><td>23</td></tr>
                <tr><td>User calls</td><td>567</td><td>234</td></tr>
                <tr><td>Parses</td><td>123</td><td>56</td></tr>
                <tr><td>Hard parses</td><td>12</td><td>5</td></tr>
                <tr><td>Sorts</td><td>78</td><td>34</td></tr>
                <tr><td>Logons</td><td>2</td><td>1</td></tr>
                <tr><td>Executes</td><td>890</td><td>456</td></tr>
                <tr><td>Rollbacks</td><td>1</td><td>0</td></tr>
                <tr><td>Transactions</td><td>2.3</td><td>1.0</td></tr>
            </table>
            
            <a name="topevents">Top 5 Timed Events</a>
            <table>
                <tr><th>Event</th><th>Waits</th><th>Total Wait Time (sec)</th><th>% DB Time</th><th>Wait Class</th></tr>
                <tr><td>db file sequential read</td><td>1234</td><td>56.78</td><td>45.2%</td><td>User I/O</td></tr>
                <tr><td>log file sync</td><td>567</td><td>23.45</td><td>18.7%</td><td>Commit</td></tr>
                <tr><td>db file scattered read</td><td>234</td><td>12.34</td><td>9.8%</td><td>User I/O</td></tr>
            </table>
            
            <a name="topsql">SQL ordered by Elapsed Time</a>
            <table>
                <tr><th>SQL ID</th><th>Executions</th><th>Elapsed Time (s)</th><th>CPU Time (s)</th><th>Buffer Gets</th><th>Disk Reads</th></tr>
                <tr><td>abc123def456</td><td>100</td><td>120.5</td><td>80.3</td><td>50000</td><td>1000</td></tr>
                <tr><td>def456ghi789</td><td>50</td><td>60.2</td><td>40.1</td><td>25000</td><td>500</td></tr>
            </table>
            
            <a name="sysstat">Instance Activity Statistics</a>
            <table>
                <tr><th>Statistic Name</th><th>Total</th><th>Per Second</th><th>Per Transaction</th></tr>
                <tr><td>user commits</td><td>12345</td><td>2.3</td><td>1.0</td></tr>
                <tr><td>user rollbacks</td><td>123</td><td>0.02</td><td>0.01</td></tr>
                <tr><td>session logical reads</td><td>1234567</td><td>234.5</td><td>123.4</td></tr>
            </table>
        </body>
        </html>
        """
        
        # 创建RAC格式的HTML
        self.rac_html = """
        <html>
        <body>
            <h1>Oracle Database 19c RAC AWR Report</h1>
            <a name="dbinfo">Database Information</a>
            <table>
                <tr><td>DB Name</td><td>RACDB</td></tr>
                <tr><td>Instance</td><td>racdb1</td></tr>
                <tr><td>Instance Number</td><td>1</td></tr>
                <tr><td>Cluster</td><td>YES</td></tr>
                <tr><td>Host Name</td><td>node1</td></tr>
            </table>
        </body>
        </html>
        """
        
        # 创建CDB/PDB格式的HTML
        self.cdb_html = """
        <html>
        <body>
            <h1>Oracle Database 19c CDB AWR Report</h1>
            <a name="dbinfo">Database Information</a>
            <table>
                <tr><td>DB Name</td><td>CDB1</td></tr>
                <tr><td>Container Name</td><td>CDB$ROOT</td></tr>
                <tr><td>Instance</td><td>cdb1</td></tr>
            </table>
        </body>
        </html>
        """
    
    def test_can_parse_oracle_19c(self):
        """测试Oracle 19c格式识别"""
        # 测试正确识别Oracle 19c
        self.assertTrue(self.parser.can_parse(self.oracle_19c_html))
        
        # 测试不同的版本标识
        version_variants = [
            '<p>Oracle Database 19c Enterprise Edition</p>',
            '<p>Release 19.8.0.0.0</p>',
            '<p>version="19.3.0.0.0"</p>',
            '<p>19.15.0.0.0 - Production</p>'
        ]
        
        for variant in version_variants:
            html = f"<html><body>{variant}</body></html>"
            self.assertTrue(self.parser.can_parse(html), f"Should recognize: {variant}")
    
    def test_can_parse_by_anchors(self):
        """测试通过锚点识别AWR格式"""
        html_with_anchors = """
        <html>
        <body>
            <a name="dbinfo">DB Info</a>
            <a name="loadprofile">Load Profile</a>
            <a name="topevents">Top Events</a>
        </body>
        </html>
        """
        
        self.assertTrue(self.parser.can_parse(html_with_anchors))
    
    def test_cannot_parse_invalid_format(self):
        """测试拒绝无效格式"""
        invalid_html = [
            "<html><body>Not an AWR report</body></html>",
            "<html><body>Oracle Database 11g</body></html>",
            "<html><body>Oracle Database 12c</body></html>",
            ""
        ]
        
        for html in invalid_html:
            self.assertFalse(self.parser.can_parse(html))
    
    def test_parse_db_info_standard(self):
        """测试解析标准数据库信息"""
        soup = BeautifulSoup(self.oracle_19c_html, 'html.parser')
        db_info = self.parser.parse_db_info(soup)
        
        self.assertIsInstance(db_info, DBInfo)
        self.assertEqual(db_info.db_name, "TESTDB")
        self.assertEqual(db_info.instance_name, "testdb1")
        self.assertEqual(db_info.version, OracleVersion.ORACLE_19C)
        self.assertEqual(db_info.host_name, "server01")
        self.assertEqual(db_info.platform, "Linux x86 64-bit")
        self.assertEqual(db_info.instance_type, InstanceType.SINGLE)
        self.assertFalse(db_info.is_rac)
        self.assertIsNone(db_info.container_name)
    
    def test_parse_db_info_rac(self):
        """测试解析RAC数据库信息"""
        soup = BeautifulSoup(self.rac_html, 'html.parser')
        db_info = self.parser.parse_db_info(soup)
        
        self.assertEqual(db_info.db_name, "RACDB")
        self.assertEqual(db_info.instance_name, "racdb1")
        self.assertEqual(db_info.instance_type, InstanceType.RAC)
        self.assertTrue(db_info.is_rac)
    
    def test_parse_db_info_cdb(self):
        """测试解析CDB数据库信息"""
        soup = BeautifulSoup(self.cdb_html, 'html.parser')
        db_info = self.parser.parse_db_info(soup)
        
        self.assertEqual(db_info.db_name, "CDB1")
        self.assertEqual(db_info.instance_type, InstanceType.CDB)
        self.assertEqual(db_info.container_name, "CDB$ROOT")
    
    def test_parse_db_info_missing_table(self):
        """测试数据库信息表格缺失的情况"""
        html = "<html><body><p>No database info table</p></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        db_info = self.parser.parse_db_info(soup)
        
        self.assertEqual(db_info.db_name, "UNKNOWN")
        self.assertEqual(db_info.instance_name, "UNKNOWN")
        self.assertEqual(db_info.instance_type, InstanceType.SINGLE)
    
    def test_parse_snapshot_info(self):
        """测试解析快照信息"""
        # 创建包含快照信息的HTML
        snapshot_html = """
        <html>
        <body>
            <table>
                <tr><td>Begin Snap</td><td>123</td></tr>
                <tr><td>End Snap</td><td>124</td></tr>
                <tr><td>Elapsed Time</td><td>60.5 mins</td></tr>
                <tr><td>DB Time</td><td>45.2 mins</td></tr>
            </table>
        </body>
        </html>
        """
        
        soup = BeautifulSoup(snapshot_html, 'html.parser')
        snapshot_info = self.parser.parse_snapshot_info(soup)
        
        self.assertIsInstance(snapshot_info, SnapshotInfo)
        self.assertEqual(snapshot_info.begin_snap_id, 123)
        self.assertEqual(snapshot_info.end_snap_id, 124)
        self.assertEqual(snapshot_info.elapsed_time_minutes, 60.5)
        self.assertEqual(snapshot_info.db_time_minutes, 45.2)
    
    def test_parse_snapshot_info_table_format(self):
        """测试解析表格格式的快照信息"""
        table_html = """
        <html>
        <body>
            <table>
                <tr><th>Snap ID</th><th>Instance</th><th>Startup Time</th></tr>
                <tr><td>123</td><td>1</td><td>01-Jun-25 10:00:00</td></tr>
                <tr><td>124</td><td>1</td><td>01-Jun-25 10:00:00</td></tr>
            </table>
        </body>
        </html>
        """
        
        soup = BeautifulSoup(table_html, 'html.parser')
        snapshot_info = self.parser.parse_snapshot_info(soup)
        
        self.assertEqual(snapshot_info.begin_snap_id, 123)
        self.assertEqual(snapshot_info.end_snap_id, 124)
    
    def test_parse_load_profile(self):
        """测试解析负载概要"""
        soup = BeautifulSoup(self.oracle_19c_html, 'html.parser')
        load_profile = self.parser.parse_load_profile(soup)
        
        self.assertIsInstance(load_profile, LoadProfile)
        self.assertEqual(load_profile.db_time_per_second, 1.23)
        self.assertEqual(load_profile.db_time_per_transaction, 0.56)
        self.assertEqual(load_profile.logical_reads_per_second, 12345.0)
        self.assertEqual(load_profile.logical_reads_per_transaction, 5678.0)
        self.assertEqual(load_profile.physical_reads_per_second, 234.0)
        self.assertEqual(load_profile.physical_writes_per_second, 45.0)
        self.assertEqual(load_profile.user_calls_per_second, 567.0)
        self.assertEqual(load_profile.parses_per_second, 123.0)
        self.assertEqual(load_profile.hard_parses_per_second, 12.0)
        self.assertEqual(load_profile.sorts_per_second, 78.0)
        self.assertEqual(load_profile.logons_per_second, 2.0)
        self.assertEqual(load_profile.executes_per_second, 890.0)
        self.assertEqual(load_profile.rollbacks_per_second, 1.0)
        self.assertEqual(load_profile.transactions_per_second, 2.3)
    
    def test_parse_load_profile_missing_table(self):
        """测试负载概要表格缺失的情况"""
        html = "<html><body><p>No load profile</p></body></html>"
        soup = BeautifulSoup(html, 'html.parser')
        load_profile = self.parser.parse_load_profile(soup)
        
        # 应该返回默认值
        self.assertEqual(load_profile.db_time_per_second, 0.0)
        self.assertEqual(load_profile.logical_reads_per_second, 0.0)
    
    def test_parse_wait_events(self):
        """测试解析等待事件"""
        soup = BeautifulSoup(self.oracle_19c_html, 'html.parser')
        wait_events = self.parser.parse_wait_events(soup)
        
        self.assertIsInstance(wait_events, list)
        self.assertEqual(len(wait_events), 3)
        
        # 验证第一个等待事件
        first_event = wait_events[0]
        self.assertIsInstance(first_event, WaitEvent)
        self.assertEqual(first_event.event_name, "db file sequential read")
        self.assertEqual(first_event.waits, 1234)
        self.assertEqual(first_event.total_wait_time_sec, 56.78)
        self.assertEqual(first_event.percent_db_time, 45.2)
        self.assertEqual(first_event.wait_class, "User I/O")
        
        # 验证平均等待时间计算
        expected_avg_wait = (56.78 * 1000) / 1234
        self.assertAlmostEqual(first_event.avg_wait_ms, expected_avg_wait, places=2)
    
    def test_parse_wait_events_empty_table(self):
        """测试等待事件表格为空的情况"""
        html = """
        <html>
        <body>
            <a name="topevents">Top Events</a>
            <table>
                <tr><th>Event</th><th>Waits</th></tr>
            </table>
        </body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        wait_events = self.parser.parse_wait_events(soup)
        
        self.assertEqual(len(wait_events), 0)
    
    def test_parse_sql_statistics(self):
        """测试解析SQL统计"""
        soup = BeautifulSoup(self.oracle_19c_html, 'html.parser')
        sql_statistics = self.parser.parse_sql_statistics(soup)
        
        self.assertIsInstance(sql_statistics, list)
        self.assertEqual(len(sql_statistics), 2)
        
        # 验证第一个SQL统计
        first_sql = sql_statistics[0]
        self.assertIsInstance(first_sql, SQLStatistic)
        self.assertEqual(first_sql.sql_id, "abc123def456")
        self.assertEqual(first_sql.executions, 100)
        self.assertEqual(first_sql.elapsed_time_sec, 120.5)
        self.assertEqual(first_sql.cpu_time_sec, 80.3)
        self.assertEqual(first_sql.gets, 50000)
        self.assertEqual(first_sql.reads, 1000)
        
        # 验证IO时间计算
        expected_io_time = 120.5 - 80.3
        self.assertAlmostEqual(first_sql.io_time_sec, expected_io_time, places=2)
    
    def test_parse_sql_statistics_missing_columns(self):
        """测试SQL统计表格缺少列的情况"""
        html = """
        <html>
        <body>
            <a name="topsql">Top SQL</a>
            <table>
                <tr><th>SQL ID</th><th>Executions</th></tr>
                <tr><td>abc123</td><td>100</td></tr>
            </table>
        </body>
        </html>
        """
        
        soup = BeautifulSoup(html, 'html.parser')
        sql_statistics = self.parser.parse_sql_statistics(soup)
        
        self.assertEqual(len(sql_statistics), 1)
        sql_stat = sql_statistics[0]
        self.assertEqual(sql_stat.sql_id, "abc123")
        self.assertEqual(sql_stat.executions, 100)
        self.assertEqual(sql_stat.elapsed_time_sec, 0.0)  # 默认值
    
    def test_parse_instance_activity(self):
        """测试解析实例活动统计"""
        soup = BeautifulSoup(self.oracle_19c_html, 'html.parser')
        activities = self.parser.parse_instance_activity(soup)
        
        self.assertIsInstance(activities, list)
        self.assertEqual(len(activities), 3)
        
        # 验证第一个活动统计
        first_activity = activities[0]
        self.assertIsInstance(first_activity, InstanceActivity)
        self.assertEqual(first_activity.statistic_name, "user commits")
        self.assertEqual(first_activity.total_value, 12345)
        self.assertEqual(first_activity.per_second, 2.3)
        self.assertEqual(first_activity.per_transaction, 1.0)
    
    def test_parse_time_duration(self):
        """测试时间duration解析"""
        # 测试各种时间格式
        test_cases = [
            ("60.5 mins", 60.5),
            ("1.5 hrs", 90.0),  # 1.5小时 = 90分钟
            ("3600 secs", 60.0),  # 3600秒 = 60分钟
            ("120", 120.0),  # 纯数字假设为分钟
            ("", 0.0),  # 空字符串
            ("invalid", 0.0)  # 无效格式
        ]
        
        for time_str, expected_minutes in test_cases:
            result = self.parser._parse_time_duration(time_str)
            self.assertAlmostEqual(result, expected_minutes, places=1, 
                                 msg=f"Failed for input: {time_str}")
    
    def test_detect_instance_type(self):
        """测试实例类型检测"""
        # 测试RAC检测
        rac_data = {"Instance Number": "1", "Cluster": "YES"}
        self.assertEqual(self.parser._detect_instance_type(rac_data), InstanceType.RAC)
        
        # 测试CDB检测
        cdb_data = {"Container Name": "CDB$ROOT"}
        self.assertEqual(self.parser._detect_instance_type(cdb_data), InstanceType.CDB)
        
        # 测试PDB检测
        pdb_data = {"Container Name": "PDB1"}
        self.assertEqual(self.parser._detect_instance_type(pdb_data), InstanceType.PDB)
        
        # 测试单实例
        single_data = {"DB Name": "TESTDB"}
        self.assertEqual(self.parser._detect_instance_type(single_data), InstanceType.SINGLE)
    
    def test_extract_db_name(self):
        """测试数据库名提取"""
        test_cases = [
            ({"DB Name": "TESTDB"}, "TESTDB"),
            ({"Database Name": "PRODDB"}, "PRODDB"), 
            ({"DB_NAME": "DEVDB"}, "DEVDB"),
            ({"Name": "STAGEDB"}, "STAGEDB"),
            ({}, "UNKNOWN")  # 没有匹配的键
        ]
        
        for db_data, expected in test_cases:
            result = self.parser._extract_db_name(db_data)
            self.assertEqual(result, expected)
    
    def test_extract_startup_time(self):
        """测试启动时间提取"""
        # 测试有效时间格式
        db_data = {"Startup Time": "01-Jun-25 10:30:45"}
        startup_time = self.parser._extract_startup_time(db_data)
        
        self.assertIsInstance(startup_time, datetime)
        self.assertEqual(startup_time.year, 2025)
        self.assertEqual(startup_time.month, 6)
        self.assertEqual(startup_time.day, 1)
        self.assertEqual(startup_time.hour, 10)
        self.assertEqual(startup_time.minute, 30)
        self.assertEqual(startup_time.second, 45)
        
        # 测试无效时间格式
        invalid_data = {"Startup Time": "invalid format"}
        self.assertIsNone(self.parser._extract_startup_time(invalid_data))
        
        # 测试缺少启动时间
        empty_data = {}
        self.assertIsNone(self.parser._extract_startup_time(empty_data))
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试空HTML
        empty_soup = BeautifulSoup("", 'html.parser')
        
        # 所有解析方法都应该返回默认值而不抛出异常
        db_info = self.parser.parse_db_info(empty_soup)
        self.assertEqual(db_info.db_name, "UNKNOWN")
        
        snapshot_info = self.parser.parse_snapshot_info(empty_soup)
        self.assertEqual(snapshot_info.begin_snap_id, 0)
        
        load_profile = self.parser.parse_load_profile(empty_soup)
        self.assertEqual(load_profile.db_time_per_second, 0.0)
        
        wait_events = self.parser.parse_wait_events(empty_soup)
        self.assertEqual(len(wait_events), 0)
        
        sql_statistics = self.parser.parse_sql_statistics(empty_soup)
        self.assertEqual(len(sql_statistics), 0)
        
        activities = self.parser.parse_instance_activity(empty_soup)
        self.assertEqual(len(activities), 0)
    
    def test_can_parse_exception_handling(self):
        """测试can_parse方法的异常处理"""
        # 测试无效HTML导致的异常
        with patch('bs4.BeautifulSoup') as mock_soup:
            mock_soup.side_effect = Exception("Parsing error")
            result = self.parser.can_parse("some html")
            self.assertFalse(result)
    
    def test_logging(self):
        """测试日志记录功能"""
        # 测试成功识别时的行为
        result = self.parser.can_parse(self.oracle_19c_html)
        self.assertTrue(result)
        
        # 测试失败时的行为
        result = self.parser.can_parse("<html><body>Not AWR</body></html>")
        self.assertFalse(result)
        
        # 测试异常处理
        result = self.parser.can_parse("")
        self.assertFalse(result)


class TestOracle19cParserIntegration(unittest.TestCase):
    """Oracle 19c解析器集成测试"""
    
    def setUp(self):
        """集成测试初始化"""
        self.parser = Oracle19cParser()
        
        # 创建完整的AWR HTML示例
        self.complete_awr_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <title>Oracle Database 19c AWR Report</title>
        </head>
        <body>
            <h1>WORKLOAD REPOSITORY report for Oracle Database 19c Enterprise Edition</h1>
            <p>Release 19.8.0.0.0 - Production on Mon Jun 02 11:25:00 2025</p>
            
            <!-- 数据库信息 -->
            <a name="dbinfo">Database DB Id DB Name Inst Num Instance Startup Time</a>
            <table>
                <tr><td>DB Name</td><td>PRODDB</td></tr>
                <tr><td>Instance</td><td>proddb1</td></tr>
                <tr><td>Host Name</td><td>prod-server01.company.com</td></tr>
                <tr><td>Platform</td><td>Linux x86 64-bit</td></tr>
                <tr><td>Startup Time</td><td>01-Jun-25 08:30:15</td></tr>
            </table>
            
            <!-- 快照信息 -->
            <table>
                <tr><td>Begin Snap Id</td><td>12345</td></tr>
                <tr><td>End Snap Id</td><td>12346</td></tr>
                <tr><td>Elapsed Time</td><td>60.0 mins</td></tr>
                <tr><td>DB Time</td><td>48.5 mins</td></tr>
            </table>
            
            <!-- 负载概要 -->
            <a name="loadprofile">Load Profile</a>
            <h3>Load Profile</h3>
            <table>
                <tr><th></th><th>Per Second</th><th>Per Transaction</th></tr>
                <tr><td>DB Time(s)</td><td>0.81</td><td>0.42</td></tr>
                <tr><td>Logical reads</td><td>45678</td><td>23456</td></tr>
                <tr><td>Physical reads</td><td>1234</td><td>567</td></tr>
                <tr><td>Physical writes</td><td>234</td><td>123</td></tr>
                <tr><td>User calls</td><td>2345</td><td>1234</td></tr>
                <tr><td>Parses</td><td>567</td><td>234</td></tr>
                <tr><td>Hard parses</td><td>23</td><td>12</td></tr>
                <tr><td>Sorts</td><td>345</td><td>178</td></tr>
                <tr><td>Logons</td><td>5</td><td>2</td></tr>
                <tr><td>Executes</td><td>3456</td><td>1789</td></tr>
                <tr><td>Rollbacks</td><td>12</td><td>6</td></tr>
                <tr><td>Transactions</td><td>1.95</td><td>1.00</td></tr>
            </table>
            
            <!-- 等待事件 -->
            <a name="topevents">Top 10 Timed Events</a>
            <table>
                <tr><th>Event</th><th>Waits</th><th>Total Wait Time (sec)</th><th>% DB Time</th><th>Wait Class</th></tr>
                <tr><td>db file sequential read</td><td>23456</td><td>1234.5</td><td>42.3%</td><td>User I/O</td></tr>
                <tr><td>log file sync</td><td>12345</td><td>567.8</td><td>19.5%</td><td>Commit</td></tr>
                <tr><td>db file scattered read</td><td>5678</td><td>234.6</td><td>8.1%</td><td>User I/O</td></tr>
                <tr><td>latch: cache buffers chains</td><td>3456</td><td>123.4</td><td>4.2%</td><td>Concurrency</td></tr>
                <tr><td>buffer busy waits</td><td>1234</td><td>67.8</td><td>2.3%</td><td>Concurrency</td></tr>
            </table>
            
            <!-- SQL统计 -->
            <a name="topsql">SQL ordered by Elapsed Time</a>
            <table>
                <tr><th>SQL ID</th><th>Executions</th><th>Elapsed Time (s)</th><th>CPU Time (s)</th><th>Buffer Gets</th><th>Disk Reads</th></tr>
                <tr><td>1a2b3c4d5e6f7890</td><td>500</td><td>890.5</td><td>567.3</td><td>234567</td><td>12345</td></tr>
                <tr><td>2b3c4d5e6f789012</td><td>300</td><td>456.7</td><td>234.5</td><td>123456</td><td>6789</td></tr>
                <tr><td>3c4d5e6f78901234</td><td>200</td><td>234.6</td><td>123.4</td><td>67890</td><td>3456</td></tr>
            </table>
            
            <!-- 实例活动统计 -->
            <a name="sysstat">Instance Activity Statistics</a>
            <table>
                <tr><th>Statistic Name</th><th>Total</th><th>Per Second</th><th>Per Transaction</th></tr>
                <tr><td>user commits</td><td>234567</td><td>65.2</td><td>33.4</td></tr>
                <tr><td>user rollbacks</td><td>1234</td><td>0.34</td><td>0.18</td></tr>
                <tr><td>session logical reads</td><td>12345678</td><td>3429.3</td><td>1756.8</td></tr>
                <tr><td>physical reads</td><td>567890</td><td>157.7</td><td>80.8</td></tr>
                <tr><td>physical writes</td><td>123456</td><td>34.3</td><td>17.6</td></tr>
            </table>
        </body>
        </html>
        """
    
    def test_complete_parsing_workflow(self):
        """测试完整的解析工作流程"""
        # 验证可以解析
        self.assertTrue(self.parser.can_parse(self.complete_awr_html))
        
        # 执行完整解析
        soup = BeautifulSoup(self.complete_awr_html, 'html.parser')
        
        # 解析各个部分
        db_info = self.parser.parse_db_info(soup)
        snapshot_info = self.parser.parse_snapshot_info(soup) 
        load_profile = self.parser.parse_load_profile(soup)
        wait_events = self.parser.parse_wait_events(soup)
        sql_statistics = self.parser.parse_sql_statistics(soup)
        activities = self.parser.parse_instance_activity(soup)
        
        # 验证所有部分都正确解析
        self.assertEqual(db_info.db_name, "PRODDB")
        self.assertEqual(db_info.instance_name, "proddb1")
        
        self.assertEqual(snapshot_info.begin_snap_id, 12345)
        self.assertEqual(snapshot_info.end_snap_id, 12346)
        
        self.assertEqual(load_profile.db_time_per_second, 0.81)
        self.assertEqual(load_profile.logical_reads_per_second, 45678.0)
        
        self.assertEqual(len(wait_events), 5)
        self.assertEqual(wait_events[0].event_name, "db file sequential read")
        
        self.assertEqual(len(sql_statistics), 3)
        self.assertEqual(sql_statistics[0].sql_id, "1a2b3c4d5e6f7890")
        
        self.assertEqual(len(activities), 5)
        self.assertEqual(activities[0].statistic_name, "user commits")
    
    def test_parsing_with_missing_sections(self):
        """测试部分区块缺失时的解析"""
        partial_html = """
        <html>
        <body>
            <h1>Oracle Database 19c AWR Report</h1>
            <a name="dbinfo">Database Information</a>
            <table>
                <tr><td>DB Name</td><td>PARTIALDB</td></tr>
                <tr><td>Instance</td><td>partial1</td></tr>
            </table>
            <!-- 其他区块缺失 -->
        </body>
        </html>
        """
        
        soup = BeautifulSoup(partial_html, 'html.parser')
        
        # 数据库信息应该正常解析
        db_info = self.parser.parse_db_info(soup)
        self.assertEqual(db_info.db_name, "PARTIALDB")
        
        # 其他区块应该返回默认值或空列表
        load_profile = self.parser.parse_load_profile(soup)
        self.assertEqual(load_profile.db_time_per_second, 0.0)
        
        wait_events = self.parser.parse_wait_events(soup)
        self.assertEqual(len(wait_events), 0)
        
        sql_statistics = self.parser.parse_sql_statistics(soup)
        self.assertEqual(len(sql_statistics), 0)
        
        activities = self.parser.parse_instance_activity(soup)
        self.assertEqual(len(activities), 0)


if __name__ == '__main__':
    unittest.main() 