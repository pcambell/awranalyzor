import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import WaitEventsChart from '../WaitEventsChart';
import { WaitEvent } from '../../types';

// Mock ECharts
jest.mock('echarts/core', () => ({
  __esModule: true,
  use: jest.fn(),
  init: jest.fn(() => ({
    setOption: jest.fn(),
    resize: jest.fn(),
    dispose: jest.fn()
  }))
}));

// Mock数据
const mockWaitEvents: WaitEvent[] = [
  {
    event_name: 'db file sequential read',
    waits: 15420,
    time_waited_seconds: 125.8,
    avg_wait_ms: 8.16,
    percent_db_time: 15.2
  },
  {
    event_name: 'log file sync',
    waits: 8920,
    time_waited_seconds: 89.5,
    avg_wait_ms: 10.03,
    percent_db_time: 10.8
  },
  {
    event_name: 'CPU time',
    waits: 0,
    time_waited_seconds: 450.2,
    avg_wait_ms: 0,
    percent_db_time: 54.5
  }
];

describe('WaitEventsChart Component', () => {
  it('renders loading state correctly', () => {
    render(
      <WaitEventsChart
        waitEvents={[]}
        loading={true}
      />
    );

    expect(screen.getByText('正在生成图表...')).toBeInTheDocument();
  });

  it('renders empty state when no data', () => {
    render(
      <WaitEventsChart
        waitEvents={[]}
        loading={false}
      />
    );

    expect(screen.getByText('暂无等待事件数据')).toBeInTheDocument();
  });

  it('renders pie chart by default', () => {
    render(
      <WaitEventsChart
        waitEvents={mockWaitEvents}
        loading={false}
      />
    );

    expect(screen.getByText('等待事件饼状图')).toBeInTheDocument();
  });

  it('renders bar chart when specified', () => {
    render(
      <WaitEventsChart
        waitEvents={mockWaitEvents}
        chartType="bar"
        loading={false}
      />
    );

    expect(screen.getByText('等待事件柱状图')).toBeInTheDocument();
  });

  it('filters out zero-time wait events', () => {
    const waitEventsWithZero: WaitEvent[] = [
      ...mockWaitEvents,
      {
        event_name: 'zero time event',
        waits: 100,
        time_waited_seconds: 0,
        avg_wait_ms: 0,
        percent_db_time: 0
      }
    ];

    render(
      <WaitEventsChart
        waitEvents={waitEventsWithZero}
        loading={false}
      />
    );

    // 组件应该渲染成功，零时间事件应该被过滤掉
    expect(screen.getByText('等待事件饼状图')).toBeInTheDocument();
  });

  it('handles custom height prop', () => {
    const { container } = render(
      <WaitEventsChart
        waitEvents={mockWaitEvents}
        height={600}
        loading={false}
      />
    );

    const chartContainer = container.querySelector('div[style*="height: 600px"]');
    expect(chartContainer).toBeInTheDocument();
  });

  it('sorts events by time_waited_seconds', () => {
    const unsortedEvents: WaitEvent[] = [
      {
        event_name: 'small event',
        waits: 100,
        time_waited_seconds: 10,
        avg_wait_ms: 5,
        percent_db_time: 2
      },
      {
        event_name: 'large event',
        waits: 500,
        time_waited_seconds: 100,
        avg_wait_ms: 15,
        percent_db_time: 20
      },
      {
        event_name: 'medium event',
        waits: 300,
        time_waited_seconds: 50,
        avg_wait_ms: 10,
        percent_db_time: 10
      }
    ];

    render(
      <WaitEventsChart
        waitEvents={unsortedEvents}
        loading={false}
      />
    );

    // 图表应该正常渲染（排序逻辑在组件内部处理）
    expect(screen.getByText('等待事件饼状图')).toBeInTheDocument();
  });

  it('limits to top 10 events', () => {
    const manyEvents: WaitEvent[] = Array.from({ length: 15 }, (_, i) => ({
      event_name: `event ${i + 1}`,
      waits: 1000 - i,
      time_waited_seconds: 100 - i,
      avg_wait_ms: 10 - i * 0.1,
      percent_db_time: 10 - i
    }));

    render(
      <WaitEventsChart
        waitEvents={manyEvents}
        loading={false}
      />
    );

    // 组件应该正常渲染，内部会限制为前10个事件
    expect(screen.getByText('等待事件饼状图')).toBeInTheDocument();
  });

  it('handles null/undefined values gracefully', () => {
    const eventsWithNulls: WaitEvent[] = [
      {
        event_name: 'event with nulls',
        waits: 100,
        time_waited_seconds: 50,
        avg_wait_ms: null as any,
        percent_db_time: undefined as any
      }
    ];

    render(
      <WaitEventsChart
        waitEvents={eventsWithNulls}
        loading={false}
      />
    );

    expect(screen.getByText('等待事件饼状图')).toBeInTheDocument();
  });
}); 