# 技术栈方案

## 设计原则

1. **简单优先** - 减少依赖，降低维护成本
2. **稳定可靠** - 选择成熟、社区活跃的技术
3. **最小化运维** - 优先使用托管服务

---

## 一、开发语言

| 领域 | 语言 | 选型理由 |
|-----|------|---------|
| 后端 | Python 3.11+ | 语法简洁，AI/TTS生态完善 |
| 前端 | TypeScript | 类型安全，IDE支持好 |
| 脚本/工具 | Python | 复用后端代码 |

---

## 二、后端技术栈

### 2.1 核心框架

| 包名 | 版本 | 用途 |
|-----|------|-----|
| FastAPI | ^0.109 | Web框架，自动生成API文档 |
| Uvicorn | ^0.27 | ASGI服务器 |
| pydantic | ^2.5 | 数据校验与序列化 |

### 2.2 业务依赖

| 包名 | 版本 | 用途 |
|-----|------|-----|
| python-pptx | ^0.18 | PPT解析 |
| edge-tts | ^6.1 | 文字转语音 |
| httpx | ^0.26 | HTTP客户端 |

### 2.3 文件与存储

| 包名 | 版本 | 用途 |
|-----|------|-----|
| aiofiles | ^23.0 | 异步文件操作 |
| python-dotenv | ^1.0 | 环境变量管理 |

### 2.4 数据存储

```
方案: SQLite (MVP阶段)
     ────────────────────
     Pros: 无需独立服务、零配置、单一文件
     Cons: 并发有限

     迁移路径: PostgreSQL (用户量增长后)
```

| 包名 | 版本 | 用途 |
|-----|------|-----|
| sqlmodel | ^0.0 | ORM (SQLAlchemy + Pydantic) |

### 2.5 后端目录结构

```
backend/
├── app/
│   ├── __init__.py
│   ├── main.py              # 应用入口
│   ├── config.py            # 配置管理
│   ├── models.py            # 数据模型
│   ├── database.py          # 数据库连接
│   ├── deps.py              # 依赖注入
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── tasks.py         # 任务相关API
│   │   └── files.py         # 文件相关API
│   └── services/
│       ├── __init__.py
│       ├── ppt_service.py   # PPT解析
│       ├── script_service.py # LLM调用
│       └── tts_service.py   # 音频生成
├── static/
│   ├── uploads/             # PPT文件
│   └── audio/               # 音频文件
├── tests/
├── .env
├── requirements.txt
└── run.py
```

---

## 三、前端技术栈

### 3.1 框架与基础

| 包名 | 版本 | 用途 |
|-----|------|-----|
| React | ^18.2 | UI框架 |
| TypeScript | ^5.3 | 类型安全 |
| Vite | ^5.0 | 构建工具 (比 CRA 快 10 倍) |
| Ant Design | ^5.13 | 组件库 |

### 3.2 状态与请求

| 包名 | 版本 | 用途 |
|-----|------|-----|
| TanStack Query | ^5.0 | 数据请求/缓存 |
| Axios | ^1.6 | HTTP客户端 |
| Zustand | ^4.4 | 轻量状态管理 |

### 3.3 编辑器

| 包名 | 版本 | 用途 |
|-----|------|-----|
| @uiw/react-md-editor | ^4.0 | Markdown编辑器 |

### 3.4 前端目录结构

```
frontend/
├── src/
│   ├── api/                 # API调用层
│   ├── components/          # 公共组件
│   ├── pages/               # 页面
│   │   ├── Home/            # 首页
│   │   └── Task/            # 任务详情
│   ├── hooks/               # 自定义hooks
│   ├── store/               # Zustand状态
│   ├── types/               # TypeScript类型
│   ├── utils/               # 工具函数
│   ├── App.tsx
│   └── main.tsx
├── index.html
├── package.json
├── tsconfig.json
└── vite.config.ts
```

---

## 四、外部服务

### 4.1 LLM 服务

```
选择优先级:
┌─────────────────────────────────────────────┐
│  智谱AI (ChatGLM)  ←  国内访问稳定，便宜    │
│       ↓                                      │
│  Claude API          ←  效果好，全球可用     │
│       ↓                                      │
│  OpenAI GPT-4        ←  备选                 │
└─────────────────────────────────────────────┘
```

### 4.2 TTS 服务

```
Edge TTS (微软)  ←  免费、效果好、无需API Key
                 缺点: 国内网络可能不稳定

备选方案:
├── Azure TTS          ←  稳定，需付费
└── 阿里云语音合成     ←  国内访问稳定
```

---

## 五、文件存储

```
方案: 本地文件系统 (MVP阶段)
     ─────────────────────────
     uploads/    → PPT源文件
     audio/      → 生成的音频

     备份策略: 定期打包下载
```

**未来迁移方向:**
- 对象存储: 阿里云 OSS / AWS S3
- CDN: 阿里云 CDN / Cloudflare

---

## 六、部署架构

### 6.1 开发环境

```bash
# 后端
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# 前端
cd frontend
npm install
npm run dev
```

### 6.2 生产环境

```
                    ┌─────────────────┐
                    │    Nginx        │
                    │  (80/443端口)   │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                             │
              ▼                             ▼
    ┌─────────────────┐           ┌─────────────────┐
    │   前端静态资源   │           │  后端 API 服务   │
    │   (Nginx托管)   │  ◄────►   │  (Gunicorn)     │
    └─────────────────┘           └─────────────────┘
                                             │
                                      ┌──────┴──────┐
                                      │             │
                                      ▼             ▼
                            ┌─────────────┐  ┌─────────────┐
                            │  SQLite     │  │  文件存储    │
                            │  (数据)     │  │  (uploads/  │
                            │             │  │   audio/)   │
                            └─────────────┘  └─────────────┘
```

### 6.3 Docker 部署 (可选)

```dockerfile
# backend/Dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    volumes:
      - ./backend/uploads:/app/uploads
      - ./backend/audio:/app/audio
    env_file:
      - ./backend/.env

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
    volumes:
      - ./frontend/dist:/usr/share/nginx/html
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
```

---

## 七、环境变量

### 7.1 后端 .env 示例

```bash
# Server
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Database
DATABASE_URL=sqlite+aiosqlite:///./data/app.db

# LLM
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=claude-3-sonnet-20240229

# TTS
TTS_VOICE=zh-CN-XiaoxiaoNeural

# Paths
UPLOAD_DIR=./uploads
AUDIO_DIR=./static/audio
STATIC_DIR=./static
```

### 7.2 前端 .env 示例

```bash
VITE_API_BASE_URL=http://localhost:8000/api
```

---

## 八、开发工具

| 工具 | 用途 |
|-----|------|
| Git | 版本控制 |
| ruff | Python 代码检查/格式化 |
| pytest | 后端单元测试 |
| React Testing Library | 前端组件测试 |
| Postman / Insomnia | API 测试 |

---

## 九、依赖清单汇总

### requirements.txt

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

### package.json (核心依赖)

```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "antd": "^5.13.0",
    "@tanstack/react-query": "^5.0.0",
    "axios": "^1.6.0",
    "zustand": "^4.4.0",
    "@uiw/react-md-editor": "^4.0.0"
  },
  "devDependencies": {
    "typescript": "^5.3.0",
    "vite": "^5.0.0",
    "@types/react": "^18.2.0",
    "@types/react-dom": "^18.2.0"
  }
}
```

---

## 十、技术选型总结

| 层级 | 选择 | 理由 |
|-----|------|-----|
| 后端框架 | FastAPI | 异步高性能、自动文档、类型提示完善 |
| 前端框架 | React + Vite | 开发快、体积小、TS支持好 |
| UI库 | Ant Design | 组件丰富、文档完善、拿来即用 |
| 数据库 | SQLite → PostgreSQL | MVP简单、扩展平滑 |
| LLM | 智谱AI / Claude | 效果好、性价比高 |
| TTS | Edge TTS | 免费、效果好 |
| 部署 | Nginx + Gunicorn | 成熟稳定、配置简单 |
| 文件存储 | 本地文件系统 | MVP阶段足够、未来可迁移OSS |

---

## 十一、风险与应对

| 风险 | 级别 | 应对措施 |
|-----|------|---------|
| Edge TTS 网络不稳定 | 中 | 提供 Azure TTS 降级选项 |
| SQLite 并发限制 | 低 | 后期迁移 PostgreSQL |
| LLM API 限流 | 中 | 添加请求队列、缓存机制 |
| 大文件存储 | 低 | 限制单文件 50MB，迁移 OSS |
