"""
TripGenius 旅行规划 Agent
使用 CopilotKit + LangGraph + MiniMax (OpenAI 兼容)

直接运行: python -m uvicorn main:app --port 8123 --host 0.0.0.0
"""

import os
import json
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langgraph.prebuilt import create_react_agent
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware

from src.travel import travel_tools, AgentState

# 加载环境变量
load_dotenv()

# 获取配置
api_key = os.getenv("OPENAI_API_KEY", "")
base_url = os.getenv("OPENAI_BASE_URL", "https://api.minimax.io/v1")
model_name = os.getenv("OPENAI_MODEL_NAME", "MiniMax-M2.7")

# 创建 LLM（使用 OpenAI 兼容接口连接 MiniMax）
llm = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url=base_url,
    temperature=0.7,
)

# 使用 create_react_agent 创建 agent
agent = create_react_agent(
    model=llm,
    tools=travel_tools,
    state_schema=AgentState,
    prompt="""
        你是一位专业的旅行规划师，擅长根据用户的需求生成个性化的旅行行程。

        用户交互流程：
        1. 用户说"我想去X"时，调用 start_travel_planning 开始规划
        2. 根据用户的回复，逐步调用 confirm_start_date、confirm_departure_city、confirm_transport、confirm_travelers
        3. 收集完信息后，调用 generate_itinerary 生成最终行程

        旅行风格说明：
        - chill: 轻松休闲游，享受慢生活
        - 美食: 以品尝当地特色美食为主
        - 打卡: 必去网红景点，拍照留念
        - 出片: 摄影之旅，寻找最美角度

        重要：
        - 每次只问一个问题
        - 使用中文回复
        - 行程生成后，告诉用户查看结果
        - 如果后端连接失败，提醒用户启动 RAG 后端
    """,
)

# 创建 FastAPI ASGI app
app = FastAPI(title="TripGenius Agent")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/invoke")
async def invoke(request: Request):
    """CopilotKit 调用的端点"""
    body = await request.json()
    messages = body.get("messages", [])

    async def stream():
        async for event in agent.astream_events(
            {"messages": messages},
            config={"configurable": {"model": model_name}}
        ):
            if event["event"] == "on_chat_model_stream":
                content = event["data"]["chunk"].content
                if content:
                    yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream")

@app.get("/health")
async def health():
    return {"status": "ok"}
