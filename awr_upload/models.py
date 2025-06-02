"""
Oracle AWR分析器 - 文件上传模块数据模型
{{CHENGQI: P1-LD-003 实现AWRReport和文件上传相关模型 - 2025-06-01 23:20:37 +08:00}}
"""
import os
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


def awr_file_upload_path(instance, filename):
    """AWR文件上传路径生成函数"""
    # 按年/月/日/用户ID组织文件存储
    now = timezone.now()
    return f'awr_files/{now.year}/{now.month:02d}/{now.day:02d}/{instance.uploaded_by.id}/{filename}'


class AWRReport(models.Model):
    """
    AWR报告主模型
    存储AWR报告的基础信息和元数据
    """
    # 基础信息
    name = models.CharField(
        max_length=200,
        verbose_name='报告名称',
        db_comment='用户定义的报告名称'
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='报告描述',
        db_comment='用户对报告的描述信息'
    )
    
    # 文件信息
    original_filename = models.CharField(
        max_length=255,
        verbose_name='原始文件名',
        db_comment='上传时的原始文件名'
    )
    
    file_path = models.FileField(
        upload_to=awr_file_upload_path,
        max_length=500,
        verbose_name='文件路径',
        db_comment='AWR文件在服务器上的存储路径'
    )
    
    file_size = models.PositiveBigIntegerField(
        verbose_name='文件大小',
        db_comment='文件大小（字节）'
    )
    
    file_hash = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='文件哈希',
        db_comment='文件SHA-256哈希值，用于去重和完整性校验'
    )
    
    # Oracle实例信息（从AWR报告中解析）
    oracle_version = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Oracle版本',
        db_comment='Oracle数据库版本，如11g、12c、19c'
    )
    
    instance_name = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='实例名称',
        db_comment='Oracle实例名称'
    )
    
    host_name = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='主机名',
        db_comment='数据库服务器主机名'
    )
    
    database_id = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='数据库ID',
        db_comment='Oracle数据库ID'
    )
    
    instance_number = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name='实例编号',
        db_comment='RAC环境下的实例编号'
    )
    
    # AWR报告时间范围
    snapshot_begin_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='快照开始时间',
        db_comment='AWR报告快照的开始时间'
    )
    
    snapshot_end_time = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='快照结束时间',
        db_comment='AWR报告快照的结束时间'
    )
    
    snapshot_duration_minutes = models.PositiveIntegerField(
        blank=True,
        null=True,
        verbose_name='快照时长(分钟)',
        db_comment='AWR快照时间范围（分钟）'
    )
    
    # 状态管理
    STATUS_CHOICES = [
        ('uploaded', '已上传'),
        ('validating', '校验中'),
        ('validated', '校验完成'),
        ('parsing', '解析中'),
        ('parsed', '解析完成'),
        ('analyzing', '分析中'),
        ('completed', '完成'),
        ('failed', '失败'),
    ]
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='uploaded',
        verbose_name='处理状态',
        db_comment='报告处理流程状态'
    )
    
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='错误信息',
        db_comment='处理失败时的错误详情'
    )
    
    # 关联信息
    uploaded_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='uploaded_reports',
        verbose_name='上传用户',
        db_comment='上传此报告的用户'
    )
    
    # 标签和分类
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name='标签',
        db_comment='用户定义的报告标签'
    )
    
    category = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('production', '生产环境'),
            ('test', '测试环境'),
            ('development', '开发环境'),
            ('staging', '预发布环境'),
        ],
        verbose_name='环境分类',
        db_comment='数据库环境分类'
    )
    
    # 元数据
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        db_comment='报告记录创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        db_comment='报告记录最后更新时间'
    )

    class Meta:
        db_table = 'awranalyzer_awr_report'
        db_table_comment = 'AWR报告主表'
        verbose_name = 'AWR报告'
        verbose_name_plural = 'AWR报告'
        indexes = [
            models.Index(fields=['uploaded_by', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['oracle_version']),
            models.Index(fields=['instance_name']),
            models.Index(fields=['snapshot_begin_time']),
            models.Index(fields=['category']),
        ]
        constraints = [
            models.CheckConstraint(
                check=models.Q(file_size__gt=0),
                name='positive_file_size'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.original_filename})"

    def get_duration_display(self):
        """获取快照时长的友好显示"""
        if self.snapshot_duration_minutes:
            hours = self.snapshot_duration_minutes // 60
            minutes = self.snapshot_duration_minutes % 60
            if hours > 0:
                return f"{hours}小时{minutes}分钟"
            return f"{minutes}分钟"
        return "未知"

    def is_processing(self):
        """检查是否正在处理中"""
        return self.status in ['validating', 'parsing', 'analyzing']

    def is_completed(self):
        """检查是否处理完成"""
        return self.status == 'completed'

    def is_failed(self):
        """检查是否处理失败"""
        return self.status == 'failed'
