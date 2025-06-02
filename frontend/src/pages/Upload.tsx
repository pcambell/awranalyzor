import React from 'react';
import { Typography, Card } from 'antd';

const { Title, Paragraph } = Typography;

const Upload: React.FC = () => {
  return (
    <div>
      <Title level={2}>文件上传</Title>
      <Paragraph>上传Oracle AWR报告文件进行解析</Paragraph>
      
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Paragraph>文件上传组件将在下一个任务中实现</Paragraph>
        </div>
      </Card>
    </div>
  );
};

export default Upload; 