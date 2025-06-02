# 数据结构设计 - Oracle AWR报告分析软件

> 更新时间：2025-06-01 22:15:55 +08:00  
> 版本：v1.0-final  
> 负责人：AR（架构师）  
> 数据库：PostgreSQL 14  
> 缓存：Redis 7

## 1. 数据模型设计概览

### 1.1 设计原则
- **规范化设计**：避免数据冗余，确保数据一致性
- **性能优化**：合理的索引设计，支持高效查询
- **扩展性**：支持未来功能扩展，如ASH报告、多数据库类型
- **安全性**：敏感数据加密，访问控制
- **可维护性**：清晰的表结构和约束定义

### 1.2 核心实体关系图

```
┌─────────────┐    ┌─────────────────┐    ┌─────────────────┐
│    User     │1:N │   AWRReport     │1:N │ PerformanceMetric│
│             │────│                 │────│                 │
│ - id        │    │ - id            │    │ - id            │
│ - username  │    │ - filename      │    │ - category      │
│ - email     │    │ - db_version    │    │ - metric_name   │
│ - password  │    │ - instance_type │    │ - value         │
└─────────────┘    │ - status        │    └─────────────────┘
                   │ - raw_data      │              
                   └─────────────────┘              
                           │1:N                     
                   ┌─────────────────┐              
                   │ AnalysisResult  │              
                   │                 │              
                   │ - id            │              
                   │ - severity      │              
                   │ - category      │              
                   │ - title         │              
                   │ - description   │              
                   │ - recommendation│              
                   └─────────────────┘              

┌─────────────────┐N:N┌─────────────────┐
│   AWRReport     │───│ReportComparison │
│   (baseline)    │   │                 │
└─────────────────┘   │ - comparison_data│
                      │ - summary       │
┌─────────────────┐   │ - created_at    │
│   AWRReport     │───│                 │
│   (target)      │   └─────────────────┘
└─────────────────┘
```

## 2. 详细表结构设计

### 2.1 用户认证相关表

#### users表 (Django内置User模型扩展)
```sql
CREATE TABLE auth_user (
    id SERIAL PRIMARY KEY,
    username VARCHAR(150) UNIQUE NOT NULL,
    email VARCHAR(254) NOT NULL,
    password VARCHAR(128) NOT NULL,
    first_name VARCHAR(150) DEFAULT '',
    last_name VARCHAR(150) DEFAULT '',
    is_active BOOLEAN DEFAULT TRUE,
    is_staff BOOLEAN DEFAULT FALSE,
    is_superuser BOOLEAN DEFAULT FALSE,
    date_joined TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP WITH TIME ZONE
);

-- 用户配置扩展表
CREATE TABLE user_profiles (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE REFERENCES auth_user(id) ON DELETE CASCADE,
    timezone VARCHAR(50) DEFAULT 'Asia/Shanghai',
    language VARCHAR(10) DEFAULT 'zh-CN',
    notification_enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);
```

### 2.2 AWR报告主表

#### awr_reports表
```sql
CREATE TABLE awr_reports (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    
    -- 文件信息
    filename VARCHAR(255) NOT NULL,
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    file_hash VARCHAR(64) UNIQUE, -- SHA-256哈希，防重复上传
    upload_time TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 数据库元数据
    db_name VARCHAR(100) NOT NULL,
    db_version VARCHAR(10) NOT NULL, -- 11g, 12c, 19c, 21c
    db_id INTEGER,
    db_unique_name VARCHAR(100),
    instance_type VARCHAR(20) NOT NULL, -- single, rac, cdb
    instance_names JSONB DEFAULT '[]', -- RAC实例名列表
    
    -- 快照信息
    begin_snap_id INTEGER NOT NULL,
    end_snap_id INTEGER NOT NULL,
    begin_time TIMESTAMP WITH TIME ZONE NOT NULL,
    end_time TIMESTAMP WITH TIME ZONE NOT NULL,
    elapsed_time_minutes DECIMAL(10,2) NOT NULL,
    
    -- 处理状态
    status VARCHAR(20) DEFAULT 'uploading', -- uploading, parsing, analyzing, completed, failed
    progress_percentage SMALLINT DEFAULT 0,
    error_message TEXT,
    
    -- 原始数据（大字段）
    raw_data JSONB, -- 解析后的结构化数据
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    CONSTRAINT valid_status CHECK (status IN ('uploading', 'parsing', 'analyzing', 'completed', 'failed')),
    CONSTRAINT valid_db_version CHECK (db_version IN ('11g', '12c', '19c', '21c')),
    CONSTRAINT valid_instance_type CHECK (instance_type IN ('single', 'rac', 'cdb')),
    CONSTRAINT valid_progress CHECK (progress_percentage >= 0 AND progress_percentage <= 100),
    CONSTRAINT valid_snap_sequence CHECK (end_snap_id > begin_snap_id),
    CONSTRAINT valid_time_sequence CHECK (end_time > begin_time)
);

-- 索引设计
CREATE INDEX idx_awr_reports_user_upload_time ON awr_reports(user_id, upload_time DESC);
CREATE INDEX idx_awr_reports_status ON awr_reports(status);
CREATE INDEX idx_awr_reports_db_version ON awr_reports(db_version);
CREATE INDEX idx_awr_reports_time_range ON awr_reports(begin_time, end_time);
CREATE INDEX idx_awr_reports_file_hash ON awr_reports(file_hash);
CREATE UNIQUE INDEX idx_awr_reports_unique_snapshot ON awr_reports(db_name, begin_snap_id, end_snap_id) WHERE status = 'completed';
```

### 2.3 性能指标表

#### performance_metrics表
```sql
CREATE TABLE performance_metrics (
    id BIGSERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES awr_reports(id) ON DELETE CASCADE,
    
    -- 指标分类
    category VARCHAR(50) NOT NULL, -- load_profile, instance_efficiency, wait_events, sql_stats, io_stats, memory_stats, time_model
    subcategory VARCHAR(50), -- 子分类，如sql_stats下的select, insert, update等
    
    -- 指标信息
    metric_name VARCHAR(100) NOT NULL,
    metric_value DECIMAL(20,4) NOT NULL,
    metric_unit VARCHAR(20), -- per_sec, percentage, bytes, ms等
    
    -- 实例信息（RAC环境）
    instance_name VARCHAR(50), -- RAC实例名
    
    -- 排序和权重
    sort_order INTEGER DEFAULT 0,
    is_key_metric BOOLEAN DEFAULT FALSE, -- 是否为关键指标
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    CONSTRAINT valid_category CHECK (category IN (
        'load_profile', 'instance_efficiency', 'wait_events', 
        'sql_stats', 'io_stats', 'memory_stats', 'time_model'
    ))
);

-- 唯一约束和索引
CREATE UNIQUE INDEX idx_performance_metrics_unique ON performance_metrics(
    report_id, category, metric_name, COALESCE(instance_name, '')
);
CREATE INDEX idx_performance_metrics_category ON performance_metrics(category, is_key_metric);
CREATE INDEX idx_performance_metrics_report_id ON performance_metrics(report_id);
```

### 2.4 分析结果表

#### analysis_results表
```sql
CREATE TABLE analysis_results (
    id BIGSERIAL PRIMARY KEY,
    report_id INTEGER NOT NULL REFERENCES awr_reports(id) ON DELETE CASCADE,
    
    -- 诊断信息
    severity VARCHAR(20) NOT NULL, -- critical, warning, info
    category VARCHAR(50) NOT NULL, -- memory, cpu, io, sql, config, performance
    rule_name VARCHAR(100) NOT NULL, -- 规则名称
    
    -- 问题描述
    title VARCHAR(200) NOT NULL,
    description TEXT NOT NULL,
    recommendation TEXT NOT NULL,
    
    -- 关联数据
    metric_value DECIMAL(20,4), -- 关联的指标值
    evidence JSONB, -- 证据数据（JSON格式）
    
    -- 优先级和权重
    priority_score INTEGER DEFAULT 0, -- 优先级评分 0-100
    confidence_level DECIMAL(3,2) DEFAULT 0.0, -- 置信度 0.0-1.0
    
    -- 实例信息
    instance_name VARCHAR(50), -- 针对特定实例的建议
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    CONSTRAINT valid_severity CHECK (severity IN ('critical', 'warning', 'info')),
    CONSTRAINT valid_category CHECK (category IN ('memory', 'cpu', 'io', 'sql', 'config', 'performance')),
    CONSTRAINT valid_priority_score CHECK (priority_score >= 0 AND priority_score <= 100),
    CONSTRAINT valid_confidence_level CHECK (confidence_level >= 0.0 AND confidence_level <= 1.0)
);

-- 索引设计
CREATE INDEX idx_analysis_results_report_severity ON analysis_results(report_id, severity, priority_score DESC);
CREATE INDEX idx_analysis_results_category ON analysis_results(category);
CREATE INDEX idx_analysis_results_rule_name ON analysis_results(rule_name);
```

### 2.5 报告对比表

#### report_comparisons表
```sql
CREATE TABLE report_comparisons (
    id SERIAL PRIMARY KEY,
    
    -- 对比报告
    baseline_report_id INTEGER NOT NULL REFERENCES awr_reports(id) ON DELETE CASCADE,
    target_report_id INTEGER NOT NULL REFERENCES awr_reports(id) ON DELETE CASCADE,
    
    -- 对比结果
    comparison_data JSONB NOT NULL, -- 详细对比数据
    summary TEXT NOT NULL, -- 对比摘要
    
    -- 差异统计
    performance_change_percentage DECIMAL(6,2), -- 整体性能变化百分比
    critical_changes_count INTEGER DEFAULT 0, -- 严重变化数量
    warning_changes_count INTEGER DEFAULT 0, -- 警告变化数量
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    
    -- 约束
    CONSTRAINT different_reports CHECK (baseline_report_id != target_report_id)
);

-- 唯一约束和索引
CREATE UNIQUE INDEX idx_report_comparisons_unique ON report_comparisons(baseline_report_id, target_report_id);
CREATE INDEX idx_report_comparisons_baseline ON report_comparisons(baseline_report_id);
CREATE INDEX idx_report_comparisons_target ON report_comparisons(target_report_id);
```

### 2.6 导出记录表

#### export_records表
```sql
CREATE TABLE export_records (
    id SERIAL PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES auth_user(id) ON DELETE CASCADE,
    report_id INTEGER REFERENCES awr_reports(id) ON DELETE SET NULL,
    comparison_id INTEGER REFERENCES report_comparisons(id) ON DELETE SET NULL,
    
    -- 导出信息
    export_type VARCHAR(20) NOT NULL, -- pdf, excel, csv
    export_format VARCHAR(50) NOT NULL, -- 具体格式，如detailed_pdf, summary_excel
    file_path VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    
    -- 导出状态
    status VARCHAR(20) DEFAULT 'processing', -- processing, completed, failed
    error_message TEXT,
    
    -- 时间戳
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP WITH TIME ZONE,
    
    -- 约束
    CONSTRAINT valid_export_type CHECK (export_type IN ('pdf', 'excel', 'csv')),
    CONSTRAINT valid_export_status CHECK (status IN ('processing', 'completed', 'failed')),
    CONSTRAINT export_source_check CHECK (
        (report_id IS NOT NULL AND comparison_id IS NULL) OR 
        (report_id IS NULL AND comparison_id IS NOT NULL)
    )
);

-- 索引设计
CREATE INDEX idx_export_records_user_created ON export_records(user_id, created_at DESC);
CREATE INDEX idx_export_records_status ON export_records(status);
```

### 2.7 系统配置表

#### system_configurations表
```sql
CREATE TABLE system_configurations (
    id SERIAL PRIMARY KEY,
    key VARCHAR(100) UNIQUE NOT NULL,
    value TEXT NOT NULL,
    description TEXT,
    category VARCHAR(50) DEFAULT 'general', -- general, parser, analyzer, export
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- 初始化配置数据
INSERT INTO system_configurations (key, value, description, category) VALUES
('max_file_size_mb', '100', '最大文件上传大小(MB)', 'general'),
('max_concurrent_parsing', '5', '最大并发解析任务数', 'parser'),
('cache_timeout_minutes', '30', '缓存超时时间(分钟)', 'general'),
('diagnostic_rules_enabled', 'true', '是否启用诊断规则', 'analyzer'),
('export_retention_days', '30', '导出文件保留天数', 'export');
```

## 3. 数据库优化策略

### 3.1 分区策略

```sql
-- 对于大量历史数据，按时间分区 awr_reports 表
CREATE TABLE awr_reports_y2025m01 PARTITION OF awr_reports
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');

CREATE TABLE awr_reports_y2025m02 PARTITION OF awr_reports
FOR VALUES FROM ('2025-02-01') TO ('2025-03-01');

-- 自动创建分区的函数
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
DECLARE
    end_date date := start_date + interval '1 month';
    partition_name text := table_name || '_y' || to_char(start_date, 'YYYY') || 'm' || to_char(start_date, 'MM');
BEGIN
    EXECUTE format('CREATE TABLE %I PARTITION OF %I FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
END;
$$ LANGUAGE plpgsql;
```

### 3.2 索引优化策略

```sql
-- 复合索引优化查询
CREATE INDEX idx_awr_reports_user_status_time ON awr_reports(user_id, status, upload_time DESC)
WHERE status IN ('completed', 'failed');

-- 部分索引节省空间
CREATE INDEX idx_awr_reports_active ON awr_reports(id, upload_time)
WHERE status = 'completed';

-- 表达式索引
CREATE INDEX idx_awr_reports_time_range_hours ON awr_reports(
    extract(epoch from (end_time - begin_time))/3600
);

-- GIN索引支持JSON查询
CREATE INDEX idx_awr_reports_raw_data_gin ON awr_reports USING gin(raw_data);
CREATE INDEX idx_analysis_results_evidence_gin ON analysis_results USING gin(evidence);
```

### 3.3 查询优化

```sql
-- 常用查询的物化视图
CREATE MATERIALIZED VIEW awr_reports_summary AS
SELECT 
    user_id,
    db_version,
    instance_type,
    COUNT(*) as total_reports,
    COUNT(*) FILTER (WHERE status = 'completed') as completed_reports,
    COUNT(*) FILTER (WHERE status = 'failed') as failed_reports,
    AVG(elapsed_time_minutes) as avg_elapsed_time,
    MAX(upload_time) as last_upload_time
FROM awr_reports
GROUP BY user_id, db_version, instance_type;

-- 刷新物化视图的触发器
CREATE OR REPLACE FUNCTION refresh_awr_reports_summary()
RETURNS trigger AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY awr_reports_summary;
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_refresh_awr_summary
AFTER INSERT OR UPDATE OR DELETE ON awr_reports
FOR EACH STATEMENT EXECUTE FUNCTION refresh_awr_reports_summary();
```

## 4. Redis缓存设计

### 4.1 缓存键命名规范

```
缓存键命名规范：
├── awr:report:{report_id}:metrics          # 报告指标缓存
├── awr:report:{report_id}:analysis         # 分析结果缓存
├── awr:comparison:{baseline_id}:{target_id} # 对比结果缓存
├── awr:user:{user_id}:reports              # 用户报告列表缓存
├── awr:stats:global                        # 全局统计缓存
└── awr:config:system                       # 系统配置缓存
```

### 4.2 缓存策略配置

```python
# Redis缓存配置
REDIS_CACHE_CONFIG = {
    'report_metrics': {
        'timeout': 1800,  # 30分钟
        'version': 1,
    },
    'analysis_results': {
        'timeout': 3600,  # 1小时
        'version': 1,
    },
    'comparison_results': {
        'timeout': 86400,  # 24小时
        'version': 1,
    },
    'user_reports_list': {
        'timeout': 300,   # 5分钟
        'version': 1,
    },
    'system_config': {
        'timeout': 3600,  # 1小时
        'version': 1,
    }
}
```

### 4.3 缓存失效策略

```python
# 缓存失效规则
def invalidate_report_cache(report_id):
    """报告相关缓存失效"""
    cache_keys = [
        f'awr:report:{report_id}:metrics',
        f'awr:report:{report_id}:analysis',
        f'awr:user:{report.user_id}:reports',
    ]
    cache.delete_many(cache_keys)

def invalidate_comparison_cache(baseline_id, target_id):
    """对比结果缓存失效"""
    cache_keys = [
        f'awr:comparison:{baseline_id}:{target_id}',
        f'awr:comparison:{target_id}:{baseline_id}',
    ]
    cache.delete_many(cache_keys)
```

## 5. 数据安全和备份策略

### 5.1 数据加密

```sql
-- 敏感字段加密存储
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 用户密码哈希（Django内置）
-- 文件路径混淆
CREATE OR REPLACE FUNCTION encrypt_file_path(original_path text, secret_key text)
RETURNS text AS $$
BEGIN
    RETURN encode(encrypt(original_path::bytea, secret_key, 'aes'), 'base64');
END;
$$ LANGUAGE plpgsql;
```

### 5.2 数据备份策略

```bash
# 定期备份脚本
#!/bin/bash
# backup_awr_db.sh

DB_NAME="awranalyzor"
BACKUP_DIR="/var/backups/awr"
DATE=$(date +"%Y%m%d_%H%M%S")

# 创建备份目录
mkdir -p $BACKUP_DIR

# 数据库完整备份
pg_dump -h localhost -U postgres -d $DB_NAME -f "$BACKUP_DIR/awr_full_$DATE.sql"

# 压缩备份文件
gzip "$BACKUP_DIR/awr_full_$DATE.sql"

# 删除7天前的备份
find $BACKUP_DIR -name "awr_full_*.sql.gz" -mtime +7 -delete

# 日志记录
echo "$(date): Backup completed - awr_full_$DATE.sql.gz" >> /var/log/awr_backup.log
```

### 5.3 数据归档策略

```sql
-- 历史数据归档存储过程
CREATE OR REPLACE FUNCTION archive_old_reports(cutoff_date date)
RETURNS integer AS $$
DECLARE
    archived_count integer := 0;
BEGIN
    -- 归档超过指定日期的已完成报告
    WITH archived_reports AS (
        DELETE FROM awr_reports 
        WHERE upload_time < cutoff_date 
        AND status = 'completed'
        RETURNING *
    )
    INSERT INTO awr_reports_archive 
    SELECT * FROM archived_reports;
    
    GET DIAGNOSTICS archived_count = ROW_COUNT;
    
    -- 记录归档操作
    INSERT INTO system_logs (operation, message, created_at)
    VALUES ('archive', format('Archived %s reports older than %s', archived_count, cutoff_date), NOW());
    
    RETURN archived_count;
END;
$$ LANGUAGE plpgsql;

-- 定期执行归档（保留最近90天数据）
SELECT archive_old_reports(CURRENT_DATE - INTERVAL '90 days');
```

---

**数据结构设计确认：**
- ✅ 规范化设计，避免数据冗余
- ✅ 完善的索引策略，支持高效查询
- ✅ 分区策略应对大数据量
- ✅ Redis缓存设计优化性能
- ✅ 数据安全和备份策略完善
- ✅ 支持未来扩展需求

*更新记录：*
- 2025-06-01 22:15:55 +08:00 - 创建数据结构设计v1.0-final - AR 