# Oracle AWR报告多版本结构对比与分析

> 记录时间：2025-06-01 21:31:36 +08:00

## 0. 项目背景与需求澄清

### 需求来源与目标
- 本项目旨在开发一个Oracle AWR报告分析软件，支持用户上传AWR报告（HTML格式），系统自动完成报告的读取、分析和反馈。
- 目标是为DBA等专业用户提供智能化的性能诊断、优化建议、历史对比和多格式报告导出能力。

### 需求澄清与用户反馈（阶段性总结）
1. **分析深度**：
   - 需要具备智能化的性能诊断与优化建议（不仅仅是数据提取，需有规则/模型驱动的分析）。
2. **反馈形式**：
   - Web端展示分析结果。
   - 支持导出PDF/Excel格式的分析报告。
3. **用户类型**：
   - 主要面向DBA，分析内容和建议需专业、深入。
4. **历史对比分析**：
   - 支持单个或多个AWR报告上传，能进行历史对比分析。
5. **安全性**：
   - 严格校验上传文件，防止恶意代码执行（如XSS、文件类型伪装等）。
6. **用户界面**：
   - 友好、易用，支持多语言（以中文为主）。
7. **可扩展性**：
   - 架构需支持后续集成新分析模块（如ASH报告等）。
8. **兼容性**：
   - 能兼容不同Oracle版本（11g、12c、19c等）生成的AWR报告，包括RAC、CDB/PDB等多种类型。
9. **其他补充**：
   - 支持后续品牌化、UI风格定制。
   - 部署形态可适配本地/云端/私有化需求。

---

## 1. 主要结构与共性

- **报告头部信息**：所有版本均有数据库基本信息（DB Name、Instance、版本、RAC/CDB标识）、主机信息、快照信息（Snap Id/Time）、分析区间等。
- **核心指标区块**：
  - Load Profile（负载概要）
  - Instance Efficiency Percentages（实例效率百分比）
  - Top 10 Foreground Events（前10等待事件）
  - Wait Classes by Total Wait Time（按等待类别统计）
  - Host/Instance CPU、IO Profile、Memory Statistics等
- **主报告导航**：均有目录（Main Report），指向各分析区块（如Wait Events、SQL Statistics、Instance Activity、IO Stats等）。
- **详细区块**：如SQL统计、等待事件、Latch、Buffer Pool、Undo、Segment、Library Cache等。

## 2. 版本/类型差异点

- **RAC与单实例**：
  - RAC报告多出"Global Cache blocks received/served"等RAC特有指标。
  - Snap信息中多出Instances列。
- **12c/19c（CDB/PDB）**：
  - 增加了CDB/PDB相关信息（如Container Name/Id、Pluggable Databases Open等）。
  - 12c/19c部分报告有"WORKLOAD REPOSITORY PDB report (root snapshots)"等新表述。
- **19c/12c新特性**：
  - 19c报告出现"Flash Cache Hit %"、"In-Memory Area"等新指标。
  - 12c/19c部分报告有"ADDM Findings"、"Active Session History (ASH) Report"等新内容。
- **表格结构细节**：
  - 列名、顺序、单位等在不同版本间略有差异（如"Avg Wait(ms)"/"Avg Wait"/"Avg Wait Time"等）。
  - 12c/19c部分表格采用了更复杂的thead/tbody结构。

## 3. 解析与兼容性建议

- **HTML结构**：所有报告均为结构化HTML，表格（table）为主，配合h1/h2/h3/li等标签，便于用BeautifulSoup等库解析。
- **导航锚点**：目录区块通过<a name="xxx">、<a href="#xxx">等锚点跳转，便于定位各分析区块。
- **多实例/多PDB**：需支持多实例（RAC）和多PDB（CDB）场景下的多组数据提取与对比。
- **兼容性**：解析器需适配不同版本、不同表头/列名、单位等差异，建议采用"表头识别+内容抽取"而非硬编码行号。
- **扩展性**：为后续ASH、ADDM等新模块预留接口。

## 4. 下一步RESEARCH计划

1. 详细梳理各版本AWR报告的目录与区块映射，形成"通用区块+特有区块"清单。
2. 提取典型表格结构样例，为后续解析器设计提供依据。
3. 总结各版本/类型的差异点与兼容性处理建议。
4. 持续补充本文件，作为后续架构设计和开发的基础。

## 3. 核心区块字段详细梳理

### 3.1 SQL Statistics区块表格结构

#### SQL ordered by Elapsed Time（按执行时间排序）
| 字段名 | 说明 | 11g | 12c | 19c |
|--------|------|-----|-----|-----|
| Elapsed Time (s) | SQL执行总耗时 | ✓ | ✓ | ✓ |
| Executions | 执行次数 | ✓ | ✓ | ✓ |
| Elapsed Time per Exec (s) | 平均单次执行时间 | ✓ | ✓ | ✓ |
| %Total | 占总DB Time百分比 | ✓ | ✓ | ✓ |
| %CPU | CPU时间占执行时间百分比 | ✓ | ✓ | ✓ |
| %IO | IO时间占执行时间百分比 | ✓ | ✓ | ✓ |
| SQL Id | SQL语句标识符 | ✓ | ✓ | ✓ |
| SQL Module | 调用模块 | ✓ | ✓ | ✓ |
| SQL Text | SQL文本摘要 | ✓ | ✓ | ✓ |
| Container Name | 容器名（CDB/PDB） | - | ✓ | ✓ |

#### SQL ordered by CPU Time（按CPU时间排序）
- 字段结构与Elapsed Time类似，但主排序字段为CPU Time

#### SQL ordered by Gets（按逻辑读排序）
| 字段名 | 说明 | 11g | 12c | 19c |
|--------|------|-----|-----|-----|
| Buffer Gets | 缓冲区获取数 | ✓ | ✓ | ✓ |
| Executions | 执行次数 | ✓ | ✓ | ✓ |
| Gets per Exec | 平均单次逻辑读 | ✓ | ✓ | ✓ |
| %Total | 占总逻辑读百分比 | ✓ | ✓ | ✓ |
| 其他字段同Elapsed Time表 | - | ✓ | ✓ | ✓ |

#### SQL ordered by Reads（按物理读排序）
| 字段名 | 说明 | 11g | 12c | 19c |
|--------|------|-----|-----|-----|
| Physical Reads | 物理读次数 | ✓ | ✓ | ✓ |
| Reads per Exec | 平均单次物理读 | ✓ | ✓ | ✓ |
| Physical Reads (UnOptimized) | 未优化的物理读 | - | ✓ | ✓ |

### 3.2 Instance Activity Stats区块表格结构

#### Key Instance Activity Stats（关键实例活动统计）
| 字段名 | 说明 | 11g | 12c | 19c |
|--------|------|-----|-----|-----|
| Statistic | 统计项名称 | ✓ | ✓ | ✓ |
| Total | 总量 | ✓ | ✓ | ✓ |
| per Second | 每秒值 | ✓ | ✓ | ✓ |
| per Trans | 每事务值 | ✓ | ✓ | ✓ |

常见统计项：
- db block changes：数据块变更数
- execute count：执行计数
- gc cr blocks received：RAC全局缓存块接收（RAC特有）
- gc current blocks received：RAC当前块接收（RAC特有）
- logical reads：逻辑读
- physical reads：物理读
- redo size：重做日志大小
- user calls：用户调用数

### 3.3 IO Stats区块表格结构（19c新增细化）

#### IOStat by Function summary
| 字段名 | 说明 | 11g | 12c | 19c |
|--------|------|-----|-----|-----|
| Function Name | 功能名称 | - | - | ✓ |
| Reads: Data | 读取数据量 | - | - | ✓ |
| Reqs per sec | 每秒请求数 | - | - | ✓ |
| Data per sec | 每秒数据量 | - | - | ✓ |
| Writes: Data | 写入数据量 | - | - | ✓ |
| Waits: Count | 等待计数 | - | - | ✓ |
| Avg Time | 平均时间 | - | - | ✓ |

功能类型包括：Others、DBWR、LGWR、Buffer Cache Reads、Direct Reads/Writes等

#### Tablespace IO Stats（表空间IO统计）
| 字段名 | 说明 | 11g | 12c | 19c |
|--------|------|-----|-----|-----|
| Tablespace | 表空间名称 | ✓ | ✓ | ✓ |
| Reads | 读取次数 | ✓ | ✓ | ✓ |
| Av Reads/s | 平均每秒读 | ✓ | ✓ | ✓ |
| Av Rd(ms) | 平均读延迟 | ✓ | ✓ | ✓ |
| Av Blks/Rd | 平均块数/读 | ✓ | ✓ | ✓ |
| Writes | 写入次数 | ✓ | ✓ | ✓ |
| Buffer Waits | 缓冲等待 | ✓ | ✓ | ✓ |

### 3.4 Wait Events区块表格结构

#### Top 10 Foreground Events by Total Wait Time
| 字段名 | 说明 | 11g | 12c | 19c |
|--------|------|-----|-----|-----|
| Event | 等待事件名称 | ✓ | ✓ | ✓ |
| Waits | 等待次数 | ✓ | ✓ | ✓ |
| Total Wait Time (sec) | 总等待时间 | ✓ | ✓ | ✓ |
| Avg wait (ms) | 平均等待时间 | ✓ | ✓ | ✓ |
| %DB time | 占DB时间百分比 | ✓ | ✓ | ✓ |
| Wait Class | 等待类别 | ✓ | ✓ | ✓ |

### 3.5 Time Model Statistics区块

| 字段名 | 说明 | 11g | 12c | 19c |
|--------|------|-----|-----|-----|
| Statistic Name | 统计项名称 | ✓ | ✓ | ✓ |
| Time (s) | 时间（秒） | ✓ | ✓ | ✓ |
| % of DB Time | 占DB时间百分比 | ✓ | ✓ | ✓ |

核心时间模型项：
- DB time：数据库时间
- DB CPU：CPU时间
- sql execute elapsed time：SQL执行时间
- parse time elapsed：解析时间
- hard parse elapsed time：硬解析时间
- PL/SQL execution elapsed time：PL/SQL执行时间

### 3.6 Service Statistics区块（服务级统计）

| 字段名 | 说明 | 11g | 12c | 19c |
|--------|------|-----|-----|-----|
| Service Name | 服务名称 | ✓ | ✓ | ✓ |
| DB Time (s) | 数据库时间 | ✓ | ✓ | ✓ |
| DB CPU (s) | CPU时间 | ✓ | ✓ | ✓ |
| Physical Reads (K) | 物理读（千） | ✓ | ✓ | ✓ |
| Logical Reads (K) | 逻辑读（千） | ✓ | ✓ | ✓ |

### 3.7 Buffer Pool Statistics区块

| 字段名 | 说明 | 11g | 12c | 19c |
|--------|------|-----|-----|-----|
| P | 池类型（D:default, K:keep, R:recycle） | ✓ | ✓ | ✓ |
| Number of Buffers | 缓冲区数量 | ✓ | ✓ | ✓ |
| Pool Hit% | 池命中率 | ✓ | ✓ | ✓ |
| Buffer Gets | 缓冲区获取数 | ✓ | ✓ | ✓ |
| Physical Reads | 物理读 | ✓ | ✓ | ✓ |
| Physical Writes | 物理写 | ✓ | ✓ | ✓ |
| Free Buff Wait | 空闲缓冲等待 | ✓ | ✓ | ✓ |
| Buffer Busy Waits | 缓冲忙等待 | ✓ | ✓ | ✓ |

### 3.8 Advisory Statistics区块（建议统计）

#### PGA Memory Advisory
| 字段名 | 说明 | 11g | 12c | 19c |
|--------|------|-----|-----|-----|
| PGA Target Est (MB) | PGA目标估计值 | ✓ | ✓ | ✓ |
| Size Factr | 大小因子 | ✓ | ✓ | ✓ |
| W/A MB Processed | 工作区处理MB数 | ✓ | ✓ | ✓ |
| Estd Extra W/A MB Read/Written | 估计额外读写 | ✓ | ✓ | ✓ |
| Estd PGA Cache Hit % | 估计PGA缓存命中率 | ✓ | ✓ | ✓ |
| Estd PGA Overalloc Count | 估计PGA过度分配数 | ✓ | ✓ | ✓ |

#### Shared Pool Advisory
类似结构，包含Size Factor、Est LC Size、Est LC Mem Obj等字段

### 3.5 Segment Statistics区块表格结构

#### Segments by Logical Reads（按逻辑读排序）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Owner | 对象所有者 | IDC_U_UNIAUTH |
| Tablespace Name | 表空间名称 | TS_UNIAUTH |
| Object Name | 对象名称 | T_ONLINE_USER |
| Subobject Name | 子对象名称（如分区） | WRH$_ACTIVE_1932768254_0 |
| Obj. Type | 对象类型 | TABLE/INDEX/LOB |
| Logical Reads | 逻辑读次数 | 3,226,592 |
| %Total | 占总逻辑读百分比 | 89.38 |

#### Segments by Physical Reads（按物理读排序）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Owner | 对象所有者 | SYS |
| Tablespace Name | 表空间名称 | SYSAUX |
| Object Name | 对象名称 | WRH$_LATCH_CHILDREN |
| Physical Reads | 物理读次数 | 3,025 |
| %Total | 占总物理读百分比 | 96.12 |

#### Segments by Physical Writes（按物理写排序）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Direct Writes | 直接写次数 | 915,548 |
| %Total | 占总直接写百分比 | 88.06 |

#### Segments by Row Lock Waits（按行锁等待排序）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Row Lock Waits | 行锁等待次数 | 2 |
| % of Capture | 占捕获的行锁等待百分比 | 66.67 |

#### Segments by Buffer Busy Waits（按缓冲忙等待排序）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Buffer Busy Waits | 缓冲忙等待次数 | 195 |
| % of Capture | 占捕获的缓冲忙等待百分比 | 97.01 |

#### Segments by Table Scans（按表扫描排序）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Table Scans | 表扫描次数 | 39,807 |
| %Total | 占总表扫描百分比 | 96.59 |

#### Segments by DB Blocks Changes（按数据块变化排序）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| DB Block Changes | 数据块变化次数 | 4,439,424 |
| % of Capture | 占捕获的数据块变化百分比 | 53.40 |

### 3.6 Dictionary Cache Stats（字典缓存统计）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Cache | 缓存名称 | dc_histogram_defs |
| Get Requests | Get请求次数 | 197,969 |
| Pct Miss | Get请求未命中率 | 0.27 |
| Scan Reqs | 扫描请求次数 | 0 |
| Pct Miss | 扫描请求未命中率 | - |
| Mod Reqs | 修改请求次数 | 0 |
| Final Usage | 最终使用量 | 5,940 |

### 3.7 Library Cache Activity（库缓存活动）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Namespace | 命名空间 | SQL AREA |
| Get Requests | Get请求次数 | 105,340 |
| Pct Miss | Get请求未命中率 | 0.38 |
| Pin Requests | Pin请求次数 | 662,963 |
| Pct Miss | Pin请求未命中率 | 0.30 |
| Reloads | 重载次数 | 205 |
| Invalidations | 失效次数 | 4 |

### 3.8 Memory Statistics（内存统计）

#### Memory Dynamic Components（动态内存组件）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Component | 组件名称 | DEFAULT buffer cache |
| Begin Snap Size (Mb) | 快照开始时大小 | 15,872.00 |
| Current Size (Mb) | 当前大小 | 15,872.00 |
| Min Size (Mb) | 最小大小 | 15,872.00 |
| Max Size (Mb) | 最大大小 | 16,064.00 |
| Oper Count | 操作次数 | 0 |
| Last Op Typ/Mod | 最后操作类型/模式 | SHR/DEF |

#### Process Memory Summary（进程内存汇总）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Category | 内存类别 | Other/Freeable/SQL/PL/SQL |
| Alloc (MB) | 分配内存 | 894.85 |
| Used (MB) | 使用内存 | - |
| Avg Alloc (MB) | 平均分配 | 3.87 |
| Std Dev Alloc (MB) | 分配标准差 | 24.73 |
| Max Alloc (MB) | 最大分配 | 373 |
| Hist Max Alloc (MB) | 历史最大分配 | 373 |
| Num Proc | 进程数 | 231 |
| Num Alloc | 分配数 | 231 |

#### SGA Memory Summary（SGA内存汇总）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| SGA regions | SGA区域 | Database Buffers |
| Begin Size (Bytes) | 开始大小（字节） | 16,642,998,272 |
| End Size (Bytes) | 结束大小（字节） | 相同则不显示 |

#### SGA breakdown difference（SGA细分差异）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Pool | 池名称 | shared/large/java |
| Name | 组件名称 | KGLH0/SQLA/free memory |
| Begin MB | 开始大小(MB) | 1,585.98 |
| End MB | 结束大小(MB) | 1,574.24 |
| % Diff | 变化百分比 | -0.74 |

### 3.9 Shared Server Statistics（共享服务器统计）

#### Shared Servers Activity（共享服务器活动）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Avg Total Connections | 平均总连接数 | 0 |
| Avg Active Connections | 平均活动连接数 | 0 |
| Avg Total Shared Srvrs | 平均总共享服务器数 | 1 |
| Avg Active Shared Srvrs | 平均活动共享服务器数 | 0 |
| Avg Total Dispatchers | 平均总调度器数 | 1 |
| Avg Active Dispatchers | 平均活动调度器数 | 0 |

#### Shared Servers Rates（共享服务器速率）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Common Queue Per Sec | 每秒公共队列数 | 0 |
| Disp Queue Per Sec | 每秒调度队列数 | 0 |
| Server Msgs/Sec | 每秒服务器消息数 | 0 |
| Server KB/Sec | 每秒服务器KB数 | 0.00 |
| Common Queue Total | 公共队列总数 | 0 |
| Disp Queue Total | 调度队列总数 | 0 |
| Server Total Msgs | 服务器总消息数 | 0 |
| Server Total(KB) | 服务器总KB数 | 0 |

#### Shared Servers Utilization（共享服务器利用率）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Total Server Time (s) | 总服务器时间（秒） | 1,711 |
| %Busy | 忙碌百分比 | 0.00 |
| %Idle | 空闲百分比 | 100.00 |
| Incoming Net % | 传入网络百分比 | 0.00 |
| Outgoing Net % | 传出网络百分比 | 0.00 |

#### Shared Servers Dispatchers（共享服务器调度器）
| 字段名 | 说明 | 示例值 |
|--------|------|---------|
| Name | 调度器名称 | D000 |
| Avg Conns | 平均连接数 | 0.00 |
| Total Disp Time (s) | 总调度时间（秒） | 1,711 |
| %Busy | 忙碌百分比 | 0.00 |
| %Idle | 空闲百分比 | 100.00 |
| Total Queued | 总队列数 | 0 |
| Total Queue Wait (s) | 总队列等待时间（秒） | 0 |
| Avg Queue Wait (ms) | 平均队列等待时间（毫秒） | - |

## 4. 多版本AWR报告区块导航目录对比（续）

### 已梳理的核心区块覆盖度
- ✓ Load Profile
- ✓ Instance Efficiency Percentages
- ✓ Top 10 Foreground Events by Total Wait Time
- ✓ Wait Events Statistics
- ✓ SQL Statistics (多维度)
- ✓ Instance Activity Stats
- ✓ I/O Stats (多维度)
- ✓ Buffer Pool Statistics
- ✓ Segment Statistics (多维度)
- ✓ Dictionary Cache Stats
- ✓ Library Cache Activity
- ✓ Memory Statistics (多维度)
- ✓ Shared Server Statistics (多维度)
- 待梳理：Undo Statistics
- 待梳理：Latch Statistics
- 待梳理：Enqueue Activity
- 待梳理：PGA/SGA/Buffer Pool Advisory
- 待梳理：RAC特有统计（Global Cache/Enqueue Services等）

## 5. 性能诊断规则初步研究（待深化）

### 5.1 核心性能指标阈值参考
根据Oracle官方最佳实践和DBA社区经验：

#### Instance Efficiency指标
- Buffer Nowait %: 应 > 99%
- Buffer Hit %: 应 > 95% (OLTP) 或 > 90% (DSS)
- Library Hit %: 应 > 95%
- Soft Parse %: 应 > 95%
- Execute to Parse %: 越高越好，应 > 70%
- Parse CPU to Parse Elapsd %: 应 > 90%

#### 等待事件分析
- DB CPU应占DB Time的主要部分（理想60-80%）
- 关注Top等待事件：
  - db file sequential read（索引读）
  - db file scattered read（全表扫描）
  - log file sync（日志同步）
  - buffer busy waits（热块竞争）
  - enq: TX - row lock contention（行锁竞争）

#### SQL性能
- 单个SQL不应占用超过10%的DB Time
- 高逻辑读的SQL需要优化
- 执行计划变化需要关注

### 5.2 智能分析功能方向
1. **性能瓶颈自动识别**
   - CPU瓶颈：高CPU等待、高Parse CPU
   - I/O瓶颈：高物理读、慢I/O响应时间
   - 内存瓶颈：低Buffer Hit、高Hard Parse
   - 锁竞争：高锁等待时间

2. **SQL优化建议**
   - 识别TOP SQL（按各维度）
   - 分析执行特征（高频小查询vs低频大查询）
   - 提供索引建议、SQL改写建议

3. **配置优化建议**
   - 基于Advisory统计的内存配置建议
   - 基于负载特征的参数调优建议

---
*更新记录：*
- 2025-06-01 21:31:36 +08:00 - 添加核心区块字段详细梳理（v0.2） 