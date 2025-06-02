# 代码架构设计 - Oracle AWR报告分析软件

> 更新时间：2025-06-01 22:15:55 +08:00  
> 版本：v1.0-final  
> 负责人：AR（架构师）  
> 技术负责人：LD（首席开发）  
> 基于：Django 4.2 + 模块化设计方案

## 1. 总体架构设计

### 1.1 架构风格
- **架构模式**：分层架构 + 模块化单体应用
- **设计原则**：严格遵循SOLID原则，KISS & YAGNI指导
- **技术栈**：Django 4.2 + DRF + React 18 + PostgreSQL + Redis + Celery

### 1.2 分层架构设计

```
┌─────────────────────────────────────────────────────────────┐
│                    表现层 (Presentation Layer)               │
│  React 18 + Ant Design + TypeScript                       │
│  - 用户界面组件                                             │
│  - 状态管理 (Redux Toolkit)                                │
│  - API客户端                                               │
└─────────────────────────────────────────────────────────────┘
                              ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    应用层 (Application Layer)                │
│  Django REST Framework                                    │
│  - RESTful API接口                                         │
│  - 序列化器 (Serializers)                                  │
│  - 权限控制                                                │
│  - 异常处理                                                │
└─────────────────────────────────────────────────────────────┘
                              ↕ 
┌─────────────────────────────────────────────────────────────┐
│                    业务层 (Business Layer)                   │
│  Django Apps (Modular Design)                            │
│  - 业务逻辑处理                                             │
│  - 服务层 (Services)                                       │
│  - 工作流引擎                                               │
│  - 规则引擎                                                │
└─────────────────────────────────────────────────────────────┘
                              ↕
┌─────────────────────────────────────────────────────────────┐
│                    数据层 (Data Layer)                       │
│  Django ORM + PostgreSQL + Redis                         │
│  - 数据模型 (Models)                                        │
│  - 数据访问对象 (DAO)                                       │
│  - 缓存层                                                  │
│  - 文件存储                                                │
└─────────────────────────────────────────────────────────────┘
```

## 2. Django应用模块化设计

### 2.1 应用模块结构

```
awranalyzor/                    # 项目根目录
├── config/                     # 项目配置
│   ├── settings/              # 分环境配置
│   │   ├── base.py           # 基础配置
│   │   ├── development.py    # 开发环境
│   │   ├── production.py     # 生产环境
│   │   └── testing.py        # 测试环境
│   ├── urls.py               # 根URL配置
│   └── wsgi.py               # WSGI配置
├── apps/                      # 应用模块目录
│   ├── core/                 # 核心公共模块
│   ├── accounts/             # 用户认证模块
│   ├── upload/               # 文件上传模块  
│   ├── parser/               # AWR解析模块
│   ├── analyzer/             # 诊断分析模块
│   ├── export/               # 报告导出模块
│   ├── comparison/           # 历史对比模块
│   └── dashboard/            # API接口模块
├── static/                   # 静态文件
├── media/                    # 媒体文件
├── templates/                # 模板文件
├── tests/                    # 测试文件
├── requirements/             # 依赖管理
├── docker/                   # Docker配置
└── docs/                     # 项目文档
```

### 2.2 核心模块详细设计

#### 2.2.1 Core模块 (apps/core)
**职责**：提供公共基础组件和工具类

```python
apps/core/
├── __init__.py
├── models.py                 # 抽象基础模型
├── utils.py                  # 通用工具函数
├── exceptions.py             # 自定义异常类
├── permissions.py            # 权限类
├── pagination.py             # 分页类
├── validators.py             # 验证器
├── constants.py              # 常量定义
└── mixins.py                # 混入类

# 核心基础模型
class TimestampedModel(models.Model):
    """时间戳抽象基类 - 单一职责原则"""
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        abstract = True

class UUIDModel(models.Model):
    """UUID主键抽象基类"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    
    class Meta:
        abstract = True
```

#### 2.2.2 Upload模块 (apps/upload) - 文件上传与校验
**职责**：处理AWR文件上传、校验、存储（单一职责）

```python
apps/upload/
├── models.py                 # 上传文件模型
├── views.py                  # 上传API视图
├── serializers.py            # 序列化器
├── validators.py             # 文件校验器
├── services.py               # 业务服务层
├── tasks.py                  # Celery异步任务
└── utils.py                  # 工具函数

# 文件校验器设计（开闭原则）
class FileValidator(ABC):
    @abstractmethod
    def validate(self, file) -> ValidationResult:
        pass

class AWRFileValidator(FileValidator):
    def validate(self, file) -> ValidationResult:
        # 实现AWR文件特定校验逻辑
        pass

class SecurityValidator(FileValidator):
    def validate(self, file) -> ValidationResult:
        # 实现安全校验逻辑
        pass

# 校验器链（责任链模式）
class FileValidatorChain:
    def __init__(self):
        self.validators = [
            SecurityValidator(),
            AWRFileValidator(),
            SizeValidator(),
        ]
    
    def validate(self, file) -> List[ValidationResult]:
        return [v.validate(file) for v in self.validators]
```

#### 2.2.3 Parser模块 (apps/parser) - AWR解析引擎
**职责**：解析不同版本的AWR报告（开闭原则支持扩展）

```python
apps/parser/
├── models.py                 # 解析结果模型
├── parsers/                  # 解析器实现
│   ├── base.py              # 抽象解析器基类
│   ├── oracle11g.py         # Oracle 11g解析器
│   ├── oracle12c.py         # Oracle 12c解析器
│   ├── oracle19c.py         # Oracle 19c解析器
│   └── factory.py           # 解析器工厂
├── services.py              # 解析服务
├── tasks.py                 # 异步解析任务
└── utils.py                 # 解析工具

# 解析器抽象基类（里氏替换原则）
class AbstractAWRParser(ABC):
    """AWR解析器抽象基类"""
    
    @abstractmethod
    def parse_header(self, soup: BeautifulSoup) -> Dict:
        """解析报告头部信息"""
        pass
    
    @abstractmethod
    def parse_load_profile(self, soup: BeautifulSoup) -> Dict:
        """解析负载概要"""
        pass
    
    @abstractmethod
    def parse_wait_events(self, soup: BeautifulSoup) -> List[Dict]:
        """解析等待事件"""
        pass
    
    def parse(self, html_content: str) -> ParseResult:
        """模板方法模式 - 定义解析流程"""
        soup = BeautifulSoup(html_content, 'html.parser')
        
        try:
            result = ParseResult()
            result.header = self.parse_header(soup)
            result.load_profile = self.parse_load_profile(soup)
            result.wait_events = self.parse_wait_events(soup)
            result.sql_stats = self.parse_sql_statistics(soup)
            result.io_stats = self.parse_io_statistics(soup)
            return result
        except Exception as e:
            raise ParsingError(f"解析失败: {str(e)}")

# 解析器工厂（工厂模式）
class AWRParserFactory:
    """解析器工厂类"""
    
    _parsers = {
        ('11g', 'single'): Oracle11gSingleParser,
        ('11g', 'rac'): Oracle11gRACParser,
        ('12c', 'single'): Oracle12cSingleParser,
        ('12c', 'cdb'): Oracle12cCDBParser,
        ('19c', 'single'): Oracle19cSingleParser,
        ('19c', 'rac'): Oracle19cRACParser,
        ('19c', 'cdb'): Oracle19cCDBParser,
    }
    
    @classmethod
    def create_parser(cls, db_version: str, instance_type: str) -> AbstractAWRParser:
        parser_class = cls._parsers.get((db_version, instance_type))
        if not parser_class:
            raise UnsupportedVersionError(f"不支持的版本组合: {db_version}, {instance_type}")
        return parser_class()
```

#### 2.2.4 Analyzer模块 (apps/analyzer) - 诊断分析引擎
**职责**：实现性能诊断规则和分析逻辑

```python
apps/analyzer/
├── models.py                 # 分析结果模型
├── rules/                    # 诊断规则
│   ├── base.py              # 抽象规则基类
│   ├── buffer_rules.py      # 缓冲区规则
│   ├── cpu_rules.py         # CPU性能规则
│   ├── sql_rules.py         # SQL性能规则
│   ├── wait_rules.py        # 等待事件规则
│   └── io_rules.py          # IO性能规则
├── engine.py                # 诊断引擎
├── services.py              # 分析服务
└── tasks.py                 # 异步分析任务

# 诊断规则抽象基类（策略模式）
@dataclass
class DiagnosticResult:
    severity: str              # critical, warning, info
    category: str             # memory, cpu, io, sql
    title: str
    description: str
    recommendation: str
    metric_value: Optional[float] = None
    evidence: Optional[Dict] = None

class AbstractDiagnosticRule(ABC):
    """诊断规则抽象基类"""
    
    @property
    @abstractmethod
    def rule_name(self) -> str:
        """规则名称"""
        pass
    
    @property
    @abstractmethod
    def category(self) -> str:
        """规则分类"""
        pass
    
    @abstractmethod
    def analyze(self, metrics: Dict) -> Optional[DiagnosticResult]:
        """执行诊断分析"""
        pass
    
    def is_applicable(self, metrics: Dict) -> bool:
        """判断规则是否适用"""
        return True

# 具体规则实现
class BufferHitRateRule(AbstractDiagnosticRule):
    """缓冲区命中率诊断规则"""
    
    @property
    def rule_name(self) -> str:
        return "缓冲区命中率检查"
    
    @property
    def category(self) -> str:
        return "memory"
    
    def analyze(self, metrics: Dict) -> Optional[DiagnosticResult]:
        buffer_hit_rate = metrics.get('instance_efficiency', {}).get('buffer_hit_rate')
        
        if buffer_hit_rate is None:
            return None
        
        if buffer_hit_rate < 90.0:
            severity = 'critical' if buffer_hit_rate < 85.0 else 'warning'
            return DiagnosticResult(
                severity=severity,
                category=self.category,
                title=f'缓冲区命中率过低 ({buffer_hit_rate:.2f}%)',
                description=f'当前缓冲区命中率为 {buffer_hit_rate:.2f}%，低于推荐值95%',
                recommendation='建议增加SGA中的DB_CACHE_SIZE参数，或优化SQL减少物理读',
                metric_value=buffer_hit_rate,
                evidence={'buffer_hit_rate': buffer_hit_rate}
            )
        
        return None

# 诊断引擎（责任链模式）
class DiagnosticEngine:
    """诊断引擎 - 执行所有诊断规则"""
    
    def __init__(self):
        self.rules: List[AbstractDiagnosticRule] = [
            BufferHitRateRule(),
            SoftParseRateRule(),
            CPUUsageRule(),
            TopWaitEventRule(),
            SQLPerformanceRule(),
            IOThroughputRule(),
            # 更多规则...
        ]
    
    def analyze(self, report_data: Dict) -> List[DiagnosticResult]:
        """执行完整诊断分析"""
        results = []
        
        for rule in self.rules:
            try:
                if rule.is_applicable(report_data):
                    result = rule.analyze(report_data)
                    if result:
                        results.append(result)
            except Exception as e:
                logger.error(f"规则执行失败 {rule.rule_name}: {str(e)}")
        
        return self._sort_by_severity(results)
    
    def _sort_by_severity(self, results: List[DiagnosticResult]) -> List[DiagnosticResult]:
        """按严重程度排序"""
        severity_order = {'critical': 0, 'warning': 1, 'info': 2}
        return sorted(results, key=lambda x: severity_order.get(x.severity, 3))
```

### 2.3 设计模式应用总结

```
设计模式应用：
├── 工厂模式 (Factory Pattern)
│   └── AWRParserFactory - 创建不同版本的解析器
├── 策略模式 (Strategy Pattern)  
│   └── DiagnosticRule - 不同的诊断规则策略
├── 责任链模式 (Chain of Responsibility)
│   ├── FileValidatorChain - 文件校验链
│   └── DiagnosticEngine - 诊断规则链
├── 模板方法模式 (Template Method)
│   └── AbstractAWRParser.parse() - 定义解析流程
├── 观察者模式 (Observer Pattern)
│   └── Django Signals - 模型事件通知
└── 依赖注入模式 (Dependency Injection)
    └── Service层 - 依赖抽象而非具体实现
```

## 3. 数据访问层设计

### 3.1 仓储模式应用

```python
# 抽象仓储接口（依赖倒置原则）
class AbstractRepository(ABC):
    @abstractmethod
    def find_by_id(self, id: Any) -> Optional[Model]:
        pass
    
    @abstractmethod
    def find_all(self) -> QuerySet:
        pass
    
    @abstractmethod
    def save(self, entity: Model) -> Model:
        pass

# 具体仓储实现
class AWRReportRepository(AbstractRepository):
    def find_by_id(self, id: int) -> Optional[AWRReport]:
        return AWRReport.objects.filter(id=id).first()
    
    def find_by_user(self, user: User) -> QuerySet:
        return AWRReport.objects.filter(user=user).order_by('-upload_time')
    
    def save(self, report: AWRReport) -> AWRReport:
        report.save()
        return report
```

### 3.2 服务层设计

```python
# 服务层 - 封装业务逻辑
class AWRAnalysisService:
    def __init__(self, 
                 report_repo: AWRReportRepository,
                 parser_factory: AWRParserFactory,
                 diagnostic_engine: DiagnosticEngine):
        self.report_repo = report_repo
        self.parser_factory = parser_factory
        self.diagnostic_engine = diagnostic_engine
    
    def analyze_report(self, report_id: int) -> AnalysisResult:
        """完整的报告分析流程"""
        # 1. 获取报告
        report = self.report_repo.find_by_id(report_id)
        if not report:
            raise ReportNotFoundError(f"Report {report_id} not found")
        
        # 2. 创建解析器
        parser = self.parser_factory.create_parser(
            report.db_version, report.instance_type
        )
        
        # 3. 解析报告
        parse_result = parser.parse(report.raw_content)
        
        # 4. 执行诊断
        diagnosis = self.diagnostic_engine.analyze(parse_result.to_dict())
        
        # 5. 保存结果
        return self._save_analysis_result(report, diagnosis)
```

## 4. 异步处理架构

### 4.1 Celery任务设计

```python
# 异步任务设计
@shared_task(bind=True, max_retries=3)
def parse_awr_report(self, report_id: int):
    """异步解析AWR报告"""
    try:
        report = AWRReport.objects.get(id=report_id)
        report.status = 'parsing'
        report.save()
        
        # 执行解析
        service = AWRAnalysisService()
        result = service.analyze_report(report_id)
        
        report.status = 'completed'
        report.save()
        
        return {'status': 'success', 'report_id': report_id}
        
    except Exception as exc:
        # 指数退避重试
        countdown = 2 ** self.request.retries
        raise self.retry(exc=exc, countdown=countdown)

# 大文件分片处理
@shared_task
def process_large_file_chunk(file_path: str, chunk_start: int, chunk_size: int):
    """处理大文件分片"""
    with open(file_path, 'r') as f:
        f.seek(chunk_start)
        chunk_data = f.read(chunk_size)
        # 处理分片数据
        return process_chunk(chunk_data)
```

## 5. 缓存策略设计

### 5.1 多层缓存架构

```python
# 缓存装饰器
def cache_result(timeout=3600, key_prefix=''):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            result = cache.get(cache_key)
            
            if result is None:
                result = func(*args, **kwargs)
                cache.set(cache_key, result, timeout)
            
            return result
        return wrapper
    return decorator

# 应用缓存策略
class AWRMetricsService:
    @cache_result(timeout=1800, key_prefix='awr_metrics')
    def get_report_metrics(self, report_id: int) -> Dict:
        """获取报告指标（缓存30分钟）"""
        return self._calculate_metrics(report_id)
    
    @cache_result(timeout=86400, key_prefix='awr_comparison')
    def compare_reports(self, baseline_id: int, target_id: int) -> Dict:
        """报告对比（缓存24小时）"""
        return self._perform_comparison(baseline_id, target_id)
```

## 6. 错误处理与监控

### 6.1 异常处理架构

```python
# 自定义异常类层次
class AWRAnalysisError(Exception):
    """AWR分析基础异常"""
    pass

class ParsingError(AWRAnalysisError):
    """解析异常"""
    pass

class ValidationError(AWRAnalysisError):
    """校验异常"""
    pass

class UnsupportedVersionError(AWRAnalysisError):
    """不支持的版本异常"""
    pass

# 全局异常处理器
@api_view(['GET', 'POST', 'PUT', 'DELETE'])
def api_exception_handler(exc, context):
    """全局API异常处理器"""
    if isinstance(exc, AWRAnalysisError):
        return Response({
            'error': exc.__class__.__name__,
            'message': str(exc),
            'code': getattr(exc, 'code', 'ANALYSIS_ERROR')
        }, status=400)
    
    return default_exception_handler(exc, context)
```

### 6.2 日志与监控

```python
# 日志配置
LOGGING = {
    'version': 1,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/awr_analysis.log',
            'maxBytes': 1024 * 1024 * 10,  # 10MB
            'backupCount': 5,
        },
        'performance': {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': 'logs/performance.log',
        }
    },
    'loggers': {
        'awr.parser': {'handlers': ['file'], 'level': 'INFO'},
        'awr.analyzer': {'handlers': ['file'], 'level': 'INFO'},
        'awr.performance': {'handlers': ['performance'], 'level': 'INFO'},
    }
}

# 性能监控装饰器
def monitor_performance(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(f"Performance: {func.__name__} executed in {execution_time:.2f}s")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Performance: {func.__name__} failed after {execution_time:.2f}s: {str(e)}")
            raise
    return wrapper
```

---

**代码架构设计原则确认：**
- ✅ 严格遵循SOLID原则（单一职责、开闭、里氏替换、接口隔离、依赖倒置）
- ✅ 应用多种设计模式解决复杂性
- ✅ 分层架构清晰，职责分明
- ✅ 支持扩展但避免过度设计（YAGNI）
- ✅ 异步处理和缓存策略完善
- ✅ 错误处理和监控机制健全

*更新记录：*
- 2025-06-01 22:15:55 +08:00 - 创建代码架构设计v1.0-final - AR, LD 