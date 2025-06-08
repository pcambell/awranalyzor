"""
Oracle AWR分析器 - 报告对比模块数据模型
{{CHENGQI: P1-LD-003 实现ReportComparison报告对比模型 - 2025-06-01 23:20:37 +08:00}}
"""
from django.db import models
from django.contrib.auth.models import User


class ReportComparison(models.Model):
    """
    报告对比模型
    存储AWR报告间的对比分析数据
    """
    # 基础信息
    name = models.CharField(
        max_length=200,
        verbose_name='对比名称',
        db_comment='用户定义的对比分析名称'
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='对比描述',
        db_comment='对比分析的详细描述'
    )
    
    # 对比报告（基准报告）
    baseline_report = models.ForeignKey(
        'awr_upload.AWRReport',
        on_delete=models.CASCADE,
        related_name='baseline_comparisons',
        verbose_name='基准报告',
        db_comment='作为基准的AWR报告'
    )
    
    # 对比报告（目标报告）
    target_report = models.ForeignKey(
        'awr_upload.AWRReport',
        on_delete=models.CASCADE,
        related_name='target_comparisons',
        verbose_name='目标报告',
        db_comment='被对比的AWR报告'
    )
    
    # 对比类型和范围
    comparison_type = models.CharField(
        max_length=50,
        choices=[
            ('full', '全面对比'),
            ('performance', '性能对比'),
            ('wait_events', '等待事件对比'),
            ('sql_analysis', 'SQL分析对比'),
            ('resource_usage', '资源使用对比'),
            ('custom', '自定义对比'),
        ],
        default='full',
        verbose_name='对比类型',
        db_comment='对比分析的类型'
    )
    
    comparison_scope = models.JSONField(
        default=list,
        blank=True,
        verbose_name='对比范围',
        db_comment='指定的对比指标范围'
    )
    
    # 对比结果概要
    overall_assessment = models.CharField(
        max_length=50,
        choices=[
            ('improved', '性能改善'),
            ('degraded', '性能下降'),
            ('stable', '性能稳定'),
            ('mixed', '有升有降'),
            ('inconclusive', '无明确结论'),
        ],
        blank=True,
        null=True,
        verbose_name='总体评估',
        db_comment='对比的总体性能评估结果'
    )
    
    improvement_score = models.DecimalField(
        max_digits=6,
        decimal_places=2,
        blank=True,
        null=True,
        verbose_name='改善评分',
        db_comment='性能改善评分（-100到100，正数表示改善）'
    )
    
    # 关键差异指标
    key_differences = models.JSONField(
        default=list,
        blank=True,
        verbose_name='关键差异',
        db_comment='对比中发现的关键性能差异'
    )
    
    significant_changes = models.JSONField(
        default=list,
        blank=True,
        verbose_name='显著变化',
        db_comment='显著的性能指标变化'
    )
    
    # 详细对比数据
    metric_comparisons = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='指标对比',
        db_comment='详细的指标对比数据'
    )
    
    wait_event_comparisons = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='等待事件对比',
        db_comment='等待事件的对比分析'
    )
    
    sql_comparisons = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='SQL对比',
        db_comment='SQL性能的对比分析'
    )
    
    # 对比配置
    comparison_config = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='对比配置',
        db_comment='对比分析的配置参数'
    )
    
    threshold_settings = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='阈值设置',
        db_comment='判断显著变化的阈值设置'
    )
    
    # 状态管理
    status = models.CharField(
        max_length=20,
        choices=[
            ('pending', '待处理'),
            ('processing', '处理中'),
            ('completed', '已完成'),
            ('failed', '失败'),
        ],
        default='pending',
        verbose_name='处理状态',
        db_comment='对比分析的处理状态'
    )
    
    error_message = models.TextField(
        blank=True,
        null=True,
        verbose_name='错误信息',
        db_comment='处理失败时的错误信息'
    )
    
    progress_percentage = models.PositiveSmallIntegerField(
        default=0,
        verbose_name='进度百分比',
        db_comment='对比处理的进度百分比'
    )
    
    # 用户信息
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_comparisons',
        verbose_name='创建用户',
        db_comment='创建此对比的用户'
    )
    
    # 分享和协作
    is_shared = models.BooleanField(
        default=False,
        verbose_name='是否共享',
        db_comment='对比结果是否与其他用户共享'
    )
    
    shared_with = models.ManyToManyField(
        User,
        blank=True,
        related_name='shared_comparisons',
        verbose_name='共享用户'
    )
    
    # 标签和分类
    tags = models.JSONField(
        default=list,
        blank=True,
        verbose_name='标签',
        db_comment='用户定义的对比标签'
    )
    
    # 元数据
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        db_comment='对比记录创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        db_comment='对比记录最后更新时间'
    )
    
    completed_at = models.DateTimeField(
        blank=True,
        null=True,
        verbose_name='完成时间',
        db_comment='对比分析完成时间'
    )

    class Meta:
        db_table = 'awranalyzer_report_comparison'
        db_table_comment = '报告对比表'
        verbose_name = '报告对比'
        verbose_name_plural = '报告对比'
        indexes = [
            models.Index(fields=['created_by', 'created_at']),
            models.Index(fields=['status']),
            models.Index(fields=['comparison_type']),
            models.Index(fields=['baseline_report']),
            models.Index(fields=['target_report']),
        ]
        constraints = [
            # 确保不能对比同一个报告
            models.CheckConstraint(
                check=~models.Q(baseline_report=models.F('target_report')),
                name='different_reports_only'
            ),
        ]

    def __str__(self):
        return f"{self.name} ({self.baseline_report.name} vs {self.target_report.name})"

    def get_duration_display(self):
        """获取对比处理时长"""
        if self.completed_at and self.created_at:
            duration = self.completed_at - self.created_at
            total_seconds = int(duration.total_seconds())
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            seconds = total_seconds % 60
            
            if hours > 0:
                return f"{hours}时{minutes}分{seconds}秒"
            elif minutes > 0:
                return f"{minutes}分{seconds}秒"
            else:
                return f"{seconds}秒"
        return "未完成"

    def is_processing(self):
        """检查是否正在处理中"""
        return self.status in ['pending', 'processing']

    def is_completed(self):
        """检查是否处理完成"""
        return self.status == 'completed'

    def get_key_differences_count(self):
        """获取关键差异数量"""
        return len(self.key_differences) if self.key_differences else 0

    def get_improvement_trend(self):
        """获取改善趋势描述"""
        if self.improvement_score is None:
            return "未评估"
        elif self.improvement_score > 10:
            return "显著改善"
        elif self.improvement_score > 5:
            return "轻微改善"
        elif self.improvement_score > -5:
            return "基本稳定"
        elif self.improvement_score > -10:
            return "轻微下降"
        else:
            return "显著下降"
