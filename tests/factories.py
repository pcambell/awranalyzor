"""
Oracle AWR分析器 - 测试数据工厂
{{CHENGQI: P1-TE-004 基础测试框架配置 - 2025-06-01 23:45:00 +08:00}}

使用factory_boy创建测试数据的工厂类
"""
import factory
from django.contrib.auth.models import User
from django.utils import timezone
from faker import Faker

fake = Faker(['zh_CN', 'en_US'])


class UserFactory(factory.django.DjangoModelFactory):
    """用户工厂"""
    
    class Meta:
        model = User
    
    username = factory.Sequence(lambda n: f"user_{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    first_name = factory.Faker('first_name')
    last_name = factory.Faker('last_name')
    is_active = True
    is_staff = False
    is_superuser = False
    
    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        if not create:
            return
        password = extracted or 'testpass123'
        self.set_password(password)
        self.save()


class AdminUserFactory(UserFactory):
    """管理员用户工厂"""
    
    username = factory.Sequence(lambda n: f"admin_{n}")
    is_staff = True
    is_superuser = True


class AWRReportFactory(factory.django.DjangoModelFactory):
    """AWR报告工厂"""
    
    class Meta:
        model = 'awr_upload.AWRReport'
    
    name = factory.Faker('sentence', nb_words=3)
    database_name = factory.Faker('pystr', min_chars=3, max_chars=8)
    instance_number = factory.Faker('random_int', min=1, max=4)
    oracle_version = factory.Faker('random_element', elements=('11g', '12c', '19c'))
    is_rac = factory.Faker('boolean', chance_of_getting_true=30)
    is_cdb = factory.Faker('boolean', chance_of_getting_true=40)
    container_name = factory.LazyAttribute(
        lambda obj: fake.pystr(min_chars=3, max_chars=10) if obj.is_cdb else None
    )
    
    begin_snap_id = factory.Faker('random_int', min=1000, max=9999)
    end_snap_id = factory.LazyAttribute(lambda obj: obj.begin_snap_id + fake.random_int(min=1, max=10))
    begin_time = factory.Faker('date_time_this_year', tzinfo=timezone.get_current_timezone())
    end_time = factory.LazyAttribute(
        lambda obj: obj.begin_time + timezone.timedelta(hours=1)
    )
    
    file_size = factory.Faker('random_int', min=1024, max=10485760)  # 1KB to 10MB
    file_hash = factory.Faker('sha256')
    
    uploaded_by = factory.SubFactory(UserFactory)
    
    status = 'uploaded'
    error_message = None


class ParsedAWRReportFactory(AWRReportFactory):
    """已解析的AWR报告工厂"""
    
    status = 'parsed'
    parsed_at = factory.LazyAttribute(
        lambda obj: obj.uploaded_at + timezone.timedelta(minutes=5)
    )


class FailedAWRReportFactory(AWRReportFactory):
    """解析失败的AWR报告工厂"""
    
    status = 'failed'
    error_message = factory.Faker('sentence')


class PerformanceMetricFactory(factory.django.DjangoModelFactory):
    """性能指标工厂"""
    
    class Meta:
        model = 'performance.PerformanceMetric'
    
    awr_report = factory.SubFactory(AWRReportFactory)
    metric_name = factory.Faker(
        'random_element', 
        elements=(
            'CPU_USAGE', 'MEMORY_USAGE', 'IO_WAIT', 'BUFFER_HIT_RATIO',
            'LIBRARY_CACHE_HIT_RATIO', 'REDO_SIZE', 'LOGICAL_READS'
        )
    )
    metric_value = factory.Faker('pydecimal', left_digits=5, right_digits=2, positive=True)
    unit = factory.Faker('random_element', elements=('%', 'MB', 'seconds', 'count'))
    category = factory.Faker(
        'random_element',
        elements=('CPU', 'Memory', 'IO', 'SQL', 'Wait Events')
    )


class AnalysisResultFactory(factory.django.DjangoModelFactory):
    """分析结果工厂"""
    
    class Meta:
        model = 'diagnostics.AnalysisResult'
    
    awr_report = factory.SubFactory(AWRReportFactory)
    rule_name = factory.Faker('sentence', nb_words=2)
    severity = factory.Faker('random_element', elements=('LOW', 'MEDIUM', 'HIGH', 'CRITICAL'))
    title = factory.Faker('sentence', nb_words=4)
    description = factory.Faker('text', max_nb_chars=200)
    recommendation = factory.Faker('text', max_nb_chars=300)
    
    category = factory.Faker(
        'random_element',
        elements=('Performance', 'Configuration', 'Resource', 'SQL')
    )
    
    details = factory.LazyFunction(
        lambda: {
            'current_value': fake.pydecimal(left_digits=3, right_digits=2),
            'threshold': fake.pydecimal(left_digits=3, right_digits=2),
            'impact': fake.random_element(['Low', 'Medium', 'High'])
        }
    )


class ReportComparisonFactory(factory.django.DjangoModelFactory):
    """报告对比工厂"""
    
    class Meta:
        model = 'comparisons.ReportComparison'
    
    name = factory.Faker('sentence', nb_words=3)
    baseline_report = factory.SubFactory(AWRReportFactory)
    target_report = factory.SubFactory(AWRReportFactory)
    
    comparison_type = factory.Faker(
        'random_element',
        elements=('full', 'performance', 'wait_events', 'sql_analysis')
    )
    
    status = 'pending'
    created_by = factory.SubFactory(UserFactory)


class ExportRecordFactory(factory.django.DjangoModelFactory):
    """导出记录工厂"""
    
    class Meta:
        model = 'exports.ExportRecord'
    
    name = factory.Faker('sentence', nb_words=3)
    export_type = factory.Faker(
        'random_element',
        elements=('report', 'comparison', 'batch_reports')
    )
    export_format = factory.Faker(
        'random_element',
        elements=('pdf', 'excel', 'csv', 'html')
    )
    
    awr_report = factory.SubFactory(AWRReportFactory)
    status = 'pending'
    created_by = factory.SubFactory(UserFactory)


# 特殊场景的工厂

class Oracle11gReportFactory(AWRReportFactory):
    """Oracle 11g报告工厂"""
    oracle_version = '11g'
    is_cdb = False
    container_name = None


class Oracle12cCDBReportFactory(AWRReportFactory):
    """Oracle 12c CDB报告工厂"""
    oracle_version = '12c'
    is_cdb = True
    container_name = factory.Faker('pystr', min_chars=3, max_chars=10)


class Oracle19cRACReportFactory(AWRReportFactory):
    """Oracle 19c RAC报告工厂"""
    oracle_version = '19c'
    is_rac = True
    instance_number = factory.Faker('random_int', min=1, max=4)


class LargeAWRReportFactory(AWRReportFactory):
    """大型AWR报告工厂"""
    file_size = factory.Faker('random_int', min=50485760, max=104857600)  # 50MB to 100MB
    begin_snap_id = factory.Faker('random_int', min=1000, max=9999)
    end_snap_id = factory.LazyAttribute(lambda obj: obj.begin_snap_id + fake.random_int(min=50, max=100))


# 批量创建的辅助函数

def create_test_user_with_reports(report_count: int = 3):
    """创建带有多个报告的测试用户"""
    user = UserFactory()
    reports = [AWRReportFactory(uploaded_by=user) for _ in range(report_count)]
    return user, reports


def create_comparison_test_data():
    """创建对比测试数据"""
    user = UserFactory()
    baseline_report = AWRReportFactory(uploaded_by=user)
    target_report = AWRReportFactory(uploaded_by=user)
    comparison = ReportComparisonFactory(
        baseline_report=baseline_report,
        target_report=target_report,
        created_by=user
    )
    return user, baseline_report, target_report, comparison


def create_analysis_test_data():
    """创建分析测试数据"""
    user = UserFactory()
    report = ParsedAWRReportFactory(uploaded_by=user)
    
    # 创建多个性能指标
    metrics = [
        PerformanceMetricFactory(awr_report=report, metric_name='CPU_USAGE', metric_value=85.5),
        PerformanceMetricFactory(awr_report=report, metric_name='MEMORY_USAGE', metric_value=92.1),
        PerformanceMetricFactory(awr_report=report, metric_name='IO_WAIT', metric_value=12.3),
    ]
    
    # 创建分析结果
    results = [
        AnalysisResultFactory(awr_report=report, severity='HIGH', category='Performance'),
        AnalysisResultFactory(awr_report=report, severity='MEDIUM', category='Configuration'),
    ]
    
    return user, report, metrics, results 