import React from 'react';
import { Typography, Card } from 'antd';

const { Title, Paragraph } = Typography;

const Results: React.FC = () => {
  return (
    <div>
      <Title level={2}>解析结果</Title>
      <Paragraph>查看AWR报告解析结果和性能分析</Paragraph>
      
      <Card>
        <div style={{ textAlign: 'center', padding: '40px 0' }}>
          <Paragraph>解析结果展示组件将在后续任务中实现</Paragraph>
        </div>
      </Card>
    </div>
  );
};

export default Results; 