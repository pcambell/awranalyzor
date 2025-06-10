"""
AWR解析通用工具类
{{CHENGQI: P2-AR-001 AWR解析器架构最终化设计 - 2025-06-02 11:05:00 +08:00}}

提供HTML解析、版本检测、数据清洗等通用功能
遵循单一职责原则，每个类专注于特定功能
"""

import re
import logging
from typing import List, Optional, Dict, Any, Union
from bs4 import BeautifulSoup, Tag, NavigableString
from .base import OracleVersion, InstanceType


logger = logging.getLogger(__name__)


class VersionDetector:
    """
    Oracle版本检测器
    基于AWR HTML内容特征识别Oracle版本
    """
    
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)
        
        # 版本检测模式（按优先级排序）
        self.version_patterns = [
            # Oracle 19c 模式
            (OracleVersion.ORACLE_19C, [
                r'Oracle Database 19c',
                r'Release 19\.',
                r'19\.\d+\.\d+\.\d+',
                r'version="19\.',
                r'<td[^>]*>\s*19\.\d+\.\d+\.\d+\s*</td>',  # 新增: HTML表格中的版本号
                r'19\.\d+\.\d+\.\d+\.\d+'  # 新增: 完整版本号格式
            ]),
            # Oracle 12c 模式  
            (OracleVersion.ORACLE_12C, [
                r'Oracle Database 12c',
                r'Release 12\.',
                r'12\.\d+\.\d+\.\d+',
                r'version="12\.',
                r'<td[^>]*>\s*12\.\d+\.\d+\.\d+\s*</td>',  # 新增: HTML表格中的版本号
                r'12\.\d+\.\d+\.\d+\.\d+'  # 新增: 完整版本号格式
            ]),
            # Oracle 11g 模式
            (OracleVersion.ORACLE_11G, [
                r'Oracle Database 11g',
                r'Release 11\.',
                r'11\.\d+\.\d+\.\d+',
                r'version="11\.',
                r'<td[^>]*>\s*11\.\d+\.\d+\.\d+\s*</td>',  # 新增: HTML表格中的版本号
                r'11\.\d+\.\d+\.\d+\.\d+'  # 新增: 完整版本号格式
            ]),
            # Oracle 10g 模式
            (OracleVersion.ORACLE_10G, [
                r'Oracle Database 10g',
                r'Release 10\.',
                r'10\.\d+\.\d+\.\d+',
                r'version="10\.',
                r'<td[^>]*>\s*10\.\d+\.\d+\.\d+\s*</td>',  # HTML表格中的版本号
                r'10\.\d+\.\d+\.\d+\.\d+'  # 完整版本号格式
            ])
        ]
    
    def detect_version(self, html_content: str) -> OracleVersion:
        """
        检测Oracle版本
        
        Args:
            html_content: AWR HTML内容
            
        Returns:
            OracleVersion: 检测到的版本
        """
        try:
            # 首先检查是否为ASH报告（而非AWR报告）
            if self._is_ash_report(html_content):
                self.logger.warning("检测到ASH报告，不是AWR报告")
                return OracleVersion.UNKNOWN
            
            # 按优先级检查版本模式
            for version, patterns in self.version_patterns:
                for pattern in patterns:
                    if re.search(pattern, html_content, re.IGNORECASE):
                        self.logger.info(f"通过模式检测到 {version.value}")
                        return version
            
            # 尝试从HTML标题中提取版本
            soup = BeautifulSoup(html_content, 'html.parser')
            title = soup.find('title')
            if title and title.string:
                version = self._extract_version_from_title(title.string)
                if version != OracleVersion.UNKNOWN:
                    self.logger.info(f"从标题检测到 {version.value}")
                    return version
            
            # 尝试从第一个h1标签检测
            h1 = soup.find('h1')
            if h1 and h1.get_text():
                version = self._extract_version_from_title(h1.get_text())
                if version != OracleVersion.UNKNOWN:
                    self.logger.info(f"从h1标签检测到 {version.value}")
                    return version
            
            self.logger.warning("无法识别Oracle版本")
            return OracleVersion.UNKNOWN
            
        except Exception as e:
            self.logger.error(f"版本检测时出错: {e}")
            return OracleVersion.UNKNOWN
    
    def detect_from_html(self, html_content: str) -> OracleVersion:
        """
        从HTML内容检测Oracle版本（detect_version的别名）
        
        Args:
            html_content: AWR HTML内容
            
        Returns:
            检测到的Oracle版本
        """
        return self.detect_version(html_content)
    
    def _extract_version_from_title(self, title: str) -> OracleVersion:
        """从HTML标题中提取版本"""
        title_lower = title.lower()
        
        if '19c' in title_lower or 'release 19' in title_lower:
            return OracleVersion.ORACLE_19C
        elif '12c' in title_lower or 'release 12' in title_lower:
            return OracleVersion.ORACLE_12C
        elif '11g' in title_lower or 'release 11' in title_lower:
            return OracleVersion.ORACLE_11G
        elif '10g' in title_lower or 'release 10' in title_lower:
            return OracleVersion.ORACLE_10G
        
        return OracleVersion.UNKNOWN
    
    def _is_ash_report(self, html_content: str) -> bool:
        """
        检测是否为ASH报告（而非AWR报告）
        
        Args:
            html_content: HTML内容
            
        Returns:
            bool: 如果是ASH报告返回True
        """
        # {{CHENGQI: 修复ASH报告误判 - 2025-06-09 20:04:47 +08:00 - 
        # Action: Modified; Reason: 现代AWR报告包含ASH部分是正常的，需要精确区分纯ASH报告和包含ASH的AWR报告; Principle_Applied: 业务逻辑正确性}}
        
        # 首先检查是否是AWR报告（包含ASH部分的AWR是正常的）
        awr_strong_indicators = [
            r'<title[^>]*>AWR\s+Report',
            r'AWR\s+Report\s+for\s+DB',
            r'<h1[^>]*>AWR\s+Report',
            r'Automatic\s+Workload\s+Repository',
            r'Database\s+Summary',
            r'Load\s+Profile',
            r'Instance\s+Activity\s+Stats',
            r'Tablespace\s+IO\s+Stats'
        ]
        
        # 如果包含强AWR特征，即使有ASH部分也是AWR报告
        for pattern in awr_strong_indicators:
            if re.search(pattern, html_content, re.IGNORECASE):
                return False  # 这是AWR报告，不是ASH报告
        
        # 纯ASH报告的特征标识（标题中明确为ASH且不包含AWR特征）
        ash_title_indicators = [
            r'<title[^>]*>ASH\s+Report[^<]*</title>',
            r'<h1[^>]*>ASH\s+Report</h1>',
            r'<title[^>]*>Active\s+Session\s+History\s+Report[^<]*</title>'
        ]
        
        # 检查是否是纯ASH报告
        for pattern in ash_title_indicators:
            if re.search(pattern, html_content, re.IGNORECASE):
                return True
        
        return False


class HTMLSectionExtractor:
    """
    HTML区块提取器
    负责从AWR HTML中提取特定区块内容
    """
    
    def __init__(self, soup: BeautifulSoup):
        self.soup = soup
        self.logger = logging.getLogger(self.__class__.__name__)
    
    def find_section_by_anchor(self, anchor_name: str) -> Optional[Tag]:
        """
        根据锚点名称查找区块
        
        Args:
            anchor_name: 锚点名称
            
        Returns:
            找到的HTML标签或None
        """
        # 查找锚点
        anchor = self.soup.find('a', {'name': anchor_name})
        if not anchor:
            # 尝试查找id属性
            anchor = self.soup.find(attrs={'id': anchor_name})
        
        if not anchor:
            self.logger.debug(f"未找到锚点: {anchor_name}")
            return None
        
        # 查找锚点后的表格或内容区块
        current = anchor.next_sibling
        while current:
            if isinstance(current, Tag):
                if current.name in ['table', 'div', 'section']:
                    return current
                # 检查是否包含表格
                table = current.find('table')
                if table:
                    return table
            current = current.next_sibling
        
        self.logger.debug(f"锚点 {anchor_name} 后未找到内容区块")
        return None
    
    def find_section_by_title(self, title_pattern: str) -> Optional[Tag]:
        """
        根据标题模式查找区块
        
        Args:
            title_pattern: 标题模式（正则表达式）
            
        Returns:
            找到的HTML标签或None
        """
        # 查找包含指定标题的元素
        for tag in self.soup.find_all(['h1', 'h2', 'h3', 'h4', 'td', 'th']):
            if tag.string and re.search(title_pattern, tag.string, re.IGNORECASE):
                # 查找标题后的表格
                current = tag.parent
                while current:
                    table = current.find('table')
                    if table:
                        return table
                    current = current.next_sibling
                    if isinstance(current, Tag) and current.name == 'table':
                        return current
        
        self.logger.debug(f"未找到标题模式: {title_pattern}")
        return None
    
    def extract_table_data(self, table: Tag) -> List[Dict[str, str]]:
        """
        提取表格数据
        
        Args:
            table: 表格标签
            
        Returns:
            表格数据列表，每行为一个字典
        """
        if not table or table.name != 'table':
            return []
        
        data = []
        headers = []
        
        # 提取表头
        header_row = table.find('tr')
        if header_row:
            headers = [self._clean_text(th.get_text()) for th in header_row.find_all(['th', 'td'])]
        
        # 提取数据行
        rows = table.find_all('tr')[1:]  # 跳过表头
        for row in rows:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= len(headers):
                row_data = {}
                for i, cell in enumerate(cells[:len(headers)]):
                    if i < len(headers):
                        row_data[headers[i]] = self._clean_text(cell.get_text())
                data.append(row_data)
        
        return data
    
    def _clean_text(self, text: str) -> str:
        """清理文本内容"""
        if not text:
            return ""
        return re.sub(r'\s+', ' ', text.strip())


class DataCleaner:
    """
    数据清洗器
    负责清理和标准化从HTML提取的数据
    """
    
    @staticmethod
    def clean_numeric_value(value: str) -> Union[int, float, None]:
        """
        清理和转换数字值，支持单位
        
        Args:
            value: 原始字符串值
            
        Returns:
            转换后的数字或None
        """
        if not value or value.strip() == '':
            return None
        
        # 移除逗号、空格等
        cleaned = re.sub(r'[,\s]', '', str(value))
        
        # 检查单位并计算乘数
        multiplier = 1
        units_pattern = r'([KMGTkmgt])$'
        unit_match = re.search(units_pattern, cleaned)
        if unit_match:
            unit = unit_match.group(1).upper()
            unit_multipliers = {
                'K': 1000,
                'M': 1000000,
                'G': 1000000000,
                'T': 1000000000000
            }
            multiplier = unit_multipliers.get(unit, 1)
            # 移除单位
            cleaned = re.sub(units_pattern, '', cleaned)
        else:
            # 移除其他单位（如%等）
            cleaned = re.sub(r'[A-Za-z%]+$', '', cleaned)
        
        try:
            # 尝试转换为数字并应用乘数
            if '.' not in cleaned:
                return int(float(cleaned) * multiplier)
            else:
                return float(cleaned) * multiplier
        except ValueError:
            logger.warning(f"无法转换数字: {value}")
            return None
    
    @staticmethod
    def clean_text(value: str) -> str:
        """
        清理文本内容
        
        Args:
            value: 原始文本值
            
        Returns:
            清理后的文本
        """
        if not value:
            return ""
        # 移除多余空格、换行、制表符
        cleaned = re.sub(r'\s+', ' ', str(value).strip())
        return cleaned
    
    @staticmethod
    def clean_percentage(value: str) -> Optional[float]:
        """
        清理百分比数据
        
        Args:
            value: 包含百分比的字符串
            
        Returns:
            百分比数值（0-100）或None
        """
        if not value:
            return None
        
        # 提取数字部分
        match = re.search(r'([\d,]+\.?\d*)', str(value))
        if match:
            try:
                return float(match.group(1).replace(',', ''))
            except ValueError:
                pass
        
        return None
    
    @staticmethod
    def clean_time_format(value: str) -> Optional[float]:
        """
        清理时间格式，转换为秒
        
        Args:
            value: 时间字符串（如 "1.23s", "123ms", "1m 23s"）
            
        Returns:
            时间秒数或None
        """
        if not value:
            return None
        
        value = str(value).strip().lower()
        total_seconds = 0.0
        
        # 匹配各种时间格式
        patterns = [
            (r'(\d+\.?\d*)\s*s(?:ec)?(?:onds?)?', 1),      # 秒
            (r'(\d+\.?\d*)\s*ms?(?:ec)?', 0.001),          # 毫秒
            (r'(\d+\.?\d*)\s*us?(?:ec)?', 0.000001),       # 微秒
            (r'(\d+)\s*m(?:in)?(?:utes?)?', 60),           # 分钟
            (r'(\d+)\s*h(?:our)?(?:ours?)?', 3600),        # 小时
        ]
        
        for pattern, multiplier in patterns:
            matches = re.findall(pattern, value)
            for match in matches:
                try:
                    total_seconds += float(match) * multiplier
                except ValueError:
                    pass
        
        return total_seconds if total_seconds > 0 else None
    
    @staticmethod
    def detect_instance_type(db_info: Dict[str, Any]) -> InstanceType:
        """
        检测实例类型
        
        Args:
            db_info: 数据库信息字典
            
        Returns:
            实例类型
        """
        # 检查是否为RAC
        if any(key in str(db_info).lower() for key in ['rac', 'cluster', 'instance_number']):
            return InstanceType.RAC
        
        # 检查是否为CDB/PDB
        if any(key in str(db_info).lower() for key in ['cdb', 'pdb', 'container']):
            if 'pdb' in str(db_info).lower():
                return InstanceType.PDB
            else:
                return InstanceType.CDB
        
        return InstanceType.SINGLE
    
    @staticmethod
    def standardize_event_name(event_name: str) -> str:
        """
        标准化等待事件名称
        
        Args:
            event_name: 原始事件名称
            
        Returns:
            标准化后的事件名称
        """
        if not event_name:
            return ""
        
        # 移除多余空格
        cleaned = re.sub(r'\s+', ' ', event_name.strip())
        
        # 标准化常见事件名称
        mappings = {
            'db file sequential read': 'db file sequential read',
            'db file scattered read': 'db file scattered read', 
            'log file sync': 'log file sync',
            'log file parallel write': 'log file parallel write',
            'latch: cache buffers chains': 'latch: cache buffers chains',
            'buffer busy waits': 'buffer busy waits',
        }
        
        cleaned_lower = cleaned.lower()
        for standard, replacement in mappings.items():
            if standard in cleaned_lower:
                return replacement
        
        return cleaned


class AWRStructureAnalyzer:
    """
    AWR结构分析器
    分析AWR HTML的结构特征，用于解析器适配
    """
    
    def __init__(self, soup: BeautifulSoup):
        self.soup = soup
    
    def analyze_structure(self) -> Dict[str, Any]:
        """
        分析AWR结构
        
        Returns:
            结构分析结果
        """
        analysis = {
            'table_count': len(self.soup.find_all('table')),
            'anchor_count': len(self.soup.find_all('a')),
            'has_navigation': bool(self.soup.find('a', {'name': re.compile(r'top|contents')})),
            'sections': self._identify_sections(),
            'encoding': self._detect_encoding(),
        }
        
        return analysis
    
    def _identify_sections(self) -> List[str]:
        """识别AWR包含的主要区块"""
        sections = []
        
        # 常见区块锚点
        common_anchors = [
            'dbinfo', 'sysstat', 'loadprofile', 'topevents', 
            'topsql', 'instanceactivity', 'waitevents', 'sqlstats'
        ]
        
        for anchor in common_anchors:
            if self.soup.find('a', {'name': anchor}):
                sections.append(anchor)
        
        return sections
    
    def _detect_encoding(self) -> str:
        """检测字符编码"""
        meta_charset = self.soup.find('meta', {'charset': True})
        if meta_charset:
            return meta_charset['charset']
        
        meta_content = self.soup.find('meta', {'http-equiv': 'Content-Type'})
        if meta_content and 'content' in meta_content.attrs:
            content = meta_content['content']
            charset_match = re.search(r'charset=([^;]+)', content)
            if charset_match:
                return charset_match.group(1)
        
        return 'utf-8'  # 默认编码 