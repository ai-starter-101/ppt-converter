# PPT讲解生成器 - 产品设计文档

## 1. 项目概述

### 1.1 产品定位
一个帮助用户将PPT转换为带讲解脚本和音频的演示材料的工具。

### 1.2 核心价值
- 自动分析PPT内容生成讲解脚本
- 支持用户编辑和定制讲解内容
- 一键生成讲解音频
- 支持在线播放讲解音频

### 1.3 技术栈
- **前端**: React + Ant Design
- **后端**: Python + FastAPI
- **LLM**: Claude API / 智谱API
- **TTS**: Edge TTS

---

## 2. 功能需求

### 2.1 MVP 功能列表

| 功能模块 | 功能描述 | 优先级 |
|---------|---------|-------|
| PPT上传 | 上传 .pptx 文件 | P0 |
| 脚本生成 | 调用LLM生成讲解脚本 | P0 |
| 脚本编辑 | 用户在线编辑脚本内容 | P0 |
| 音频生成 | 使用Edge TTS生成音频 | P0 |
| 音频播放 | 在线播放生成的音频 | P0 |
| 文件管理 | 查看历史上传记录 | P1 |

---

## 3. 系统架构

### 3.1 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                      前端 (React)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐ │
│  │ 文件上传  │  │ 脚本编辑  │  │ 音频播放  │  │ 历史记录  │ │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘ │
└─────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────┐
│                    后端 (FastAPI)                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐              │
│  │ PPT解析   │  │ LLM调用  │  │ TTS合成  │              │
│  └──────────┘  └──────────┘  └──────────┘              │
└─────────────────────────────────────────────────────────┘
                           │
            ┌──────────────┼──────────────┐
            ▼              ▼              ▼
      ┌──────────┐  ┌──────────┐  ┌──────────┐
      │ 文件存储  │  │ LLM API  │  │ Edge TTS │
      └──────────┘  └──────────┘  └──────────┘
```

### 3.2 数据库设计

```sql
-- 任务表：存储PPT转换任务
CREATE TABLE tasks (
    id VARCHAR(36) PRIMARY KEY,          -- 任务ID (UUID)
    filename VARCHAR(255),               -- 原始文件名
    file_path VARCHAR(500),              -- 文件存储路径
    status VARCHAR(20),                  -- 状态: pending/processing/completed/failed
    script TEXT,                         -- 讲解脚本内容
    audio_path VARCHAR(500),             -- 音频文件路径
    audio_duration FLOAT,                -- 音频时长(秒)
    created_at TIMESTAMP,                -- 创建时间
    updated_at TIMESTAMP                 -- 更新时间
);
```

---

## 4. API 设计

### 4.1 API 列表

| 方法 | 路径 | 功能 |
|-----|------|-----|
| POST | /api/tasks | 创建转换任务 |
| POST | /api/tasks/{id}/upload | 上传PPT文件 |
| POST | /api/tasks/{id}/script | 生成讲解脚本 |
| PUT | /api/tasks/{id}/script | 更新脚本内容 |
| POST | /api/tasks/{id}/audio | 生成音频 |
| GET | /api/tasks/{id} | 获取任务详情 |
| GET | /api/tasks | 获取任务列表 |
| GET | /api/tasks/{id}/audio | 获取音频文件 |

### 4.2 接口详细设计

#### 4.2.1 创建任务并上传PPT
```
POST /api/tasks/{id}/upload
Content-Type: multipart/form-data

Request:
  file: .pptx文件

Response:
  {
    "id": "task-uuid",
    "filename": "demo.pptx",
    "status": "uploaded",
    "message": "文件上传成功"
  }
```

#### 4.2.2 生成讲解脚本
```
POST /api/tasks/{id}/script

Response:
  {
    "id": "task-uuid",
    "script": "# 幻灯片1\n\n各位好，今天我们要介绍...",
    "status": "script_ready"
  }
```

#### 4.2.3 生成音频
```
POST /api/tasks/{id}/audio

Response:
  {
    "id": "task-uuid",
    "audio_path": "/static/audio/task-uuid.mp3",
    "audio_duration": 120.5,
    "status": "audio_ready"
  }
```

---

## 5. 前端设计

### 5.1 页面结构

```
pages/
├── HomePage              # 任务列表页
│   ├── 任务卡片列表
│   └── 新建任务按钮
├── TaskDetailPage        # 任务详情页
│   ├── Step 1: 上传PPT
│   ├── Step 2: 脚本生成/编辑
│   ├── Step 3: 音频生成
│   └── Step 4: 播放音频
```

### 5.2 核心组件

| 组件名 | 功能描述 |
|-------|---------|
| UploadPanel | PPT文件上传 |
| ScriptEditor | 脚本编辑区（Markdown编辑器） |
| AudioPlayer | 音频播放器 |
| TaskCard | 任务卡片 |
| StepProgress | 步骤进度指示器 |

### 5.3 用户流程

```
┌──────────────────────────────────────────────────────────┐
│  1. 上传PPT  →  2. 生成脚本  →  3. 编辑脚本  →  4. 生成音频  │
│      ↓             ↓              ↓              ↓        │
│  [上传区域]    [LLM生成]      [在线编辑]     [Edge TTS]   │
│                                                              │
│                                      →  5. 播放音频          │
│                                             ↓              │
│                                      [音频播放器]           │
└──────────────────────────────────────────────────────────┘
```

---

## 6. 后端实现

### 6.1 目录结构

```
backend/
├── app/
│   ├── main.py              # FastAPI入口
│   ├── api/
│   │   └── routes.py        # API路由
│   ├── services/
│   │   ├── ppt_service.py   # PPT解析服务
│   │   ├── llm_service.py   # LLM调用服务
│   │   └── tts_service.py   # TTS合成服务
│   ├── models/
│   │   └── task.py          # 数据模型
│   └── utils/
│       └── file_util.py     # 文件工具
├── static/
│   └── audio/               # 音频文件存储
├── uploads/                 # PPT文件存储
└── requirements.txt
```

### 6.2 核心服务

#### 6.2.1 PPT解析服务
```python
# 使用 python-pptx 解析PPT
from pptx import Presentation

def extract_text_from_ppt(file_path: str) -> str:
    prs = Presentation(file_path)
    text_content = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                for paragraph in shape.text_frame.paragraphs:
                    text_content.append(paragraph.text)
    return "\n".join(text_content)
```

#### 6.2.2 LLM服务
```python
# 调用Claude/智谱API生成脚本
async def generate_script(ppt_content: str) -> str:
    prompt = f"""
请根据以下PPT内容，生成一份讲解脚本。

PPT内容：
{ppt_content}

要求：
1. 脚本要口语化，适合演讲
2. 每页PPT对应一段讲解
3. 保持专业但易懂
"""
    # 调用API返回脚本内容
```

#### 6.2.3 TTS服务
```python
# 使用 edge-tts 生成音频
import asyncio
from edge_tts import Communicate

async def generate_audio(text: str, output_path: str) -> float:
    communicate = Communicate(text, voice="zh-CN-XiaoxiaoNeural")
    await communicate.save(output_path)
    # 返回音频时长
```

---

## 7. 依赖清单

### 7.1 后端依赖
```
fastapi==0.109.0
uvicorn[standard]==0.27.0
python-multipart==0.0.6
python-pptx==0.18.2
edge-tts==6.1.0
httpx==0.26.0
python-dotenv==1.0.0
```

### 7.2 前端依赖
```
react==18.2.0
antd==5.13.0
axios==1.6.0
react-router-dom==6.21.0
@uiw/react-md-editor==4.0.0
```

---

## 8. 部署方案

### 8.1 开发环境
- 后端: `uvicorn app.main:app --reload`
- 前端: `npm run dev`

### 8.2 生产环境
- 前端: Nginx 反向代理
- 后端: Gunicorn + Uvicorn
- 文件存储: 本地文件系统

---

## 9. 里程碑

### Phase 1: MVP (当前版本)
- [x] PPT上传功能
- [x] 脚本生成与编辑
- [x] 音频生成与播放

### Phase 2: 后续迭代
- [ ] PPT预览功能
- [ ] 批量任务处理
- [ ] 多种语音选择
- [ ] 导出为视频

---

## 10. 风险与应对

| 风险 | 影响 | 应对措施 |
|-----|-----|---------|
| PPT解析失败 | 功能不可用 | 提示用户检查文件格式 |
| LLM API调用失败 | 无法生成脚本 | 添加重试机制和错误提示 |
| Edge TTS不稳定 | 音频生成失败 | 降级方案或备用TTS服务 |
| 大文件上传超时 | 上传中断 | 增加文件大小限制和超时配置 |

---

## 11. 验收标准

1. 用户可以成功上传 .pptx 文件
2. 上传后可以触发脚本生成
3. 用户可以编辑生成的脚本
4. 点击生成音频后可以下载/播放音频文件
5. 整个流程操作流畅，无明显卡顿
