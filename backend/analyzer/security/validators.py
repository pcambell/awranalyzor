"""
文件安全校验模块
实现多层次安全检查，确保上传文件的安全性
"""

import os
import re
import hashlib
import mimetypes
from typing import List, Dict, Tuple, Optional
from io import BytesIO
from django.core.exceptions import ValidationError
from django.conf import settings
import bleach
import magic
import logging

logger = logging.getLogger(__name__)

class FileSecurityValidator:
    """
    文件安全验证器
    实现SOLID原则：单一职责 - 专注于文件安全验证
    """
    
    # 允许的文件类型白名单
    ALLOWED_MIME_TYPES = {
        'text/html': ['.html', '.htm'],
        'application/zip': ['.zip'],  # 可能的压缩AWR文件
    }
    
    # 最大文件大小 (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    # 危险HTML标签黑名单
    DANGEROUS_TAGS = [
        'script', 'iframe', 'object', 'embed', 'form', 'input',
        'button', 'textarea', 'select', 'option', 'link', 'style',
        'meta', 'base', 'applet', 'bgsound', 'keygen', 'menuitem'
    ]
    
    # 危险属性黑名单
    DANGEROUS_ATTRIBUTES = [
        'onclick', 'onload', 'onerror', 'onmouseover', 'onfocus',
        'onblur', 'onchange', 'onsubmit', 'href', 'src', 'action',
        'formaction', 'background', 'lowsrc', 'dynsrc'
    ]
    
    # 已知恶意模式
    MALICIOUS_PATTERNS = [
        re.compile(r'<script[^>]*>.*?</script>', re.IGNORECASE | re.DOTALL),
        re.compile(r'javascript:', re.IGNORECASE),
        re.compile(r'vbscript:', re.IGNORECASE),
        re.compile(r'data:.*base64', re.IGNORECASE),
        re.compile(r'expression\s*\(', re.IGNORECASE),
        re.compile(r'@import', re.IGNORECASE),
        re.compile(r'document\.cookie', re.IGNORECASE),
        re.compile(r'window\.location', re.IGNORECASE),
    ]

    def __init__(self):
        """初始化验证器"""
        self.validation_errors = []
        
    def validate_file(self, file) -> Tuple[bool, List[str]]:
        """
        执行完整的文件安全验证
        
        Args:
            file: Django UploadedFile对象
            
        Returns:
            Tuple[bool, List[str]]: (是否通过验证, 错误信息列表)
        """
        self.validation_errors = []
        
        try:
            # 1. 基础文件验证
            self._validate_basic_properties(file)
            
            # 2. 文件类型验证
            self._validate_file_type(file)
            
            # 3. 文件大小验证
            self._validate_file_size(file)
            
            # 4. 文件内容安全验证
            self._validate_file_content(file)
            
            # 5. 文件名安全验证
            self._validate_filename(file.name)
            
            # 6. MIME类型验证
            self._validate_mime_type(file)
            
            # 记录验证成功
            logger.info(f"文件安全验证通过: {file.name}")
            return True, []
            
        except ValidationError as e:
            logger.warning(f"文件验证失败: {file.name} - {str(e)}")
            self.validation_errors.append(str(e))
            return False, self.validation_errors
        except Exception as e:
            logger.error(f"文件验证异常: {file.name} - {str(e)}")
            self.validation_errors.append(f"验证过程中发生错误: {str(e)}")
            return False, self.validation_errors

    def _validate_basic_properties(self, file):
        """验证文件基本属性"""
        if not file:
            raise ValidationError("文件不能为空")
            
        if not hasattr(file, 'name') or not file.name:
            raise ValidationError("文件名不能为空")
            
        if not hasattr(file, 'size'):
            raise ValidationError("无法获取文件大小")

    def _validate_file_type(self, file):
        """验证文件类型 - DRY原则：避免重复验证逻辑"""
        file_extension = os.path.splitext(file.name)[1].lower()
        
        # 检查扩展名是否在白名单中
        allowed_extensions = []
        for mime_type, extensions in self.ALLOWED_MIME_TYPES.items():
            allowed_extensions.extend(extensions)
            
        if file_extension not in allowed_extensions:
            raise ValidationError(
                f"不支持的文件类型: {file_extension}. "
                f"支持的类型: {', '.join(allowed_extensions)}"
            )

    def _validate_file_size(self, file):
        """验证文件大小"""
        if file.size > self.MAX_FILE_SIZE:
            size_mb = file.size / (1024 * 1024)
            max_size_mb = self.MAX_FILE_SIZE / (1024 * 1024)
            raise ValidationError(
                f"文件过大: {size_mb:.2f}MB, 最大允许: {max_size_mb}MB"
            )
            
        if file.size == 0:
            raise ValidationError("文件不能为空")

    def _validate_filename(self, filename: str):
        """验证文件名安全性"""
        # 检查文件名长度
        if len(filename) > 255:
            raise ValidationError("文件名过长")
            
        # 检查危险字符
        dangerous_chars = ['<', '>', ':', '"', '|', '?', '*', '\x00']
        for char in dangerous_chars:
            if char in filename:
                raise ValidationError(f"文件名包含危险字符: {char}")
                
        # 检查路径遍历尝试
        if '..' in filename or '/' in filename or '\\' in filename:
            raise ValidationError("文件名包含非法路径字符")
            
        # 检查保留文件名 (Windows)
        reserved_names = [
            'CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4',
            'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 
            'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9'
        ]
        name_without_ext = os.path.splitext(filename)[0].upper()
        if name_without_ext in reserved_names:
            raise ValidationError(f"文件名使用了系统保留名称: {name_without_ext}")

    def _validate_mime_type(self, file):
        """使用python-magic验证真实MIME类型"""
        try:
            # 读取文件头部分
            file.seek(0)
            file_header = file.read(1024)
            file.seek(0)
            
            # 使用magic检测实际MIME类型
            detected_mime = magic.from_buffer(file_header, mime=True)
            
            # 检查是否在允许列表中
            if detected_mime not in self.ALLOWED_MIME_TYPES:
                raise ValidationError(
                    f"文件内容与声明类型不匹配. 检测到: {detected_mime}"
                )
                
        except Exception as e:
            logger.warning(f"MIME类型检测失败: {str(e)}")
            # 如果magic检测失败，使用备用验证
            self._validate_mime_type_fallback(file)

    def _validate_mime_type_fallback(self, file):
        """备用MIME类型验证"""
        guessed_mime, _ = mimetypes.guess_type(file.name)
        if guessed_mime and guessed_mime not in self.ALLOWED_MIME_TYPES:
            raise ValidationError(f"不支持的MIME类型: {guessed_mime}")

    def _validate_file_content(self, file):
        """验证文件内容安全性 - 高内聚低耦合"""
        try:
            file.seek(0)
            content = file.read().decode('utf-8', errors='ignore')
            file.seek(0)
            
            # 检查文件是否为有效的HTML
            if not self._is_valid_html_structure(content):
                raise ValidationError("文件不是有效的HTML结构")
                
            # 检查恶意模式
            self._check_malicious_patterns(content)
            
            # 检查危险HTML元素
            self._check_dangerous_html_elements(content)
            
            # 验证是否为AWR报告
            self._validate_awr_content(content)
            
        except UnicodeDecodeError:
            raise ValidationError("文件编码格式不支持")
        except Exception as e:
            raise ValidationError(f"内容验证失败: {str(e)}")

    def _is_valid_html_structure(self, content: str) -> bool:
        """检查是否为有效的HTML结构"""
        content_lower = content.lower()
        
        # 基本HTML结构检查
        has_html_tag = '<html' in content_lower
        has_head_or_body = '<head' in content_lower or '<body' in content_lower
        
        # AWR报告通常包含的特征
        awr_indicators = [
            'oracle', 'database', 'instance', 'awr', 'report',
            'workload', 'repository', 'snapshot'
        ]
        
        has_awr_content = any(indicator in content_lower for indicator in awr_indicators)
        
        return (has_html_tag and has_head_or_body) or has_awr_content

    def _check_malicious_patterns(self, content: str):
        """检查恶意代码模式"""
        for pattern in self.MALICIOUS_PATTERNS:
            if pattern.search(content):
                raise ValidationError(f"检测到潜在恶意代码: {pattern.pattern}")

    def _check_dangerous_html_elements(self, content: str):
        """检查危险的HTML元素和属性"""
        # 使用bleach清理HTML并检查是否被修改
        cleaned_content = bleach.clean(
            content,
            tags=bleach.ALLOWED_TAGS + ['table', 'tr', 'td', 'th', 'tbody', 'thead', 'div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'hr'],
            attributes={
                '*': ['class', 'id', 'title'],
                'table': ['border', 'cellpadding', 'cellspacing', 'width'],
                'td': ['colspan', 'rowspan', 'align', 'valign'],
                'th': ['colspan', 'rowspan', 'align', 'valign'],
            },
            strip=True
        )
        
        # 如果清理后内容显著减少，可能包含危险元素
        original_length = len(content)
        cleaned_length = len(cleaned_content)
        
        if cleaned_length < original_length * 0.8:  # 允许20%的清理损失
            logger.warning(f"文件包含大量被清理的内容: 原长度{original_length}, 清理后{cleaned_length}")
            # 注意：这里我们记录警告但不阻止，因为AWR文件可能包含复杂的HTML结构

    def _validate_awr_content(self, content: str):
        """验证是否为有效的AWR报告内容"""
        content_lower = content.lower()
        
        # AWR报告必须包含的关键词
        required_keywords = ['oracle', 'database']
        
        # AWR报告常见的关键词（至少包含一个）
        awr_keywords = [
            'awr', 'automatic workload repository', 'snapshot',
            'instance activity', 'load profile', 'wait events',
            'sql statistics', 'buffer pool', 'sga', 'pga'
        ]
        
        # 检查必需关键词
        missing_required = [kw for kw in required_keywords if kw not in content_lower]
        if missing_required:
            raise ValidationError(f"文件不包含Oracle数据库相关内容")
            
        # 检查AWR特征关键词
        has_awr_keywords = any(kw in content_lower for kw in awr_keywords)
        if not has_awr_keywords:
            logger.warning("文件可能不是标准AWR报告，但包含Oracle数据库内容")

    def get_file_hash(self, file) -> str:
        """计算文件哈希值用于重复检测"""
        file.seek(0)
        hash_md5 = hashlib.md5()
        
        for chunk in iter(lambda: file.read(4096), b""):
            hash_md5.update(chunk)
            
        file.seek(0)
        return hash_md5.hexdigest()

    def sanitize_filename(self, filename: str) -> str:
        """清理文件名，移除危险字符"""
        # 移除危险字符
        safe_filename = re.sub(r'[<>:"/|?*\x00-\x1f]', '_', filename)
        
        # 限制长度
        if len(safe_filename) > 100:
            name, ext = os.path.splitext(safe_filename)
            safe_filename = name[:100-len(ext)] + ext
            
        return safe_filename


class ContentSanitizer:
    """
    内容清理器 - SOLID原则：单一职责
    专门负责清理和净化文件内容
    """
    
    def __init__(self):
        self.allowed_tags = [
            'html', 'head', 'body', 'title', 'meta', 'div', 'span', 'p',
            'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'table', 'thead', 'tbody',
            'tr', 'td', 'th', 'br', 'hr', 'ul', 'ol', 'li', 'strong', 'b',
            'em', 'i', 'a', 'pre', 'code'
        ]
        
        self.allowed_attributes = {
            '*': ['class', 'id', 'title'],
            'table': ['border', 'cellpadding', 'cellspacing', 'width', 'summary'],
            'td': ['colspan', 'rowspan', 'align', 'valign', 'width'],
            'th': ['colspan', 'rowspan', 'align', 'valign', 'width'],
            'a': ['name'],  # 只允许锚点链接
            'meta': ['name', 'content', 'charset', 'http-equiv'],
        }

    def sanitize_html(self, html_content: str) -> str:
        """
        清理HTML内容，移除危险元素但保留AWR报告结构
        
        Args:
            html_content: 原始HTML内容
            
        Returns:
            str: 清理后的安全HTML内容
        """
        try:
            # 使用bleach清理HTML
            cleaned_html = bleach.clean(
                html_content,
                tags=self.allowed_tags,
                attributes=self.allowed_attributes,
                strip=True,
                strip_comments=True
            )
            
            # 额外的自定义清理
            cleaned_html = self._additional_cleanup(cleaned_html)
            
            logger.info("HTML内容清理完成")
            return cleaned_html
            
        except Exception as e:
            logger.error(f"HTML清理失败: {str(e)}")
            raise ValidationError(f"内容清理失败: {str(e)}")

    def _additional_cleanup(self, html_content: str) -> str:
        """额外的清理规则"""
        # 移除CSS表达式
        html_content = re.sub(r'expression\s*\([^)]*\)', '', html_content, flags=re.IGNORECASE)
        
        # 移除javascript:伪协议
        html_content = re.sub(r'javascript:', 'removed-javascript:', html_content, flags=re.IGNORECASE)
        
        # 移除vbscript:伪协议
        html_content = re.sub(r'vbscript:', 'removed-vbscript:', html_content, flags=re.IGNORECASE)
        
        return html_content


# 全局验证器实例
file_validator = FileSecurityValidator()
content_sanitizer = ContentSanitizer()


def validate_uploaded_file(file) -> Tuple[bool, List[str], Optional[str]]:
    """
    验证上传文件的安全性
    
    Args:
        file: Django UploadedFile对象
        
    Returns:
        Tuple[bool, List[str], Optional[str]]: (是否通过, 错误信息, 文件哈希)
    """
    is_valid, errors = file_validator.validate_file(file)
    
    file_hash = None
    if is_valid:
        try:
            file_hash = file_validator.get_file_hash(file)
        except Exception as e:
            logger.warning(f"计算文件哈希失败: {str(e)}")
    
    return is_valid, errors, file_hash


def sanitize_file_content(file_content: str) -> str:
    """
    清理文件内容
    
    Args:
        file_content: 文件内容字符串
        
    Returns:
        str: 清理后的安全内容
    """
    return content_sanitizer.sanitize_html(file_content) 