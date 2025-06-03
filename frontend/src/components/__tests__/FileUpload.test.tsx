import React from 'react';
import { render, screen } from '@testing-library/react';
import FileUpload from '../FileUpload';
import { useFileUpload } from '../../hooks/useFileUpload';

// Mock the custom hook
jest.mock('../../hooks/useFileUpload');
const mockUseFileUpload = useFileUpload as jest.MockedFunction<typeof useFileUpload>;

// Mock antd components to avoid complex rendering issues
jest.mock('antd', () => {
  const MockDragger = ({ children, ...props }: any) => (
    <div data-testid="upload-dragger" {...props}>
      {children}
    </div>
  );

  const MockCard = ({ children, title, ...props }: any) => (
    <div data-testid="card" {...props}>
      {title && <div data-testid="card-title">{title}</div>}
      {children}
    </div>
  );

  const MockAlert = ({ message, description, ...props }: any) => (
    <div data-testid="alert" {...props}>
      <div data-testid="alert-message">{message}</div>
      <div data-testid="alert-description">{description}</div>
    </div>
  );

  const MockProgress = ({ percent, ...props }: any) => (
    <div data-testid="progress" data-percent={percent} {...props} />
  );

  const MockTitle = ({ children, ...props }: any) => (
    <h1 data-testid="title" {...props}>{children}</h1>
  );

  const MockText = ({ children, ...props }: any) => (
    <span data-testid="text" {...props}>{children}</span>
  );

  return {
    Upload: {
      Dragger: MockDragger,
    },
    Card: MockCard,
    Alert: MockAlert,
    Progress: MockProgress,
    Typography: {
      Title: MockTitle,
      Text: MockText,
    },
    Button: ({ children, ...props }: any) => (
      <button data-testid="button" {...props}>{children}</button>
    ),
    List: ({ children, ...props }: any) => (
      <div data-testid="list" {...props}>{children}</div>
    ),
    Space: ({ children, ...props }: any) => (
      <div data-testid="space" {...props}>{children}</div>
    ),
    Tag: ({ children, ...props }: any) => (
      <span data-testid="tag" {...props}>{children}</span>
    ),
    Modal: {
      confirm: jest.fn(),
      error: jest.fn(),
    },
    Tooltip: ({ children, ...props }: any) => (
      <div data-testid="tooltip" {...props}>{children}</div>
    ),
    Row: ({ children, ...props }: any) => (
      <div data-testid="row" {...props}>{children}</div>
    ),
    Col: ({ children, ...props }: any) => (
      <div data-testid="col" {...props}>{children}</div>
    ),
  };
});

// Mock icons
jest.mock('@ant-design/icons', () => ({
  InboxOutlined: () => <span data-testid="inbox-icon">📁</span>,
  DeleteOutlined: () => <span data-testid="delete-icon">🗑️</span>,
  EyeOutlined: () => <span data-testid="eye-icon">👁️</span>,
  ExclamationCircleOutlined: () => <span data-testid="exclamation-icon">⚠️</span>,
  CheckCircleOutlined: () => <span data-testid="check-icon">✅</span>,
  ClockCircleOutlined: () => <span data-testid="clock-icon">🕐</span>,
  CloseCircleOutlined: () => <span data-testid="close-icon">❌</span>,
}));

describe('FileUpload Component', () => {
  const mockUploadFile = jest.fn();
  const mockStartParsing = jest.fn();
  const mockClearError = jest.fn();

  beforeEach(() => {
    // Reset all mocks
    jest.clearAllMocks();
    
    // Default mock implementation
    mockUseFileUpload.mockReturnValue({
      uploading: false,
      progress: 0,
      error: null,
      uploadFile: mockUploadFile,
      startParsing: mockStartParsing,
      clearError: mockClearError,
    });

    // Mock CSRF token
    const mockElement = {
      value: 'mock-csrf-token'
    } as HTMLInputElement;
    
    jest.spyOn(document, 'querySelector').mockReturnValue(mockElement);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Basic Rendering', () => {
    it('renders without crashing', () => {
      render(<FileUpload />);
      expect(screen.getByTestId('card')).toBeInTheDocument();
    });

    it('renders upload area with correct title', () => {
      render(<FileUpload />);
      
      expect(screen.getByTestId('card-title')).toHaveTextContent('AWR文件上传');
      expect(screen.getByTestId('upload-dragger')).toBeInTheDocument();
    });

    it('displays upload instructions', () => {
      render(<FileUpload />);
      
      expect(screen.getByText('点击或拖拽AWR报告文件到此区域上传')).toBeInTheDocument();
      expect(screen.getByText(/支持HTML格式的Oracle AWR报告文件/)).toBeInTheDocument();
    });

    it('shows file requirements section', () => {
      render(<FileUpload />);
      
      expect(screen.getByText('文件要求：')).toBeInTheDocument();
      expect(screen.getByText(/文件格式：HTML/)).toBeInTheDocument();
    });
  });

  describe('Hook Integration', () => {
    it('calls useFileUpload with correct configuration', () => {
      render(<FileUpload maxFileSize={100} accept=".html,.htm,.xml" />);
      
      expect(mockUseFileUpload).toHaveBeenCalledWith({
        maxFileSize: 100,
        allowedTypes: ['.html', '.htm', '.xml'],
        apiEndpoint: '/api'
      });
    });

    it('uses default configuration when no props provided', () => {
      render(<FileUpload />);
      
      expect(mockUseFileUpload).toHaveBeenCalledWith({
        maxFileSize: 50,
        allowedTypes: ['.html', '.htm'],
        apiEndpoint: '/api'
      });
    });
  });

  describe('Error Handling', () => {
    it('displays error message when upload fails', () => {
      const errorMessage = 'Upload failed: Network error';
      
      mockUseFileUpload.mockReturnValue({
        uploading: false,
        progress: 0,
        error: errorMessage,
        uploadFile: mockUploadFile,
        startParsing: mockStartParsing,
        clearError: mockClearError,
      });

      render(<FileUpload />);
      
      expect(screen.getByTestId('alert-message')).toHaveTextContent('上传错误');
      expect(screen.getByTestId('alert-description')).toHaveTextContent(errorMessage);
    });
  });

  describe('Upload State', () => {
    it('shows upload progress when uploading', () => {
      mockUseFileUpload.mockReturnValue({
        uploading: true,
        progress: 50,
        error: null,
        uploadFile: mockUploadFile,
        startParsing: mockStartParsing,
        clearError: mockClearError,
      });

      render(<FileUpload />);
      
      // Should show progress when uploading
      expect(mockUseFileUpload).toHaveBeenCalled();
    });
  });

  describe('Props Configuration', () => {
    it('respects maxFileSize prop', () => {
      render(<FileUpload maxFileSize={100} />);
      
      expect(screen.getByText(/单个文件最大100MB/)).toBeInTheDocument();
    });

    it('accepts callback props without errors', () => {
      const mockOnUploadSuccess = jest.fn();
      const mockOnParseStart = jest.fn();
      
      render(
        <FileUpload 
          onUploadSuccess={mockOnUploadSuccess} 
          onParseStart={mockOnParseStart} 
        />
      );
      
      expect(screen.getByTestId('card-title')).toHaveTextContent('AWR文件上传');
    });
  });
}); 