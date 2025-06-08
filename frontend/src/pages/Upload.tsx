import React, { useState, useEffect } from 'react';
import { 
  Typography, 
  Card, 
  message, 
  Space, 
  Divider, 
  Button,
  Row,
  Col,
  Statistic,
  List,
  Tag
} from 'antd';
import { useNavigate } from 'react-router-dom';
import { useDispatch, useSelector } from 'react-redux';
import { 
  EyeOutlined, 
  PlayCircleOutlined,
  HistoryOutlined,
  ReloadOutlined
} from '@ant-design/icons';
import FileUpload from '../components/FileUpload';
import { UploadedFile, AWRParseResult } from '../types';
import { 
  startParsing, 
  fetchParseHistory,
  selectActiveTasks,
  selectRecentTasks
} from '../store/slices/parseSlice';
import type { RootState } from '../store';

const { Title, Paragraph } = Typography;

const Upload: React.FC = () => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const navigate = useNavigate();
  const dispatch = useDispatch();

  // Redux状态
  const activeTasks = useSelector(selectActiveTasks);
  const recentTasks = useSelector(selectRecentTasks);
  
  // 组件加载时获取解析历史
  useEffect(() => {
    // dispatch(fetchParseHistory());
  }, [dispatch]);

  // 处理文件上传成功 - SOLID原则：单一职责
  const handleUploadSuccess = (file: UploadedFile) => {
    message.success(`文件 "${file.name}" 上传成功！`);
    setUploadedFiles(prev => [file, ...prev]);
  };

  // 处理解析开始 - 使用Redux管理状态
  const handleParseStart = async (file: UploadedFile) => {
    try {
      message.info('正在启动AWR文件解析...');
      
      // 暂时模拟解析开始
      const taskId = 'mock-task-' + Date.now();
      message.success('解析任务已启动！');
      
      // 跳转到解析进度页面
      navigate(`/parse-progress/${taskId}`);
      
      /*
      const resultAction = await dispatch(startParsing({
        fileId: file.id,
        fileName: file.name
      }));
      
      if (startParsing.fulfilled.match(resultAction)) {
        const { taskId } = resultAction.payload;
        message.success('解析任务已启动！');
        
        // 跳转到解析进度页面
        navigate(`/parse-progress/${taskId}`);
      } else {
        message.error('启动解析失败，请重试');
      }
      */
    } catch (error: any) {
      console.error('启动解析失败:', error);
      message.error('启动解析失败: ' + (error.message || '未知错误'));
    }
  };

  // 查看解析结果
  const handleViewResult = (resultId: string) => {
    navigate(`/results/${resultId}`);
  };

  // 查看解析进度
  const handleViewProgress = (taskId: string) => {
    navigate(`/parse-progress/${taskId}`);
  };

  // 查看历史
  const handleViewHistory = () => {
    navigate('/history');
  };

  // 刷新任务状态
  const handleRefresh = () => {
    // dispatch(fetchParseHistory());
    message.success('任务状态已刷新');
  };

  return (
    <div>
      <Title level={2}>AWR文件上传与解析</Title>
      <Paragraph>
        上传Oracle AWR报告文件，系统将自动解析并提取关键性能指标。
        支持Oracle 11g和19c版本的单实例及RAC环境。
      </Paragraph>
      
      <Divider />
      
      {/* 文件上传组件 */}
      <FileUpload
        onUploadSuccess={handleUploadSuccess}
        onParseStart={(result: AWRParseResult) => {
          // 简化处理，直接跳转到结果页面
          navigate(`/results/${result.id}`);
        }}
        maxFileSize={50}
        accept=".html,.htm"
        multiple={false}
      />

      {/* 活跃任务状态 */}
      {activeTasks.length > 0 && (
        <Card 
          title={
            <Space>
              <PlayCircleOutlined />
              <span>进行中的解析任务</span>
              <Button 
                size="small" 
                icon={<ReloadOutlined />}
                onClick={handleRefresh}
              >
                刷新
              </Button>
            </Space>
          }
          style={{ marginTop: 24 }}
        >
          <Row gutter={[16, 16]}>
            {activeTasks.slice(0, 4).map(task => (
              <Col xs={24} sm={12} md={6} key={task.id}>
                <Card
                  size="small"
                  hoverable
                  onClick={() => handleViewProgress(task.id)}
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
                  <div style={{ marginTop: 8 }}>
                    <Tag color={task.status === 'running' ? 'processing' : 'success'}>
                      {task.status === 'running' ? '进行中' : '已完成'}
                    </Tag>
                  </div>
                  <div style={{ marginTop: 4, fontSize: 12, color: '#666' }}>
                    {task.currentStep}
                  </div>
                </Card>
              </Col>
            ))}
          </Row>
          
          {activeTasks.length > 4 && (
            <div style={{ textAlign: 'center', marginTop: 16 }}>
              <Button type="link" onClick={handleViewHistory}>
                查看全部活跃任务 ({activeTasks.length})
              </Button>
            </div>
          )}
        </Card>
      )}

      {/* 最近的解析结果 */}
      {recentTasks.length > 0 && (
        <Card 
          title={
            <Space>
              <HistoryOutlined />
              <span>最近的解析结果</span>
              <Button 
                type="link" 
                onClick={handleViewHistory}
              >
                查看全部
              </Button>
            </Space>
          }
          style={{ marginTop: 24 }}
        >
          <List
            dataSource={recentTasks.slice(0, 5)}
            renderItem={task => (
              <List.Item
                actions={[
                  task.resultId ? (
                    <Button 
                      type="link" 
                      icon={<EyeOutlined />}
                      onClick={() => handleViewResult(task.resultId!)}
                    >
                      查看结果
                    </Button>
                  ) : (
                    <Tag color="error">无结果</Tag>
                  )
                ]}
              >
                <List.Item.Meta
                  title={
                    <Space>
                      <span>{task.fileName}</span>
                      <Tag color={
                        task.status === 'completed' ? 'success' :
                        task.status === 'failed' ? 'error' :
                        task.status === 'cancelled' ? 'default' : 'processing'
                      }>
                        {task.status === 'completed' ? '已完成' :
                         task.status === 'failed' ? '失败' :
                         task.status === 'cancelled' ? '已取消' : '进行中'}
                      </Tag>
                    </Space>
                  }
                  description={
                    <Space>
                      <span>任务ID: {task.id}</span>
                      {task.endTime && (
                        <span>完成时间: {new Date(task.endTime).toLocaleString()}</span>
                      )}
                      {task.error && (
                        <span style={{ color: '#ff4d4f' }}>错误: {task.error}</span>
                      )}
                    </Space>
                  }
                />
              </List.Item>
            )}
          />
        </Card>
      )}

      {/* 开发调试信息 */}
      {process.env.NODE_ENV === 'development' && (
        <Card title="开发调试信息" style={{ marginTop: 24 }} size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>已上传文件数: {uploadedFiles.length}</div>
            <div>活跃任务数: {activeTasks.length}</div>
            <div>最近任务数: {recentTasks.length}</div>
            <div>API端点: /api/start-parsing/, /api/parse-status/</div>
          </Space>
        </Card>
      )}
    </div>
  );
};

export default Upload; 