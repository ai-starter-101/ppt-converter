# 架构文档

> 说明后端每个文件的作用和职责

## 后端目录结构

```
backend/
├── app/                          # FastAPI 应用主包
│   ├── __init__.py               # 包标识
│   ├── main.py                   # FastAPI 应用入口，配置 CORS 和静态文件服务
│   ├── config.py                 # 配置管理，读取 .env 环境变量
│   ├── database.py               # 数据库连接配置 (SQLModel Engine & Session)
│   ├── deps.py                   # 依赖注入 (如 get_db, get_current_task)
│   ├── routes/                   # API 路由
│   │   ├── __init__.py
│   │   ├── tasks.py              # 任务相关 API：创建/查询任务、上传/生成/播放
│   │   └── files.py              # 文件相关 API (如需独立文件管理)
│   ├── services/                 # 业务逻辑层
│   │   ├── __init__.py
│   │   ├── ppt_service.py        # PPT 解析：提取 .pptx 文本内容
│   │   ├── script_service.py     # LLM 服务：调用 Claude/智谱AI 生成脚本
│   │   └── tts_service.py        # TTS 服务：使用 Edge TTS 生成音频
│   ├── models/                   # 数据模型
│   │   ├── __init__.py
│   │   └── task.py               # Task 模型定义
│   └── utils/                    # 工具函数
│       └── __init__.py
├── static/                       # 静态文件目录 (由 FastAPI 托管)
│   ├── uploads/                  # 上传的 .pptx 文件
│   └── audio/                    # 生成的 .mp3 音频文件
├── tests/                        # 单元测试
│   └── __init__.py
├── requirements.txt              # Python 依赖清单
├── .env                          # 环境变量配置
└── run.py                        # 启动脚本 (可选)
```

## 核心文件职责

### app/main.py
- FastAPI 应用初始化
- CORS 中间件配置
- 静态文件挂载 (`/static` 前缀)
- 路由注册

### app/config.py
- 使用 `python-dotenv` 读取环境变量
- 导出配置类 (`Settings`)，包含：
  - `DATABASE_URL`: SQLite 连接字符串
  - `LLM_*`: LLM API 配置
  - `TTS_VOICE`: Edge TTS 语音
  - `*_DIR`: 文件存储路径

### app/database.py
- 创建 `sqlmodel` 的 `Engine`
- 创建 `SessionLocal` 依赖
- 初始化数据库表

### app/models/task.py
- `Task` 模型：
  - `id`: UUID 字符串，主键
  - `filename`: 原始文件名
  - `file_path`: PPT 文件路径
  - `status`: 任务状态
  - `script`: 讲解脚本内容
  - `audio_path`: 音频文件路径
  - `audio_duration`: 音频时长
  - `created_at` / `updated_at`: 时间戳

### app/services/ppt_service.py
- `extract_text_from_ppt(file_path: str) -> str`
- 遍历 PPT 所有幻灯片，提取文本内容
- 返回格式化的文本字符串

### app/services/script_service.py
- `generate_script(ppt_content: str) -> str`
- 构建 LLM prompt，调用 API
- 支持 Claude / 智谱AI 两种 provider

### app/services/tts_service.py
- `generate_audio(text: str, output_path: str) -> float`
- 使用 Edge TTS 生成音频
- 返回音频时长

### app/routes/tasks.py
- `POST /api/tasks`: 创建任务
- `GET /api/tasks`: 任务列表
- `GET /api/tasks/{id}`: 任务详情
- `POST /api/tasks/{id}/upload`: 上传 PPT
- `POST /api/tasks/{id}/script`: 生成脚本
- `PUT /api/tasks/{id}/script`: 更新脚本
- `POST /api/tasks/{id}/audio`: 生成音频
- `GET /api/tasks/{id}/audio`: 音频流播放
