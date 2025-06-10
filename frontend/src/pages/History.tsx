import React, { useState, useEffect } from 'react';
import { 
  Typography, 
  Card, 
  Table, 
  Tag, 
  Button, 
  Space, 
  Row, 
  Col,
  Statistic,
  message,
  Modal,
  Tooltip
} from 'antd';
import { 
  EyeOutlined, 
  DeleteOutlined, 
  ReloadOutlined,
  DownloadOutlined,
  InfoCircleOutlined
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import type { ColumnsType } from 'antd/es/table';
import { UploadedFile } from '../types';

const { Title, Paragraph, Text } = Typography;
const { confirm } = Modal;

const History: React.FC = () => {
  const navigate = useNavigate();
  const [files, setFiles] = useState<UploadedFile[]>([]);
  const [loading, setLoading] = useState(false);
  const [stats, setStats] = useState({
    total: 0,
    completed: 0,
    failed: 0,
    processing: 0
  });

  // 获取历史记录
  const fetchHistory = async () => {
    setLoading(true);
    try {
      const response = await fetch('/api/reports/', {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (response.ok) {
        const data = await response.json();
        const fileList = data.results || data;
        if (Array.isArray(fileList)) {
          const formattedFiles: UploadedFile[] = fileList.map((file: any) => ({
            id: file.id.toString(),
            name: file.original_filename || file.name,
            size: file.file_size || 0,
            upload_time: file.created_at || new Date().toISOString(),
            status: file.status === 'completed' ? 'completed' : 
                    file.status === 'parsed' ? 'completed' :
                    file.status === 'failed' ? 'failed' :
                    file.status === 'processing' ? 'processing' : 'uploaded',
            file_path: file.file_path,
            error_message: file.error_message
          }));
          setFiles(formattedFiles);

          // 计算统计信息
          const total = formattedFiles.length;
          const completed = formattedFiles.filter(f => f.status === 'completed').length;
          const failed = formattedFiles.filter(f => f.status === 'failed').length;
          const processing = formattedFiles.filter(f => f.status === 'processing').length;
          
          setStats({ total, completed, failed, processing });
        }
      } else {
        throw new Error('获取历史记录失败');
      }
    } catch (error: any) {
      console.error('获取历史记录失败:', error);
      message.error('获取历史记录失败: ' + error.message);
    } finally {
      setLoading(false);
    }
  };

  // 删除文件
  const handleDelete = (fileId: string, fileName: string) => {
    console.log('handleDelete called with:', fileId, fileName); // 调试日志
    
    // 使用浏览器原生确认对话框，确保能够显示
    const confirmed = window.confirm(`确定要删除文件 "${fileName}" 吗？此操作不可恢复。`);
    
    if (confirmed) {
      console.log('User confirmed deletion'); // 调试日志
      
      const performDelete = async () => {
        try {
          console.log('Sending DELETE request to:', `/api/reports/${fileId}/`); // 调试日志
          const response = await fetch(`/api/reports/${fileId}/`, {
            method: 'DELETE',
            headers: {
              'Content-Type': 'application/json',
            },
          });

          console.log('DELETE response:', response.status, response.statusText); // 调试日志
          if (response.ok) {
            message.success('文件删除成功');
            fetchHistory(); // 重新获取列表
          } else {
            const errorData = await response.text();
            console.error('DELETE failed:', errorData); // 调试日志
            throw new Error('删除失败');
          }
        } catch (error: any) {
          console.error('Delete error:', error); // 调试日志
          message.error('删除失败: ' + error.message);
        }
      };
      
      performDelete();
    } else {
      console.log('User cancelled deletion'); // 调试日志
    }
  };

  // 查看详情
  const handleViewDetails = (file: UploadedFile) => {
    console.log('handleViewDetails called with:', file); // 调试日志
    
    // 先使用简单的alert方式测试，然后再优化为Modal
    const details = [
      `文件名: ${file.name}`,
      `文件大小: ${formatFileSize(file.size)}`,
      `上传时间: ${new Date(file.upload_time).toLocaleString()}`,
      `状态: ${getStatusText(file.status)}`,
      file.error_message ? `错误信息: ${file.error_message}` : '',
      file.file_path ? `文件路径: ${file.file_path}` : ''
    ].filter(Boolean).join('\n');
    
    alert('文件详情:\n\n' + details);
  };

  // 查看解析结果
  const handleViewResults = (fileId: string) => {
    navigate(`/results/${fileId}`);
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // 获取状态文本
  const getStatusText = (status: string): string => {
    const statusMap: Record<string, string> = {
      uploaded: '已上传',
      processing: '解析中',
      completed: '完成',
      failed: '失败'
    };
    return statusMap[status] || status;
  };

  // 获取状态颜色
  const getStatusColor = (status: string): string => {
    const colorMap: Record<string, string> = {
      uploaded: 'blue',
      processing: 'orange',
      completed: 'green',
      failed: 'red'
    };
    return colorMap[status] || 'default';
  };

  // 表格列配置
  const columns: ColumnsType<UploadedFile> = [
    {
      title: '文件名',
      dataIndex: 'name',
      key: 'name',
      ellipsis: true,
      render: (text: string) => (
        <Tooltip title={text}>
          <Text strong>{text}</Text>
        </Tooltip>
      ),
    },
    {
      title: '文件大小',
      dataIndex: 'size',
      key: 'size',
      width: 120,
      render: (size: number) => formatFileSize(size),
    },
    {
      title: '上传时间',
      dataIndex: 'upload_time',
      key: 'upload_time',
      width: 180,
      render: (time: string) => new Date(time).toLocaleString(),
    },
    {
      title: '状态',
      dataIndex: 'status',
      key: 'status',
      width: 100,
      render: (status: string) => (
        <Tag color={getStatusColor(status)}>
          {getStatusText(status)}
        </Tag>
      ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 200,
      render: (_, record) => (
        <Space size="small">
          <Tooltip title="查看详情">
            <Button 
              type="text" 
              icon={<InfoCircleOutlined />}
              onClick={() => {
                console.log('Info button clicked for record:', record);
                handleViewDetails(record);
              }}
              style={{ color: '#1890ff' }}
            />
          </Tooltip>
          {record.status === 'completed' && (
            <Tooltip title="查看解析结果">
              <Button 
                type="text" 
                icon={<EyeOutlined />}
                onClick={() => handleViewResults(record.id)}
              />
            </Tooltip>
          )}
          <Tooltip title="删除文件">
            <Button 
              type="text" 
              danger 
              icon={<DeleteOutlined />}
              onClick={() => {
                console.log('Delete button clicked for record:', record);
                handleDelete(record.id, record.name);
              }}
              style={{ color: '#ff4d4f' }}
            />
          </Tooltip>
        </Space>
      ),
    },
  ];

  // 组件挂载时获取数据
  useEffect(() => {
    fetchHistory();
  }, []);

  return (
    <div>
      {/* 页面头部 */}
      <div style={{ marginBottom: 24 }}>
        <Row justify="space-between" align="middle">
          <Col>
            <Title level={2}>历史记录</Title>
            <Paragraph>查看所有AWR文件上传和解析历史记录</Paragraph>
          </Col>
          <Col>
            <Button 
              type="primary"
              loading={loading}
              onClick={fetchHistory}
              icon={<ReloadOutlined />}
            >
              刷新
            </Button>
          </Col>
        </Row>
      </div>

      {/* 统计概览 */}
      <Row gutter={16} style={{ marginBottom: 24 }}>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic title="总文件数" value={stats.total} />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic 
              title="已完成" 
              value={stats.completed} 
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic 
              title="解析中" 
              value={stats.processing}
              valueStyle={{ color: '#fa8c16' }}
            />
          </Card>
        </Col>
        <Col xs={24} sm={6}>
          <Card>
            <Statistic 
              title="失败" 
              value={stats.failed}
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>
      </Row>

      {/* 文件列表 */}
      <Card title="文件列表" extra={
        <Button 
          type="link" 
          onClick={() => {
            console.log('Test button clicked!');
            message.info('测试按钮点击正常');
          }}
        >
          测试按钮
        </Button>
      }>
        <Table
          columns={columns}
          dataSource={files}
          rowKey="id"
          loading={loading}
          pagination={{
            total: files.length,
            pageSize: 20,
            showSizeChanger: true,
            showQuickJumper: true,
            showTotal: (total, range) => 
              `第 ${range[0]}-${range[1]} 条 / 共 ${total} 条`,
          }}
          scroll={{ x: 800 }}
        />
      </Card>
    </div>
  );
};

export default History; 