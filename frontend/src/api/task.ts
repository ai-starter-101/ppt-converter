// 任务相关 API
import { apiClient } from './client';
import type {
  Task,
  TaskDetail,
  UploadResponse,
  ScriptsGenerateResponse,
  ScriptResponse,
  AudioResponse
} from '../types';

// 创建任务
export const createTask = async (): Promise<{ id: string }> => {
  return apiClient.post('/tasks');
};

// 获取任务列表
export const getTaskList = async (): Promise<Task[]> => {
  return apiClient.get('/tasks');
};

// 获取任务详情
export const getTask = async (id: string): Promise<Task> => {
  return apiClient.get(`/tasks/${id}`);
};

// 上传 PPT 文件
export const uploadPPT = async (id: string, file: File): Promise<UploadResponse> => {
  const formData = new FormData();
  formData.append('file', file);
  return apiClient.post(`/tasks/${id}/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};

// 获取幻灯片列表（包含内容、脚本、音频）
export const getSlides = async (id: string): Promise<TaskDetail> => {
  return apiClient.get(`/tasks/${id}/slides`);
};

// 按页生成所有脚本
export const generateScripts = async (id: string): Promise<ScriptsGenerateResponse> => {
  return apiClient.post(`/tasks/${id}/scripts/generate`);
};

// 更新单页脚本
export const updateScript = async (
  id: string,
  pageNum: number,
  script: string
): Promise<ScriptResponse> => {
  return apiClient.put(`/tasks/${id}/scripts/${pageNum}`, { script });
};

// 生成单页脚本
export const generateSingleScript = async (
  id: string,
  pageNum: number
): Promise<ScriptResponse> => {
  return apiClient.post(`/tasks/${id}/scripts/${pageNum}/generate`);
};

// 生成单页音频
export const generateAudio = async (id: string, pageNum: number): Promise<AudioResponse> => {
  return apiClient.post(`/tasks/${id}/audio/${pageNum}`);
};

// 生成所有页面音频
export const generateAllAudio = async (id: string): Promise<{ task_id: string; audios: any[] }> => {
  return apiClient.post(`/tasks/${id}/audio/generate-all`);
};

// 获取单页音频 URL
export const getAudioUrl = (id: string, pageNum: number): string => {
  const baseURL = apiClient.defaults.baseURL?.replace('/api', '') || 'http://localhost:8000';
  return `${baseURL}/api/tasks/${id}/audio/${pageNum}`;
};

// 删除任务
export const deleteTask = async (id: string): Promise<{ message: string; task_id: string }> => {
  return apiClient.delete(`/tasks/${id}`);
};

// 合成视频（将音频插入PPT）
export const synthesizeVideo = async (id: string): Promise<{ task_id: string; video_path: string; status: string }> => {
  return apiClient.post(`/tasks/${id}/video/synthesize`);
};

// 上传幻灯片截图
export const uploadScreenshots = async (id: string, files: File[]): Promise<{ task_id: string; screenshots: { page_num: number; screenshot_path: string }[] }> => {
  const formData = new FormData();
  for (const file of files) {
    formData.append('files', file);
  }
  return apiClient.post(`/tasks/${id}/screenshots/upload`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
};
