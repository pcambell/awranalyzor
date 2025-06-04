import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { 
  Typography, 
  Card, 
  Row, 
  Col, 
  Button, 
  Space, 
  Tabs, 
  Switch, 
  message,
  Spin,
  Alert
} from 'antd';
import { 
  LeftOutlined, 
  ReloadOutlined, 
  DownloadOutlined,
  BarChartOutlined,
  PieChartOutlined
} from '@ant-design/icons';
import ReportDisplay from '../components/ReportDisplay';
import WaitEventsChart from '../components/WaitEventsChart';
import { AWRParseResult } from '../types';

const { Title, Paragraph } = Typography;
const { TabPane } = Tabs;

const Results: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(false);
  const [parseResult, setParseResult] = useState<AWRParseResult | null>(null);
  const [chartType, setChartType] = useState<'pie' | 'bar'>('pie');
  const [error, setError] = useState<string | null>(null);

  // 获取解析结果数据 - SOLID原则：依赖注入
  const fetchParseResult = async (resultId: string) => {
    setLoading(true);
    setError(null);
    
    try {
      // 模拟API调用 - 后续替换为真实API
      const response = await fetch(`/api/parse-results/${resultId}/`);
      
      if (!response.ok) {
        throw new Error('无法获取解析结果');
      }
      
      const data: AWRParseResult = await response.json();
      setParseResult(data);
    } catch (err: any) {
      console.error('获取解析结果失败:', err);
      setError(err.message || '获取解析结果失败');
      
      // 开发模式下使用模拟数据
      if (process.env.NODE_ENV === 'development') {
        const mockData = generateMockData();
        setParseResult(mockData);
      }
    } finally {
      setLoading(false);
    }
  };

  // 生成模拟数据用于开发调试 - YAGNI原则
  const generateMockData = (): AWRParseResult => {
    return {
      id: 'mock-result-1',
      report_id: 'mock-report-1',
      status: 'completed',
      data_completeness: 95.5,
      data_quality_score: 88,
      error_message: null,
      db_info: {
        db_name: 'ORCL',
        instance_name: 'orcl1',
        db_version: '19.3.0.0.0',
        host_name: 'db-server-01',
        platform: 'Linux x86-64',
        rac_instances: null,
        cdb_name: null,
        pdb_name: null
      },
      snapshot_info: {
        begin_snap_id: 12345,
        end_snap_id: 12346,
        begin_time: '2025-06-02 10:00:00',
        end_time: '2025-06-02 11:00:00',
        snapshot_duration_minutes: 60
      },
      parse_metadata: {
        parse_duration_seconds: 15.5,
        parser_version: '1.0.0',
        oracle_version: '19c'
      },
      load_profile: [
        {
          metric_name: 'DB CPU',
          per_second: 2.5,
          per_transaction: 45.2,
          per_exec: null,
          per_call: null
        },
        {
          metric_name: 'Logical reads',
          per_second: 1500.8,
          per_transaction: 25000,
          per_exec: 120.5,
          per_call: null
        },
        {
          metric_name: 'Physical reads',
          per_second: 85.2,
          per_transaction: 1420,
          per_exec: 6.8,
          per_call: null
        }
      ],
      wait_events: [
        {
          event_name: 'db file sequential read',
          waits: 15420,
          time_waited_seconds: 125.8,
          avg_wait_ms: 8.16,
          percent_db_time: 15.2
        },
        {
          event_name: 'log file sync',
          waits: 8920,
          time_waited_seconds: 89.5,
          avg_wait_ms: 10.03,
          percent_db_time: 10.8
        },
        {
          event_name: 'CPU time',
          waits: 0,
          time_waited_seconds: 450.2,
          avg_wait_ms: 0,
          percent_db_time: 54.5
        }
      ],
      sql_statistics: [
        {
          sql_id: 'abc123def456',
          executions: 1250,
          cpu_time_seconds: 45.8,
          elapsed_time_seconds: 52.3,
          buffer_gets: 125000,
          disk_reads: 850,
          rows_processed: 25000
        },
        {
          sql_id: 'def456ghi789',
          executions: 890,
          cpu_time_seconds: 32.1,
          elapsed_time_seconds: 38.7,
          buffer_gets: 98000,
          disk_reads: 520,
          rows_processed: 18900
        }
      ]
    };
  };

  // 处理导出功能 - 安全编码原则
  const handleExport = (format: 'pdf' | 'excel') => {
    if (!parseResult) {
      message.error('暂无数据可导出');
      return;
    }

    message.info(`正在准备${format.toUpperCase()}导出...`);
    
    // TODO: 实现实际的导出功能
    // 调用后端API生成导出文件
  };

  // 刷新数据
  const handleRefresh = () => {
    if (id) {
      fetchParseResult(id);
    }
  };

  // 组件加载时获取数据
  useEffect(() => {
    if (id) {
      fetchParseResult(id);
    } else {
      setError('缺少解析结果ID');
    }
  }, [id]);

  // 错误状态处理
  if (error && !parseResult) {
    return (
      <div>
        <div style={{ marginBottom: 16 }}>
          <Button 
            icon={<LeftOutlined />}
            onClick={() => navigate('/upload')}
          >
            返回上传
          </Button>
        </div>
        
        <Alert
          message="加载失败"
          description={error}
          type="error"
          showIcon
          action={
            <Button size="small" onClick={handleRefresh}>
              重试
            </Button>
          }
        />
      </div>
    );
  }

  return (
    <div>
      {/* 页面头部 */}
      <div style={{ marginBottom: 24 }}>
        <Space style={{ marginBottom: 16 }}>
          <Button 
            icon={<LeftOutlined />}
            onClick={() => navigate('/upload')}
          >
            返回上传
          </Button>
          <Button 
            icon={<ReloadOutlined />}
            onClick={handleRefresh}
            loading={loading}
          >
            刷新
          </Button>
        </Space>
        
        <Title level={2}>AWR解析结果</Title>
        <Paragraph>
          详细的Oracle AWR报告分析结果，包含性能指标、等待事件、SQL统计等信息
        </Paragraph>
      </div>

      {/* 主要内容 */}
      <Tabs defaultActiveKey="report" type="card" size="large">
        {/* 报告详情标签页 */}
        <TabPane tab="报告详情" key="report">
          <ReportDisplay
            parseResult={parseResult}
            loading={loading}
            onExport={handleExport}
          />
        </TabPane>

        {/* 图表分析标签页 */}
        <TabPane tab="图表分析" key="charts">
          <Row gutter={[16, 16]}>
            <Col span={24}>
              <Card 
                title="等待事件分析"
                extra={
                  <Space>
                    <span>图表类型:</span>
                    <Switch
                      checkedChildren={<BarChartOutlined />}
                      unCheckedChildren={<PieChartOutlined />}
                      checked={chartType === 'bar'}
                      onChange={(checked) => setChartType(checked ? 'bar' : 'pie')}
                    />
                  </Space>
                }
              >
                <WaitEventsChart
                  waitEvents={parseResult?.wait_events || []}
                  chartType={chartType}
                  loading={loading}
                  height={500}
                />
              </Card>
            </Col>
          </Row>
        </TabPane>

        {/* 性能趋势标签页（预留） */}
        <TabPane tab="性能趋势" key="trends" disabled>
          <Card>
            <div style={{ textAlign: 'center', padding: '40px 0' }}>
              <Paragraph>性能趋势分析功能将在后续版本中实现</Paragraph>
            </div>
          </Card>
        </TabPane>
      </Tabs>
    </div>
  );
};

export default Results; 