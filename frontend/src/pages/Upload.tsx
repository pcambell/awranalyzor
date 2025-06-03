import React, { useState } from 'react';
import { Typography, Card, message, Space, Divider } from 'antd';
import { useNavigate } from 'react-router-dom';
import FileUpload from '../components/FileUpload';
import { UploadedFile, AWRParseResult } from '../types';

const { Title, Paragraph } = Typography;

const Upload: React.FC = () => {
  const [uploadedFiles, setUploadedFiles] = useState<UploadedFile[]>([]);
  const [parseResults, setParseResults] = useState<AWRParseResult[]>([]);
  const navigate = useNavigate();

  // 处理文件上传成功
  const handleUploadSuccess = (file: UploadedFile) => {
    message.success(`文件 "${file.name}" 上传成功！`);
    setUploadedFiles(prev => [file, ...prev]);
  };

  // 处理解析开始
  const handleParseStart = (result: AWRParseResult) => {
    message.info('AWR文件解析已开始，请等待...');
    setParseResults(prev => [result, ...prev]);
    
    // 可以跳转到解析进度页面
    // navigate(`/results/${result.id}`);
  };

  // 处理解析完成（可以通过WebSocket或轮询实现）
  const handleParseComplete = (result: AWRParseResult) => {
    if (result.status === 'completed') {
      message.success('AWR文件解析完成！');
      // 跳转到结果页面
      navigate(`/results/${result.id}`);
    } else if (result.status === 'failed') {
      message.error(`解析失败: ${result.error_message}`);
    }
  };

  return (
    <div>
      <Title level={2}>AWR文件上传与解析</Title>
      <Paragraph>
        上传Oracle AWR报告文件，系统将自动解析并提取关键性能指标。
        支持Oracle 11g和19c版本的单实例及RAC环境。
      </Paragraph>
      
      <Divider />
      
      <FileUpload
        onUploadSuccess={handleUploadSuccess}
        onParseStart={handleParseStart}
        maxFileSize={50}
        accept=".html,.htm"
        multiple={false}
      />

      {/* 开发调试信息 */}
      {process.env.NODE_ENV === 'development' && (
        <Card title="开发调试信息" style={{ marginTop: 24 }} size="small">
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>已上传文件数: {uploadedFiles.length}</div>
            <div>解析任务数: {parseResults.length}</div>
            <div>API端点: /api/upload/, /api/parse/</div>
          </Space>
        </Card>
      )}
    </div>
  );
};

export default Upload; 