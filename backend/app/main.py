"""FastAPI 应用入口"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.config import settings
from app.database import init_db
from app.routes import router as tasks_router

# 创建 FastAPI 应用
app = FastAPI(
    title="PPT 讲解生成器 API",
    description="将 PowerPoint 转换为带讲解脚本和音频的演示材料",
    version="1.0.0",
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory=str(settings.static_dir)), name="static")

# 注册路由
app.include_router(tasks_router)


@app.on_event("startup")
async def startup_event():
    """应用启动时初始化数据库"""
    init_db()
    print("数据库初始化完成")


@app.get("/")
async def root():
    """根路径健康检查"""
    return {"status": "ok", "message": "PPT 讲解生成器 API"}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy"}
