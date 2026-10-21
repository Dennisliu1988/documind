# FastAPI 启动入口（只做挂载，不写业务逻辑）
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import chat, document

app = FastAPI(title="DocuMind API")

# 跨域
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 挂载路由
app.include_router(document.router, prefix="/api/doc", tags=["文档管理"])
app.include_router(chat.router, prefix="/api", tags=["对话"])

# 挂载前端静态目录
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def index():
    # 返回前端页面
    return FileResponse("static/index.html")

@app.get("/health")
async def health():
    return {"status": "ok"}