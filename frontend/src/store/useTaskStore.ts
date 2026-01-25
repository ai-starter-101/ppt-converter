// 任务状态管理 (Zustand)
import { create } from 'zustand';
import type { Task, TaskStatus } from '../types';

interface TaskState {
  // 当前任务
  currentTask: Task | null;
  setCurrentTask: (task: Task | null) => void;

  // 任务列表
  tasks: Task[];
  setTasks: (tasks: Task[]) => void;
  addTask: (task: Task) => void;
  updateTask: (id: string, updates: Partial<Task>) => void;

  // 加载状态
  loading: boolean;
  setLoading: (loading: boolean) => void;

  // 错误信息
  error: string | null;
  setError: (error: string | null) => void;

  // 清除状态
  clearState: () => void;
}

export const useTaskStore = create<TaskState>((set) => ({
  // 当前任务
  currentTask: null,
  setCurrentTask: (task) => set({ currentTask: task }),

  // 任务列表
  tasks: [],
  setTasks: (tasks) => set({ tasks }),
  addTask: (task) => set((state) => ({ tasks: [task, ...state.tasks] })),
  updateTask: (id, updates) =>
    set((state) => ({
      tasks: state.tasks.map((t) =>
        t.id === id ? { ...t, ...updates } : t
      ),
      currentTask:
        state.currentTask?.id === id
          ? { ...state.currentTask, ...updates }
          : state.currentTask,
    })),

  // 加载状态
  loading: false,
  setLoading: (loading) => set({ loading }),

  // 错误信息
  error: null,
  setError: (error) => set({ error }),

  // 清除状态
  clearState: () =>
    set({
      currentTask: null,
      loading: false,
      error: null,
    }),
}));

// 根据状态获取步骤索引
// 步骤 0：上传PPT
// 步骤 1：脚本生成/音频生成
// 步骤 2：合成视频
export const getStepIndex = (status: TaskStatus): number => {
  const statusMap: Record<TaskStatus, number> = {
    pending: 0,        // 任务刚创建 - 步骤 0：上传PPT
    uploaded: 1,       // PPT 已上传 - 步骤 1：脚本和音频生成
    processing: 1,     // 处理中 - 步骤 1：脚本和音频生成
    script_ready: 1,   // 脚本已生成 - 步骤 1：脚本和音频生成
    audio_ready: 2,    // 音频已生成 - 步骤 2：合成视频
    video_ready: 2,    // 视频已合成 - 步骤 2：合成视频
    failed: 0,         // 失败 - 回到步骤 0
  };
  return statusMap[status] ?? 0;
};
