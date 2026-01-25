// API 基础配置
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    // 可以在这里添加认证 token 等
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    let message = '请求失败';
    if (error.response) {
      // 服务器返回错误状态码
      message = error.response.data?.detail || error.response.data?.message || `HTTP ${error.response.status}`;
    } else if (error.request) {
      // 请求发出但没有收到响应
      message = '网络错误，请检查后端服务是否运行';
    } else {
      message = error.message || '请求失败';
    }
    console.error('API Error:', message);
    return Promise.reject(new Error(message));
  }
);
