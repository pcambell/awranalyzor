import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import '@testing-library/jest-dom';
import ReportDisplay from '../ReportDisplay';
import { AWRParseResult } from '../../types';

// Mock数据
const mockParseResult: AWRParseResult = {
  id: 'test-result-1',
  file_id: 'test-file-1',
  report_id: 'test-report-1',
  status: 'completed',
  progress: 100,
  start_time: '2025-06-10T09:30:00+08:00',
  estimated_time_remaining: null,
  parser_version: '1.0.0',
  sections_parsed: 5,
  total_sections: 5,
  parse_errors: [],
  data_completeness: 95.5,
  data_quality_score: 88,
  error_message: null,
  db_info: {
    db_name: 'TESTDB',
    instance_name: 'test1',
    db_version: '19.3.0.0.0',
    host_name: 'test-server',
    platform: 'Linux x86-64',
    rac_instances: undefined,
    cdb_name: undefined,
    pdb_name: undefined
  },
  snapshot_info: {
    begin_snap_id: 100,
    end_snap_id: 101,
    begin_time: '2025-06-02 10:00:00',
    end_time: '2025-06-02 11:00:00',
    snapshot_duration_minutes: 60
  },
  parse_metadata: {
    parse_duration_seconds: 15.5,
    parser_version: '1.0.0',
    oracle_version: '19c'
  },
  load_profile: [
    {
      metric_name: 'DB CPU',
      per_second: 2.5,
      per_transaction: 45.2,
      per_exec: undefined,
      per_call: undefined
    }
  ],
  wait_events: [
    {
      event_name: 'db file sequential read',
      waits: 15420,
      time_waited_seconds: 125.8,
      avg_wait_ms: 8.16,
      percent_db_time: 15.2
    }
  ],
  sql_statistics: [
    {
      sql_id: 'abc123def456',
      executions: 1250,
      cpu_time_seconds: 45.8,
      elapsed_time_seconds: 52.3,
      buffer_gets: 125000,
      disk_reads: 850,
      rows_processed: 25000
    }
  ]
};

describe('ReportDisplay Component', () => {
  it('renders loading state correctly', () => {
    render(
      <ReportDisplay
        parseResult={null}
        loading={true}
      />
    );

    expect(screen.getByText('正在加载解析结果...')).toBeInTheDocument();
  });

  it('renders empty state when no data', () => {
    render(
      <ReportDisplay
        parseResult={null}
        loading={false}
      />
    );

    expect(screen.getByText('暂无解析结果')).toBeInTheDocument();
  });

  it('renders parse result data correctly', () => {
    render(
      <ReportDisplay
        parseResult={mockParseResult}
        loading={false}
      />
    );

    // 检查基本信息显示
    expect(screen.getByText('AWR报告解析结果')).toBeInTheDocument();
    expect(screen.getByText('TESTDB')).toBeInTheDocument();
    expect(screen.getByText('test1')).toBeInTheDocument();
    expect(screen.getByText('19.3.0.0.0')).toBeInTheDocument();
  });

  it('switches between tabs correctly', async () => {
    render(
      <ReportDisplay
        parseResult={mockParseResult}
        loading={false}
      />
    );

    // 默认应该在概要信息标签页
    expect(screen.getByText('解析状态')).toBeInTheDocument();

    // 切换到Load Profile标签页
    const loadProfileTab = screen.getByText('Load Profile');
    fireEvent.click(loadProfileTab);

    await waitFor(() => {
      expect(screen.getByText('指标名称')).toBeInTheDocument();
      expect(screen.getByText('DB CPU')).toBeInTheDocument();
    });

    // 切换到等待事件标签页
    const waitEventsTab = screen.getByText('等待事件');
    fireEvent.click(waitEventsTab);

    await waitFor(() => {
      expect(screen.getByText('等待事件')).toBeInTheDocument();
      expect(screen.getByText('db file sequential read')).toBeInTheDocument();
    });
  });

  it('calls export callback when export buttons clicked', () => {
    const mockOnExport = jest.fn();
    
    render(
      <ReportDisplay
        parseResult={mockParseResult}
        loading={false}
        onExport={mockOnExport}
      />
    );

    // 点击PDF导出按钮
    const pdfButton = screen.getByText('PDF');
    fireEvent.click(pdfButton);
    expect(mockOnExport).toHaveBeenCalledWith('pdf');

    // 点击Excel导出按钮
    const excelButton = screen.getByText('Excel');
    fireEvent.click(excelButton);
    expect(mockOnExport).toHaveBeenCalledWith('excel');
  });

  it('displays error message when present', () => {
    const resultWithError = {
      ...mockParseResult,
      error_message: '部分数据解析失败'
    };

    render(
      <ReportDisplay
        parseResult={resultWithError}
        loading={false}
      />
    );

    expect(screen.getByText('解析警告')).toBeInTheDocument();
    expect(screen.getByText('部分数据解析失败')).toBeInTheDocument();
  });

  it('formats snapshot duration correctly', () => {
    render(
      <ReportDisplay
        parseResult={mockParseResult}
        loading={false}
      />
    );

    // 检查时长格式化 (60分钟应该显示为1h 0m)
    expect(screen.getByText('1h 0m')).toBeInTheDocument();
  });

  it('handles table pagination correctly', async () => {
    // 创建有更多数据的mock结果
    const resultWithMoreData = {
      ...mockParseResult,
      wait_events: Array.from({ length: 25 }, (_, i) => ({
        event_name: `wait event ${i + 1}`,
        waits: 1000 + i,
        time_waited_seconds: 10 + i,
        avg_wait_ms: 5 + i,
        percent_db_time: 1 + i
      }))
    };

    render(
      <ReportDisplay
        parseResult={resultWithMoreData}
        loading={false}
      />
    );

    // 切换到等待事件标签页
    const waitEventsTab = screen.getByText('等待事件');
    fireEvent.click(waitEventsTab);

    await waitFor(() => {
      // 应该显示分页信息
      expect(screen.getByText(/共 25 个等待事件/)).toBeInTheDocument();
    });
  });

  it('renders statistics correctly', () => {
    render(
      <ReportDisplay
        parseResult={mockParseResult}
        loading={false}
      />
    );

    // 检查统计信息
    expect(screen.getByText('成功')).toBeInTheDocument(); // 解析状态
    expect(screen.getByText('95.5')).toBeInTheDocument(); // 数据完整性
    expect(screen.getByText('88')).toBeInTheDocument(); // 数据质量
  });
}); 