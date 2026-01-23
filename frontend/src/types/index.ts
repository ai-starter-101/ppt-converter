// 任务状态类型
export type TaskStatus =
  | 'pending'      // 任务刚创建
  | 'uploaded'     // PPT 已上传
  | 'processing'   // 处理中（生成脚本/音频）
  | 'script_ready' // 脚本已生成/编辑完成
  | 'audio_ready'  // 音频已生成
  | 'failed';      // 处理失败

// 单页幻灯片数据
export interface SlideData {
  page_num: number;
  content: string;       // PPT 文本内容
  script?: string;       // 讲解脚本
  audio?: AudioInfo;     // 音频信息
  screenshot?: string;   // 幻灯片截图路径
}

// 音频信息
export interface AudioInfo {
  page_num: number;
  audio_path?: string;
  duration: number;
  error?: string;
}

// 任务数据模型
export interface Task {
  id: string;
  filename: string;
  file_path: string;
  status: TaskStatus;
  slide_count: number;
  slides_content?: string;  // JSON
  slides_script?: string;   // JSON
  slides_audio?: string;    // JSON
  script?: string;          // 兼容旧版本
  audio_path?: string;
  audio_duration?: number;
  created_at: string;
  updated_at: string;
}

// 任务详情（包含解析后的幻灯片数据）
export interface TaskDetail {
  task_id: string;
  filename: string;
  slides: SlideData[];
}

// API 响应类型
export interface CreateTaskResponse {
  id: string;
  status: TaskStatus;
}

export interface UploadResponse {
  id: string;
  filename: string;
  status: TaskStatus;
  slide_count: number;
  slides: SlideData[];
  screenshots?: { page_num: number; screenshot_path: string }[];
}

export interface ScriptResponse {
  task_id: string;
  page_num: number;
  script: string;
  status: TaskStatus;
}

export interface ScriptsGenerateResponse {
  task_id: string;
  scripts: { page_num: number; script: string }[];
  status: TaskStatus;
}

export interface AudioResponse {
  task_id: string;
  page_num: number;
  audio_path: string;
  duration: number;
  status: TaskStatus;
}
