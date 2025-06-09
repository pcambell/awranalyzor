#!/usr/bin/env python3
"""
AWR上传服务层
{{CHENGQI: P2-LD-005 解析器工厂和集成 - Django文件存储集成 - 2025-06-02T14:40:00}}
{{CHENGQI: 扩展文件验证逻辑支持ASH报告 - 2025-06-09 19:12:20 +08:00 - 
Action: Modified; Reason: 修复文件验证逻辑以支持ASH报告识别，避免有效的Oracle性能报告被错误拒绝; Principle_Applied: 业务逻辑完整性}}
{{CHENGQI: 增强AWR文件验证鲁棒性 - 2025-06-09 19:32:31 +08:00 - 
Action: Modified; Reason: BUGFIX-004解决有效AWR报告被错误拒绝问题，增加多编码支持、扩大检测范围至16KB、增强关键词检测逻辑; Principle_Applied: 容错性、可用性}}

提供文件上传、验证、解析调度等服务
"""

import hashlib
import logging
import os
from typing import Optional, Dict, Any, Union
from django.conf import settings
from django.core.files.uploadedfile import UploadedFile
from django.contrib.auth.models import User
from django.db import transaction
from django.utils import timezone

from .models import AWRReport
from awr_parser.parsers.factory import create_parser, parse_awr
from awr_parser.parsers.base import ParseResult, OracleVersion

logger = logging.getLogger(__name__)


class AWRFileValidationError(Exception):
    """AWR文件验证错误"""
    pass


class AWRParsingError(Exception):
    """AWR解析错误"""
    pass


class AWRUploadService:
    """
    AWR文件上传和处理服务
    
    负责文件上传、验证、基础信息提取和异步解析调度
    """
    
    def __init__(self):
        self.max_file_size = getattr(settings, 'AWR_SETTINGS', {}).get('MAX_FILE_SIZE', 50 * 1024 * 1024)
        self.allowed_extensions = getattr(settings, 'AWR_SETTINGS', {}).get('ALLOWED_FILE_TYPES', ['.html', '.htm'])
    
    def validate_file(self, uploaded_file: UploadedFile) -> Dict[str, Any]:
        """
        验证上传的AWR文件
        
        Args:
            uploaded_file: Django UploadedFile对象
            
        Returns:
            Dict包含验证信息
            
        Raises:
            AWRFileValidationError: 文件验证失败
        """
        errors = []
        
        # 文件大小检查
        if uploaded_file.size > self.max_file_size:
            errors.append(f"文件大小 {uploaded_file.size} 字节超过限制 {self.max_file_size} 字节")
        
        # 文件扩展名检查
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        if file_ext not in self.allowed_extensions:
            errors.append(f"不支持的文件类型 {file_ext}，仅支持 {', '.join(self.allowed_extensions)}")
        
        # 基础内容检查
        try:
            # 读取文件开头进行基础验证 - 增加读取量和编码兼容性
            uploaded_file.seek(0)
            
            # 尝试多种编码方式
            content_sample = None
            encodings = ['utf-8', 'utf-8-sig', 'latin-1', 'cp1252', 'iso-8859-1']
            
            for encoding in encodings:
                try:
                    uploaded_file.seek(0)
                    raw_content = uploaded_file.read(16384)  # 增加到16KB
                    content_sample = raw_content.decode(encoding, errors='ignore')
                    break
                except Exception:
                    continue
            
            if content_sample is None:
                # 最后兜底方案
                uploaded_file.seek(0)
                content_sample = uploaded_file.read(16384).decode('utf-8', errors='replace')
            
            uploaded_file.seek(0)  # 重置文件指针
            
            # 检查是否为Oracle AWR或ASH报告 - 扩展检测逻辑
            content_lower = content_sample.lower()
            
            # AWR报告检测
            is_awr_report = (
                'workload repository' in content_lower or
                'awr report' in content_lower or
                ('automatic workload repository' in content_lower)
            )
            
            # ASH报告检测
            is_ash_report = (
                'ash report' in content_lower or
                'active session history' in content_lower or
                ('ash report for' in content_lower)
            )
            
            # 通用Oracle报告检测
            is_oracle_report = (
                'oracle' in content_lower and (
                    'report' in content_lower or 
                    'database' in content_lower or
                    'instance' in content_lower
                )
            )
            
            # 进一步的Oracle特征检测
            oracle_features = (
                'db name' in content_lower or
                'db id' in content_lower or
                'instance name' in content_lower or
                'host name' in content_lower or
                'snap id' in content_lower or
                'begin snap' in content_lower or
                'end snap' in content_lower or
                'oracle database' in content_lower
            )
            
            logger.debug(f"文件验证检测结果 - AWR: {is_awr_report}, ASH: {is_ash_report}, Oracle通用: {is_oracle_report}, Oracle特征: {oracle_features}")
            
            # 临时调试输出
            print(f"[DEBUG] 文件验证检测结果:")
            print(f"[DEBUG]   AWR报告: {is_awr_report}")
            print(f"[DEBUG]   ASH报告: {is_ash_report}")
            print(f"[DEBUG]   Oracle通用: {is_oracle_report}")
            print(f"[DEBUG]   Oracle特征: {oracle_features}")
            print(f"[DEBUG]   总体通过: {is_awr_report or is_ash_report or is_oracle_report or oracle_features}")
            print(f"[DEBUG]   content_sample长度: {len(content_sample)}")
            print(f"[DEBUG]   content_sample前200字符: {content_sample[:200]}")
            
            if not (is_awr_report or is_ash_report or is_oracle_report or oracle_features):
                errors.append("文件内容不像是Oracle AWR/ASH报告")
                
        except Exception as e:
            logger.error(f"读取文件内容时出错: {str(e)}")
            errors.append(f"读取文件内容时出错: {str(e)}")
        
        if errors:
            raise AWRFileValidationError('; '.join(errors))
        
        return {
            'size': uploaded_file.size,
            'name': uploaded_file.name,
            'content_type': uploaded_file.content_type,
            'valid': True
        }
    
    def calculate_file_hash(self, uploaded_file: UploadedFile) -> str:
        """
        计算文件的SHA-256哈希值
        
        Args:
            uploaded_file: Django UploadedFile对象
            
        Returns:
            文件的十六进制哈希值
        """
        hash_sha256 = hashlib.sha256()
        uploaded_file.seek(0)
        
        for chunk in uploaded_file.chunks():
            hash_sha256.update(chunk)
        
        uploaded_file.seek(0)  # 重置文件指针
        return hash_sha256.hexdigest()
    
    def extract_basic_info(self, file_content: str) -> Dict[str, Any]:
        """
        从AWR内容中提取基础信息
        
        Args:
            file_content: AWR HTML内容
            
        Returns:
            Dict包含提取的基础信息
        """
        try:
            # 使用解析器工厂进行初步解析
            parser = create_parser(file_content)
            if parser is None:
                logger.warning("无法创建解析器，返回默认信息")
                return {}
            
            # 快速提取基础信息（不进行完整解析）
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(file_content, 'html.parser')
            
            info = {}
            
            # 提取Oracle版本信息
            try:
                db_info = parser.parse_db_info(soup)
                if db_info:
                    info.update({
                        'oracle_version': db_info.version.value if db_info.version != OracleVersion.UNKNOWN else None,
                        'instance_name': db_info.instance_name,
                        'database_id': db_info.db_name,
                    })
            except Exception as e:
                logger.debug(f"提取数据库信息时出错: {e}")
            
            # 提取快照时间信息
            try:
                snapshot_info = parser.parse_snapshot_info(soup)
                if snapshot_info:
                    info.update({
                        'snapshot_begin_time': snapshot_info.begin_time,
                        'snapshot_end_time': snapshot_info.end_time,
                        'snapshot_duration_minutes': snapshot_info.elapsed_time_minutes,
                    })
            except Exception as e:
                logger.debug(f"提取快照信息时出错: {e}")
            
            return info
            
        except Exception as e:
            logger.error(f"提取基础信息时出错: {e}")
            return {}
    
    @transaction.atomic
    def create_awr_report(
        self, 
        uploaded_file: UploadedFile, 
        user: User,
        name: str = None,
        description: str = None,
        category: str = None,
        tags: list = None
    ) -> AWRReport:
        """
        创建AWR报告记录
        
        Args:
            uploaded_file: 上传的文件
            user: 上传用户
            name: 报告名称
            description: 报告描述
            category: 环境分类
            tags: 标签列表
            
        Returns:
            创建的AWRReport实例
            
        Raises:
            AWRFileValidationError: 文件验证失败
        """
        # 文件验证
        validation_info = self.validate_file(uploaded_file)
        
        # 计算文件哈希
        file_hash = self.calculate_file_hash(uploaded_file)
        
        # 检查是否已存在相同文件
        existing_report = AWRReport.objects.filter(file_hash=file_hash).first()
        if existing_report:
            raise AWRFileValidationError(f"文件已存在，关联报告: {existing_report.name}")
        
        # 读取文件内容提取基础信息
        uploaded_file.seek(0)
        content = uploaded_file.read().decode('utf-8', errors='ignore')
        uploaded_file.seek(0)
        
        basic_info = self.extract_basic_info(content)
        
        # 创建AWR报告记录
        awr_report = AWRReport.objects.create(
            name=name or f"AWR报告 - {uploaded_file.name}",
            description=description or "",
            original_filename=uploaded_file.name,
            file_path=uploaded_file,  # Django会自动处理文件存储
            file_size=uploaded_file.size,
            file_hash=file_hash,
            uploaded_by=user,
            category=category,
            tags=tags or [],
            status='uploaded',
            **basic_info  # 合并提取的基础信息
        )
        
        logger.info(f"AWR报告创建成功: {awr_report.id} - {awr_report.name}")
        return awr_report
    
    def update_report_status(
        self, 
        report: AWRReport, 
        status: str, 
        error_message: str = None
    ) -> AWRReport:
        """
        更新报告状态
        
        Args:
            report: AWR报告实例
            status: 新状态
            error_message: 错误信息（如果状态为失败）
            
        Returns:
            更新后的AWRReport实例
        """
        report.status = status
        if error_message:
            report.error_message = error_message
        report.save(update_fields=['status', 'error_message', 'updated_at'])
        
        logger.info(f"报告 {report.id} 状态更新为: {status}")
        return report
    
    def schedule_parsing(self, report: AWRReport) -> bool:
        """
        调度异步解析任务
        
        Args:
            report: AWR报告实例
            
        Returns:
            是否成功调度任务
        """
        try:
            # 使用任务调度器
            from .tasks import schedule_awr_parsing
            
            success = schedule_awr_parsing(report.id)
            
            if success:
                logger.info(f"AWR报告 {report.id} 解析任务调度成功")
            else:
                self.update_report_status(report, 'failed', '调度解析任务失败')
                logger.error(f"AWR报告 {report.id} 解析任务调度失败")
            
            return success
            
        except Exception as e:
            logger.error(f"调度解析任务失败: {e}")
            self.update_report_status(report, 'failed', str(e))
            return False


class AWRParsingService:
    """
    AWR解析服务
    
    负责调用解析器并处理解析结果
    """
    
    def parse_report(self, report: AWRReport) -> ParseResult:
        """
        解析AWR报告
        
        Args:
            report: AWR报告实例
            
        Returns:
            解析结果
            
        Raises:
            AWRParsingError: 解析失败
        """
        try:
            # 读取文件内容
            with open(report.file_path.path, 'r', encoding='utf-8') as file:
                content = file.read()
            
            # 使用解析器工厂进行解析
            result = parse_awr(content)
            
            if result.parse_status.value == 'failed':
                error_msg = '; '.join([f"{err.error_type}: {err.message}" for err in result.errors])
                raise AWRParsingError(f"解析失败: {error_msg}")
            
            logger.info(f"AWR报告 {report.id} 解析成功")
            return result
            
        except Exception as e:
            logger.error(f"解析AWR报告 {report.id} 时出错: {e}")
            raise AWRParsingError(str(e))
    
    def store_parse_result(self, report: AWRReport, result: ParseResult) -> bool:
        """
        存储解析结果到数据库
        
        Args:
            report: AWR报告实例
            result: 解析结果
            
        Returns:
            是否成功存储
        """
        try:
            # 更新AWR报告的解析信息
            if result.db_info:
                report.oracle_version = result.db_info.version.value
                report.instance_name = result.db_info.instance_name
                report.database_id = result.db_info.db_name
            
            if result.snapshot_info:
                report.snapshot_begin_time = result.snapshot_info.begin_time
                report.snapshot_end_time = result.snapshot_info.end_time
                report.snapshot_duration_minutes = result.snapshot_info.elapsed_time_minutes
            
            report.status = 'parsed'
            report.save()
            
            # TODO: 将详细的解析结果存储到相关表中
            # 这部分将在步骤4中实现
            
            logger.info(f"解析结果存储成功: 报告 {report.id}")
            return True
            
        except Exception as e:
            logger.error(f"存储解析结果失败: {e}")
            report.status = 'failed'
            report.error_message = str(e)
            report.save()
            return False 