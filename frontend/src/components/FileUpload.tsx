import React, { useState, useCallback } from 'react';
import { 
  Upload, 
  Progress, 
  Button, 
  Card, 
  List, 
  Typography, 
  Alert, 
  Space, 
  Tag, 
  Modal,
  Tooltip,
  Row,
  Col
} from 'antd';
import { 
  InboxOutlined, 
  DeleteOutlined,
  EyeOutlined,
  ExclamationCircleOutlined,
  CheckCircleOutlined,
  ClockCircleOutlined,
  CloseCircleOutlined
} from '@ant-design/icons';
import type { UploadProps, UploadFile } from 'antd';
import { UploadedFile, AWRParseResult } from '../types';
import { useFileUpload } from '../hooks/useFileUpload';

const { Dragger } = Upload;
const { Title, Text } = Typography;
const { confirm } = Modal;

// 获取CSRF Token - 移到组件外部避免引用问题
const getCsrfToken = (): string => {
  const token = document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement;
  return token?.value || '';
};

interface FileUploadProps {
  onUploadSuccess?: (file: UploadedFile) => void;
  onParseStart?: (result: AWRParseResult) => void;
  maxFileSize?: number; // MB
  accept?: string;
  multiple?: boolean;
}

const FileUpload: React.FC<FileUploadProps> = ({
  onUploadSuccess,
  onParseStart,
  maxFileSize = 50,
  accept = '.html,.htm',
  multiple = false
}) => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [currentFile, setCurrentFile] = useState<UploadFile | null>(null);

  // 使用自定义Hook - DRY原则
  const {
    uploading,
    progress,
    error,
    uploadFile,
    startParsing,
    clearError
  } = useFileUpload({
    maxFileSize,
    allowedTypes: accept.split(','),
    apiEndpoint: '/api'
  });

  // 处理文件上传前的准备 - Clean Code原则
  const beforeUpload = useCallback((file: File): boolean => {
    setCurrentFile({
      uid: file.name + Date.now(),
      name: file.name,
      status: 'uploading',
      size: file.size
    } as UploadFile);
    
    return true;
  }, []);

  // 处理文件上传 - SOLID原则：依赖注入
  const handleUpload = useCallback(async (file: File): Promise<void> => {
    const uploadedFile = await uploadFile(file);
    
    if (uploadedFile) {
      // 更新本地状态
      setUploadedFiles(prev => [uploadedFile, ...prev]);
      setCurrentFile(null);
      
      // 回调通知父组件
      onUploadSuccess?.(uploadedFile);

      // 自动开始解析
      if (uploadedFile.status === 'uploaded') {
        const parseResult = await startParsing(uploadedFile.id);
        if (parseResult) {
          onParseStart?.(parseResult);
        }
      }
    } else {
      // 上传失败，清理当前文件状态
      setCurrentFile(null);
    }
  }, [uploadFile, startParsing, onUploadSuccess, onParseStart]);

  // 删除文件 - 安全编码原则：确认操作
  const handleDelete = useCallback((fileId: string) => {
    const file = uploadedFiles.find(f => f.id === fileId);
    
    confirm({
      title: '确认删除',
      icon: <ExclamationCircleOutlined />,
      content: `确定要删除文件 "${file?.name}" 吗？此操作不可恢复。`,
      okText: '删除',
      cancelText: '取消',
      okType: 'danger',
      onOk: async () => {
        try {
          const response = await fetch(`/api/files/${fileId}/`, {
            method: 'DELETE',
            headers: {
              'X-CSRFToken': getCsrfToken(),
            },
          });

          if (response.ok) {
            setUploadedFiles(prev => prev.filter(f => f.id !== fileId));
          } else {
            throw new Error('删除失败');
          }
        } catch (error: any) {
          Modal.error({
            title: '删除失败',
            content: error.message || '无法删除文件，请稍后重试',
          });
        }
      },
    });
  }, [uploadedFiles]);

  // 获取状态配置 - KISS原则：保持简单
  const getStatusConfig = (status: UploadedFile['status']) => {
    const configs = {
      uploaded: { icon: <CheckCircleOutlined />, color: 'green', text: '已上传' },
      processing: { icon: <ClockCircleOutlined />, color: 'blue', text: '解析中' },
      completed: { icon: <CheckCircleOutlined />, color: 'green', text: '完成' },
      failed: { icon: <CloseCircleOutlined />, color: 'red', text: '失败' }
    };
    return configs[status] || configs.uploaded;
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  // Upload组件属性配置
  const uploadProps: UploadProps = {
    name: 'file',
    multiple,
    accept,
    beforeUpload,
    customRequest: ({ file }) => handleUpload(file as File),
    showUploadList: false,
    disabled: uploading,
  };

  return (
    <div>
      {/* 错误提示 */}
      {error && (
        <Alert
          message="上传错误"
          description={error}
          type="error"
          closable
          onClose={clearError}
          style={{ marginBottom: 16 }}
        />
      )}

      {/* 文件上传区域 */}
      <Card title="AWR文件上传" style={{ marginBottom: 24 }}>
        <Dragger {...uploadProps} style={{ marginBottom: 16 }}>
          <p className="ant-upload-drag-icon">
            <InboxOutlined style={{ fontSize: 48, color: '#1890ff' }} />
          </p>
          <p className="ant-upload-text">
            点击或拖拽AWR报告文件到此区域上传
          </p>
          <p className="ant-upload-hint">
            支持HTML格式的Oracle AWR报告文件，单个文件最大{maxFileSize}MB
          </p>
        </Dragger>

        {/* 上传进度 */}
        {uploading && currentFile && (
          <Card size="small" style={{ marginTop: 16 }}>
            <Space direction="vertical" style={{ width: '100%' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                <Text strong>{currentFile.name}</Text>
                <Text type="secondary">
                  {formatFileSize(currentFile.size || 0)}
                </Text>
              </div>
              <Progress 
                percent={progress} 
                status={progress === 100 ? 'success' : 'active'}
                format={(percent) => `${percent}% 上传中...`}
              />
            </Space>
          </Card>
        )}

        {/* 上传说明 */}
        <div style={{ marginTop: 16, padding: 16, backgroundColor: '#f6f8fa', borderRadius: 6 }}>
          <Title level={5}>文件要求：</Title>
          <ul style={{ marginBottom: 0, paddingLeft: 20 }}>
            <li>文件格式：HTML (.html, .htm)</li>
            <li>文件来源：Oracle Database AWR Report</li>
            <li>支持版本：Oracle 11g, 19c (单实例/RAC)</li>
            <li>文件大小：最大 {maxFileSize}MB</li>
          </ul>
        </div>
      </Card>

      {/* 上传历史 */}
      {uploadedFiles.length > 0 && (
        <Card title="最近上传的文件" 
              extra={
                <Text type="secondary">
                  共 {uploadedFiles.length} 个文件
                </Text>
              }>
          <List
            itemLayout="horizontal"
            dataSource={uploadedFiles}
            renderItem={(file) => {
              const statusConfig = getStatusConfig(file.status);
              return (
                <List.Item
                  actions={[
                    <Tooltip title="查看详情">
                      <Button 
                        type="text" 
                        icon={<EyeOutlined />} 
                        onClick={() => {
                          // TODO: 实现查看详情功能
                          Modal.info({
                            title: '文件详情',
                            content: (
                              <div>
                                <p><strong>文件名:</strong> {file.name}</p>
                                <p><strong>大小:</strong> {formatFileSize(file.size)}</p>
                                <p><strong>状态:</strong> {statusConfig.text}</p>
                                <p><strong>上传时间:</strong> {new Date(file.upload_time).toLocaleString()}</p>
                                {file.error_message && (
                                  <p><strong>错误信息:</strong> <span style={{color: 'red'}}>{file.error_message}</span></p>
                                )}
                              </div>
                            ),
                          });
                        }}
                      />
                    </Tooltip>,
                    <Tooltip title="删除文件">
                      <Button 
                        type="text" 
                        danger 
                        icon={<DeleteOutlined />}
                        onClick={() => handleDelete(file.id)}
                      />
                    </Tooltip>
                  ]}
                >
                  <List.Item.Meta
                    title={
                      <Space>
                        {statusConfig.icon}
                        <Text strong>{file.name}</Text>
                        <Tag color={statusConfig.color}>{statusConfig.text}</Tag>
                      </Space>
                    }
                    description={
                      <Row gutter={16}>
                        <Col>
                          <Text type="secondary">
                            大小: {formatFileSize(file.size)}
                          </Text>
                        </Col>
                        <Col>
                          <Text type="secondary">
                            上传时间: {new Date(file.upload_time).toLocaleString()}
                          </Text>
                        </Col>
                        {file.error_message && (
                          <Col span={24}>
                            <Text type="danger">{file.error_message}</Text>
                          </Col>
                        )}
                      </Row>
                    }
                  />
                </List.Item>
              );
            }}
          />
        </Card>
      )}
    </div>
  );
};

export default FileUpload; 