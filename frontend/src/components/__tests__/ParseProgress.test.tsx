import React from 'react';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import '@testing-library/jest-dom';
import { message } from 'antd';
import ParseProgress, { ParseStatus } from '../ParseProgress';

// Mock Ant Design message
jest.mock('antd', () => ({
  ...jest.requireActual('antd'),
  message: {
    success: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
  },
}));

// Mock fetch API
global.fetch = jest.fn();

// Mock ParseProgress组件的默认props
const defaultProps = {
  parseId: 'test-parse-id-123',
  autoRefresh: false, // 测试时关闭自动刷新
};

const mockParseStatus: ParseStatus = {
  id: 'test-parse-id-123',
  status: 'running',
  progress: 45,
  currentStep: '解析Wait Events数据',
  startTime: '2025-06-03 09:30:00',
  estimatedTimeRemaining: 120,
  stages: [
    {
      name: '文件验证',
      status: 'completed',
      progress: 100,
      startTime: '2025-06-03 09:30:00',
      endTime: '2025-06-03 09:30:15',
      details: '文件格式验证通过'
    },
    {
      name: '解析数据库信息',
      status: 'completed',
      progress: 100,
      startTime: '2025-06-03 09:30:15',
      endTime: '2025-06-03 09:30:45',
      details: 'Oracle 19c数据库信息提取完成'
    },
    {
      name: '解析Wait Events',
      status: 'running',
      progress: 60,
      startTime: '2025-06-03 09:31:20',
      details: '正在解析等待事件数据...'
    },
    {
      name: '解析SQL Statistics',
      status: 'pending',
      progress: 0,
      details: '等待开始'
    }
  ]
};

describe('ParseProgress组件测试', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    (global.fetch as jest.Mock).mockClear();
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  test('应该正确渲染加载状态', () => {
    // 模拟fetch延迟
    (global.fetch as jest.Mock).mockImplementation(() => 
      new Promise(resolve => setTimeout(resolve, 1000))
    );

    render(<ParseProgress {...defaultProps} />);
    
    expect(screen.getByText('正在获取解析状态...')).toBeInTheDocument();
  });

  test('应该正确渲染运行中的解析状态', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockParseStatus)
    });

    render(<ParseProgress {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('解析进度')).toBeInTheDocument();
      expect(screen.getByText('进行中')).toBeInTheDocument();
      expect(screen.getByText('45%')).toBeInTheDocument();
      expect(screen.getByText('解析Wait Events数据')).toBeInTheDocument();
    });
  });

  test('应该正确显示详细步骤进度', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockParseStatus)
    });

    render(<ParseProgress {...defaultProps} />);

    await waitFor(() => {
      // 检查各个阶段
      expect(screen.getByText('文件验证')).toBeInTheDocument();
      expect(screen.getByText('解析数据库信息')).toBeInTheDocument();
      expect(screen.getByText('解析Wait Events')).toBeInTheDocument();
      expect(screen.getByText('解析SQL Statistics')).toBeInTheDocument();
      
      // 检查阶段详情
      expect(screen.getByText('文件格式验证通过')).toBeInTheDocument();
      expect(screen.getByText('Oracle 19c数据库信息提取完成')).toBeInTheDocument();
      expect(screen.getByText('正在解析等待事件数据...')).toBeInTheDocument();
    });
  });

  test('应该正确渲染完成状态', async () => {
    const completedStatus: ParseStatus = {
      ...mockParseStatus,
      status: 'completed',
      progress: 100,
      endTime: '2025-06-03 09:32:30',
      stages: mockParseStatus.stages.map(stage => ({
        ...stage,
        status: 'completed',
        progress: 100
      }))
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(completedStatus)
    });

    const onComplete = jest.fn();
    render(<ParseProgress {...defaultProps} onComplete={onComplete} />);

    await waitFor(() => {
      expect(screen.getByText('已完成')).toBeInTheDocument();
      expect(screen.getByText('100%')).toBeInTheDocument();
      expect(onComplete).toHaveBeenCalledWith(completedStatus);
    });
  });

  test('应该正确渲染失败状态', async () => {
    const failedStatus: ParseStatus = {
      ...mockParseStatus,
      status: 'failed',
      error: '解析过程中遇到格式错误'
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(failedStatus)
    });

    const onError = jest.fn();
    render(<ParseProgress {...defaultProps} onError={onError} />);

    await waitFor(() => {
      expect(screen.getByText('失败')).toBeInTheDocument();
      expect(screen.getByText('解析过程中遇到格式错误')).toBeInTheDocument();
      expect(onError).toHaveBeenCalledWith('解析过程中遇到格式错误');
    });
  });

  test('应该能够取消解析', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockParseStatus)
      })
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve({ success: true })
      });

    const onCancel = jest.fn();
    render(<ParseProgress {...defaultProps} onCancel={onCancel} />);

    await waitFor(() => {
      expect(screen.getByText('取消解析')).toBeInTheDocument();
    });

    const cancelButton = screen.getByText('取消解析');
    fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(global.fetch).toHaveBeenCalledWith(
        `/api/parse-cancel/${defaultProps.parseId}/`,
        { method: 'POST' }
      );
      expect(message.success).toHaveBeenCalledWith('已发送取消请求');
      expect(onCancel).toHaveBeenCalled();
    });
  });

  test('应该处理网络错误', async () => {
    (global.fetch as jest.Mock).mockRejectedValue(new Error('网络错误'));

    render(<ParseProgress {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('无法获取解析状态')).toBeInTheDocument();
      expect(screen.getByText('重试')).toBeInTheDocument();
    });
  });

  test('应该在开发模式下使用模拟数据', async () => {
    // 临时设置为开发模式
    const originalEnv = process.env.NODE_ENV;
    process.env.NODE_ENV = 'development';

    (global.fetch as jest.Mock).mockRejectedValue(new Error('API不可用'));

    render(<ParseProgress {...defaultProps} />);

    await waitFor(() => {
      // 应该显示模拟数据而不是错误
      expect(screen.getByText('解析进度')).toBeInTheDocument();
    });

    // 恢复环境变量
    process.env.NODE_ENV = originalEnv;
  });

  test('应该格式化时间显示', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockParseStatus)
    });

    render(<ParseProgress {...defaultProps} />);

    await waitFor(() => {
      // 检查预计剩余时间格式化
      expect(screen.getByText(/2分0秒/)).toBeInTheDocument();
    });
  });

  test('应该正确显示解析信息', async () => {
    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(mockParseStatus)
    });

    render(<ParseProgress {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText(defaultProps.parseId)).toBeInTheDocument();
      expect(screen.getByText('2025-06-03 09:30:00')).toBeInTheDocument();
    });
  });

  test('取消解析时应该处理非运行状态', async () => {
    const completedStatus: ParseStatus = {
      ...mockParseStatus,
      status: 'completed'
    };

    (global.fetch as jest.Mock).mockResolvedValue({
      ok: true,
      json: () => Promise.resolve(completedStatus)
    });

    render(<ParseProgress {...defaultProps} />);

    await waitFor(() => {
      expect(screen.queryByText('取消解析')).not.toBeInTheDocument();
    });
  });

  test('应该处理取消解析失败', async () => {
    (global.fetch as jest.Mock)
      .mockResolvedValueOnce({
        ok: true,
        json: () => Promise.resolve(mockParseStatus)
      })
      .mockResolvedValueOnce({
        ok: false,
        status: 500
      });

    render(<ParseProgress {...defaultProps} />);

    await waitFor(() => {
      expect(screen.getByText('取消解析')).toBeInTheDocument();
    });

    const cancelButton = screen.getByText('取消解析');
    fireEvent.click(cancelButton);

    await waitFor(() => {
      expect(message.error).toHaveBeenCalledWith('取消解析失败');
    });
  });
}); 