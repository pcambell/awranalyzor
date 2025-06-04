import React, { useState, useEffect, useCallback } from 'react';
import {
  Card,
  Progress,
  Typography,
  Space,
  Button,
  Alert,
  Steps,
  Tag,
  Descriptions,
  Divider,
  message
} from 'antd';
import {
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  CheckCircleOutlined,
  CloseCircleOutlined,
  LoadingOutlined,
  ClockCircleOutlined
} from '@ant-design/icons';

const { Title, Text, Paragraph } = Typography;
const { Step } = Steps;

// 解析状态类型定义
export interface ParseStatus {
  id: string;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  progress: number;
  currentStep: string;
  startTime?: string;
  endTime?: string;
  estimatedTimeRemaining?: number;
  error?: string;
  stages: ParseStage[];
}

export interface ParseStage {
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress: number;
  startTime?: string;
  endTime?: string;
  details?: string;
}

interface ParseProgressProps {
  parseId: string;
  onComplete?: (result: any) => void;
  onError?: (error: string) => void;
  onCancel?: () => void;
  autoRefresh?: boolean;
  refreshInterval?: number;
}

const ParseProgress: React.FC<ParseProgressProps> = ({
  parseId,
  onComplete,
  onError,
  onCancel,
  autoRefresh = true,
  refreshInterval = 2000
}) => {
  const [parseStatus, setParseStatus] = useState<ParseStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [cancelling, setCancelling] = useState(false);

  // 获取解析状态 - 单一职责原则
  const fetchParseStatus = useCallback(async () => {
    try {
      const response = await fetch(`/api/parse-status/${parseId}/`);
      
      if (!response.ok) {
        throw new Error('无法获取解析状态');
      }
      
      const status: ParseStatus = await response.json();
      setParseStatus(status);
      
      // 处理完成状态
      if (status.status === 'completed' && onComplete) {
        onComplete(status);
      } else if (status.status === 'failed' && onError) {
        onError(status.error || '解析失败');
      }
      
    } catch (err: any) {
      console.error('获取解析状态失败:', err);
      
      // 开发模式使用模拟数据
      if (process.env.NODE_ENV === 'development') {
        setParseStatus(generateMockStatus());
      } else {
        message.error('获取解析状态失败');
      }
    } finally {
      setLoading(false);
    }
  }, [parseId, onComplete, onError]);

  // 生成模拟状态数据 - 开发调试用
  const generateMockStatus = (): ParseStatus => {
    const mockProgress = Math.min(85, Date.now() % 100);
    return {
      id: parseId,
      status: mockProgress >= 100 ? 'completed' : 'running',
      progress: mockProgress,
      currentStep: '解析Wait Events数据',
      startTime: '2025-06-03 09:30:00',
      estimatedTimeRemaining: Math.max(0, Math.floor((100 - mockProgress) / 10) * 5),
      stages: [
        {
          name: '文件验证',
          status: 'completed',
          progress: 100,
          startTime: '2025-06-03 09:30:00',
          endTime: '2025-06-03 09:30:15',
          details: '文件格式验证通过'
        },
        {
          name: '解析数据库信息',
          status: 'completed',
          progress: 100,
          startTime: '2025-06-03 09:30:15',
          endTime: '2025-06-03 09:30:45',
          details: 'Oracle 19c数据库信息提取完成'
        },
        {
          name: '解析Load Profile',
          status: 'completed',
          progress: 100,
          startTime: '2025-06-03 09:30:45',
          endTime: '2025-06-03 09:31:20',
          details: '负载概要数据解析完成'
        },
        {
          name: '解析Wait Events',
          status: mockProgress >= 80 ? 'completed' : 'running',
          progress: Math.min(100, mockProgress + 15),
          startTime: '2025-06-03 09:31:20',
          endTime: mockProgress >= 80 ? '2025-06-03 09:32:10' : undefined,
          details: mockProgress >= 80 ? '等待事件数据解析完成' : '正在解析等待事件数据...'
        },
        {
          name: '解析SQL Statistics',
          status: mockProgress >= 90 ? 'completed' : mockProgress >= 80 ? 'running' : 'pending',
          progress: Math.max(0, Math.min(100, mockProgress - 80) * 5),
          startTime: mockProgress >= 80 ? '2025-06-03 09:32:10' : undefined,
          details: mockProgress >= 90 ? 'SQL统计数据解析完成' : 
                   mockProgress >= 80 ? '正在解析SQL统计数据...' : '等待开始'
        }
      ]
    };
  };

  // 取消解析 - 错误处理
  const handleCancel = async () => {
    if (!parseStatus || parseStatus.status !== 'running') {
      message.warning('当前状态无法取消');
      return;
    }

    setCancelling(true);
    
    try {
      const response = await fetch(`/api/parse-cancel/${parseId}/`, {
        method: 'POST'
      });
      
      if (!response.ok) {
        throw new Error('取消解析失败');
      }
      
      message.success('已发送取消请求');
      
      if (onCancel) {
        onCancel();
      }
      
    } catch (err: any) {
      console.error('取消解析失败:', err);
      message.error('取消解析失败');
    } finally {
      setCancelling(false);
    }
  };

  // 格式化时间 - DRY原则
  const formatDuration = (seconds: number): string => {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = seconds % 60;
    
    if (minutes > 0) {
      return `${minutes}分${remainingSeconds}秒`;
    }
    return `${remainingSeconds}秒`;
  };

  // 获取状态图标
  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'pending':
        return <ClockCircleOutlined style={{ color: '#faad14' }} />;
      case 'running':
        return <LoadingOutlined style={{ color: '#1890ff' }} />;
      case 'completed':
        return <CheckCircleOutlined style={{ color: '#52c41a' }} />;
      case 'failed':
        return <CloseCircleOutlined style={{ color: '#ff4d4f' }} />;
      case 'cancelled':
        return <StopOutlined style={{ color: '#d9d9d9' }} />;
      default:
        return <ClockCircleOutlined style={{ color: '#d9d9d9' }} />;
    }
  };

  // 自动刷新机制
  useEffect(() => {
    fetchParseStatus();
    
    if (!autoRefresh) return;
    
    const interval = setInterval(() => {
      if (parseStatus?.status === 'running') {
        fetchParseStatus();
      }
    }, refreshInterval);
    
    return () => clearInterval(interval);
  }, [fetchParseStatus, autoRefresh, refreshInterval, parseStatus?.status]);

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <LoadingOutlined style={{ fontSize: 24 }} />
          <div style={{ marginTop: 16 }}>
            <Text>正在获取解析状态...</Text>
          </div>
        </div>
      </Card>
    );
  }

  if (!parseStatus) {
    return (
      <Card>
        <Alert
          message="无法获取解析状态"
          description="请检查网络连接或稍后重试"
          type="error"
          showIcon
          action={
            <Button size="small" onClick={() => fetchParseStatus()}>
              重试
            </Button>
          }
        />
      </Card>
    );
  }

  return (
    <div>
      {/* 总体进度卡片 */}
      <Card
        title={
          <Space>
            {getStatusIcon(parseStatus.status)}
            <Text strong>解析进度</Text>
            <Tag color={parseStatus.status === 'running' ? 'processing' : 
                        parseStatus.status === 'completed' ? 'success' :
                        parseStatus.status === 'failed' ? 'error' : 'default'}>
              {parseStatus.status === 'running' ? '进行中' :
               parseStatus.status === 'completed' ? '已完成' :
               parseStatus.status === 'failed' ? '失败' :
               parseStatus.status === 'cancelled' ? '已取消' : '等待中'}
            </Tag>
          </Space>
        }
        extra={
          parseStatus.status === 'running' && (
            <Button 
              danger
              icon={<StopOutlined />}
              onClick={handleCancel}
              loading={cancelling}
              size="small"
            >
              取消解析
            </Button>
          )
        }
        style={{ marginBottom: 16 }}
      >
        {/* 主进度条 */}
        <div style={{ marginBottom: 24 }}>
          <Progress
            percent={parseStatus.progress}
            status={parseStatus.status === 'failed' ? 'exception' : 
                    parseStatus.status === 'completed' ? 'success' : 'active'}
            strokeWidth={8}
            format={percent => (
              <span style={{ fontSize: 16, fontWeight: 'bold' }}>
                {percent}%
              </span>
            )}
          />
          <div style={{ marginTop: 8, textAlign: 'center' }}>
            <Text>{parseStatus.currentStep}</Text>
          </div>
        </div>

        {/* 解析信息 */}
        <Descriptions column={3} size="small">
          <Descriptions.Item label="解析ID">
            <Text code>{parseStatus.id}</Text>
          </Descriptions.Item>
          <Descriptions.Item label="开始时间">
            {parseStatus.startTime || '-'}
          </Descriptions.Item>
          <Descriptions.Item label="预计剩余">
            {parseStatus.estimatedTimeRemaining ? 
              formatDuration(parseStatus.estimatedTimeRemaining) : '-'}
          </Descriptions.Item>
        </Descriptions>

        {/* 错误信息 */}
        {parseStatus.error && (
          <Alert
            message="解析错误"
            description={parseStatus.error}
            type="error"
            showIcon
            style={{ marginTop: 16 }}
          />
        )}
      </Card>

      {/* 详细步骤进度 */}
      <Card title="详细步骤" size="small">
        <Steps
          direction="vertical"
          current={parseStatus.stages.findIndex(stage => stage.status === 'running')}
          status={parseStatus.status === 'failed' ? 'error' : undefined}
        >
          {parseStatus.stages.map((stage, index) => (
            <Step
              key={index}
              title={stage.name}
              description={
                <div>
                  <div style={{ marginBottom: 8 }}>
                    <Progress
                      percent={stage.progress}
                      size="small"
                      status={stage.status === 'failed' ? 'exception' : 
                              stage.status === 'completed' ? 'success' : 'active'}
                      showInfo={false}
                    />
                    <Text style={{ marginLeft: 8, fontSize: 12 }}>
                      {stage.progress}%
                    </Text>
                  </div>
                  {stage.details && (
                    <Text type="secondary" style={{ fontSize: 12 }}>
                      {stage.details}
                    </Text>
                  )}
                  {stage.startTime && (
                    <div style={{ marginTop: 4 }}>
                      <Text type="secondary" style={{ fontSize: 12 }}>
                        开始: {stage.startTime}
                        {stage.endTime && ` | 结束: ${stage.endTime}`}
                      </Text>
                    </div>
                  )}
                </div>
              }
              status={stage.status === 'running' ? 'process' :
                      stage.status === 'completed' ? 'finish' :
                      stage.status === 'failed' ? 'error' : 'wait'}
              icon={stage.status === 'running' ? <LoadingOutlined /> : undefined}
            />
          ))}
        </Steps>
      </Card>
    </div>
  );
};

export default ParseProgress; 