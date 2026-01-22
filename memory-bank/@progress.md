# 实施进度

## 已确认的设计决策

### 状态管理
- Zustand 用于 UI 状态（如步骤指示器当前步、展开/折叠状态）
- React Query 用于服务器状态（任务列表、任务详情）

### 脚本编辑流程
1. 用户点击"生成脚本"按钮调用 LLM
2. 脚本生成后显示在编辑器中
3. 用户可编辑脚本内容
4. 边输入边保存（自动保存）

### LLM API 兼容
- 配置文件指定使用哪个 provider（Claude / 智谱AI）
- 代码内部根据 provider 调用不同 API

### 音频播放
- `GET /api/tasks/{id}/audio` 直接返回整个 MP3 文件流

### 任务状态枚举
- `pending` - 任务刚创建
- `uploaded` - PPT 已上传
- `processing` - 处理中（生成脚本/音频）
- `script_ready` - 脚本已生成/编辑完成
- `audio_ready` - 音频已生成
- `failed` - 处理失败

### 新建任务流程
1. 首页点击"新建任务"
2. 调用 `POST /api/tasks` 创建任务
3. 跳转到 `/task/{task_id}` 详情页

---

## 步骤记录

### 步骤 1.1：创建后端项目结构 ✅

**完成时间**：2026-01-19

**操作内容**：
- 创建 `backend/` 目录及子目录结构
- 创建 `app/__init__.py`、`app/routes/__init__.py`、`app/services/__init__.py`、`app/models/__init__.py`、`app/utils/__init__.py`
- 创建 `static/uploads/` 和 `static/audio/` 目录
- 创建 `tests/__init__.py`
- 创建 `backend/requirements.txt`（注意：python-pptx 版本改为 1.0.2，0.18.2 不存在）
- 创建 `backend/.env` 配置文件

**验证命令**：
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python -c "import fastapi; import sqlmodel; from pptx import Presentation; import edge_tts; print('All imports successful')"
```

**已知问题**：
- `python-pptx` 导入方式为 `from pptx import Presentation`，非 `import python_pptx`

### 步骤 2.1：创建数据库连接和模型 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `app/database.py` - 数据库引擎和会话管理
- 创建 `app/models/task.py` - Task 数据模型
- 更新 `app/config.py` - 使用同步 SQLite（移除 aiosqlite）

**验证结果**：
- Task 模型实例化成功
- 数据库表创建成功
- 所有字段正确：`id`, `filename`, `file_path`, `status`, `script`, `audio_path`, `audio_duration`, `created_at`, `updated_at`

### 步骤 2.2：创建 PPT 解析服务 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `app/services/ppt_service.py`
- 实现 `extract_text_from_ppt()` 函数
- 实现 `get_ppt_info()` 函数

**验证结果**：
- 成功提取 PPT 文本内容
- 正确解析幻灯片结构
- 返回格式化的文本字符串

### 步骤 2.3：创建 LLM 服务 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `app/services/script_service.py`
- 实现 `call_claude_api()` - Claude API 调用
- 实现 `call_zhipu_api()` - 智谱AI API 调用
- 实现 `generate_script()` - 主函数

**验证结果**：
- 成功调用智谱AI API
- 生成的口语化讲解脚本质量良好
- 支持 Claude / 智谱AI 两种 provider

### 步骤 2.4：创建 TTS 服务 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `app/services/tts_service.py`
- 实现 `generate_audio()` - Edge TTS 音频生成
- 实现 `get_audio_duration()` - 获取音频时长

**验证结果**：
- TTS 服务代码结构正确
- 配置正确（zh-CN-XiaoxiaoNeural）
- Edge TTS 需要网络环境支持（在有代理环境下可正常工作）

### 步骤 3.1：创建 FastAPI 应用入口 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `app/main.py`
- 配置 FastAPI 应用和 CORS 中间件
- 挂载静态文件目录（/static）
- 注册任务路由

**验证结果**：
- FastAPI 应用创建成功
- CORS 配置正确
- 静态文件服务正常

### 步骤 3.2：创建任务路由 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `app/routes/tasks.py`
- 实现 `POST /api/tasks` - 创建任务
- 实现 `GET /api/tasks` - 获取任务列表
- 实现 `GET /api/tasks/{id}` - 获取任务详情

**验证结果**：
- 所有路由注册成功
- 数据库查询正常
- 响应格式正确

### 步骤 3.3：创建文件上传接口 ✅

**完成时间**：2026-01-21

**操作内容**：
- 实现 `POST /api/tasks/{id}/upload` 端点
- 验证文件类型（.pptx）
- 生成唯一文件名并保存
- 更新任务状态为 `uploaded`

**验证结果**：
- 文件上传功能正常
- PPT 文件验证正确
- 任务状态更新正确

### 步骤 3.4：创建脚本生成接口 ✅

**完成时间**：2026-01-21

**操作内容**：
- 实现 `POST /api/tasks/{id}/script` - 调用 LLM 生成脚本
- 实现 `PUT /api/tasks/{id}/script` - 更新脚本内容
- 状态检查和错误处理

**验证结果**：
- 脚本生成功能正常
- 支持 Claude / 智谱AI 两种 provider
- 脚本编辑功能正常

### 步骤 3.5：创建音频生成和播放接口 ✅

**完成时间**：2026-01-21

**操作内容**：
- 实现 `POST /api/tasks/{id}/audio` - 生成音频
- 实现 `GET /api/tasks/{id}/audio` - 音频流播放
- 返回音频时长信息

**验证结果**：
- 音频生成功能正常
- 音频流播放正常
- 时长计算正确

### 步骤 4.1：配置 API 请求层 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `frontend/src/api/client.ts` - Axios 基础配置
- 创建 `frontend/src/api/task.ts` - 任务相关 API 函数
  - `createTask()` - 创建任务
  - `uploadPPT(taskId, file)` - 上传文件
  - `generateScript(taskId)` - 生成脚本
  - `updateScript(taskId, script)` - 更新脚本
  - `generateAudio(taskId)` - 生成音频
  - `getTask(taskId)` - 获取任务详情
  - `getTaskList()` - 获取任务列表
  - `getAudioUrl(taskId)` - 获取音频 URL

**验证结果**：
- API 客户端配置正确
- 请求拦截器和响应拦截器正常

### 步骤 4.2：创建类型定义 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `frontend/src/types/index.ts`
- 定义 `TaskStatus` 类型（pending / uploaded / processing / script_ready / audio_ready / failed）
- 定义 `Task` 接口（包含所有字段类型）
- 定义 API 响应类型联合类型

**验证结果**：
- TypeScript 类型检查通过
- 类型定义与后端模型对应

### 步骤 4.3：创建状态管理 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `frontend/src/store/useTaskStore.ts`
- 使用 Zustand 管理全局状态
- 实现状态：currentTask, tasks, loading, error
- 实现方法：setCurrentTask, setTasks, updateTask, clearState
- 实现 `getStepIndex(status)` - 根据状态获取步骤索引

**验证结果**：
- Zustand store 创建成功
- 状态更新正常

### 步骤 4.4：创建首页 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `frontend/src/pages/Home/index.tsx`
- 使用 React Query 获取任务列表
- 显示任务卡片列表（文件名、状态、创建时间）
- 提供"新建任务"按钮
- 状态标签颜色配置

**验证结果**：
- 任务列表正确显示
- 新建任务按钮可正常跳转

### 步骤 4.5：创建任务详情页框架 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `frontend/src/pages/Task/index.tsx`
- 使用 Ant Design Steps 组件创建进度指示器
- 4 个步骤：上传PPT / 脚本生成 / 音频生成 / 播放
- 根据任务状态自动高亮当前步骤
- 失败状态显示错误页面

**验证结果**：
- 步骤指示器显示正确
- 当前步骤正确高亮

### 步骤 4.6：实现文件上传组件 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `frontend/src/components/UploadPanel.tsx`
- 使用 Ant Design Upload 组件（Dragger）
- 限制上传文件类型为 `.pptx`
- 限制文件大小 50MB
- 拖拽上传支持
- 上传成功后刷新页面

**验证结果**：
- 文件上传功能正常
- 文件类型验证正确

### 步骤 4.7：实现脚本编辑组件 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `frontend/src/components/ScriptEditor.tsx`
- 使用 `@uiw/react-md-editor` 组件
- 显示/编辑脚本内容（Markdown 格式）
- 提供"生成脚本"和"重新生成"按钮
- 提供"保存脚本"按钮
- 实时预览支持

**验证结果**：
- Markdown 编辑器正常工作
- 脚本生成和保存功能正常

### 步骤 4.8：实现音频播放组件 ✅

**完成时间**：2026-01-21

**操作内容**：
- 创建 `frontend/src/components/AudioPlayer.tsx`
- 使用 HTML5 `<audio>` 元素播放音频
- 显示音频时长信息
- 提供"生成音频"按钮
- 提供"重新生成"按钮
- 提供下载按钮
- 生成中显示进度条

**验证结果**：
- 音频播放器正常工作
- 下载功能正常

### 步骤 4.9：配置路由和 React Query ✅

**完成时间**：2026-01-21

**操作内容**：
- 更新 `frontend/src/main.tsx`
  - 配置 QueryClient
  - 配置 BrowserRouter
  - 配置 Ant Design ConfigProvider (中文)
- 更新 `frontend/src/App.tsx`
  - 配置路由：/ 和 /task/:id
  - 移除默认模板代码

**验证结果**：
- 前端构建成功 (`npm run build`)
- 路由跳转正常
- React Query 数据获取正常
