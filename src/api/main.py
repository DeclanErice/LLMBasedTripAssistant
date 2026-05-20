"""
FastAPI 后端服务主文件
"""

import os
import sys
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.api.routes import router as api_router
from src.api.ag_ui_routes import router as ag_ui_router
from src.embedding import get_or_create_kb
from src.llm_client import get_client
from src.rag import create_rag_chain

# 加载环境变量
load_dotenv()

# 全局变量
kb_instance = None
llm_client = None
rag_chain = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    global kb_instance, llm_client, rag_chain

    # 启动时初始化
    print("Initializing TripGenius...")

    # 初始化知识库
    try:
        kb_instance = get_or_create_kb()
        print("Knowledge base loaded")
    except Exception as e:
        print(f"Warning: Failed to load knowledge base: {e}")

    # 初始化LLM客户端
    try:
        llm_client = get_client()
        print("LLM client initialized")
    except Exception as e:
        print(f"Warning: Failed to initialize LLM client: {e}")

    # 初始化RAG Chain
    if kb_instance and llm_client:
        rag_chain = create_rag_chain(kb_instance, llm_client)
        print("RAG chain initialized")

    print("TripGenius ready!")

    yield

    # 关闭时清理
    print("Shutting down TripGenius...")


# 创建FastAPI应用
app = FastAPI(
    title="TripGenius API",
    description="AI Travel Guide Generator API",
    version="0.1.0",
    lifespan=lifespan,
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router, prefix="/api")
app.include_router(ag_ui_router)


@app.get("/")
async def root():
    """根路径健康检查"""
    return {
        "name": "TripGenius",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health():
    """健康检查端点"""
    return {
        "status": "healthy",
        "knowledge_base": kb_instance is not None,
        "llm_client": llm_client is not None,
        "rag_chain": rag_chain is not None,
    }


def start_server(host: str = "0.0.0.0", port: int = 8000):
    """启动服务器"""
    uvicorn.run(
        "src.api.main:app",
        host=host,
        port=port,
        reload=True,
    )


if __name__ == "__main__":
    start_server()
