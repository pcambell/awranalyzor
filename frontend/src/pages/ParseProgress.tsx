import React, { useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { 
  Typography, 
  Button, 
  Space, 
  message,
  Card,
  Row,
  Col,
  Statistic
} from 'antd';
import { 
  LeftOutlined, 
  EyeOutlined,
  HistoryOutlined
} from '@ant-design/icons';
import ParseProgress from '../components/ParseProgress';
import { useParseStatusSocket } from '../hooks/useParseStatusSocket';
import { 
  updateTaskStatus, 
  completeParseTask, 
  failParseTask, 
  cancelParseTask,
  selectTaskById,
  selectActiveTasks
} from '../store/slices/parseSlice';
import type { RootState } from '../store';

const { Title, Paragraph } = Typography;

const ParseProgressPage: React.FC = () => {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const dispatch = useDispatch();
  
  // Redux状态
  const currentTask = useSelector((state: RootState) => 
    taskId ? selectTaskById(state, taskId) : null
  );
  const activeTasks = useSelector(selectActiveTasks);
  
  // WebSocket实时通信 - 高内聚低耦合
  const { connected, connecting, error: socketError } = useParseStatusSocket({
    parseId: taskId || '',
    onStatusUpdate: (status) => {
      if (taskId) {
        dispatch(updateTaskStatus({ taskId, status }));
      }
    },
    onComplete: (result) => {
      if (taskId) {
        dispatch(completeParseTask({ 
          taskId, 
          resultId: result?.resultId 
        }));
        message.success('解析完成！');
        
        // 自动跳转到结果页面
        if (result?.resultId) {
          setTimeout(() => {
            navigate(`/results/${result.resultId}`);
          }, 2000);
        }
      }
    },
    onError: (error) => {
      if (taskId) {
        dispatch(failParseTask({ taskId, error }));
        message.error(`解析失败: ${error}`);
      }
    },
    onCancel: () => {
      if (taskId) {
        dispatch(cancelParseTask({ taskId }));
        message.info('解析已取消');
        navigate('/upload');
      }
    }
  });

  // 处理取消解析
  const handleCancel = () => {
    navigate('/upload');
  };

  // 查看结果
  const handleViewResult = () => {
    if (currentTask?.resultId) {
      navigate(`/results/${currentTask.resultId}`);
    }
  };

  // 查看历史
  const handleViewHistory = () => {
    navigate('/history');
  };

  useEffect(() => {
    if (!taskId) {
      message.error('缺少解析任务ID');
      navigate('/upload');
    }
  }, [taskId, navigate]);

  if (!taskId) {
    return null;
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
          
          {currentTask?.status === 'completed' && currentTask.resultId && (
            <Button 
              type="primary"
              icon={<EyeOutlined />}
              onClick={handleViewResult}
            >
              查看解析结果
            </Button>
          )}
          
          <Button 
            icon={<HistoryOutlined />}
            onClick={handleViewHistory}
          >
            解析历史
          </Button>
        </Space>
        
        <Title level={2}>解析进度跟踪</Title>
        {currentTask && (
          <Paragraph>
            文件: <strong>{currentTask.fileName}</strong> | 
            任务ID: <code>{currentTask.id}</code>
          </Paragraph>
        )}
      </div>

      {/* 连接状态指示 */}
      {socketError && (
        <Card 
          type="inner" 
          style={{ marginBottom: 16, borderColor: '#ff4d4f' }}
        >
          <Row gutter={16} align="middle">
            <Col flex="auto">
              <Paragraph style={{ margin: 0, color: '#ff4d4f' }}>
                实时连接异常: {socketError}
              </Paragraph>
            </Col>
            <Col>
              <Button size="small" onClick={() => window.location.reload()}>
                刷新页面
              </Button>
            </Col>
          </Row>
        </Card>
      )}

      {connecting && (
        <Card 
          type="inner" 
          style={{ marginBottom: 16, borderColor: '#faad14' }}
        >
          <Paragraph style={{ margin: 0, color: '#faad14' }}>
            正在建立实时连接...
          </Paragraph>
        </Card>
      )}

      {connected && (
        <Card 
          type="inner" 
          style={{ marginBottom: 16, borderColor: '#52c41a' }}
        >
          <Paragraph style={{ margin: 0, color: '#52c41a' }}>
            实时连接已建立，状态将自动更新
          </Paragraph>
        </Card>
      )}

      {/* 主要解析进度 */}
      <ParseProgress
        parseId={taskId}
        onComplete={(result) => {
          // 由WebSocket处理，这里可以添加额外逻辑
          console.log('解析完成:', result);
        }}
        onError={(error) => {
          // 由WebSocket处理
          console.error('解析错误:', error);
        }}
        onCancel={handleCancel}
        autoRefresh={!connected} // 如果WebSocket连接，则不需要轮询
        refreshInterval={connected ? 0 : 3000}
      />

      {/* 其他活跃任务概览 */}
      {activeTasks.length > 1 && (
        <Card 
          title="其他进行中的任务" 
          style={{ marginTop: 24 }}
          size="small"
        >
          <Row gutter={[16, 16]}>
            {activeTasks
              .filter(task => task.id !== taskId)
              .slice(0, 3)
              .map(task => (
                <Col xs={24} sm={12} md={8} key={task.id}>
                  <Card
                    size="small"
                    hoverable
                    onClick={() => navigate(`/parse-progress/${task.id}`)}
                    style={{ cursor: 'pointer' }}
                  >
                    <Statistic
                      title={task.fileName}
                      value={task.progress}
                      suffix="%"
                      valueStyle={{ 
                        fontSize: 16,
                        color: task.status === 'running' ? '#1890ff' : '#52c41a'
                      }}
                    />
                    <div style={{ marginTop: 8, fontSize: 12, color: '#666' }}>
                      {task.currentStep}
                    </div>
                  </Card>
                </Col>
              ))}
          </Row>
          
          {activeTasks.length > 4 && (
            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <Button 
                type="link" 
                onClick={handleViewHistory}
              >
                查看全部活跃任务 ({activeTasks.length})
              </Button>
            </div>
          )}
        </Card>
      )}
    </div>
  );
};

export default ParseProgressPage; 