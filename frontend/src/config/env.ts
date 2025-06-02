// 环境配置
export const config = {
  // API配置
  apiBaseUrl: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api',
  
  // WebSocket配置
  wsUrl: process.env.REACT_APP_WS_URL || 'ws://localhost:8000/ws',
  
  // 应用配置
  appTitle: process.env.REACT_APP_TITLE || 'Oracle AWR Analyzer',
  debug: process.env.REACT_APP_DEBUG === 'true',
  
  // 文件上传配置
  maxFileSize: parseInt(process.env.REACT_APP_MAX_FILE_SIZE || '52428800'), // 50MB
  allowedFileTypes: ['.html', '.htm'],
  
  // 功能开关
  enableServiceWorker: process.env.REACT_APP_ENABLE_SERVICE_WORKER === 'true',
  
  // 主题配置
  defaultTheme: 'light' as 'light' | 'dark',
  
  // 分页配置
  defaultPageSize: 10,
  pageSizeOptions: ['10', '20', '50', '100'],
  
  // 请求超时配置
  requestTimeout: 30000, // 30秒
  
  // 解析进度轮询间隔
  progressPollingInterval: 2000, // 2秒
};

// 开发环境检查
export const isDevelopment = process.env.NODE_ENV === 'development';
export const isProduction = process.env.NODE_ENV === 'production';

// 版本信息
export const version = process.env.REACT_APP_VERSION || '1.0.0';

export default config; 