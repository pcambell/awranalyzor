"""
Oracle AWR分析器 - 性能分析模块数据模型
{{CHENGQI: P1-LD-003 实现PerformanceMetric性能指标模型 - 2025-06-01 23:20:37 +08:00}}
"""
from django.db import models
from django.contrib.auth.models import User


class PerformanceMetric(models.Model):
    """
    性能指标模型
    存储从AWR报告中提取的各类性能指标数据
    """
    # 关联到AWR报告
    awr_report = models.ForeignKey(
        'awr_upload.AWRReport',
        on_delete=models.CASCADE,
        related_name='performance_metrics',
        verbose_name='AWR报告',
        db_comment='关联的AWR报告'
    )
    
    # 指标分类和基础信息
    metric_category = models.CharField(
        max_length=50,
        choices=[
            ('load_profile', '负载概要'),
            ('instance_efficiency', '实例效率'),
            ('wait_events', '等待事件'),
            ('sql_statistics', 'SQL统计'),
            ('memory_statistics', '内存统计'),
            ('io_statistics', 'IO统计'),
            ('system_statistics', '系统统计'),
            ('time_model', '时间模型'),
            ('rac_statistics', 'RAC统计'),
        ],
        verbose_name='指标分类',
        db_comment='性能指标的分类'
    )
    
    metric_name = models.CharField(
        max_length=100,
        verbose_name='指标名称',
        db_comment='性能指标的具体名称'
    )
    
    metric_unit = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        verbose_name='指标单位',
        db_comment='指标的计量单位，如次/秒、MB、%等'
    )
    
    # 指标数值
    value = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        verbose_name='指标值',
        db_comment='指标的数值'
    )
    
    # 每秒平均值（适用于频率类指标）
    per_second = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='每秒平均值',
        db_comment='指标的每秒平均值'
    )
    
    # 每事务平均值（适用于事务相关指标）
    per_transaction = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='每事务平均值',
        db_comment='指标的每事务平均值'
    )
    
    # 百分比值（适用于比率类指标）
    percentage = models.DecimalField(
        max_digits=6,
        decimal_places=3,
        blank=True,
        null=True,
        verbose_name='百分比',
        db_comment='指标的百分比值'
    )
    
    # 排名信息（适用于Top N类指标）
    rank = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        verbose_name='排名',
        db_comment='在同类指标中的排名'
    )
    
    # 时间相关（适用于等待事件等）
    total_wait_time = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='总等待时间',
        db_comment='总等待时间（秒）'
    )
    
    avg_wait_time = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='平均等待时间',
        db_comment='平均等待时间（毫秒）'
    )
    
    # 额外的上下文信息
    context_info = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='上下文信息',
        db_comment='存储额外的上下文数据，如SQL_ID、对象名等'
    )
    
    # 基准值和阈值
    baseline_value = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='基准值',
        db_comment='该指标的基准值'
    )
    
    warning_threshold = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='警告阈值',
        db_comment='指标的警告阈值'
    )
    
    critical_threshold = models.DecimalField(
        max_digits=20,
        decimal_places=6,
        blank=True,
        null=True,
        verbose_name='严重阈值',
        db_comment='指标的严重问题阈值'
    )
    
    # 状态评估
    status = models.CharField(
        max_length=20,
        choices=[
            ('normal', '正常'),
            ('warning', '警告'),
            ('critical', '严重'),
            ('unknown', '未知'),
        ],
        default='unknown',
        verbose_name='状态',
        db_comment='基于阈值的指标状态评估'
    )
    
    # 元数据
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        db_comment='指标记录创建时间'
    )

    class Meta:
        db_table = 'awranalyzer_performance_metric'
        db_table_comment = '性能指标表'
        verbose_name = '性能指标'
        verbose_name_plural = '性能指标'
        indexes = [
            models.Index(fields=['awr_report', 'metric_category']),
            models.Index(fields=['metric_category', 'metric_name']),
            models.Index(fields=['status']),
            models.Index(fields=['rank']),
        ]
        constraints = [
            # 确保同一报告中的同类指标名称唯一
            models.UniqueConstraint(
                fields=['awr_report', 'metric_category', 'metric_name'],
                name='unique_metric_per_report'
            ),
        ]

    def __str__(self):
        return f"{self.awr_report.name} - {self.metric_name}: {self.value}"

    def get_display_value(self):
        """获取带单位的显示值"""
        if self.metric_unit:
            return f"{self.value} {self.metric_unit}"
        return str(self.value)

    def evaluate_status(self):
        """根据阈值评估指标状态"""
        if self.critical_threshold and self.value >= self.critical_threshold:
            self.status = 'critical'
        elif self.warning_threshold and self.value >= self.warning_threshold:
            self.status = 'warning'
        else:
            self.status = 'normal'
        return self.status

    def get_variance_from_baseline(self):
        """计算与基准值的偏差百分比"""
        if self.baseline_value and self.baseline_value != 0:
            variance = ((self.value - self.baseline_value) / self.baseline_value) * 100
            return round(variance, 2)
        return None


class PerformanceBaseline(models.Model):
    """
    性能基线模型
    存储特定环境或时间段的性能基线数据
    """
    name = models.CharField(
        max_length=100,
        verbose_name='基线名称',
        db_comment='性能基线的名称'
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='基线描述',
        db_comment='基线的详细描述'
    )
    
    # 基线适用条件
    oracle_version = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Oracle版本',
        db_comment='适用的Oracle版本'
    )
    
    instance_pattern = models.CharField(
        max_length=100,
        blank=True,
        null=True,
        verbose_name='实例模式',
        db_comment='适用的实例名称模式（支持通配符）'
    )
    
    environment_type = models.CharField(
        max_length=50,
        blank=True,
        null=True,
        choices=[
            ('production', '生产环境'),
            ('test', '测试环境'),
            ('development', '开发环境'),
            ('staging', '预发布环境'),
        ],
        verbose_name='环境类型',
        db_comment='适用的环境类型'
    )
    
    # 基线数据
    baseline_metrics = models.JSONField(
        default=dict,
        verbose_name='基线指标',
        db_comment='基线的各项性能指标数据'
    )
    
    # 创建信息
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_baselines',
        verbose_name='创建用户',
        db_comment='创建此基线的用户'
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否激活',
        db_comment='基线是否处于激活状态'
    )
    
    # 元数据
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        db_comment='基线创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        db_comment='基线最后更新时间'
    )

    class Meta:
        db_table = 'awranalyzer_performance_baseline'
        db_table_comment = '性能基线表'
        verbose_name = '性能基线'
        verbose_name_plural = '性能基线'
        indexes = [
            models.Index(fields=['oracle_version']),
            models.Index(fields=['environment_type']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.name} ({self.oracle_version or '通用'})"
