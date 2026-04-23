"""
TripGenius 旅行规划 Agent
使用 CopilotKit + LangGraph + OpenAI

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
base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4.1-mini")

# 创建 LLM
llm = ChatOpenAI(
    model=model_name,
    api_key=api_key,
    base_url=base_url,
    temperature=0.7,
    max_retries=6,
    timeout=120,
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
        2. 如果天数/预算/风格缺失，优先逐步补全：
           - 天数缺失时调用 confirm_days
           - 预算缺失时调用 confirm_budget
           - 风格缺失时调用 confirm_style
        3. 核心信息齐全后，继续调用 confirm_start_date、confirm_departure_city、confirm_transport、confirm_travelers
        4. 收集完信息后，调用 generate_itinerary 生成最终行程

        预算规则：
        - 如果用户明确说"预算随便"、"不在意预算"，调用 confirm_budget 时使用 budget_mode="flexible"
        - 如果用户给出明确预算数字，使用 budget_mode="fixed"

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
        - 严禁向用户暴露内部推理过程、工具调用过程或函数名
        - 不要说“我要调用某工具”或“按照流程我需要”
        - 只输出面向用户的自然语言问题、确认或结果
        - 当问题存在固定备选答案时，在末尾添加“可选项：A / B / C”
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
