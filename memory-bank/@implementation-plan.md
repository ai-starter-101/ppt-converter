# PPT讲解生成器 - 实施计划

> 本文档为 AI 开发者提供详细的分步实施指令。聚焦 MVP 基础功能，每个步骤包含具体验证方法。

---

## 第一阶段：项目基础架构

### 步骤 1.1：创建后端项目结构

**目标**：建立 FastAPI 后端项目的基础目录结构

**操作指令**：
1. 在项目根目录下创建 `backend` 目录
2. 在 `backend` 目录下创建 `app` 包（包含 `__init__.py`）
3. 在 `app` 目录下创建以下子目录：`routes/`、`services/`、`models/`、`utils/`，每个目录都添加 `__init__.py`
4. 在 `backend` 目录下创建 `static/uploads/` 和 `static/audio/` 目录
5. 在 `backend` 目录下创建 `tests/` 目录（包含 `__init__.py`）
6. 创建 `backend/requirements.txt` 文件

**验证方法**：
- 检查目录结构是否与以下内容匹配：
  ```
  backend/
  ├── app/
  │   ├── __init__.py
  │   ├── routes/
  │   ├── services/
  │   ├── models/
  │   └── utils/
  ├── static/
  │   ├── uploads/
  │   └── audio/
  ├── tests/
  │   └── __init__.py
  ├── requirements.txt
  └── .env
  ```

---

### 步骤 1.2：配置后端依赖

**目标**：安装并配置后端所需的所有 Python 依赖包

**操作指令**：
1. 在 `backend/requirements.txt` 中添加以下依赖：
   ```
   fastapi==0.109.2
   uvicorn[standard]==0.27.1
   sqlmodel==0.0.14
   python-multipart==0.0.9
   python-pptx==0.18.2
   edge-tts==6.1.0
   httpx==0.26.0
   aiofiles==23.2.1
   python-dotenv==1.0.1
   pytest==7.4.4
   pytest-asyncio==0.23.3
   ```
2. 创建 Python 虚拟环境：`python -m venv venv`
3. 激活虚拟环境并安装依赖：`pip install -r requirements.txt`

**验证方法**：
- 运行 `python -c "import fastapi; import sqlmodel; import python_pptx; import edge_tts; print('All imports successful')"`
- 确认无 ImportError 异常

---

### 步骤 1.3：创建后端配置文件

**目标**：建立统一的环境变量和配置管理

**操作指令**：
1. 在 `backend/app/` 目录下创建 `config.py`
2. 使用 `python-dotenv` 读取环境变量
3. 创建以下配置项：
   - `DATABASE_URL`：SQLite 连接字符串
   - `LLM_API_KEY`、`LLM_BASE_URL`、`LLM_MODEL`：LLM 配置
   - `TTS_VOICE`：默认语音（`zh-CN-XiaoxiaoNeural`）
   - `UPLOAD_DIR`、`AUDIO_DIR`：文件存储路径
   - `HOST`、`PORT`：服务地址
4. 创建 `backend/.env` 文件，包含所有环境变量示例值

**验证方法**：
- 运行 `python -c "from app.config import settings; print(settings.DATABASE_URL)"` 确认配置可读取
- 确认 `.env` 文件中的默认值符合预期

---

### 步骤 1.4：创建前端项目

**目标**：使用 Vite + React + TypeScript 初始化前端项目

**操作指令**：
1. 在项目根目录下创建 `frontend` 目录
2. 运行 `npm create vite@latest . -- --template react-ts` 初始化项目
3. 安装核心依赖：
   ```
   npm install antd @tanstack/react-query axios zustand @uiw/react-md-editor
   npm install -D @types/react @types/react-dom
   ```
4. 创建 `frontend/.env` 文件，设置 `VITE_API_BASE_URL=http://localhost:8000/api`

**验证方法**：
- 运行 `npm run dev` 确认开发服务器可启动
- 在浏览器访问 http://localhost:5173 确认页面可加载

---

### 步骤 1.5：配置前端目录结构

**目标**：建立前端代码的组织结构

**操作指令**：
1. 在 `frontend/src/` 下创建以下目录：`api/`、`components/`、`pages/`、`hooks/`、`store/`、`types/`、`utils/`
2. 在 `frontend/src/pages/` 下创建 `Home/` 和 `Task/` 目录（各含 `index.tsx`）
3. 配置 TypeScript 路径别名（编辑 `tsconfig.json`）

**验证方法**：
- 检查目录结构是否匹配预期
- 运行 `npm run build` 确认无路径别名相关错误

---

## 第二阶段：后端核心服务

### 步骤 2.1：创建数据库连接和模型

**目标**：使用 SQLModel 配置 SQLite 数据库和任务模型

**操作指令**：
1. 在 `backend/app/` 下创建 `database.py`，配置 SQLModel 的 Engine 和 Session
2. 在 `backend/app/models/` 下创建 `task.py`，定义 `Task` 模型：
   - `id`：UUID 字符串，主键
   - `filename`：原始文件名
   - `file_path`：文件存储路径
   - `status`：状态枚举（pending、uploaded、processing、completed、failed）
   - `script`：讲解脚本内容（可选）
   - `audio_path`：音频文件路径（可选）
   - `audio_duration`：音频时长（可选，浮点数）
   - `created_at`、`updated_at`：时间戳
3. 创建 `backend/app/models/__init__.py` 导出模型

**验证方法**：
- 运行 `python -c "from app.models import Task; t = Task(filename='test.pptx'); print(t.model_dump())"` 确认模型可实例化
- 确认数据库文件在运行应用后创建

---

### 步骤 2.2：创建 PPT 解析服务

**目标**：实现从 .pptx 文件中提取文本内容的功能

**操作指令**：
1. 在 `backend/app/services/` 下创建 `ppt_service.py`
2. 实现 `extract_text_from_ppt(file_path: str) -> str` 函数：
   - 使用 `python-pptx` 打开演示文稿
   - 遍历所有幻灯片
   - 提取每个形状中的文本内容
   - 返回格式化的文本字符串（每页幻灯片用分隔符区分）
3. 添加必要的错误处理（文件不存在、不是有效 PPTX 等）

**验证方法**：
- 创建一个测试 PPT 文件
- 运行测试代码：`python -c "from app.services.ppt_service import extract_text_from_ppt; print(extract_text_from_ppt('test.pptx'))"`
- 确认输出包含所有幻灯片的文本内容

---

### 步骤 2.3：创建 LLM 服务

**目标**：实现调用 LLM API 生成讲解脚本的功能

**操作指令**：
1. 在 `backend/app/services/` 下创建 `script_service.py`
2. 创建 `generate_script(ppt_content: str) -> str` 异步函数：
   - 构建提示词（要求口语化、每页对应一段讲解）
   - 使用 `httpx` 异步调用 LLM API（支持 Claude 和智谱AI）
   - 处理 API 响应，返回生成的脚本
3. 添加 API 调用错误处理和重试逻辑
4. 创建 `backend/app/services/__init__.py` 导出服务

**验证方法**：
- 配置有效的 LLM API Key
- 运行测试：`python -c "from app.services.script_service import generate_script; import asyncio; print(asyncio.run(generate_script('测试内容')))"`
- 确认返回有效的脚本文本（非错误信息）

---

### 步骤 2.4：创建 TTS 服务

**目标**：实现使用 Edge TTS 生成音频的功能

**操作指令**：
1. 在 `backend/app/services/` 下创建 `tts_service.py`
2. 实现 `generate_audio(text: str, output_path: str) -> float` 异步函数：
   - 使用 `edge-tts` 的 `Communicate` 类
   - 指定中文字音（默认 `zh-CN-XiaoxiaoNeural`）
   - 将文本转换为音频并保存到文件
   - 返回音频文件时长（秒）
3. 实现 `get_audio_duration(audio_path: str) -> float` 函数用于获取已有音频的时长

**验证方法**：
- 创建测试文本文件
- 运行测试代码生成音频
- 确认输出文件是有效的 MP3 格式
- 确认返回的时长是合理的数值（> 0）

---

## 第三阶段：后端 API 接口

### 步骤 3.1：创建 FastAPI 应用入口

**目标**：搭建 FastAPI 主应用，配置 CORS 和静态文件服务

**操作指令**：
1. 在 `backend/app/` 下创建 `main.py`
2. 初始化 FastAPI 应用
3. 配置 CORS 中间件（允许前端跨域请求）
4. 挂载静态文件目录（用于音频文件访问）
5. 包含路由模块

**验证方法**：
- 运行 `uvicorn app.main:app --reload` 启动服务
- 访问 http://localhost:8000/docs 确认自动生成的 API 文档可访问
- 检查 CORS 响应头是否正确设置

---

### 步骤 3.2：创建任务路由

**目标**：实现任务管理的 API 端点

**操作指令**：
1. 在 `backend/app/routes/` 下创建 `tasks.py`
2. 实现以下端点：
   - `POST /api/tasks`：创建新任务（返回任务ID）
   - `GET /api/tasks`：获取任务列表
   - `GET /api/tasks/{id}`：获取单个任务详情
3. 每个端点返回符合数据模型的 JSON 响应
4. 添加路径参数校验和错误处理

**验证方法**：
- 使用 curl 或 Postman 测试每个端点：
  ```
  # 创建任务
  curl -X POST http://localhost:8000/api/tasks

  # 获取列表
  curl http://localhost:8000/api/tasks

  # 获取详情
  curl http://localhost:8000/api/tasks/{task_id}
  ```
- 确认响应状态码正确，JSON 格式符合预期

---

### 步骤 3.3：创建文件上传接口

**目标**：实现 PPT 文件上传功能

**操作指令**：
1. 在 `backend/app/routes/` 下扩展 `tasks.py`
2. 实现 `POST /api/tasks/{id}/upload` 端点：
   - 接收 multipart/form-data 的文件上传
   - 验证文件扩展名为 `.pptx`
   - 生成唯一文件名并保存到 `uploads/` 目录
   - 更新任务状态为 `uploaded`
   - 返回上传结果
3. 添加文件大小限制（建议 50MB）

**验证方法**：
- 使用 curl 测试文件上传：
  ```
  curl -X POST -F "file=@demo.pptx" http://localhost:8000/api/tasks/{id}/upload
  ```
- 确认文件保存到 `backend/static/uploads/` 目录
- 确认任务状态正确更新

---

### 步骤 3.4：创建脚本生成接口

**目标**：实现调用 LLM 生成讲解脚本的功能

**操作指令**：
1. 在 `backend/app/routes/` 下扩展 `tasks.py`
2. 实现 `POST /api/tasks/{id}/script` 端点：
   - 检查任务状态是否为 `uploaded`
   - 调用 `ppt_service` 提取 PPT 内容
   - 调用 `script_service` 生成脚本
   - 保存脚本内容到任务记录
   - 更新任务状态为 `script_ready`
   - 返回生成的脚本内容
3. 实现 `PUT /api/tasks/{id}/script` 端点用于用户编辑脚本

**验证方法**：
- 对已上传文件的任务调用脚本生成接口
- 确认返回的脚本内容与 PPT 内容相关
- 确认任务状态正确更新
- 测试更新脚本接口，确认修改生效

---

### 步骤 3.5：创建音频生成和播放接口

**目标**：实现 TTS 音频生成和流媒体播放功能

**操作指令**：
1. 在 `backend/app/routes/` 下扩展 `tasks.py`
2. 实现 `POST /api/tasks/{id}/audio` 端点：
   - 检查任务状态是否为 `script_ready`
   - 调用 `tts_service` 生成音频文件
   - 保存音频路径和时长到任务记录
   - 更新任务状态为 `audio_ready`
   - 返回音频信息
3. 实现 `GET /api/tasks/{id}/audio` 端点：
   - 返回音频文件的流媒体响应
   - 设置正确的 Content-Type（audio/mpeg）

**验证方法**：
- 对已完成脚本的任务调用音频生成接口
- 确认音频文件保存到 `backend/static/audio/` 目录
- 访问音频播放端点，确认可下载/播放音频文件

---

## 第四阶段：前端界面开发

### 步骤 4.1：配置 API 请求层

**目标**：建立前端的 API 调用机制

**操作指令**：
1. 在 `frontend/src/api/` 下创建基础 API 客户端（使用 axios）
2. 创建任务相关的 API 函数：
   - `createTask()`：创建任务
   - `uploadPPT(taskId, file)`：上传文件
   - `generateScript(taskId)`：生成脚本
   - `updateScript(taskId, script)`：更新脚本
   - `generateAudio(taskId)`：生成音频
   - `getTask(taskId)`：获取任务详情
   - `getTaskList()`：获取任务列表
3. 配置请求拦截器添加必要的 headers

**验证方法**：
- 运行前端项目，确认 API 函数可正常导入
- 使用浏览器开发者工具 Network 面板确认请求发送正确

---

### 步骤 4.2：创建类型定义

**目标**：建立 TypeScript 类型定义，确保类型安全

**操作指令**：
1. 在 `frontend/src/types/` 下创建 `index.ts`
2. 定义 `Task` 接口，包含所有字段类型
3. 定义 API 响应类型的联合类型
4. 导出所有类型供其他模块使用

**验证方法**：
- 运行 `npx tsc --noEmit` 确认无类型错误
- 在 API 函数中使用定义的类型，确认类型推断正确

---

### 步骤 4.3：创建状态管理

**目标**：使用 Zustand 管理全局状态

**操作指令**：
1. 在 `frontend/src/store/` 下创建 `useTaskStore.ts`
2. 定义任务相关状态：
   - 当前任务详情
   - 任务列表
   - 加载状态
   - 错误信息
3. 创建更新状态的方法

**验证方法**：
- 在组件中导入 store，测试状态更新
- 确认状态在不同组件间正确共享

---

### 步骤 4.4：创建首页

**目标**：实现任务列表页面

**操作指令**：
1. 在 `frontend/src/pages/Home/` 下编辑 `index.tsx`
2. 实现以下功能：
   - 使用 React Query 获取任务列表
   - 显示任务卡片列表
   - 每个卡片显示：文件名、状态、创建时间
   - 提供"新建任务"按钮跳转到任务详情页
3. 使用 Ant Design 组件（Card、Button、Tag 等）

**验证方法**：
- 运行前端项目，访问首页
- 确认任务列表正确显示
- 确认"新建任务"按钮可点击并跳转

---

### 步骤 4.5：创建任务详情页框架

**目标**：搭建任务详情页的基础结构和步骤指示器

**操作指令**：
1. 在 `frontend/src/pages/Task/` 下编辑 `index.tsx`
2. 使用 Ant Design Steps 组件创建进度指示器：
   - Step 1: 上传PPT
   - Step 2: 脚本生成/编辑
   - Step 3: 音频生成
   - Step 4: 播放音频
3. 根据当前任务状态自动高亮对应步骤
4. 根据路由参数加载对应任务

**验证方法**：
- 进入任务详情页，确认步骤指示器显示正确
- 确认当前步骤正确高亮

---

### 步骤 4.6：实现文件上传组件

**目标**：创建 PPT 文件上传界面

**操作指令**：
1. 在 `frontend/src/components/` 下创建 `UploadPanel.tsx`
2. 使用 Ant Design Upload 组件：
   - 限制上传文件类型为 `.pptx`
   - 限制文件大小（建议 50MB）
   - 显示上传进度
3. 上传成功后调用 API 更新任务状态
4. 添加拖拽上传支持

**验证方法**：
- 拖拽 PPT 文件到上传区域
- 确认上传成功，界面更新
- 尝试上传非 PPT 文件，确认被拒绝

---

### 步骤 4.7：实现脚本编辑组件

**目标**：创建脚本查看和编辑界面

**操作指令**：
1. 在 `frontend/src/components/` 下创建 `ScriptEditor.tsx`
2. 使用 `@uiw/react-md-editor` 组件：
   - 显示当前脚本内容（Markdown 格式）
   - 允许用户编辑脚本
3. 提供"生成脚本"和"保存脚本"按钮
4. 编辑器支持实时预览

**验证方法**：
- 点击"生成脚本"按钮，确认脚本内容加载
- 修改脚本内容，确认编辑器可编辑
- 保存后刷新页面，确认修改持久化

---

### 步骤 4.8：实现音频播放组件

**目标**：创建音频播放和下载界面

**操作指令**：
1. 在 `frontend/src/components/` 下创建 `AudioPlayer.tsx`
2. 使用 Ant Design Audio 组件播放音频
3. 显示音频时长信息
4. 提供下载按钮（指向音频文件 URL）
5. 添加"生成音频"按钮（如果尚未生成）

**验证方法**：
- 点击"生成音频"按钮，确认音频生成
- 确认音频播放器可播放音频
- 确认下载按钮可下载音频文件

---

## 第五阶段：集成与测试

### 步骤 5.1：配置 React Query

**目标**：设置 TanStack Query 用于数据请求和缓存

**操作指令**：
1. 在 `frontend/src/main.tsx` 中配置 QueryClient
2. 封装任务相关的查询 hooks：
   - `useTask(taskId)`：获取单个任务
   - `useTasks()`：获取任务列表
   - `useGenerateScript(taskId)`：生成脚本 mutation
   - `useGenerateAudio(taskId)`：生成音频 mutation
3. 配置合适的缓存策略

**验证方法**：
- 在组件中使用自定义 hooks
- 确认数据正确加载和缓存

---

### 步骤 5.2：配置路由

**目标**：使用 react-router-dom 配置页面路由

**操作指令**：
1. 在 `frontend/src/App.tsx` 中配置路由
2. 设置以下路由：
   - `/`：首页（任务列表）
   - `/task/:id`：任务详情页
3. 配置路由守卫（如需要登录）
4. 使用 Ant Design Layout 组件包装页面

**验证方法**：
- 测试路由跳转是否正常
- 确认 URL 参数正确传递到页面组件

---

### 步骤 5.3：端到端功能测试

**目标**：验证完整的用户流程

**操作指令**：
1. 准备一个测试用的 PPT 文件（包含 3-5 页简单内容）
2. 按以下流程执行测试：
   - 首页点击"新建任务"
   - 上传 PPT 文件，确认上传成功
   - 点击"生成脚本"，等待脚本生成
   - 编辑脚本内容并保存
   - 点击"生成音频"，等待音频生成
   - 播放音频，确认声音正常
3. 返回首页，确认任务出现在列表中

**验证方法**：
- 每个步骤完成后确认 UI 反馈正确
- 检查数据库中的任务记录状态是否按预期更新
- 检查上传目录和音频目录的文件是否正确生成

---

### 步骤 5.4：后端单元测试

**目标**：为核心服务编写单元测试

**操作指令**：
1. 在 `backend/tests/` 下创建测试文件
2. 为 `ppt_service.py` 编写测试：
   - 测试正常 PPT 文件解析
   - 测试空文件处理
   - 测试不存在的文件
3. 为 `script_service.py` 编写测试（需要 mock LLM API）
4. 为 `tts_service.py` 编写测试（需要 mock 音频生成）

**验证方法**：
- 运行 `pytest` 确认所有测试通过
- 检查测试覆盖率报告

---

### 步骤 5.5：错误处理测试

**目标**：验证系统的错误处理能力

**操作指令**：
1. 测试以下错误场景：
   - 上传非 PPT 文件
   - 上传超大文件
   - 调用不存在的任务 ID
   - 在错误的状态下调用接口（如未上传就生成脚本）
   - 模拟 LLM API 失败
   - 模拟 TTS 服务失败
2. 确认前端正确显示错误提示
3. 确认后端返回合适的 HTTP 状态码

**验证方法**：
- 每个错误场景都产生预期的错误响应
- 错误信息对用户友好

---

## 验收标准

完成本计划后，系统应满足以下验收标准：

| 功能 | 验收条件 |
|-----|---------|
| PPT 上传 | 用户可成功上传 .pptx 文件，文件保存到服务器 |
| 脚本生成 | 上传后点击生成，30 秒内返回讲解脚本 |
| 脚本编辑 | 用户可修改脚本内容并保存 |
| 音频生成 | 点击生成后，2 分钟内生成完整音频文件 |
| 音频播放 | 用户可在线播放音频，可下载音频文件 |
| 任务管理 | 用户可在首页查看历史任务列表 |

---

## 后续迭代（不在 MVP 范围内）

- PPT 预览功能
- 批量任务处理
- 多种语音选择
- 导出为视频
- 用户认证系统
