# Generated by Django 4.2.16 on 2025-06-02 07:04

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('organization', models.CharField(blank=True, db_comment='用户所属组织或公司名称', max_length=100, null=True, verbose_name='组织机构')),
                ('department', models.CharField(blank=True, db_comment='用户所属部门', max_length=50, null=True, verbose_name='部门')),
                ('user_timezone', models.CharField(db_comment='用户偏好时区设置', default='Asia/Shanghai', max_length=50, verbose_name='时区')),
                ('language', models.CharField(choices=[('zh-hans', '简体中文'), ('en', 'English')], db_comment='用户界面语言偏好', default='zh-hans', max_length=10, verbose_name='语言')),
                ('default_analysis_scope', models.CharField(choices=[('basic', '基础分析'), ('standard', '标准分析'), ('comprehensive', '全面分析')], db_comment='用户偏好的默认分析深度', default='comprehensive', max_length=20, verbose_name='默认分析范围')),
                ('auto_diagnostic', models.BooleanField(db_comment='是否自动执行诊断规则', default=True, verbose_name='自动诊断')),
                ('email_notifications', models.BooleanField(db_comment='是否接收邮件通知', default=True, verbose_name='邮件通知')),
                ('notification_types', models.JSONField(blank=True, db_comment='详细的通知类型偏好设置', default=dict, verbose_name='通知类型配置')),
                ('reports_uploaded', models.PositiveIntegerField(db_comment='用户累计上传的AWR报告数量', default=0, verbose_name='上传报告数')),
                ('last_activity', models.DateTimeField(db_comment='用户最后一次活动的时间戳', default=django.utils.timezone.now, verbose_name='最后活动时间')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_comment='用户配置文件创建时间', verbose_name='创建时间')),
                ('updated_at', models.DateTimeField(auto_now=True, db_comment='用户配置文件最后更新时间', verbose_name='更新时间')),
                ('user', models.OneToOneField(db_comment='关联到Django内置用户表', on_delete=django.db.models.deletion.CASCADE, related_name='profile', to=settings.AUTH_USER_MODEL, verbose_name='关联用户')),
            ],
            options={
                'verbose_name': '用户配置文件',
                'verbose_name_plural': '用户配置文件',
                'db_table': 'awranalyzer_user_profile',
                'db_table_comment': 'AWR分析器用户配置文件表',
                'indexes': [models.Index(fields=['organization'], name='awranalyzer_organiz_fde737_idx'), models.Index(fields=['last_activity'], name='awranalyzer_last_ac_fa25da_idx')],
            },
        ),
    ]
