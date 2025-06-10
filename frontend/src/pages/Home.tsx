import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Typography,
  Row,
  Col,
  Card,
  Space,
  Statistic,
  Alert,
  List,
  Timeline,
  Button,
} from 'antd';
import {
  UploadOutlined,
  BarChartOutlined,
  HistoryOutlined,
  FileTextOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ReloadOutlined,
} from '@ant-design/icons';

const { Title, Paragraph } = Typography;

const Home: React.FC = () => {
  const navigate = useNavigate();
  
  // 统计数据状态
  const [stats, setStats] = useState({
    totalFiles: 0,
    totalParses: 0,
    successRate: 0,
    avgParseTime: 0,
  });
  const [loading, setLoading] = useState(false);

  // 获取统计数据
  const fetchStatistics = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/dashboard/statistics/', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        setStats({
          totalFiles: data.total_files || 0,
          totalParses: data.total_parses || 0,
          successRate: data.success_rate || 0,
          avgParseTime: data.avg_parse_time || 0,
        });
      } else {
        console.error('获取统计数据失败:', response.status);
        // 保持默认值0，不显示错误消息
      }
    } catch (error) {
      console.error('获取统计数据失败:', error);
      // 保持默认值0，不显示错误消息
    } finally {
      setLoading(false);
    }
  };

  // 组件挂载时获取数据
  useEffect(() => {
    fetchStatistics();
  }, []);

  // 快速操作
  const quickActions = [
    {
      title: '上传AWR文件',
      description: '上传Oracle AWR报告进行解析',
      icon: <UploadOutlined style={{ fontSize: 24 }} />,
      action: () => navigate('/upload'),
      type: 'primary' as const,
    },
    {
      title: '查看结果',
      description: '查看已解析的AWR报告结果',
      icon: <BarChartOutlined style={{ fontSize: 24 }} />,
      action: () => navigate('/results'),
      type: 'default' as const,
    },
    {
      title: '历史记录',
      description: '查看所有解析历史记录',
      icon: <HistoryOutlined style={{ fontSize: 24 }} />,
      action: () => navigate('/history'),
      type: 'default' as const,
    },
  ];

  // 支持的功能列表
  const features = [
    'Oracle 11g/12c/19c AWR报告解析',
    'RAC（Real Application Clusters）支持',
    'CDB/PDB（Container Database）支持',
    '性能指标分析和可视化',
    '等待事件分析',
    'SQL语句性能统计',
    '实例活动统计',
    '历史趋势对比',
  ];

  // 最近更新（示例）
  const recentUpdates = [
    {
      title: '系统上线',
      description: 'AWR分析器系统正式上线',
      time: '2025-06-02',
      status: 'completed',
    },
    {
      title: '核心解析引擎',
      description: 'Oracle 19c/11g解析器开发完成',
      time: '2025-06-02',
      status: 'completed',
    },
    {
      title: 'Web界面',
      description: '用户界面开发完成',
      time: '2025-06-02',
      status: 'completed',
    },
  ];

  return (
    <div>
      <div style={{ marginBottom: 24 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={2}>Oracle AWR 分析器</Title>
            <Paragraph>
              一个专业的Oracle AWR（Automatic Workload Repository）报告分析工具，
              支持多版本Oracle数据库，提供详细的性能分析和可视化展示。
            </Paragraph>
          </Col>
          <Col>
            <Button 
              type="text" 
              loading={loading}
              onClick={fetchStatistics}
              icon={<ReloadOutlined />}
            >
              刷新数据
            </Button>
          </Col>
        </Row>
      </div>

      {/* 统计概览 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic
              title="已上传文件"
              value={stats.totalFiles}
              prefix={<FileTextOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic
              title="解析次数"
              value={stats.totalParses}
              prefix={<BarChartOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic
              title="成功率"
              value={stats.successRate}
              suffix="%"
              prefix={<CheckCircleOutlined />}
            />
          </Card>
        </Col>
        <Col xs={24} sm={12} md={6}>
          <Card loading={loading}>
            <Statistic
              title="平均解析时间"
              value={stats.avgParseTime}
              suffix="秒"
              prefix={<ClockCircleOutlined />}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16} style={{ marginBottom: 24 }}>
        {/* 快速操作 */}
        <Col xs={24} lg={16}>
          <Card title="快速操作" style={{ height: '100%' }}>
            <Row gutter={16}>
              {quickActions.map((action, index) => (
                <Col xs={24} md={8} key={index} style={{ marginBottom: 16 }}>
                  <Card
                    hoverable
                    style={{
                      textAlign: 'center',
                      height: 140,
                      display: 'flex',
                      flexDirection: 'column',
                      justifyContent: 'center',
                    }}
                    onClick={action.action}
                  >
                    <Space direction="vertical" size="small">
                      {action.icon}
                      <Title level={5} style={{ margin: 0 }}>
                        {action.title}
                      </Title>
                      <Paragraph 
                        style={{ margin: 0, fontSize: 12, color: '#666' }}
                        ellipsis={{ rows: 2 }}
                      >
                        {action.description}
                      </Paragraph>
                    </Space>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>

        {/* 最近更新 */}
        <Col xs={24} lg={8}>
          <Card title="最近更新" style={{ height: '100%' }}>
            <Timeline>
              {recentUpdates.map((update, index) => (
                <Timeline.Item
                  key={index}
                  color={update.status === 'completed' ? 'green' : 'blue'}
                >
                  <div style={{ fontSize: 12, color: '#999' }}>{update.time}</div>
                  <div style={{ fontWeight: 500 }}>{update.title}</div>
                  <div style={{ fontSize: 12, color: '#666' }}>{update.description}</div>
                </Timeline.Item>
              ))}
            </Timeline>
          </Card>
        </Col>
      </Row>

      {/* 功能特性 */}
      <Row gutter={16}>
        <Col xs={24} lg={12}>
          <Card title="支持的功能">
            <List
              size="small"
              dataSource={features}
              renderItem={(item) => (
                <List.Item>
                  <CheckCircleOutlined style={{ color: '#52c41a', marginRight: 8 }} />
                  {item}
                </List.Item>
              )}
            />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card title="使用说明">
            <Alert
              message="开始使用"
              description={
                <div>
                  <Paragraph style={{ marginBottom: 8 }}>
                    1. 点击"上传AWR文件"上传您的Oracle AWR报告
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 8 }}>
                    2. 系统将自动检测Oracle版本并解析报告
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 8 }}>
                    3. 在"解析结果"页面查看详细的性能分析
                  </Paragraph>
                  <Paragraph style={{ marginBottom: 0 }}>
                    4. 支持多个文件对比分析和历史趋势查看
                  </Paragraph>
                </div>
              }
              type="info"
              showIcon
            />
          </Card>
        </Col>
      </Row>
    </div>
  );
};

export default Home; 