"""
Oracle AWR分析器 - 导出功能模块数据模型
{{CHENGQI: P1-LD-003 实现ExportRecord导出记录模型 - 2025-06-01 23:20:37 +08:00}}
"""
import os
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


def export_file_upload_path(instance, filename):
    """导出文件上传路径生成函数"""
    now = timezone.now()
    return f'exports/{now.year}/{now.month:02d}/{now.day:02d}/{instance.created_by.id}/{filename}'


class ExportRecord(models.Model):
    """
    导出记录模型
    存储各种格式的导出任务和结果
    """
    # 基础信息
    name = models.CharField(
        max_length=200,
        verbose_name='导出名称',
        db_comment='用户定义的导出任务名称'
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='导出描述',
        db_comment='导出任务的详细描述'
    )
    
    # 导出类型和格式
    export_type = models.CharField(
        max_length=50,
        choices=[
            ('report', '单个报告导出'),
            ('comparison', '对比分析导出'),
            ('batch_reports', '批量报告导出'),
            ('dashboard', '仪表盘导出'),
            ('custom_data', '自定义数据导出'),
        ],
        verbose_name='导出类型',
        db_comment='导出的内容类型'
    )
    
    export_format = models.CharField(
        max_length=20,
        choices=[
            ('pdf', 'PDF'),
            ('excel', 'Excel'),
            ('csv', 'CSV'),
            ('json', 'JSON'),
            ('html', 'HTML'),
        ],
        verbose_name='导出格式',
        db_comment='导出文件的格式'
    )
    
    # 关联的源数据
    awr_report = models.ForeignKey(
        'awr_upload.AWRReport',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='export_records',
        verbose_name='AWR报告',
        db_comment='导出关联的AWR报告（单报告导出时）'
    )
    
    comparison = models.ForeignKey(
        'comparisons.ReportComparison',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='export_records',
        verbose_name='对比分析',
        db_comment='导出关联的对比分析（对比导出时）'
    )
    
    # 导出配置
    export_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='导出配置',
        db_comment='导出的详细配置参数'
    )
    
    data_filters = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='数据过滤器',
        db_comment='数据筛选和过滤条件'
    )
    
    template_settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='模板设置',
        db_comment='导出模板的配置设置'
    )
    
    # 导出内容范围
    include_sections = models.JSONField(
        default=list,
        blank=True,
        verbose_name='包含章节',
        db_comment='导出中包含的数据章节'
    )
    
    exclude_sections = models.JSONField(
        default=list,
        blank=True,
        verbose_name='排除章节',
        db_comment='导出中排除的数据章节'
    )
    
    # 导出状态
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '等待中'),
            ('processing', '处理中'),
            ('completed', '已完成'),
            ('failed', '失败'),
            ('cancelled', '已取消'),
        ],
        default='pending',
        verbose_name='导出状态',
        db_comment='导出任务的处理状态'
    )
    
    progress_percentage = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='进度百分比',
        db_comment='导出处理的进度百分比'
    )
    
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='错误信息',
        db_comment='导出失败时的错误详情'
    )
    
    # 输出文件信息
    output_filename = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        verbose_name='输出文件名',
        db_comment='生成的导出文件名'
    )
    
    output_file_path = models.FileField(
        upload_to=export_file_upload_path,
        blank=True,
        null=True,
        max_length=500,
        verbose_name='输出文件路径',
        db_comment='导出文件在服务器上的存储路径'
    )
    
    file_size = models.PositiveBigIntegerField(
        blank=True,
        null=True,
        verbose_name='文件大小',
        db_comment='导出文件大小（字节）'
    )
    
    file_hash = models.CharField(
        max_length=64,
        blank=True,
        null=True,
        verbose_name='文件哈希',
        db_comment='导出文件的SHA-256哈希值'
    )
    
    # 访问控制
    is_public = models.BooleanField(
        default=False,
        verbose_name='是否公开',
        db_comment='导出文件是否公开可访问'
    )
    
    download_count = models.PositiveIntegerField(
        default=0,
        verbose_name='下载次数',
        db_comment='文件被下载的次数'
    )
    
    # 过期管理
    expires_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='过期时间',
        db_comment='导出文件的过期时间'
    )
    
    auto_cleanup = models.BooleanField(
        default=True,
        verbose_name='自动清理',
        db_comment='过期后是否自动清理文件'
    )
    
    # 用户信息
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='export_records',
        verbose_name='创建用户',
        db_comment='创建此导出任务的用户'
    )
    
    # 分享设置
    shared_with = models.ManyToManyField(
        User,
        blank=True,
        related_name='shared_exports',
        verbose_name='共享用户'
    )
    
    # 元数据
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        db_comment='导出任务创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        db_comment='导出任务最后更新时间'
    )
    
    started_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='开始时间',
        db_comment='导出处理开始时间'
    )
    
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='完成时间',
        db_comment='导出处理完成时间'
    )

    class Meta:
        db_table = 'awranalyzer_export_record'
        db_table_comment = '导出记录表'
        verbose_name = '导出记录'
        verbose_name_plural = '导出记录'
        indexes = [
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['export_type', 'export_format']),
            models.Index(fields=['expires_at']),
            models.Index(fields=['awr_report']),
            models.Index(fields=['comparison']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(file_size__gte=0),
                name='non_negative_file_size'
            ),
            models.CheckConstraint(
                check=models.Q(download_count__gte=0),
                name='non_negative_download_count'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.export_format.upper()})"

    def get_duration_display(self):
        """获取导出处理时长"""
        if self.completed_at and self.started_at:
            duration = self.completed_at - self.started_at
            total_seconds = int(duration.total_seconds())
            
            if total_seconds < 60:
                return f"{total_seconds}秒"
            elif total_seconds < 3600:
                minutes = total_seconds // 60
                seconds = total_seconds % 60
                return f"{minutes}分{seconds}秒"
            else:
                hours = total_seconds // 3600
                minutes = (total_seconds % 3600) // 60
                return f"{hours}时{minutes}分"
        return "未完成"

    def get_file_size_display(self):
        """获取文件大小的友好显示"""
        if self.file_size:
            if self.file_size < 1024:
                return f"{self.file_size} B"
            elif self.file_size < 1024 * 1024:
                return f"{self.file_size / 1024:.1f} KB"
            elif self.file_size < 1024 * 1024 * 1024:
                return f"{self.file_size / (1024 * 1024):.1f} MB"
            else:
                return f"{self.file_size / (1024 * 1024 * 1024):.1f} GB"
        return "未知"

    def is_processing(self):
        """检查是否正在处理中"""
        return self.status in ['pending', 'processing']

    def is_completed(self):
        """检查是否处理完成"""
        return self.status == 'completed'

    def is_expired(self):
        """检查是否已过期"""
        if self.expires_at:
            return timezone.now() > self.expires_at
        return False

    def can_be_downloaded(self):
        """检查是否可以下载"""
        return self.is_completed() and not self.is_expired() and self.output_file_path

    def increment_download_count(self):
        """增加下载次数"""
        self.download_count += 1
        self.save(update_fields=['download_count'])

    def get_sections_summary(self):
        """获取包含章节的摘要"""
        if self.include_sections:
            return f"包含 {len(self.include_sections)} 个章节"
        return "所有章节"
