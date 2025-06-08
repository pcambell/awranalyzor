import React, { useEffect, useRef, useMemo } from 'react';
import { Card, Typography, Empty, Spin } from 'antd';
import * as echarts from 'echarts/core';
import {
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent
} from 'echarts/components';
import {
  PieChart,
  BarChart
} from 'echarts/charts';
import { CanvasRenderer } from 'echarts/renderers';
import { WaitEvent } from '../types';

const { Text } = Typography;

// 注册ECharts组件
echarts.use([
  TitleComponent,
  TooltipComponent,
  LegendComponent,
  GridComponent,
  PieChart,
  BarChart,
  CanvasRenderer
]);

interface WaitEventsChartProps {
  waitEvents: WaitEvent[];
  chartType?: 'pie' | 'bar';
  loading?: boolean;
  height?: number;
}

const WaitEventsChart: React.FC<WaitEventsChartProps> = ({
  waitEvents,
  chartType = 'pie',
  loading = false,
  height = 400
}) => {
  const chartRef = useRef<HTMLDivElement>(null);
  const chartInstance = useRef<echarts.ECharts | null>(null);

  // 数据预处理 - DRY原则：避免重复计算
  const chartData = useMemo(() => {
    if (!waitEvents || waitEvents.length === 0) return [];
    
    // 取前10个等待事件，按时间排序
    const topEvents = waitEvents
      .filter(event => event.time_waited_seconds != null && event.time_waited_seconds > 0)
      .sort((a, b) => (b.time_waited_seconds || 0) - (a.time_waited_seconds || 0))
      .slice(0, 10);
    
    return topEvents.map(event => ({
      name: event.event_name,
      value: event.time_waited_seconds || 0,
      percentage: event.percent_db_time || 0,
      waits: event.waits || 0,
      avgWait: event.avg_wait_ms || 0
    }));
  }, [waitEvents]);

  // 生成图表配置 - SOLID原则：单一职责
  const getChartOption = useMemo(() => {
    if (chartData.length === 0) return null;

    const baseOption = {
      tooltip: {
        trigger: chartType === 'pie' ? 'item' : 'axis',
        formatter: (params: any) => {
          if (chartType === 'pie') {
            const data = params.data;
            return `
              <div style="text-align: left;">
                <strong>${data.name}</strong><br/>
                等待时间: ${data.value.toFixed(2)}s<br/>
                DB时间占比: ${data.percentage.toFixed(2)}%<br/>
                等待次数: ${data.waits.toLocaleString()}<br/>
                平均等待: ${data.avgWait.toFixed(2)}ms
              </div>
            `;
          } else {
            const data = params[0].data;
            return `
              <div style="text-align: left;">
                <strong>${data.name}</strong><br/>
                等待时间: ${data.value.toFixed(2)}s<br/>
                DB时间占比: ${data.percentage.toFixed(2)}%<br/>
                等待次数: ${data.waits.toLocaleString()}<br/>
                平均等待: ${data.avgWait.toFixed(2)}ms
              </div>
            `;
          }
        }
      },
      legend: {
        type: 'scroll',
        orient: chartType === 'pie' ? 'vertical' : 'horizontal',
        right: chartType === 'pie' ? 10 : 'center',
        top: chartType === 'pie' ? 20 : 'bottom',
        textStyle: {
          fontSize: 12
        }
      },
      color: [
        '#ff4d4f', '#fa8c16', '#fadb14', '#a0d911', '#52c41a',
        '#13c2c2', '#1890ff', '#2f54eb', '#722ed1', '#eb2f96'
      ]
    };

    if (chartType === 'pie') {
      return {
        ...baseOption,
        title: {
          text: 'Top 10 等待事件分布',
          left: 'center',
          textStyle: { fontSize: 16 }
        },
        series: [
          {
            name: '等待时间',
            type: 'pie',
            radius: ['30%', '70%'],
            center: ['35%', '50%'],
            data: chartData,
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowOffsetX: 0,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            },
            label: {
              show: true,
              formatter: '{b}\n{d}%',
              fontSize: 10
            }
          }
        ]
      };
    } else {
      return {
        ...baseOption,
        title: {
          text: 'Top 10 等待事件时间分布',
          left: 'center',
          textStyle: { fontSize: 16 }
        },
        grid: {
          left: '3%',
          right: '4%',
          bottom: '15%',
          top: '15%',
          containLabel: true
        },
        xAxis: {
          type: 'category',
          data: chartData.map(item => item.name),
          axisLabel: {
            rotate: 45,
            fontSize: 10
          }
        },
        yAxis: {
          type: 'value',
          name: '等待时间 (秒)',
          axisLabel: {
            formatter: '{value}s'
          }
        },
        series: [
          {
            name: '等待时间',
            type: 'bar',
            data: chartData,
            itemStyle: {
              borderRadius: [4, 4, 0, 0]
            },
            emphasis: {
              itemStyle: {
                shadowBlur: 10,
                shadowColor: 'rgba(0, 0, 0, 0.5)'
              }
            }
          }
        ]
      };
    }
  }, [chartData, chartType]);

  // 初始化和更新图表 - 性能优化
  useEffect(() => {
    if (!chartRef.current || !getChartOption) return;

    // 初始化图表实例
    if (!chartInstance.current) {
      chartInstance.current = echarts.init(chartRef.current);
    }

    // 设置图表配置
    chartInstance.current.setOption(getChartOption, true);

    // 响应式处理
    const handleResize = () => {
      chartInstance.current?.resize();
    };

    window.addEventListener('resize', handleResize);

    return () => {
      window.removeEventListener('resize', handleResize);
    };
  }, [getChartOption]);

  // 组件卸载时销毁图表实例 - 内存管理
  useEffect(() => {
    return () => {
      if (chartInstance.current) {
        chartInstance.current.dispose();
      }
    };
  }, []);

  if (loading) {
    return (
      <Card>
        <div style={{ textAlign: 'center', padding: '60px 0' }}>
          <Spin size="large" />
          <div style={{ marginTop: 16 }}>
            <Text>正在生成图表...</Text>
          </div>
        </div>
      </Card>
    );
  }

  if (!waitEvents || waitEvents.length === 0) {
    return (
      <Card>
        <Empty
          description="暂无等待事件数据"
          image={Empty.PRESENTED_IMAGE_SIMPLE}
        />
      </Card>
    );
  }

  return (
    <Card 
      title={`等待事件${chartType === 'pie' ? '饼状' : '柱状'}图`}
      bodyStyle={{ padding: '16px' }}
    >
      <div
        ref={chartRef}
        style={{
          width: '100%',
          height: `${height}px`,
          minHeight: '300px'
        }}
      />
    </Card>
  );
};

export default WaitEventsChart; 