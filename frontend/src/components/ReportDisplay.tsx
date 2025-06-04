import React, { useState, useEffect, useMemo } from 'react';
import {
  Card,
  Typography,
  Descriptions,
  Table,
  Tabs,
  Row,
  Col,
  Statistic,
  Progress,
  Tag,
  Space,
  Alert,
  Button,
  Tooltip,
  Spin,
  Empty,
  Divider
} from 'antd';
import {
  DownloadOutlined,
  InfoCircleOutlined,
  ClockCircleOutlined,
  DatabaseOutlined,
  BarChartOutlined,
  TableOutlined
} from '@ant-design/icons';
import type { ColumnsType } from 'antd/es/table';
import { AWRParseResult, LoadProfileMetric, WaitEvent, SqlStatistic } from '../types';

const { Title, Text, Paragraph } = Typography;

interface ReportDisplayProps {
  parseResult: AWRParseResult;
  loading?: boolean;
  onExport?: (format: 'pdf' | 'excel') => void;
}

const ReportDisplay: React.FC<ReportDisplayProps> = ({
  parseResult,
  loading = false,
  onExport
}) => {
  const [activeTab, setActiveTab] = useState('overview');

  // 报告概要信息 - KISS原则：保持简单
  const reportOverview = useMemo(() => {
    if (!parseResult || !parseResult.db_info) return null;
    
    const { db_info, snapshot_info, parse_metadata } = parseResult;
    
    return {
      database: db_info.db_name,
      instance: db_info.instance_name,
      version: db_info.db_version,
      host: db_info.host_name,
      snapRange: `${snapshot_info?.begin_snap_id} - ${snapshot_info?.end_snap_id}`,
      duration: snapshot_info?.snapshot_duration_minutes 
        ? `${Math.floor(snapshot_info.snapshot_duration_minutes / 60)}h ${snapshot_info.snapshot_duration_minutes % 60}m`
        : 'N/A',
      parseTime: parse_metadata?.parse_duration_seconds 
        ? `${parse_metadata.parse_duration_seconds}s`
        : 'N/A'
    };
  }, [parseResult]);

  // Load Profile表格配置 - 可测试性设计
  const loadProfileColumns: ColumnsType<LoadProfileMetric> = [
    {
      title: '指标名称',
      dataIndex: 'metric_name',
      key: 'metric_name',
      width: 200,
      fixed: 'left',
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: '每秒',
      dataIndex: 'per_second',
      key: 'per_second',
      width: 120,
      align: 'right',
      render: (value: number) => value?.toLocaleString() || '-'
    },
    {
      title: '每事务',
      dataIndex: 'per_transaction',
      key: 'per_transaction',
      width: 120,
      align: 'right',
      render: (value: number) => value?.toLocaleString() || '-'
    },
    {
      title: '每执行',
      dataIndex: 'per_exec',
      key: 'per_exec',
      width: 120,
      align: 'right',
      render: (value: number) => value?.toLocaleString() || '-'
    },
    {
      title: '每调用',
      dataIndex: 'per_call',
      key: 'per_call',
      width: 120,
      align: 'right',
      render: (value: number) => value?.toLocaleString() || '-'
    }
  ];

  // Wait Events表格配置 - 高内聚低耦合
  const waitEventsColumns: ColumnsType<WaitEvent> = [
    {
      title: '等待事件',
      dataIndex: 'event_name',
      key: 'event_name',
      width: 250,
      fixed: 'left',
      render: (text: string) => <Text strong>{text}</Text>
    },
    {
      title: '等待次数',
      dataIndex: 'waits',
      key: 'waits',
      width: 120,
      align: 'right',
      render: (value: number) => value?.toLocaleString() || '-'
    },
    {
      title: '时间(s)',
      dataIndex: 'time_waited_seconds',
      key: 'time_waited_seconds',
      width: 120,
      align: 'right',
      render: (value: number) => value?.toFixed(2) || '-'
    },
    {
      title: '平均等待(ms)',
      dataIndex: 'avg_wait_ms',
      key: 'avg_wait_ms',
      width: 140,
      align: 'right',
      render: (value: number) => value?.toFixed(2) || '-'
    },
    {
      title: '% DB时间',
      dataIndex: 'percent_db_time',
      key: 'percent_db_time',
      width: 120,
      align: 'right',
      render: (value: number) => {
        if (value === null || value === undefined) return '-';
        const percentage = parseFloat(value.toFixed(2));
        return (
          <div>
            <Progress
              percent={percentage}
              size="small"
              showInfo={false}
              strokeColor={percentage > 10 ? '#ff4d4f' : percentage > 5 ? '#faad14' : '#52c41a'}
            />
            <Text style={{ fontSize: 12 }}>{percentage}%</Text>
          </div>
        );
      }
    }
  ];

  // SQL Statistics表格配置
  const sqlStatsColumns: ColumnsType<SqlStatistic> = [
    {
      title: 'SQL ID',
      dataIndex: 'sql_id',
      key: 'sql_id',
      width: 120,
      fixed: 'left',
      render: (text: string) => (
        <Tooltip title="点击查看SQL详情">
          <Text code copyable={{ text }}>{text}</Text>
        </Tooltip>
      )
    },
    {
      title: '执行次数',
      dataIndex: 'executions',
      key: 'executions',
      width: 100,
      align: 'right',
      render: (value: number) => value?.toLocaleString() || '-'
    },
    {
      title: 'CPU时间(s)',
      dataIndex: 'cpu_time_seconds',
      key: 'cpu_time_seconds',
      width: 120,
      align: 'right',
      render: (value: number) => value?.toFixed(2) || '-'
    },
    {
      title: '经过时间(s)',
      dataIndex: 'elapsed_time_seconds',
      key: 'elapsed_time_seconds',
      width: 120,
      align: 'right',
      render: (value: number) => value?.toFixed(2) || '-'
    },
    {
      title: '逻辑读',
      dataIndex: 'buffer_gets',
      key: 'buffer_gets',
      width: 120,
      align: 'right',
      render: (value: number) => value?.toLocaleString() || '-'
    },
    {
      title: '物理读',
      dataIndex: 'disk_reads',
      key: 'disk_reads',
      width: 120,
      align: 'right',
      render: (value: number) => value?.toLocaleString() || '-'
    }
  ];

  // 导出功能处理 - 安全编码原则
  const handleExport = (format: 'pdf' | 'excel') => {
    if (onExport) {
      onExport(format);
    }
  };

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text>正在加载解析结果...</Text>
          </div>
        </div>
      </Card>
    );
  }

  if (!parseResult) {
    return (
      <Card>
        <Empty
          description="暂无解析结果"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    );
  }

  return (
    <div>
      {/* 报告头部信息 */}
      <Card 
        title={
          <Space>
            <DatabaseOutlined />
            <Text strong>AWR报告解析结果</Text>
          </Space>
        }
        extra={
          <Space>
            <Tooltip title="导出PDF报告">
              <Button 
                icon={<DownloadOutlined />} 
                onClick={() => handleExport('pdf')}
              >
                PDF
              </Button>
            </Tooltip>
            <Tooltip title="导出Excel数据">
              <Button 
                icon={<DownloadOutlined />} 
                onClick={() => handleExport('excel')}
              >
                Excel
              </Button>
            </Tooltip>
          </Space>
        }
        style={{ marginBottom: 24 }}
      >
        {reportOverview && (
          <Descriptions column={3} size="small">
            <Descriptions.Item 
              label={<><DatabaseOutlined /> 数据库</>}
            >
              {reportOverview.database}
            </Descriptions.Item>
            <Descriptions.Item label="实例">
              {reportOverview.instance}
            </Descriptions.Item>
            <Descriptions.Item label="版本">
              <Tag color="blue">{reportOverview.version}</Tag>
            </Descriptions.Item>
            <Descriptions.Item label="主机">
              {reportOverview.host}
            </Descriptions.Item>
            <Descriptions.Item 
              label={<><ClockCircleOutlined /> 快照范围</>}
            >
              {reportOverview.snapRange}
            </Descriptions.Item>
            <Descriptions.Item label="持续时间">
              {reportOverview.duration}
            </Descriptions.Item>
          </Descriptions>
        )}
      </Card>

      {/* 主要内容标签页 */}
      <Card>
        <Tabs 
          activeKey={activeTab} 
          onChange={setActiveTab}
          type="card"
          size="large"
          items={[
            {
              key: 'overview',
              label: (
                <Space>
                  <InfoCircleOutlined />
                  概要信息
                </Space>
              ),
              children: (
                <div>
                  <Row gutter={16}>
                    <Col xs={24} sm={12} md={6}>
                      <Statistic
                        title="解析状态"
                        value={parseResult.status === 'completed' ? '成功' : '失败'}
                        valueStyle={{ 
                          color: parseResult.status === 'completed' ? '#3f8600' : '#cf1322' 
                        }}
                      />
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                      <Statistic
                        title="数据完整性"
                        value={parseResult.data_completeness || 0}
                        suffix="%"
                        valueStyle={{ color: '#1890ff' }}
                      />
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                      <Statistic
                        title="解析时间"
                        value={reportOverview?.parseTime || 'N/A'}
                        valueStyle={{ color: '#722ed1' }}
                      />
                    </Col>
                    <Col xs={24} sm={12} md={6}>
                      <Statistic
                        title="数据质量"
                        value={parseResult.data_quality_score || 0}
                        suffix="/100"
                        valueStyle={{ color: '#eb2f96' }}
                      />
                    </Col>
                  </Row>
                  
                  {parseResult.error_message && (
                    <Alert
                      message="解析警告"
                      description={parseResult.error_message}
                      type="warning"
                      showIcon
                      style={{ marginTop: 16 }}
                    />
                  )}
                </div>
              )
            },
            {
              key: 'load_profile',
              label: (
                <Space>
                  <BarChartOutlined />
                  Load Profile
                </Space>
              ),
              children: (
                <Table
                  columns={loadProfileColumns}
                  dataSource={parseResult.load_profile || []}
                  rowKey="metric_name"
                  scroll={{ x: 800, y: 600 }}
                  pagination={{
                    pageSize: 20,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 项指标`
                  }}
                  size="small"
                />
              )
            },
            {
              key: 'wait_events',
              label: (
                <Space>
                  <ClockCircleOutlined />
                  等待事件
                </Space>
              ),
              children: (
                <Table
                  columns={waitEventsColumns}
                  dataSource={parseResult.wait_events || []}
                  rowKey="event_name"
                  scroll={{ x: 1000, y: 600 }}
                  pagination={{
                    pageSize: 20,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 个等待事件`
                  }}
                  size="small"
                />
              )
            },
            {
              key: 'sql_stats',
              label: (
                <Space>
                  <TableOutlined />
                  SQL统计
                </Space>
              ),
              children: (
                <Table
                  columns={sqlStatsColumns}
                  dataSource={parseResult.sql_statistics || []}
                  rowKey="sql_id"
                  scroll={{ x: 1200, y: 600 }}
                  pagination={{
                    pageSize: 15,
                    showSizeChanger: true,
                    showQuickJumper: true,
                    showTotal: (total) => `共 ${total} 条SQL统计`
                  }}
                  size="small"
                />
              )
            }
          ]}
        />
      </Card>
    </div>
  );
};

export default ReportDisplay; 