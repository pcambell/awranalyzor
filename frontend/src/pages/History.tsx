import React from 'react';
import { Typography, Card } from 'antd';

const { Title, Paragraph } = Typography;

const History: React.FC = () => {
  return (
    <div>
      <Title level={2}>历史记录</Title>
      <Paragraph>查看所有AWR解析历史记录</Paragraph>
      
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Paragraph>历史记录组件将在后续任务中实现</Paragraph>
        </div>
      </Card>
    </div>
  );
};

export default History; 