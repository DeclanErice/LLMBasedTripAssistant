"""
AG-UI Protocol 端点
提供流式 SSE 事件输出，支持 Agent 与前端的双向交互
"""

import os
import sys
import json
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, AsyncGenerator

from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from ag_ui.core import (
    EventType,
    RunStartedEvent,
    RunFinishedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    StateSnapshotEvent,
)
from ag_ui.encoder import EventEncoder

router = APIRouter()


class ConversationState:
    """会话状态管理"""

    def __init__(self):
        self.destination: str = ""
        self.days: int = 0
        self.budget: int = 0
        self.style: str = "chill"
        self.start_date: str = ""
        self.departure_city: str = ""
        self.travelers: int = 1
        self.current_step: int = 0  # 0=初始, 1=确认日期, 2=交通, 3=酒店, 4=生成

    def to_dict(self) -> Dict[str, Any]:
        return {
            "destination": self.destination,
            "days": self.days,
            "budget": self.budget,
            "style": self.style,
            "start_date": self.start_date,
            "departure_city": self.departure_city,
            "travelers": self.travelers,
            "current_step": self.current_step,
        }

    def reset(self):
        self.__init__()


class SimpleAgentInput(BaseModel):
    """简化版输入，支持 snake_case 和可选字段"""
    messages: List[Dict[str, Any]]
    thread_id: Optional[str] = "default"
    run_id: Optional[str] = "default"
    state: Optional[Dict[str, Any]] = {}


def get_rag_chain():
    """获取 RAG Chain"""
    from src.api.main import rag_chain
    return rag_chain


def get_llm_client():
    """获取 LLM 客户端"""
    from src.llm_client import get_client
    return get_client()


async def generate_conversation_flow(
    state: ConversationState,
    user_message: str,
    encoder: EventEncoder,
) -> AsyncGenerator[bytes, None]:
    """
    对话流程生成器
    """
    from src.rag import create_rag_chain
    from src.embedding import get_or_create_kb

    kb = get_or_create_kb()
    llm = get_llm_client()
    rag = create_rag_chain(kb, llm)

    async def events():
        msg_id = f"msg_{datetime.now().timestamp()}"

        if state.current_step == 0:
            state.current_step = 1

            parsed = rag.query_parser.parse(user_message)
            if parsed.get("destination"):
                state.destination = parsed["destination"]
            if parsed.get("days"):
                state.days = parsed["days"]
            if parsed.get("budget"):
                state.budget = parsed["budget"]
            if parsed.get("style"):
                state.style = parsed["style"]

            yield encoder.encode(StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                state=state.to_dict()
            ))

            yield encoder.encode(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=msg_id,
                role="assistant"
            ))

            question = f"好的，我了解了！您想去 {state.destination}，{state.days}天 {state.style} 风格。\n请问您计划几号出发呢？（例如：2026-04-20）"
            for char in question:
                yield encoder.encode(TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=msg_id,
                    delta=char
                ))

            yield encoder.encode(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=msg_id
            ))

        elif state.current_step == 1:
            state.start_date = user_message
            state.current_step = 2

            yield encoder.encode(StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                state=state.to_dict()
            ))

            msg_id = f"msg_{datetime.now().timestamp()}"
            yield encoder.encode(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=msg_id,
                role="assistant"
            ))

            question = f"好的，{state.start_date} 出发。请问您从哪个城市出发呢？我可以帮您查询交通方式。"
            for char in question:
                yield encoder.encode(TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=msg_id,
                    delta=char
                ))

            yield encoder.encode(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=msg_id
            ))

        elif state.current_step == 2:
            state.departure_city = user_message
            state.current_step = 3

            yield encoder.encode(StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                state=state.to_dict()
            ))

            msg_id = f"msg_{datetime.now().timestamp()}"
            yield encoder.encode(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=msg_id,
                role="assistant"
            ))

            transport_info = f"从 {state.departure_city} 到 {state.destination}，"
            if state.departure_city in ["北京", "上海", "广州", "深圳"]:
                transport_info += "建议乘坐高铁或飞机。航班约2-3小时，高铁约6-8小时。\n请问您更倾向于哪种交通方式？（飞机/高铁）"
            else:
                transport_info += "建议先乘坐飞机或高铁到附近大城市，再转乘。\n请问您计划怎么去呢？（飞机/高铁/自驾）"

            for char in transport_info:
                yield encoder.encode(TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=msg_id,
                    delta=char
                ))

            yield encoder.encode(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=msg_id
            ))

        elif state.current_step == 3:
            transport = user_message
            state.current_step = 4

            yield encoder.encode(StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                state=state.to_dict()
            ))

            msg_id = f"msg_{datetime.now().timestamp()}"
            yield encoder.encode(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=msg_id,
                role="assistant"
            ))

            question = f"好的，{transport}前往。请问几位入住？需要什么房型？（例如：2人，大床房）"
            for char in question:
                yield encoder.encode(TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=msg_id,
                    delta=char
                ))

            yield encoder.encode(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=msg_id
            ))

        elif state.current_step == 4:
            travelers_info = user_message
            traveler_match = re.search(r"(\d+)\s*[人位]", travelers_info)
            if traveler_match:
                state.travelers = int(traveler_match.group(1))

            yield encoder.encode(StateSnapshotEvent(
                type=EventType.STATE_SNAPSHOT,
                state=state.to_dict()
            ))

            msg_id = f"msg_{datetime.now().timestamp()}"
            yield encoder.encode(TextMessageStartEvent(
                type=EventType.TEXT_MESSAGE_START,
                message_id=msg_id,
                role="assistant"
            ))

            intro = "好的，信息已收集完毕！让我为您规划一份详细的行程...\n\n"
            for char in intro:
                yield encoder.encode(TextMessageContentEvent(
                    type=EventType.TEXT_MESSAGE_CONTENT,
                    message_id=msg_id,
                    delta=char
                ))

            yield encoder.encode(TextMessageEndEvent(
                type=EventType.TEXT_MESSAGE_END,
                message_id=msg_id
            ))

            try:
                itinerary = rag.run_with_structured_input(
                    destination=state.destination,
                    days=state.days,
                    budget=state.budget,
                    style=state.style,
                    k=3,
                )

                msg_id = f"msg_{datetime.now().timestamp()}"
                yield encoder.encode(TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START,
                    message_id=msg_id,
                    role="assistant"
                ))

                output = f"\n📍 目的地：{state.destination}\n📅 行程：{state.days}天\n💰 预算：{state.budget}元\n🎨 风格：{state.style}\n\n"
                output += "=" * 30 + "\n\n"

                if itinerary.get("title"):
                    output += f"🌟 {itinerary['title']}\n\n"

                if itinerary.get("itinerary"):
                    for day in itinerary["itinerary"]:
                        output += f"Day {day.get('day', '?')}: {day.get('theme', '')}\n"
                        if day.get("morning"):
                            output += f"  🌅 上午：{day['morning'].get('spot', '')}\n"
                        if day.get("afternoon"):
                            output += f"  🌆 下午：{day['afternoon'].get('spot', '')}\n"
                        if day.get("evening"):
                            output += f"  🌃 晚上：{day['evening'].get('spot', '')}\n"
                        if day.get("food"):
                            food_list = day['food']
                            if isinstance(food_list, list):
                                food_names = []
                                for f in food_list:
                                    if isinstance(f, dict):
                                        food_names.append(f.get('meal', ''))
                                    elif isinstance(f, str):
                                        food_names.append(f)
                                if food_names:
                                    output += f"  🍜 美食：{', '.join(food_names)}\n"
                        output += "\n"

                if itinerary.get("total_cost"):
                    output += f"\n💵 预估总费用：{itinerary['total_cost']}元"

                for char in output:
                    yield encoder.encode(TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=msg_id,
                        delta=char
                    ))

                yield encoder.encode(TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=msg_id
                ))

                state.reset()

            except Exception as e:
                msg_id = f"msg_{datetime.now().timestamp()}"
                yield encoder.encode(TextMessageStartEvent(
                    type=EventType.TEXT_MESSAGE_START,
                    message_id=msg_id,
                    role="assistant"
                ))

                error_msg = f"生成行程时遇到了一些问题：{str(e)}\n请稍后再试，或尝试调整您的需求。"
                for char in error_msg:
                    yield encoder.encode(TextMessageContentEvent(
                        type=EventType.TEXT_MESSAGE_CONTENT,
                        message_id=msg_id,
                        delta=char
                    ))

                yield encoder.encode(TextMessageEndEvent(
                    type=EventType.TEXT_MESSAGE_END,
                    message_id=msg_id
                ))

    return events


@router.post("/api/agent")
async def agent_endpoint(input_data: SimpleAgentInput, request: Request):
    """
    AG-UI Agent 端点
    """
    encoder = EventEncoder(accept=request.headers.get("accept"))

    state_data = input_data.state or {}
    state = ConversationState()
    if state_data:
        for key, value in state_data.items():
            if hasattr(state, key):
                setattr(state, key, value)

    user_message = ""
    messages = input_data.messages or []
    for msg in reversed(messages):
        role = msg.get("role", "")
        content = msg.get("content", "")
        if role == "user":
            user_message = content if isinstance(content, str) else str(content)
            break

    thread_id = input_data.thread_id or "default"
    run_id = input_data.run_id or "default"

    async def events():
        yield encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=thread_id,
            run_id=run_id
        ))

        async for event in generate_conversation_flow(state, user_message, encoder):
            yield event

        yield encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=thread_id,
            run_id=run_id
        ))

    return StreamingResponse(
        events(),
        media_type=encoder.get_content_type()
    )
