import { useState, useCallback } from 'react';
import { message } from 'antd';
import { UploadedFile, AWRParseResult, ApiResponse } from '../types';

interface UploadConfig {
  maxFileSize?: number; // MB
  allowedTypes?: string[];
  apiEndpoint?: string;
}

interface UseFileUploadReturn {
  uploading: boolean;
  progress: number;
  error: string | null;
  uploadFile: (file: File) => Promise<UploadedFile | null>;
  startParsing: (fileId: string) => Promise<AWRParseResult | null>;
  clearError: () => void;
}

export const useFileUpload = (config: UploadConfig = {}): UseFileUploadReturn => {
  const {
    maxFileSize = 50,
    allowedTypes = ['.html', '.htm'],
    apiEndpoint = '/api'
  } = config;

  const [uploading, setUploading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState<string | null>(null);

  // 获取CSRF Token - 安全编码原则
  const getCsrfToken = useCallback((): string => {
    const token = document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement;
    return token?.value || '';
  }, []);

  // 文件校验逻辑 - SOLID原则：单一职责
  const validateFile = useCallback((file: File): string | null => {
    // 文件类型校验
    const fileExtension = file.name.toLowerCase().substring(file.name.lastIndexOf('.'));
    if (!allowedTypes.includes(fileExtension)) {
      return `不支持的文件类型。仅支持: ${allowedTypes.join(', ')}`;
    }

    // 文件大小校验
    const maxSize = maxFileSize * 1024 * 1024;
    if (file.size > maxSize) {
      return `文件大小超过限制 (${maxFileSize}MB)`;
    }

    // AWR文件基础校验
    const fileName = file.name.toLowerCase();
    if (!fileName.includes('awr') && !fileName.includes('oracle')) {
      console.warn('文件名可能不是AWR报告文件');
    }

    return null;
  }, [allowedTypes, maxFileSize]);

  // 上传文件 - Clean Code原则：函数职责清晰
  const uploadFile = useCallback(async (file: File): Promise<UploadedFile | null> => {
    // 前置校验
    const validationError = validateFile(file);
    if (validationError) {
      setError(validationError);
      message.error(validationError);
      return null;
    }

    setUploading(true);
    setProgress(0);
    setError(null);

    const formData = new FormData();
    formData.append('file', file);

    let progressInterval: NodeJS.Timeout | null = null;

    try {
      // 模拟进度更新
      progressInterval = setInterval(() => {
        setProgress(prev => Math.min(prev + 10, 90));
      }, 200);

      const response = await fetch(`${apiEndpoint}/upload/`, {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': getCsrfToken(),
        },
      });

      if (progressInterval) {
        clearInterval(progressInterval);
      }

      if (!response.ok) {
        throw new Error(`上传失败: ${response.status} ${response.statusText}`);
      }

      const result: ApiResponse<UploadedFile> = await response.json();
      
      if (!result.success || !result.data) {
        throw new Error(result.message || '上传处理失败');
      }

      setProgress(100);
      message.success(`文件 "${file.name}" 上传成功！`);
      
      return result.data;

    } catch (err: any) {
      const errorMessage = err.message || '上传失败';
      setError(errorMessage);
      message.error(errorMessage);
      return null;

    } finally {
      if (progressInterval) {
        clearInterval(progressInterval);
      }
      setUploading(false);
      // 延迟重置进度条，让用户看到100%状态
      setTimeout(() => setProgress(0), 1000);
    }
  }, [apiEndpoint, getCsrfToken, validateFile]);

  // 开始解析 - 可测试性：独立的异步函数
  const startParsing = useCallback(async (fileId: string): Promise<AWRParseResult | null> => {
    try {
      const response = await fetch(`${apiEndpoint}/parse/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-CSRFToken': getCsrfToken(),
        },
        body: JSON.stringify({ file_id: fileId }),
      });

      if (!response.ok) {
        throw new Error(`解析启动失败: ${response.status} ${response.statusText}`);
      }

      const result: ApiResponse<AWRParseResult> = await response.json();
      
      if (!result.success || !result.data) {
        throw new Error(result.message || '解析启动失败');
      }

      message.info('AWR文件解析已开始...');
      return result.data;

    } catch (err: any) {
      const errorMessage = err.message || '解析启动失败';
      setError(errorMessage);
      message.error(errorMessage);
      return null;
    }
  }, [apiEndpoint, getCsrfToken]);

  // 清除错误状态
  const clearError = useCallback(() => {
    setError(null);
  }, []);

  return {
    uploading,
    progress,
    error,
    uploadFile,
    startParsing,
    clearError
  };
}; 