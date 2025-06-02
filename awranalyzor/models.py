"""
Oracle AWR分析器 - 系统配置模块数据模型
{{CHENGQI: P1-LD-003 实现SystemConfiguration系统配置模型 - 2025-06-01 23:20:37 +08:00}}
"""
from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone


class SystemConfiguration(models.Model):
    """
    系统配置模型
    存储AWR分析器的全局配置和参数
    """
    # 配置基础信息
    config_key = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='配置键',
        db_comment='配置项的唯一标识符'
    )
    
    config_name = models.CharField(
        max_length=200,
        verbose_name='配置名称',
        db_comment='配置项的显示名称'
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='配置描述',
        db_comment='配置项的详细说明'
    )
    
    # 配置分类
    category = models.CharField(
        max_length=50,
        choices=[
            ('system', '系统配置'),
            ('parser', '解析器配置'),
            ('analysis', '分析配置'),
            ('export', '导出配置'),
            ('notification', '通知配置'),
            ('security', '安全配置'),
            ('performance', '性能配置'),
            ('ui', '界面配置'),
        ],
        verbose_name='配置分类',
        db_comment='配置项的分类'
    )
    
    # 配置值和类型
    config_value = models.TextField(
        verbose_name='配置值',
        db_comment='配置项的值（JSON格式存储）'
    )
    
    value_type = models.CharField(
        max_length=20,
        choices=[
            ('string', '字符串'),
            ('integer', '整数'),
            ('float', '浮点数'),
            ('boolean', '布尔值'),
            ('json', 'JSON对象'),
            ('list', '列表'),
        ],
        default='string',
        verbose_name='值类型',
        db_comment='配置值的数据类型'
    )
    
    # 默认值
    default_value = models.TextField(
        blank=True,
        null=True,
        verbose_name='默认值',
        db_comment='配置项的默认值'
    )
    
    # 验证规则
    validation_rules = models.JSONField(
        default=dict,
        blank=True,
        verbose_name='验证规则',
        db_comment='配置值的验证规则'
    )
    
    # 配置属性
    is_system_config = models.BooleanField(
        default=False,
        verbose_name='系统配置',
        db_comment='是否为系统级配置（影响所有用户）'
    )
    
    is_user_configurable = models.BooleanField(
        default=True,
        verbose_name='用户可配置',
        db_comment='普通用户是否可以修改此配置'
    )
    
    is_sensitive = models.BooleanField(
        default=False,
        verbose_name='敏感配置',
        db_comment='是否为敏感配置（如密码、密钥等）'
    )
    
    requires_restart = models.BooleanField(
        default=False,
        verbose_name='需要重启',
        db_comment='修改此配置是否需要重启系统'
    )
    
    # 配置状态
    is_active = models.BooleanField(
        default=True,
        verbose_name='是否激活',
        db_comment='配置项是否处于激活状态'
    )
    
    is_readonly = models.BooleanField(
        default=False,
        verbose_name='只读配置',
        db_comment='是否为只读配置'
    )
    
    # 版本和环境
    config_version = models.CharField(
        max_length=20,
        default='1.0',
        verbose_name='配置版本',
        db_comment='配置项的版本号'
    )
    
    applicable_environments = models.JSONField(
        default=list,
        blank=True,
        verbose_name='适用环境',
        db_comment='配置适用的环境列表'
    )
    
    # 访问控制
    access_level = models.CharField(
        max_length=20,
        choices=[
            ('public', '公开'),
            ('user', '用户级'),
            ('admin', '管理员'),
            ('system', '系统级'),
        ],
        default='user',
        verbose_name='访问级别',
        db_comment='配置的访问权限级别'
    )
    
    # 变更追踪
    last_modified_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='modified_configs',
        verbose_name='最后修改者',
        db_comment='最后修改此配置的用户'
    )
    
    modification_reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='修改原因',
        db_comment='最近一次修改的原因'
    )
    
    # 元数据
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='创建时间',
        db_comment='配置项创建时间'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='更新时间',
        db_comment='配置项最后更新时间'
    )

    class Meta:
        db_table = 'awranalyzer_system_configuration'
        db_table_comment = '系统配置表'
        verbose_name = '系统配置'
        verbose_name_plural = '系统配置'
        indexes = [
            models.Index(fields=['category']),
            models.Index(fields=['is_system_config']),
            models.Index(fields=['access_level']),
            models.Index(fields=['is_active']),
        ]
        ordering = ['category', 'config_key']

    def __str__(self):
        return f"{self.config_name} ({self.config_key})"

    def get_typed_value(self):
        """获取类型化的配置值"""
        import json
        
        if self.value_type == 'boolean':
            return self.config_value.lower() in ('true', '1', 'yes', 'on')
        elif self.value_type == 'integer':
            try:
                return int(self.config_value)
            except ValueError:
                return None
        elif self.value_type == 'float':
            try:
                return float(self.config_value)
            except ValueError:
                return None
        elif self.value_type in ('json', 'list'):
            try:
                return json.loads(self.config_value)
            except json.JSONDecodeError:
                return None
        else:
            return self.config_value

    def set_typed_value(self, value):
        """设置类型化的配置值"""
        import json
        
        if self.value_type == 'boolean':
            self.config_value = str(bool(value)).lower()
        elif self.value_type in ('integer', 'float'):
            self.config_value = str(value)
        elif self.value_type in ('json', 'list'):
            self.config_value = json.dumps(value, ensure_ascii=False)
        else:
            self.config_value = str(value)

    def validate_value(self, value):
        """验证配置值是否符合规则"""
        if not self.validation_rules:
            return True, None
        
        # 这里可以实现具体的验证逻辑
        # 例如：范围检查、格式验证等
        return True, None

    def is_modifiable_by_user(self, user):
        """检查用户是否可以修改此配置"""
        if self.is_readonly:
            return False
        
        if not self.is_user_configurable:
            return user.is_staff or user.is_superuser
        
        if self.access_level == 'system':
            return user.is_superuser
        elif self.access_level == 'admin':
            return user.is_staff
        
        return True

    def get_display_value(self):
        """获取用于显示的配置值"""
        if self.is_sensitive:
            return "*" * 8
        
        value = self.get_typed_value()
        if self.value_type == 'boolean':
            return "是" if value else "否"
        elif isinstance(value, (list, dict)):
            return f"{self.value_type}: {len(value)} 项"
        
        return str(value) if value is not None else ""


class ConfigurationHistory(models.Model):
    """
    配置变更历史模型
    记录系统配置的变更历史
    """
    config = models.ForeignKey(
        SystemConfiguration,
        on_delete=models.CASCADE,
        related_name='history',
        verbose_name='关联配置',
        db_comment='关联的系统配置项'
    )
    
    # 变更信息
    action = models.CharField(
        max_length=20,
        choices=[
            ('create', '创建'),
            ('update', '更新'),
            ('delete', '删除'),
            ('activate', '激活'),
            ('deactivate', '停用'),
        ],
        verbose_name='操作类型',
        db_comment='配置变更的操作类型'
    )
    
    old_value = models.TextField(
        blank=True,
        null=True,
        verbose_name='原值',
        db_comment='变更前的配置值'
    )
    
    new_value = models.TextField(
        blank=True,
        null=True,
        verbose_name='新值',
        db_comment='变更后的配置值'
    )
    
    # 变更原因和描述
    reason = models.TextField(
        blank=True,
        null=True,
        verbose_name='变更原因',
        db_comment='配置变更的原因'
    )
    
    description = models.TextField(
        blank=True,
        null=True,
        verbose_name='变更描述',
        db_comment='变更的详细描述'
    )
    
    # 操作用户
    changed_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        related_name='config_changes',
        verbose_name='操作用户',
        db_comment='执行此变更的用户'
    )
    
    # 客户端信息
    client_ip = models.GenericIPAddressField(
        blank=True,
        null=True,
        verbose_name='客户端IP',
        db_comment='执行变更的客户端IP地址'
    )
    
    user_agent = models.TextField(
        blank=True,
        null=True,
        verbose_name='用户代理',
        db_comment='客户端的User-Agent信息'
    )
    
    # 时间戳
    changed_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='变更时间',
        db_comment='配置变更的时间'
    )

    class Meta:
        db_table = 'awranalyzer_configuration_history'
        db_table_comment = '配置变更历史表'
        verbose_name = '配置变更历史'
        verbose_name_plural = '配置变更历史'
        indexes = [
            models.Index(fields=['config', 'changed_at']),
            models.Index(fields=['changed_by']),
            models.Index(fields=['action']),
        ]
        ordering = ['-changed_at']

    def __str__(self):
        return f"{self.config.config_key} - {self.action} ({self.changed_at})" 