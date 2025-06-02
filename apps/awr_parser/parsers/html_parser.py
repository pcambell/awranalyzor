"""
HTML解析专用工具类
{{CHENGQI: P2-LD-002 BeautifulSoup解析基础工具类 - 2025-06-02 11:15:00 +08:00}}

专门的HTML表格解析器和锚点导航器
遵循单一职责原则，提供更精细的解析控制
"""

import re
import logging
from typing import List, Dict, Optional, Any, Tuple, Union
from bs4 import BeautifulSoup, Tag, NavigableString
from .base import OracleVersion


logger = logging.getLogger(__name__)


class HTMLTableParser:
    """
    专业的HTML表格解析器
    针对AWR报告中复杂表格结构进行优化
    遵循单一职责原则：专注于表格数据提取
    """
    
    def __init__(self, soup: BeautifulSoup):
        self.soup = soup
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def parse_table_with_headers(self, table: Tag, 
                                 header_row_index: int = 0) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        解析带表头的表格
        
        Args:
            table: 表格Tag对象
            header_row_index: 表头行索引（默认第一行）
            
        Returns:
            Tuple[表头列表, 数据行列表]
        """
        if not table or table.name != 'table':
            return [], []
        
        rows = table.find_all('tr')
        if len(rows) <= header_row_index:
            self.logger.warning("表格行数不足，无法提取表头")
            return [], []
        
        # 提取表头
        header_row = rows[header_row_index]
        headers = []
        for cell in header_row.find_all(['th', 'td']):
            header_text = self._extract_cell_text(cell)
            headers.append(header_text)
        
        # 提取数据行
        data_rows = []
        for row in rows[header_row_index + 1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) == 0:
                continue  # 跳过空行
            
            row_data = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    cell_text = self._extract_cell_text(cell)
                    row_data[headers[i]] = cell_text
                elif len(headers) > 0:
                    # 如果单元格数量超过表头数量，用索引作为键
                    row_data[f"column_{i}"] = self._extract_cell_text(cell)
            
            if row_data:  # 只添加非空行
                data_rows.append(row_data)
        
        self.logger.debug(f"解析表格完成: {len(headers)}列, {len(data_rows)}行")
        return headers, data_rows
    
    def parse_data_table(self, table: Tag, 
                        header_row_index: int = 0) -> Tuple[List[str], List[Dict[str, str]]]:
        """
        解析数据表格（parse_table_with_headers的别名）
        
        Args:
            table: 表格Tag对象
            header_row_index: 表头行索引（默认第一行）
            
        Returns:
            Tuple[表头列表, 数据行列表]
        """
        return self.parse_table_with_headers(table, header_row_index)
    
    def parse_key_value_table(self, table: Tag, 
                              key_column: int = 0, 
                              value_column: int = 1) -> Dict[str, str]:
        """
        解析键值对格式的表格
        
        Args:
            table: 表格Tag对象
            key_column: 键所在列索引
            value_column: 值所在列索引
            
        Returns:
            键值对字典
        """
        if not table or table.name != 'table':
            return {}
        
        result = {}
        rows = table.find_all('tr')
        
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) > max(key_column, value_column):
                key = self._extract_cell_text(cells[key_column]).strip()
                value = self._extract_cell_text(cells[value_column]).strip()
                
                if key and value:  # 忽略空键或空值
                    # 清理键名（移除冒号等）
                    key = re.sub(r'[:\s]+$', '', key)
                    result[key] = value
        
        self.logger.debug(f"解析键值表格完成: {len(result)}对")
        return result
    
    def find_table_by_caption(self, caption_pattern: str) -> Optional[Tag]:
        """
        根据表格标题查找表格
        
        Args:
            caption_pattern: 标题匹配模式（正则表达式）
            
        Returns:
            匹配的表格Tag或None
        """
        for table in self.soup.find_all('table'):
            # 查找caption标签
            caption = table.find('caption')
            if caption and re.search(caption_pattern, caption.get_text(), re.IGNORECASE):
                return table
            
            # 查找表格前的标题元素
            prev_element = table.previous_sibling
            while prev_element:
                if isinstance(prev_element, Tag):
                    if prev_element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                        if re.search(caption_pattern, prev_element.get_text(), re.IGNORECASE):
                            return table
                    break
                prev_element = prev_element.previous_sibling
        
        self.logger.debug(f"未找到标题匹配 '{caption_pattern}' 的表格")
        return None
    
    def extract_numeric_columns(self, data_rows: List[Dict[str, str]], 
                                columns: List[str]) -> Dict[str, List[Union[int, float, None]]]:
        """
        从数据行中提取数值列
        
        Args:
            data_rows: 数据行列表
            columns: 要提取的列名列表
            
        Returns:
            列名到数值列表的映射
        """
        from .utils import DataCleaner
        
        result = {col: [] for col in columns}
        
        for row in data_rows:
            for col in columns:
                if col in row:
                    numeric_value = DataCleaner.clean_number(row[col])
                    result[col].append(numeric_value)
                else:
                    result[col].append(None)
        
        return result
    
    def _extract_cell_text(self, cell: Tag) -> str:
        """
        提取单元格文本，处理复杂格式
        
        Args:
            cell: 单元格Tag对象
            
        Returns:
            清理后的文本
        """
        if not cell:
            return ""
        
        # 获取所有文本内容
        text = cell.get_text(separator=' ', strip=True)
        
        # 清理多余空格
        text = re.sub(r'\s+', ' ', text)
        
        # 移除特殊字符
        text = re.sub(r'[\r\n\t]', ' ', text)
        
        return text.strip()


class AnchorNavigator:
    """
    锚点导航器
    专门用于在AWR HTML中定位和导航到特定区块
    遵循单一职责原则：专注于锚点定位和导航
    """
    
    def __init__(self, soup: BeautifulSoup):
        self.soup = soup
        self.logger = logging.getLogger(self.__class__.__name__)
        self._anchor_cache = {}  # 缓存已找到的锚点
    
    def find_anchor(self, anchor_name: str) -> Optional[Tag]:
        """
        查找指定名称的锚点
        
        Args:
            anchor_name: 锚点名称
            
        Returns:
            锚点Tag对象或None
        """
        # 检查缓存
        if anchor_name in self._anchor_cache:
            return self._anchor_cache[anchor_name]
        
        # 查找name属性
        anchor = self.soup.find('a', {'name': anchor_name})
        
        # 如果没找到，尝试查找id属性
        if not anchor:
            anchor = self.soup.find(attrs={'id': anchor_name})
        
        # 如果还没找到，尝试模糊匹配
        if not anchor:
            anchor = self._fuzzy_find_anchor(anchor_name)
        
        # 缓存结果
        self._anchor_cache[anchor_name] = anchor
        
        if anchor:
            self.logger.debug(f"找到锚点: {anchor_name}")
        else:
            self.logger.debug(f"未找到锚点: {anchor_name}")
        
        return anchor
    
    def get_section_after_anchor(self, anchor_name: str, 
                                 section_types: List[str] = None) -> Optional[Tag]:
        """
        获取锚点后的区块内容
        
        Args:
            anchor_name: 锚点名称
            section_types: 要查找的区块类型列表（如['table', 'div']）
            
        Returns:
            区块Tag对象或None
        """
        if section_types is None:
            section_types = ['table', 'div', 'section', 'p']
        
        anchor = self.find_anchor(anchor_name)
        if not anchor:
            return None
        
        # 从锚点开始向后查找
        current = anchor.next_sibling
        while current:
            if isinstance(current, Tag):
                if current.name in section_types:
                    return current
                
                # 检查是否包含目标类型的子元素
                for section_type in section_types:
                    child = current.find(section_type)
                    if child:
                        return child
            
            current = current.next_sibling
        
        self.logger.debug(f"锚点 {anchor_name} 后未找到区块")
        return None
    
    def get_table_after_anchor(self, anchor_name: str) -> Optional[Tag]:
        """
        获取锚点后的第一个表格
        
        Args:
            anchor_name: 锚点名称
            
        Returns:
            表格Tag对象或None
        """
        return self.get_section_after_anchor(anchor_name, ['table'])
    
    def navigate_to_section(self, section_identifier: Union[str, Dict[str, str]]) -> Optional[Tag]:
        """
        导航到指定区块（支持多种定位方式）
        
        Args:
            section_identifier: 区块标识符
                - 字符串：锚点名称
                - 字典：{'anchor': '锚点名', 'title': '标题模式', 'class': '类名'}
                
        Returns:
            区块Tag对象或None
        """
        if isinstance(section_identifier, str):
            return self.get_section_after_anchor(section_identifier)
        
        elif isinstance(section_identifier, dict):
            # 尝试锚点定位
            if 'anchor' in section_identifier:
                section = self.get_section_after_anchor(section_identifier['anchor'])
                if section:
                    return section
            
            # 尝试标题定位
            if 'title' in section_identifier:
                section = self._find_section_by_title(section_identifier['title'])
                if section:
                    return section
            
            # 尝试类名定位
            if 'class' in section_identifier:
                section = self.soup.find(class_=section_identifier['class'])
                if section:
                    return section
        
        return None
    
    def get_all_anchors(self) -> List[Dict[str, str]]:
        """
        获取所有锚点信息
        
        Returns:
            锚点信息列表，每个元素包含name和位置信息
        """
        anchors = []
        
        # 查找所有带name属性的a标签
        for anchor in self.soup.find_all('a', {'name': True}):
            anchors.append({
                'name': anchor['name'],
                'type': 'name',
                'text': anchor.get_text(strip=True) or '',
            })
        
        # 查找所有带id属性的元素
        for element in self.soup.find_all(attrs={'id': True}):
            anchors.append({
                'name': element['id'],
                'type': 'id',
                'tag': element.name,
                'text': element.get_text(strip=True)[:50] or '',  # 限制文本长度
            })
        
        self.logger.info(f"找到 {len(anchors)} 个锚点")
        return anchors
    
    def _fuzzy_find_anchor(self, anchor_name: str) -> Optional[Tag]:
        """
        模糊查找锚点（用于处理名称变化）
        
        Args:
            anchor_name: 锚点名称
            
        Returns:
            匹配的锚点Tag或None
        """
        # 转换为小写进行模糊匹配
        anchor_lower = anchor_name.lower()
        
        # 查找所有锚点
        all_anchors = self.soup.find_all('a', {'name': True})
        for anchor in all_anchors:
            name = anchor['name'].lower()
            if anchor_lower in name or name in anchor_lower:
                return anchor
        
        # 查找所有id属性
        all_ids = self.soup.find_all(attrs={'id': True})
        for element in all_ids:
            element_id = element['id'].lower()
            if anchor_lower in element_id or element_id in anchor_lower:
                return element
        
        return None
    
    def _find_section_by_title(self, title_pattern: str) -> Optional[Tag]:
        """
        根据标题模式查找区块
        
        Args:
            title_pattern: 标题模式（正则表达式）
            
        Returns:
            匹配的区块Tag或None
        """
        # 查找标题元素
        for tag in self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'th', 'td']):
            if tag.string and re.search(title_pattern, tag.string, re.IGNORECASE):
                # 查找标题后的内容
                current = tag.next_sibling
                while current:
                    if isinstance(current, Tag) and current.name in ['table', 'div', 'section']:
                        return current
                    current = current.next_sibling
                
                # 如果没找到后续内容，返回包含标题的表格
                table = tag.find_parent('table')
                if table:
                    return table
        
        return None


class TableStructureAnalyzer:
    """
    表格结构分析器
    分析AWR表格的结构特征，便于选择合适的解析策略
    """
    
    def __init__(self, table: Tag):
        self.table = table
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def analyze(self) -> Dict[str, Any]:
        """
        分析表格结构
        
        Returns:
            结构分析结果
        """
        if not self.table or self.table.name != 'table':
            return {}
        
        rows = self.table.find_all('tr')
        
        analysis = {
            'row_count': len(rows),
            'column_count': self._get_max_column_count(rows),
            'has_header': self._has_header_row(rows),
            'has_footer': self._has_footer_row(rows),
            'is_key_value': self._is_key_value_table(rows),
            'data_types': self._analyze_data_types(rows),
            'structure_type': 'unknown'
        }
        
        # 判断表格类型
        if analysis['is_key_value']:
            analysis['structure_type'] = 'key_value'
        elif analysis['has_header']:
            analysis['structure_type'] = 'header_data'
        else:
            analysis['structure_type'] = 'simple'
        
        return analysis
    
    def _get_max_column_count(self, rows: List[Tag]) -> int:
        """获取最大列数"""
        max_cols = 0
        for row in rows:
            cols = len(row.find_all(['td', 'th']))
            max_cols = max(max_cols, cols)
        return max_cols
    
    def _has_header_row(self, rows: List[Tag]) -> bool:
        """检查是否有表头行"""
        if not rows:
            return False
        
        first_row = rows[0]
        # 检查第一行是否主要由th元素组成
        th_count = len(first_row.find_all('th'))
        td_count = len(first_row.find_all('td'))
        
        return th_count > td_count
    
    def _has_footer_row(self, rows: List[Tag]) -> bool:
        """检查是否有表尾行"""
        if len(rows) < 2:
            return False
        
        last_row = rows[-1]
        # 简单检查：如果最后一行只有一个单元格且跨多列，可能是表尾
        cells = last_row.find_all(['td', 'th'])
        if len(cells) == 1:
            cell = cells[0]
            colspan = cell.get('colspan', '1')
            try:
                return int(colspan) > 1
            except ValueError:
                return False
        
        return False
    
    def _is_key_value_table(self, rows: List[Tag]) -> bool:
        """检查是否为键值对表格"""
        if len(rows) < 2:
            return False
        
        # 检查是否每行都有两列
        two_column_count = 0
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) == 2:
                two_column_count += 1
        
        # 如果大部分行都是两列，认为是键值对表格
        return two_column_count / len(rows) > 0.7
    
    def _analyze_data_types(self, rows: List[Tag]) -> Dict[str, str]:
        """分析各列的数据类型"""
        if not rows:
            return {}
        
        # 取前几行数据进行分析
        sample_rows = rows[:min(5, len(rows))]
        max_cols = self._get_max_column_count(sample_rows)
        
        column_types = {}
        for col_idx in range(max_cols):
            sample_values = []
            for row in sample_rows:
                cells = row.find_all(['td', 'th'])
                if col_idx < len(cells):
                    text = cells[col_idx].get_text(strip=True)
                    if text:
                        sample_values.append(text)
            
            # 分析数据类型
            if sample_values:
                column_types[f'column_{col_idx}'] = self._detect_column_type(sample_values)
        
        return column_types
    
    def _detect_column_type(self, values: List[str]) -> str:
        """检测列的数据类型"""
        if not values:
            return 'empty'
        
        # 检查是否为数字
        numeric_count = 0
        for value in values:
            if re.match(r'^[\d,.-]+$', value.replace(' ', '')):
                numeric_count += 1
        
        if numeric_count / len(values) > 0.7:
            return 'numeric'
        
        # 检查是否为百分比
        percentage_count = 0
        for value in values:
            if '%' in value:
                percentage_count += 1
        
        if percentage_count / len(values) > 0.5:
            return 'percentage'
        
        # 检查是否为时间
        time_count = 0
        time_patterns = [r'\d+:\d+:\d+', r'\d+\.\d+s', r'\d+ms']
        for value in values:
            for pattern in time_patterns:
                if re.search(pattern, value):
                    time_count += 1
                    break
        
        if time_count / len(values) > 0.5:
            return 'time'
        
        return 'text'
    
    def has_columns(self, column_names: List[str]) -> bool:
        """
        检查表格是否包含指定的列名
        
        Args:
            column_names: 要检查的列名列表
            
        Returns:
            bool: 如果表格包含所有指定列名则返回True
        """
        if not self.table or self.table.name != 'table':
            return False
        
        rows = self.table.find_all('tr')
        if not rows:
            return False
        
        # 查找表头行（通常是第一行）
        header_row = rows[0]
        header_cells = header_row.find_all(['th', 'td'])
        
        # 提取表头文本
        header_texts = []
        for cell in header_cells:
            header_text = cell.get_text(strip=True)
            header_texts.append(header_text)
        
        # 检查是否包含所有指定列名
        for column_name in column_names:
            found = False
            for header_text in header_texts:
                if column_name.lower() in header_text.lower() or header_text.lower() in column_name.lower():
                    found = True
                    break
            if not found:
                return False
        
        return True 