import { useState, useCallback } from 'react';
import { message } from 'antd';
import { UploadedFile, AWRParseResult, ApiResponse } from '../types';

/**
 * {{CHENGQI: 修复前后端数据格式不匹配 - 2025-06-09 19:20:40 +08:00 - 
 * Action: Modified; Reason: 修复前端期望ApiResponse包装格式与后端直接返回模型对象的不匹配; Principle_Applied: 数据适配和容错处理}}
 */

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

      const result = await response.json();

      if (!response.ok) {
        // 处理重复文件的特殊情况
        if (response.status === 409) {
          const duplicateError = {
            message: result.message || result.error || '文件已存在',
            type: 'duplicate_file',
            existingFile: result.existing_file || null
          };
          throw duplicateError;
        }
        throw new Error(result.error || result.message || `上传失败: ${response.status}`);
      }
      
      // 后端直接返回AWR报告对象，不是包装的ApiResponse格式
      // 检查是否包含必要的字段来判断是否成功
      if (!result.id || typeof result.id !== 'number') {
        throw new Error(result.error || result.message || '上传处理失败');
      }

      setProgress(100);
      message.success(`文件 "${file.name}" 上传成功！`);
      
      // 转换后端返回格式到前端期望的UploadedFile格式
      const uploadedFile: UploadedFile = {
        id: result.id.toString(),
        name: result.original_filename || file.name,
        size: result.file_size || file.size,
        upload_time: result.created_at || new Date().toISOString(),
        status: result.status === 'completed' ? 'completed' : 
                result.status === 'failed' ? 'failed' :
                result.status === 'processing' ? 'processing' : 'uploaded',
        file_path: result.file_path,
        error_message: result.error_message
      };
      
      return uploadedFile;

    } catch (err: any) {
      // 处理重复文件错误
      if (err.type === 'duplicate_file') {
        const duplicateMessage = `文件重复：${err.message}`;
        setError(duplicateMessage);
        
        // 显示更友好的重复文件提示
        message.warning({
          content: duplicateMessage,
          duration: 6,
          key: 'duplicate-file-warning'
        });
        
        // 返回特殊的错误对象，让调用方知道这是重复文件
        return {
          error: true,
          type: 'duplicate_file',
          message: duplicateMessage,
          existingFile: err.existingFile
        } as any;
      }
      
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
      // {{CHENGQI: 修复parse接口404错误 - 2025-06-09 20:04:47 +08:00 - 
      // Action: Modified; Reason: 后端上传成功后自动开始解析，无需额外调用parse接口; Principle_Applied: YAGNI-移除不必要的功能}}
      // 后端在上传成功后会自动开始解析，因此不需要额外的parse接口调用
      // 直接返回一个模拟的解析结果对象，让前端可以导航到相应页面
      const mockResult: AWRParseResult = {
        id: fileId,
        file_id: fileId,
        status: 'processing',
        progress: 0,
        start_time: new Date().toISOString(),
        estimated_time_remaining: null,
        parser_version: 'auto',
        sections_parsed: 0,
        total_sections: 0,
        parse_errors: []
      };

      message.info('AWR文件已上传，系统正在自动解析...');
      return mockResult;

    } catch (err: any) {
      const errorMessage = err.message || '解析启动失败';
      setError(errorMessage);
      message.error(errorMessage);
      return null;
    }
  }, [getCsrfToken]);

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