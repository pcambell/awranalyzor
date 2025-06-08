"""
Oracle AWR分析器 - 用户管理模块数据模型
{{CHENGQI: P1-LD-003 实现UserProfile模型，扩展Django用户系统 - 2025-06-01 23:20:37 +08:00}}
"""
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class UserProfile(models.Model):
    """
    用户配置文件模型，扩展Django默认User模型
    存储AWR分析器特定的用户配置信息
    """
    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
        verbose_name='关联用户',
        db_comment='关联到Django内置用户表'
    )
    
    # 组织信息
    organization = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='组织机构',
        db_comment='用户所属组织或公司名称'
    )
    
    department = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='部门',
        db_comment='用户所属部门'
    )
    
    # 系统偏好设置
    user_timezone = models.CharField(
        max_length=50,
        default='Asia/Shanghai',
        verbose_name='时区',
        db_comment='用户偏好时区设置'
    )
    
    language = models.CharField(
        max_length=10,
        default='zh-hans',
        choices=[
            ('zh-hans', '简体中文'),
            ('en', 'English'),
        ],
        verbose_name='语言',
        db_comment='用户界面语言偏好'
    )
    
    # AWR分析偏好
    default_analysis_scope = models.CharField(
        max_length=20,
        default='comprehensive',
        choices=[
            ('basic', '基础分析'),
            ('standard', '标准分析'),
            ('comprehensive', '全面分析'),
        ],
        verbose_name='默认分析范围',
        db_comment='用户偏好的默认分析深度'
    )
    
    auto_diagnostic = models.BooleanField(
        default=True,
        verbose_name='自动诊断',
        db_comment='是否自动执行诊断规则'
    )
    
    # 通知设置
    email_notifications = models.BooleanField(
        default=True,
        verbose_name='邮件通知',
        db_comment='是否接收邮件通知'
    )
    
    notification_types = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='通知类型配置',
        db_comment='详细的通知类型偏好设置'
    )
    
    # 统计信息
    reports_uploaded = models.PositiveIntegerField(
        default=0,
        verbose_name='上传报告数',
        db_comment='用户累计上传的AWR报告数量'
    )
    
    last_activity = models.DateTimeField(
        default=timezone.now,
        verbose_name='最后活动时间',
        db_comment='用户最后一次活动的时间戳'
    )
    
    # 元数据
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        db_comment='用户配置文件创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        db_comment='用户配置文件最后更新时间'
    )

    class Meta:
        db_table = 'awranalyzer_user_profile'
        db_table_comment = 'AWR分析器用户配置文件表'
        verbose_name = '用户配置文件'
        verbose_name_plural = '用户配置文件'
        indexes = [
            models.Index(fields=['organization']),
            models.Index(fields=['last_activity']),
        ]

    def __str__(self):
        return f"{self.user.username} - {self.organization or '未设置组织'}"

    def update_activity(self):
        """更新用户最后活动时间"""
        self.last_activity = timezone.now()
        self.save(update_fields=['last_activity'])

    def increment_reports_count(self):
        """增加用户上传报告计数"""
        self.reports_uploaded += 1
        self.save(update_fields=['reports_uploaded'])
