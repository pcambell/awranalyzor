import { renderHook, act, waitFor } from '@testing-library/react';
import { message } from 'antd';
import { useFileUpload } from '../useFileUpload';

// Mock antd message
jest.mock('antd', () => ({
  message: {
    success: jest.fn(),
    error: jest.fn(),
    info: jest.fn(),
  },
}));

// Mock fetch
global.fetch = jest.fn();
const mockFetch = fetch as jest.MockedFunction<typeof fetch>;

describe('useFileUpload Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockFetch.mockClear();
    
    // Mock CSRF token for each test
    const mockElement = {
      value: 'mock-csrf-token'
    } as HTMLInputElement;
    
    jest.spyOn(document, 'querySelector').mockReturnValue(mockElement);
  });

  afterEach(() => {
    jest.restoreAllMocks();
  });

  describe('Initial State', () => {
    it('returns correct initial state', () => {
      const { result } = renderHook(() => useFileUpload());

      expect(result.current.uploading).toBe(false);
      expect(result.current.progress).toBe(0);
      expect(result.current.error).toBe(null);
      expect(typeof result.current.uploadFile).toBe('function');
      expect(typeof result.current.startParsing).toBe('function');
      expect(typeof result.current.clearError).toBe('function');
    });

    it('accepts custom configuration', () => {
      const config = {
        maxFileSize: 100,
        allowedTypes: ['.xml', '.txt'],
        apiEndpoint: '/custom-api'
      };

      const { result } = renderHook(() => useFileUpload(config));

      // Configuration is internal, but we can test its effects through validation
      expect(result.current).toBeDefined();
    });
  });

  describe('File Validation', () => {
    it('rejects files with invalid extensions', async () => {
      const { result } = renderHook(() => useFileUpload());
      
      const invalidFile = new File(['content'], 'test.pdf', { type: 'application/pdf' });

      await act(async () => {
        const uploadResult = await result.current.uploadFile(invalidFile);
        expect(uploadResult).toBe(null);
      });

      expect(result.current.error).toContain('不支持的文件类型');
      expect(message.error).toHaveBeenCalledWith(expect.stringContaining('不支持的文件类型'));
    });

    it('rejects files that are too large', async () => {
      const { result } = renderHook(() => useFileUpload({ maxFileSize: 1 })); // 1MB limit
      
      // Create a file larger than 1MB
      const largeContent = 'x'.repeat(2 * 1024 * 1024); // 2MB
      const largeFile = new File([largeContent], 'large.html', { type: 'text/html' });

      await act(async () => {
        const uploadResult = await result.current.uploadFile(largeFile);
        expect(uploadResult).toBe(null);
      });

      expect(result.current.error).toContain('文件大小超过限制');
      expect(message.error).toHaveBeenCalledWith(expect.stringContaining('文件大小超过限制'));
    });

    it('accepts valid HTML files', async () => {
      const { result } = renderHook(() => useFileUpload());
      
      const validFile = new File(['<html>AWR content</html>'], 'awr_report.html', { 
        type: 'text/html' 
      });

      // Mock successful upload response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            id: '1',
            name: 'awr_report.html',
            size: validFile.size,
            upload_time: '2023-01-01T00:00:00Z',
            status: 'uploaded'
          }
        })
      } as Response);

      let uploadResult;
      await act(async () => {
        uploadResult = await result.current.uploadFile(validFile);
      });

      expect(uploadResult).not.toBe(null);
      expect(mockFetch).toHaveBeenCalledWith('/api/upload/', expect.objectContaining({
        method: 'POST',
        headers: {
          'X-CSRFToken': 'mock-csrf-token'
        }
      }));
    });

    it('warns about non-AWR filenames but allows upload', async () => {
      const { result } = renderHook(() => useFileUpload());
      
      const consoleWarnSpy = jest.spyOn(console, 'warn').mockImplementation();
      const validFile = new File(['<html>content</html>'], 'generic.html', { 
        type: 'text/html' 
      });

      // Mock successful upload response
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            id: '1',
            name: 'generic.html',
            size: validFile.size,
            upload_time: '2023-01-01T00:00:00Z',
            status: 'uploaded'
          }
        })
      } as Response);

      await act(async () => {
        await result.current.uploadFile(validFile);
      });

      expect(consoleWarnSpy).toHaveBeenCalledWith('文件名可能不是AWR报告文件');
      consoleWarnSpy.mockRestore();
    });
  });

  describe('Upload Process', () => {
    beforeEach(() => {
      jest.useFakeTimers();
    });

    afterEach(() => {
      jest.runOnlyPendingTimers();
      jest.useRealTimers();
    });

    it('sets uploading state during upload', async () => {
      const { result } = renderHook(() => useFileUpload());
      
      const validFile = new File(['<html>AWR content</html>'], 'awr_report.html', { 
        type: 'text/html' 
      });

      // Mock a response that resolves immediately but we can control timing
      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            id: '1',
            name: 'awr_report.html',
            size: validFile.size,
            upload_time: '2023-01-01T00:00:00Z',
            status: 'uploaded'
          }
        })
      } as Response);

      // Start upload
      let uploadPromise: Promise<any>;
      act(() => {
        uploadPromise = result.current.uploadFile(validFile);
      });

      // Should be uploading immediately
      expect(result.current.uploading).toBe(true);
      expect(result.current.progress).toBe(0);

      // Fast-forward timers to simulate progress updates (avoid infinite loop)
      act(() => {
        jest.advanceTimersByTime(500); // Only advance by specific amount
      });

      expect(result.current.progress).toBeGreaterThan(0);
      expect(result.current.progress).toBeLessThanOrEqual(90);

      // Complete the upload by awaiting the promise
      await act(async () => {
        jest.advanceTimersByTime(1000); // Clear remaining progress timer
        await uploadPromise;
      });

      expect(result.current.uploading).toBe(false);
    });

    it('updates progress during upload', async () => {
      const { result } = renderHook(() => useFileUpload());
      
      const validFile = new File(['<html>AWR content</html>'], 'awr_report.html', { 
        type: 'text/html' 
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({
          success: true,
          data: {
            id: '1',
            name: 'awr_report.html',
            size: validFile.size,
            upload_time: '2023-01-01T00:00:00Z',
            status: 'uploaded'
          }
        })
      } as Response);

      let uploadPromise: Promise<any>;
      act(() => {
        uploadPromise = result.current.uploadFile(validFile);
      });

      // Simulate progress updates with controlled timer advancement
      act(() => {
        jest.advanceTimersByTime(200);
      });
      expect(result.current.progress).toBe(10);

      act(() => {
        jest.advanceTimersByTime(400);
      });
      expect(result.current.progress).toBe(30);

      // Complete upload
      await act(async () => {
        jest.advanceTimersByTime(1000); // Clear timers
        await uploadPromise;
      });

      // Don't expect 100% immediately as there's a delay in setting final progress
      expect(result.current.uploading).toBe(false);
    });

    it('handles successful upload', async () => {
      const { result } = renderHook(() => useFileUpload());
      
      const validFile = new File(['<html>AWR content</html>'], 'awr_report.html', { 
        type: 'text/html' 
      });

      const mockResponse = {
        id: '1',
        name: 'awr_report.html',
        size: validFile.size,
        upload_time: '2023-01-01T00:00:00Z',
        status: 'uploaded' as const
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, data: mockResponse })
      } as Response);

      let uploadResult;
      await act(async () => {
        const uploadPromise = result.current.uploadFile(validFile);
        jest.advanceTimersByTime(1000); // Advance all progress timers
        uploadResult = await uploadPromise;
      });

      expect(uploadResult).toEqual(mockResponse);
      expect(result.current.uploading).toBe(false);
      expect(message.success).toHaveBeenCalledWith('文件 "awr_report.html" 上传成功！');
      
      // Progress should be 100 after upload completion and timer processing
      await act(async () => {
        jest.advanceTimersByTime(100); // Allow final progress update
      });
      expect(result.current.progress).toBe(100);
    });

    it('handles upload network errors', async () => {
      const { result } = renderHook(() => useFileUpload());
      
      const validFile = new File(['<html>AWR content</html>'], 'awr_report.html', { 
        type: 'text/html' 
      });

      mockFetch.mockRejectedValueOnce(new Error('Network error'));

      let uploadResult;
      await act(async () => {
        const uploadPromise = result.current.uploadFile(validFile);
        jest.advanceTimersByTime(1000); // Clear any pending timers
        uploadResult = await uploadPromise;
      });

      expect(uploadResult).toBe(null);
      expect(result.current.error).toBe('Network error');
      expect(result.current.uploading).toBe(false);
      expect(message.error).toHaveBeenCalledWith('Network error');
    });

    it('handles upload API errors', async () => {
      const { result } = renderHook(() => useFileUpload());
      
      const validFile = new File(['<html>AWR content</html>'], 'awr_report.html', { 
        type: 'text/html' 
      });

      mockFetch.mockResolvedValueOnce({
        ok: false,
        status: 500,
        statusText: 'Internal Server Error'
      } as Response);

      let uploadResult;
      await act(async () => {
        const uploadPromise = result.current.uploadFile(validFile);
        jest.advanceTimersByTime(1000); // Clear any pending timers
        uploadResult = await uploadPromise;
      });

      expect(uploadResult).toBe(null);
      expect(result.current.error).toContain('上传失败: 500 Internal Server Error');
    });

    it('handles API response with success=false', async () => {
      const { result } = renderHook(() => useFileUpload());
      
      const validFile = new File(['<html>AWR content</html>'], 'awr_report.html', { 
        type: 'text/html' 
      });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: false, message: 'File processing failed' })
      } as Response);

      let uploadResult;
      await act(async () => {
        const uploadPromise = result.current.uploadFile(validFile);
        jest.advanceTimersByTime(1000); // Clear any pending timers
        uploadResult = await uploadPromise;
      });

      expect(uploadResult).toBe(null);
      expect(result.current.error).toBe('File processing failed');
    });
  });

  describe('Parse Functionality', () => {
    it('successfully starts parsing', async () => {
      const { result } = renderHook(() => useFileUpload());
      
      const mockParseResponse = {
        id: 'parse-1',
        file_id: 'file-1',
        status: 'pending' as const,
        progress: 0,
        created_at: '2023-01-01T00:00:00Z',
        updated_at: '2023-01-01T00:00:00Z'
      };

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, data: mockParseResponse })
      } as Response);

      let parseResult;
      await act(async () => {
        parseResult = await result.current.startParsing('file-1');
      });

      expect(parseResult).toEqual(mockParseResponse);
      expect(mockFetch).toHaveBeenCalledWith('/api/parse/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': 'mock-csrf-token'
        },
        body: JSON.stringify({ file_id: 'file-1' })
      });
      expect(message.info).toHaveBeenCalledWith('AWR文件解析已开始...');
    });

    it('handles parsing errors', async () => {
      const { result } = renderHook(() => useFileUpload());
      
      mockFetch.mockRejectedValueOnce(new Error('Parse failed'));

      let parseResult;
      await act(async () => {
        parseResult = await result.current.startParsing('file-1');
      });

      expect(parseResult).toBe(null);
      expect(result.current.error).toBe('Parse failed');
      expect(message.error).toHaveBeenCalledWith('Parse failed');
    });
  });

  describe('Error Management', () => {
    it('clears error state', async () => {
      const { result } = renderHook(() => useFileUpload());
      
      // Simulate an error by calling uploadFile with invalid file
      await act(async () => {
        await result.current.uploadFile(new File([''], 'test.pdf'));
      });

      expect(result.current.error).not.toBe(null);

      act(() => {
        result.current.clearError();
      });

      expect(result.current.error).toBe(null);
    });
  });

  describe('Custom Configuration', () => {
    it('uses custom file size limit', async () => {
      const { result } = renderHook(() => useFileUpload({ maxFileSize: 0.001 })); // Very small limit (1KB)
      
      // Create a file larger than the limit 
      const largeContent = 'x'.repeat(2 * 1024); // 2KB content
      const file = new File([largeContent], 'test.html', { type: 'text/html' });

      let uploadResult;
      await act(async () => {
        uploadResult = await result.current.uploadFile(file);
      });

      expect(uploadResult).toBe(null);
      expect(result.current.error).toContain('文件大小超过限制');
      expect(message.error).toHaveBeenCalledWith(expect.stringContaining('文件大小超过限制'));
    });

    it('uses custom allowed types', async () => {
      const { result } = renderHook(() => useFileUpload({ allowedTypes: ['.xml'] }));
      
      const htmlFile = new File(['<html></html>'], 'test.html', { type: 'text/html' });

      await act(async () => {
        const uploadResult = await result.current.uploadFile(htmlFile);
        expect(uploadResult).toBe(null);
      });

      expect(result.current.error).toContain('不支持的文件类型');
    });

    it('uses custom API endpoint', async () => {
      const { result } = renderHook(() => useFileUpload({ apiEndpoint: '/custom' }));
      
      const validFile = new File(['<html>content</html>'], 'test.html', { type: 'text/html' });

      mockFetch.mockResolvedValueOnce({
        ok: true,
        json: async () => ({ success: true, data: {} })
      } as Response);

      await act(async () => {
        await result.current.uploadFile(validFile);
      });

      expect(mockFetch).toHaveBeenCalledWith('/custom/upload/', expect.any(Object));
    });
  });
}); 