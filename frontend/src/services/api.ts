import axios from 'axios';

// 创建axios实例
const api = axios.create({
  baseURL: process.env.REACT_APP_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加认证token（如果需要）
    const token = localStorage.getItem('authToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response;
  },
  (error) => {
    // 统一错误处理
    if (error.response?.status === 401) {
      // 处理认证失败
      localStorage.removeItem('authToken');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// 文件上传API
export const uploadFile = async (file: File, onProgress?: (progressEvent: any) => void) => {
  const formData = new FormData();
  formData.append('file', file);

  const response = await api.post('/upload/', formData, {
    headers: {
      'Content-Type': 'multipart/form-data',
    },
    onUploadProgress: onProgress,
  });

  return response.data;
};

// 获取上传文件列表
export const getUploadedFiles = async () => {
  const response = await api.get('/files/');
  return response.data;
};

// 删除上传的文件
export const deleteFile = async (fileId: string) => {
  const response = await api.delete(`/files/${fileId}/`);
  return response.data;
};

// 启动AWR解析
export const startAWRParse = async (fileId: string) => {
  const response = await api.post('/parse/', {
    file_id: fileId,
  });
  return response.data;
};

// 获取解析状态
export const getParseStatus = async (parseId: string) => {
  const response = await api.get(`/parse/${parseId}/status/`);
  return response.data;
};

// 获取解析结果
export const getParseResult = async (parseId: string) => {
  const response = await api.get(`/parse/${parseId}/result/`);
  return response.data;
};

// 获取解析历史
export const getParseHistory = async () => {
  const response = await api.get('/parse/history/');
  return response.data;
};

// 取消解析任务
export const cancelParse = async (parseId: string) => {
  const response = await api.post(`/parse/${parseId}/cancel/`);
  return response.data;
};

// 健康检查
export const healthCheck = async () => {
  const response = await api.get('/health/');
  return response.data;
};

export default api; 