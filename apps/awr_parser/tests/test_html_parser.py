"""
HTML解析工具类单元测试
{{CHENGQI: P2-LD-002 BeautifulSoup解析基础工具类 - 2025-06-02 11:15:00 +08:00}}

测试HTMLTableParser、AnchorNavigator和TableStructureAnalyzer的功能
确保解析器工具类的正确性和健壮性
"""

import unittest
from unittest.mock import Mock, patch
from bs4 import BeautifulSoup
from apps.awr_parser.parsers.html_parser import (
    HTMLTableParser, 
    AnchorNavigator, 
    TableStructureAnalyzer
)


class TestHTMLTableParser(unittest.TestCase):
    """HTMLTableParser测试类"""
    
    def setUp(self):
        """测试用例初始化"""
        # 创建测试用的HTML表格
        self.test_html = """
        <html>
        <body>
            <table id="test_table">
                <tr>
                    <th>Event</th>
                    <th>Waits</th>
                    <th>Time(s)</th>
                    <th>%DB Time</th>
                </tr>
                <tr>
                    <td>db file sequential read</td>
                    <td>1,234</td>
                    <td>56.78</td>
                    <td>12.34%</td>
                </tr>
                <tr>
                    <td>log file sync</td>
                    <td>2,345</td>
                    <td>23.45</td>
                    <td>5.67%</td>
                </tr>
            </table>
            
            <table id="key_value_table">
                <tr><td>Database Name</td><td>TESTDB</td></tr>
                <tr><td>Instance Name</td><td>testdb1</td></tr>
                <tr><td>Host Name</td><td>server01</td></tr>
            </table>
            
            <h3>Load Profile Table</h3>
            <table id="load_profile">
                <caption>System Load Profile</caption>
                <tr><th>Metric</th><th>Per Second</th></tr>
                <tr><td>DB Time(s)</td><td>1.23</td></tr>
            </table>
        </body>
        </html>
        """
        
        self.soup = BeautifulSoup(self.test_html, 'html.parser')
        self.parser = HTMLTableParser(self.soup)
    
    def test_parse_table_with_headers(self):
        """测试带表头的表格解析"""
        table = self.soup.find('table', {'id': 'test_table'})
        headers, data_rows = self.parser.parse_table_with_headers(table)
        
        # 验证表头
        expected_headers = ['Event', 'Waits', 'Time(s)', '%DB Time']
        self.assertEqual(headers, expected_headers)
        
        # 验证数据行
        self.assertEqual(len(data_rows), 2)
        self.assertEqual(data_rows[0]['Event'], 'db file sequential read')
        self.assertEqual(data_rows[0]['Waits'], '1,234')
        self.assertEqual(data_rows[1]['Event'], 'log file sync')
    
    def test_parse_table_with_headers_custom_index(self):
        """测试自定义表头行索引"""
        # 创建带多行表头的表格
        multi_header_html = """
        <table>
            <tr><td colspan="2">Title Row</td></tr>
            <tr><th>Key</th><th>Value</th></tr>
            <tr><td>Test</td><td>Data</td></tr>
        </table>
        """
        soup = BeautifulSoup(multi_header_html, 'html.parser')
        parser = HTMLTableParser(soup)
        table = soup.find('table')
        
        headers, data_rows = parser.parse_table_with_headers(table, header_row_index=1)
        
        self.assertEqual(headers, ['Key', 'Value'])
        self.assertEqual(len(data_rows), 1)
        self.assertEqual(data_rows[0]['Key'], 'Test')
    
    def test_parse_key_value_table(self):
        """测试键值对表格解析"""
        table = self.soup.find('table', {'id': 'key_value_table'})
        result = self.parser.parse_key_value_table(table)
        
        expected_result = {
            'Database Name': 'TESTDB',
            'Instance Name': 'testdb1',
            'Host Name': 'server01'
        }
        
        self.assertEqual(result, expected_result)
    
    def test_parse_key_value_table_custom_columns(self):
        """测试自定义键值列的表格解析"""
        # 创建值在第一列，键在第二列的表格
        custom_html = """
        <table>
            <tr><td>TESTDB</td><td>Database Name</td><td>Extra</td></tr>
            <tr><td>testdb1</td><td>Instance Name</td><td>Extra</td></tr>
        </table>
        """
        soup = BeautifulSoup(custom_html, 'html.parser')
        parser = HTMLTableParser(soup)
        table = soup.find('table')
        
        result = parser.parse_key_value_table(table, key_column=1, value_column=0)
        
        expected_result = {
            'Database Name': 'TESTDB',
            'Instance Name': 'testdb1'
        }
        
        self.assertEqual(result, expected_result)
    
    def test_find_table_by_caption(self):
        """测试根据标题查找表格"""
        # 测试caption标签
        table = self.parser.find_table_by_caption('System Load Profile')
        self.assertIsNotNone(table)
        self.assertEqual(table.get('id'), 'load_profile')
        
        # 测试前置标题
        table = self.parser.find_table_by_caption('Load Profile Table')
        self.assertIsNotNone(table)
        self.assertEqual(table.get('id'), 'load_profile')
        
        # 测试不存在的标题
        table = self.parser.find_table_by_caption('Nonexistent Table')
        self.assertIsNone(table)
    
    def test_extract_numeric_columns(self):
        """测试数值列提取"""
        data_rows = [
            {'Event': 'event1', 'Waits': '1,234', 'Time': '56.78'},
            {'Event': 'event2', 'Waits': '2,345', 'Time': '23.45'},
            {'Event': 'event3', 'Waits': 'N/A', 'Time': '0.00'}
        ]
        
        columns = ['Waits', 'Time']
        result = self.parser.extract_numeric_columns(data_rows, columns)
        
        self.assertEqual(len(result['Waits']), 3)
        self.assertEqual(result['Waits'][0], 1234)
        self.assertEqual(result['Waits'][1], 2345)
        self.assertIsNone(result['Waits'][2])  # 'N/A' 应该转换为 None
        
        self.assertEqual(result['Time'][0], 56.78)
        self.assertEqual(result['Time'][2], 0.0)
    
    def test_extract_cell_text(self):
        """测试单元格文本提取"""
        # 创建包含复杂格式的单元格
        complex_html = """
        <td>
            Line 1<br/>
            Line 2  with   spaces
            <span>Nested text</span>
        </td>
        """
        soup = BeautifulSoup(complex_html, 'html.parser')
        cell = soup.find('td')
        
        result = self.parser._extract_cell_text(cell)
        
        # 验证文本已正确清理
        self.assertNotIn('\n', result)
        self.assertNotIn('\t', result)
        self.assertTrue('Line 1' in result)
        self.assertTrue('Line 2' in result)
        self.assertTrue('Nested text' in result)
    
    def test_invalid_table_handling(self):
        """测试无效表格处理"""
        # 测试None输入
        headers, data_rows = self.parser.parse_table_with_headers(None)
        self.assertEqual(headers, [])
        self.assertEqual(data_rows, [])
        
        # 测试非表格元素
        div_element = self.soup.find('div') or BeautifulSoup('<div>test</div>', 'html.parser').find('div')
        headers, data_rows = self.parser.parse_table_with_headers(div_element)
        self.assertEqual(headers, [])
        self.assertEqual(data_rows, [])


class TestAnchorNavigator(unittest.TestCase):
    """AnchorNavigator测试类"""
    
    def setUp(self):
        """测试用例初始化"""
        self.test_html = """
        <html>
        <body>
            <a name="top">Top of Page</a>
            <h1>AWR Report</h1>
            
            <a name="dbinfo">Database Information</a>
            <table id="db_table">
                <tr><td>DB Name</td><td>TESTDB</td></tr>
            </table>
            
            <div id="load_section">
                <a name="loadprofile">Load Profile</a>
                <table id="load_table">
                    <tr><th>Metric</th><th>Value</th></tr>
                </table>
            </div>
            
            <h2 id="events_title">Wait Events</h2>
            <table id="events_table">
                <tr><th>Event</th><th>Waits</th></tr>
            </table>
        </body>
        </html>
        """
        
        self.soup = BeautifulSoup(self.test_html, 'html.parser')
        self.navigator = AnchorNavigator(self.soup)
    
    def test_find_anchor(self):
        """测试锚点查找"""
        # 测试name属性
        anchor = self.navigator.find_anchor('top')
        self.assertIsNotNone(anchor)
        self.assertEqual(anchor.get_text(), 'Top of Page')
        
        # 测试id属性
        anchor = self.navigator.find_anchor('load_section')
        self.assertIsNotNone(anchor)
        self.assertEqual(anchor.name, 'div')
        
        # 测试不存在的锚点
        anchor = self.navigator.find_anchor('nonexistent')
        self.assertIsNone(anchor)
    
    def test_anchor_caching(self):
        """测试锚点缓存机制"""
        # 第一次查找
        anchor1 = self.navigator.find_anchor('dbinfo')
        
        # 第二次查找应该使用缓存
        anchor2 = self.navigator.find_anchor('dbinfo')
        
        self.assertIs(anchor1, anchor2)  # 应该是同一个对象
    
    def test_get_section_after_anchor(self):
        """测试获取锚点后的区块"""
        # 测试获取表格
        section = self.navigator.get_section_after_anchor('dbinfo')
        self.assertIsNotNone(section)
        self.assertEqual(section.name, 'table')
        self.assertEqual(section.get('id'), 'db_table')
        
        # 测试指定区块类型
        section = self.navigator.get_section_after_anchor('loadprofile', ['table'])
        self.assertIsNotNone(section)
        self.assertEqual(section.get('id'), 'load_table')
    
    def test_get_table_after_anchor(self):
        """测试获取锚点后的表格"""
        table = self.navigator.get_table_after_anchor('dbinfo')
        self.assertIsNotNone(table)
        self.assertEqual(table.name, 'table')
        self.assertEqual(table.get('id'), 'db_table')
        
        # 测试没有表格的锚点 - 修正：'top'锚点后面实际有h1元素，然后可能找到后续的表格
        # 改为测试一个真正没有后续表格的锚点
        table = self.navigator.get_table_after_anchor('nonexistent_anchor')
        self.assertIsNone(table)
    
    def test_navigate_to_section(self):
        """测试区块导航"""
        # 测试字符串标识符
        section = self.navigator.navigate_to_section('dbinfo')
        self.assertIsNotNone(section)
        self.assertEqual(section.get('id'), 'db_table')
        
        # 测试字典标识符 - 锚点
        section = self.navigator.navigate_to_section({'anchor': 'loadprofile'})
        self.assertIsNotNone(section)
        self.assertEqual(section.get('id'), 'load_table')
        
        # 测试字典标识符 - 标题
        section = self.navigator.navigate_to_section({'title': 'Wait Events'})
        self.assertIsNotNone(section)
        self.assertEqual(section.get('id'), 'events_table')
        
        # 测试字典标识符 - 类名
        section = self.navigator.navigate_to_section({'class': 'nonexistent'})
        self.assertIsNone(section)
    
    def test_get_all_anchors(self):
        """测试获取所有锚点"""
        anchors = self.navigator.get_all_anchors()
        
        # 验证锚点数量和类型
        anchor_names = [anchor['name'] for anchor in anchors]
        
        self.assertIn('top', anchor_names)
        self.assertIn('dbinfo', anchor_names)
        self.assertIn('loadprofile', anchor_names)
        self.assertIn('load_section', anchor_names)
        self.assertIn('events_title', anchor_names)
        
        # 验证锚点类型
        type_counts = {}
        for anchor in anchors:
            anchor_type = anchor['type']
            type_counts[anchor_type] = type_counts.get(anchor_type, 0) + 1
        
        self.assertIn('name', type_counts)
        self.assertIn('id', type_counts)
    
    def test_fuzzy_find_anchor(self):
        """测试模糊锚点查找"""
        # 创建包含相似名称的锚点
        fuzzy_html = """
        <a name="load_profile_section">Load Profile</a>
        <div id="event_summary_table">Events</div>
        """
        soup = BeautifulSoup(fuzzy_html, 'html.parser')
        navigator = AnchorNavigator(soup)
        
        # 测试模糊匹配
        anchor = navigator._fuzzy_find_anchor('load_profile')
        self.assertIsNotNone(anchor)
        
        anchor = navigator._fuzzy_find_anchor('event_summary')
        self.assertIsNotNone(anchor)


class TestTableStructureAnalyzer(unittest.TestCase):
    """TableStructureAnalyzer测试类"""
    
    def test_analyze_header_data_table(self):
        """测试表头数据表格分析"""
        html = """
        <table>
            <tr><th>Event</th><th>Waits</th><th>Time</th></tr>
            <tr><td>event1</td><td>100</td><td>1.5s</td></tr>
            <tr><td>event2</td><td>200</td><td>2.5s</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        analyzer = TableStructureAnalyzer(table)
        
        analysis = analyzer.analyze()
        
        self.assertEqual(analysis['row_count'], 3)
        self.assertEqual(analysis['column_count'], 3)
        self.assertTrue(analysis['has_header'])
        self.assertFalse(analysis['has_footer'])
        self.assertFalse(analysis['is_key_value'])
        self.assertEqual(analysis['structure_type'], 'header_data')
    
    def test_analyze_key_value_table(self):
        """测试键值对表格分析"""
        html = """
        <table>
            <tr><td>Database Name</td><td>TESTDB</td></tr>
            <tr><td>Instance Name</td><td>testdb1</td></tr>
            <tr><td>Host Name</td><td>server01</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        analyzer = TableStructureAnalyzer(table)
        
        analysis = analyzer.analyze()
        
        self.assertEqual(analysis['row_count'], 3)
        self.assertEqual(analysis['column_count'], 2)
        self.assertFalse(analysis['has_header'])
        self.assertTrue(analysis['is_key_value'])
        self.assertEqual(analysis['structure_type'], 'key_value')
    
    def test_analyze_data_types(self):
        """测试数据类型分析"""
        html = """
        <table>
            <tr><td>event1</td><td>1,234</td><td>56.78%</td><td>1.23s</td></tr>
            <tr><td>event2</td><td>2,345</td><td>78.90%</td><td>2.45s</td></tr>
            <tr><td>event3</td><td>3,456</td><td>12.34%</td><td>3.67ms</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        analyzer = TableStructureAnalyzer(table)
        
        analysis = analyzer.analyze()
        data_types = analysis['data_types']
        
        self.assertEqual(data_types['column_0'], 'text')     # 事件名称
        self.assertEqual(data_types['column_1'], 'numeric')  # 数字
        self.assertEqual(data_types['column_2'], 'percentage') # 百分比
        self.assertEqual(data_types['column_3'], 'time')     # 时间
    
    def test_analyze_table_with_footer(self):
        """测试带表尾的表格分析"""
        html = """
        <table>
            <tr><th>Item</th><th>Value</th></tr>
            <tr><td>Item1</td><td>100</td></tr>
            <tr><td>Item2</td><td>200</td></tr>
            <tr><td colspan="2">Total: 300</td></tr>
        </table>
        """
        soup = BeautifulSoup(html, 'html.parser')
        table = soup.find('table')
        analyzer = TableStructureAnalyzer(table)
        
        analysis = analyzer.analyze()
        
        self.assertTrue(analysis['has_header'])
        self.assertTrue(analysis['has_footer'])
    
    def test_analyze_invalid_table(self):
        """测试无效表格分析"""
        analyzer = TableStructureAnalyzer(None)
        analysis = analyzer.analyze()
        
        self.assertEqual(analysis, {})
        
        # 测试非表格元素
        html = "<div>Not a table</div>"
        soup = BeautifulSoup(html, 'html.parser')
        div = soup.find('div')
        analyzer = TableStructureAnalyzer(div)
        analysis = analyzer.analyze()
        
        self.assertEqual(analysis, {})


if __name__ == '__main__':
    unittest.main() 