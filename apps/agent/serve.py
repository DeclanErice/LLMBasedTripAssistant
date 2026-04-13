"""
TripGenius Agent 服务入口
LangGraph agent 需要通过 langgraph-cli 启动

如果要用 uvicorn 直接运行，代理端口到 langgraph-api
"""

import os
import subprocess
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

def start_langgraph_api():
    """启动 langgraph-api 代理"""
    port = os.getenv("LANGGRAPH_API_PORT", "8123")
    langgraph_url = os.getenv("LANGGRAPH_DEPLOYMENT_URL", "http://localhost:8123")

    print(f"请使用 langgraph-cli 启动 agent:")
    print(f"  cd apps/agent")
    print(f"  npx langgraph dev --port {port}")
    print(f"或直接运行: python -m uvicorn main:app --port {port}")

if __name__ == "__main__":
    start_langgraph_api()
