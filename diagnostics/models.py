"""
Oracle AWR分析器 - 诊断分析模块数据模型
{{CHENGQI: P1-LD-003 实现AnalysisResult诊断分析结果模型 - 2025-06-01 23:20:37 +08:00}}
"""
from django.db import models
from django.contrib.auth.models import User


class AnalysisResult(models.Model):
    """
    分析结果模型
    存储智能诊断引擎的分析结果和建议
    """
    # 关联到AWR报告
    awr_report = models.ForeignKey(
        'awr_upload.AWRReport',
        on_delete=models.CASCADE,
        related_name='analysis_results',
        verbose_name='AWR报告',
        db_comment='关联的AWR报告'
    )
    
    # 分析类型和级别
    analysis_type = models.CharField(
        max_length=50,
        choices=[
            ('performance_issue', '性能问题'),
            ('resource_bottleneck', '资源瓶颈'),
            ('configuration_issue', '配置问题'),
            ('sql_tuning', 'SQL调优'),
            ('capacity_planning', '容量规划'),
            ('system_health', '系统健康度'),
            ('security_check', '安全检查'),
        ],
        verbose_name='分析类型',
        db_comment='诊断分析的类型分类'
    )
    
    severity = models.CharField(
        max_length=20,
        choices=[
            ('info', '信息'),
            ('low', '低'),
            ('medium', '中'),
            ('high', '高'),
            ('critical', '严重'),
        ],
        default='info',
        verbose_name='严重程度',
        db_comment='问题的严重程度等级'
    )
    
    # 诊断规则信息
    rule_name = models.CharField(
        max_length=100,
        verbose_name='规则名称',
        db_comment='触发此分析结果的诊断规则名称'
    )
    
    rule_category = models.CharField(
        max_length=50,
        verbose_name='规则分类',
        db_comment='诊断规则的分类'
    )
    
    rule_version = models.CharField(
        max_length=20,
        default='1.0',
        verbose_name='规则版本',
        db_comment='诊断规则的版本号'
    )
    
    # 问题描述
    title = models.CharField(
        max_length=200,
        verbose_name='问题标题',
        db_comment='分析发现的问题标题'
    )
    
    description = models.TextField(
        verbose_name='问题描述',
        db_comment='详细的问题描述和分析'
    )
    
    # 影响评估
    impact_description = models.TextField(
        blank=True,
        null=True,
        verbose_name='影响说明',
        db_comment='问题可能造成的影响描述'
    )
    
    affected_metrics = models.JSONField(
        default=list,
        blank=True,
        verbose_name='受影响指标',
        db_comment='问题影响的性能指标列表'
    )
    
    # 根因分析
    root_cause = models.TextField(
        blank=True,
        null=True,
        verbose_name='根本原因',
        db_comment='问题的根本原因分析'
    )
    
    evidence_data = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='证据数据',
        db_comment='支持诊断结论的证据数据'
    )
    
    # 建议措施
    recommendations = models.JSONField(
        default=list,
        verbose_name='建议措施',
        db_comment='解决问题的建议措施列表'
    )
    
    priority = models.PositiveSmallIntegerField(
        default=5,
        verbose_name='优先级',
        db_comment='建议措施的执行优先级（1-10，1最高）'
    )
    
    # 预期效果
    expected_improvement = models.TextField(
        blank=True,
        null=True,
        verbose_name='预期改善',
        db_comment='执行建议后的预期改善效果'
    )
    
    estimated_impact = models.CharField(
        max_length=20,
        choices=[
            ('low', '低'),
            ('medium', '中'),
            ('high', '高'),
        ],
        blank=True,
        null=True,
        verbose_name='预估影响',
        db_comment='执行建议的预估性能影响程度'
    )
    
    # 状态跟踪
    status = models.CharField(
        max_length=20,
        choices=[
            ('new', '新发现'),
            ('acknowledged', '已确认'),
            ('in_progress', '处理中'),
            ('resolved', '已解决'),
            ('ignored', '已忽略'),
        ],
        default='new',
        verbose_name='处理状态',
        db_comment='分析结果的处理状态'
    )
    
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_analysis_results',
        verbose_name='负责人',
        db_comment='负责处理此问题的用户'
    )
    
    # 用户反馈
    user_feedback = models.TextField(
        blank=True,
        null=True,
        verbose_name='用户反馈',
        db_comment='用户对分析结果的反馈'
    )
    
    feedback_rating = models.PositiveSmallIntegerField(
        blank=True,
        null=True,
        choices=[
            (1, '很差'),
            (2, '差'),
            (3, '一般'),
            (4, '好'),
            (5, '很好'),
        ],
        verbose_name='反馈评分',
        db_comment='用户对分析结果的评分（1-5）'
    )
    
    # 元数据
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        db_comment='分析结果创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        db_comment='分析结果最后更新时间'
    )

    class Meta:
        db_table = 'awranalyzer_analysis_result'
        db_table_comment = '诊断分析结果表'
        verbose_name = '分析结果'
        verbose_name_plural = '分析结果'
        indexes = [
            models.Index(fields=['awr_report', 'severity']),
            models.Index(fields=['analysis_type', 'severity']),
            models.Index(fields=['status']),
            models.Index(fields=['priority']),
            models.Index(fields=['rule_name']),
        ]
        ordering = ['-severity', 'priority', '-created_at']

    def __str__(self):
        return f"{self.awr_report.name} - {self.title} ({self.severity})"

    def get_severity_display_color(self):
        """获取严重程度对应的显示颜色"""
        color_map = {
            'info': 'blue',
            'low': 'green',
            'medium': 'orange',
            'high': 'red',
            'critical': 'darkred',
        }
        return color_map.get(self.severity, 'gray')

    def is_actionable(self):
        """检查是否需要采取行动"""
        return self.severity in ['medium', 'high', 'critical']

    def get_recommendations_count(self):
        """获取建议措施数量"""
        return len(self.recommendations) if self.recommendations else 0


class DiagnosticRule(models.Model):
    """
    诊断规则模型
    定义智能诊断引擎使用的规则配置
    """
    # 规则基础信息
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='规则名称',
        db_comment='诊断规则的唯一名称'
    )
    
    category = models.CharField(
        max_length=50,
        verbose_name='规则分类',
        db_comment='诊断规则的分类'
    )
    
    description = models.TextField(
        verbose_name='规则描述',
        db_comment='规则的详细描述'
    )
    
    version = models.CharField(
        max_length=20,
        default='1.0',
        verbose_name='规则版本',
        db_comment='规则的版本号'
    )
    
    # 规则配置
    rule_logic = models.JSONField(
        verbose_name='规则逻辑',
        db_comment='规则的判断逻辑配置'
    )
    
    thresholds = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='阈值配置',
        db_comment='规则使用的各种阈值参数'
    )
    
    # 适用条件
    applicable_versions = models.JSONField(
        default=list,
        blank=True,
        verbose_name='适用版本',
        db_comment='规则适用的Oracle版本列表'
    )
    
    applicable_environments = models.JSONField(
        default=list,
        blank=True,
        verbose_name='适用环境',
        db_comment='规则适用的环境类型列表'
    )
    
    # 规则状态
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否激活',
        db_comment='规则是否处于激活状态'
    )
    
    priority = models.PositiveSmallIntegerField(
        default=5,
        verbose_name='执行优先级',
        db_comment='规则的执行优先级（1-10，1最高）'
    )
    
    # 统计信息
    execution_count = models.PositiveIntegerField(
        default=0,
        verbose_name='执行次数',
        db_comment='规则的累计执行次数'
    )
    
    hit_count = models.PositiveIntegerField(
        default=0,
        verbose_name='命中次数',
        db_comment='规则的累计命中次数'
    )
    
    # 创建信息
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='created_rules',
        verbose_name='创建用户',
        db_comment='创建此规则的用户'
    )
    
    # 元数据
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        db_comment='规则创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        db_comment='规则最后更新时间'
    )

    class Meta:
        db_table = 'awranalyzer_diagnostic_rule'
        db_table_comment = '诊断规则配置表'
        verbose_name = '诊断规则'
        verbose_name_plural = '诊断规则'
        indexes = [
            models.Index(fields=['category', 'is_active']),
            models.Index(fields=['priority']),
        ]
        ordering = ['priority', 'category', 'name']

    def __str__(self):
        return f"{self.name} (v{self.version})"

    def get_hit_rate(self):
        """计算规则命中率"""
        if self.execution_count > 0:
            return round((self.hit_count / self.execution_count) * 100, 2)
        return 0.0

    def increment_execution(self, hit=False):
        """增加执行统计"""
        self.execution_count += 1
        if hit:
            self.hit_count += 1
        self.save(update_fields=['execution_count', 'hit_count'])
