# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

PPT讲解生成器 - 将 PowerPoint (.pptx) 文件转换为带讲解脚本和音频的演示文稿。使用 LLM 生成讲解脚本，TTS 生成语音。

## 技术栈

- **前端**: React 18.2 + TypeScript + Ant Design 5 + Vite
- **后端**: Python 3.11 + FastAPI
- **LLM**: Claude API / 智谱AI (ChatGLM)
- **TTS**: Edge TTS
- **数据库**: SQLite (MVP)

## 常用命令

### 后端
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
pytest  # 运行测试
ruff check . && ruff format .  # 代码检查和格式化
```

### 前端
```bash
cd frontend
npm install
npm run dev
npm run build
```

## 项目结构

```
backend/
├── app/
│   ├── main.py           # FastAPI 入口
│   ├── config.py         # 配置管理
│   ├── models.py         # SQLModel 数据模型
│   ├── routes/           # API 路由 (tasks.py, files.py)
│   └── services/         # 业务逻辑 (ppt_service.py, script_service.py, tts_service.py)
├── static/uploads/       # PPT 文件存储
├── static/audio/         # 生成的音频存储
└── requirements.txt

frontend/
├── src/
│   ├── api/              # API 调用
│   ├── components/       # 共享组件
│   ├── pages/            # 页面组件 (Home/, Task/)
│   ├── hooks/            # 自定义 Hooks
│   ├── store/            # Zustand 状态管理
│   ├── types/            # TypeScript 类型定义
│   └── utils/            # 工具函数
└── package.json
```

## API 接口

| 方法 | 路径 | 描述 |
|------|------|------|
| POST | /api/tasks | 创建任务 |
| POST | /api/tasks/{id}/upload | 上传 PPT |
| POST | /api/tasks/{id}/script | 生成讲解脚本 |
| PUT | /api/tasks/{id}/script | 更新脚本 |
| POST | /api/tasks/{id}/audio | 生成音频 |
| GET | /api/tasks/{id} | 获取任务详情 |
| GET | /api/tasks | 获取任务列表 |
| GET | /api/tasks/{id}/audio | 音频流播放 |

## 环境变量

后端 (`.env`):
- `DATABASE_URL`: SQLite 连接字符串
- `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`: LLM 配置
- `TTS_VOICE`: Edge TTS 语音 (默认: `zh-CN-XiaoxiaoNeural`)
- `UPLOAD_DIR`, `AUDIO_DIR`: 存储路径

前端 (`.env`):
- `VITE_API_BASE_URL`: 后端 API 地址

## 核心服务

- **ppt_service.py**: 解析 .pptx 文件，提取幻灯片和内容
- **script_service.py**: 使用 LLM 生成讲解脚本
- **tts_service.py**: 使用 Edge TTS 将脚本转为音频

# 重要提示：
# 写任何代码前必须完整阅读 memory-bank/@architecture.md（包含完整数据库结构）
# 写任何代码前必须完整阅读 memory-bank/@product-design-document.md
# 每完成一个重大功能或里程碑后，必须更新 memory-bank/@architecture.md
