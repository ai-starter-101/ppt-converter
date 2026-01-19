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
