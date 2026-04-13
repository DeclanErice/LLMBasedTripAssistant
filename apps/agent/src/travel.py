"""
旅行规划 Agent 状态和工具
"""

from langchain.tools import ToolRuntime, tool
from langchain.messages import ToolMessage, AnyMessage
from langgraph.types import Command
from langgraph.graph.message import add_messages
from typing import TypedDict, Literal, Optional, Required, Annotated
import requests
import json
import os


class ItineraryDay(TypedDict):
    """每日行程"""
    day: int
    theme: str
    morning: dict
    afternoon: dict
    evening: dict
    food: list
    tips: list


class TravelRequest(TypedDict):
    """旅行请求状态"""
    destination: str
    days: int
    budget: int
    style: str
    start_date: str
    departure_city: str
    travelers: int
    room_type: str


class ItineraryResult(TypedDict):
    """生成的行程"""
    title: str
    destination: str
    days: int
    budget: int
    style: str
    itinerary: list[ItineraryDay]
    total_cost: int
    highlights: list[str]


class AgentState(TypedDict):
    """旅行规划 Agent 状态"""
    messages: Required[Annotated[list[AnyMessage], add_messages]]
    remaining_steps: int
    travel_request: TravelRequest
    current_step: Literal["initial", "collecting_date", "collecting_departure", "collecting_transport", "collecting_travelers", "generating", "completed"]
    itinerary: Optional[ItineraryResult]


def get_rag_url() -> str:
    """获取 RAG 后端 URL"""
    return os.getenv("RAG_BACKEND_URL", "http://localhost:8000")


@tool
def start_travel_planning(destination: str, days: int, budget: int, style: str, runtime: ToolRuntime) -> Command:
    """
    开始旅行规划。调用此工具后，Agent 会逐步收集信息并生成行程。

    Args:
        destination: 目的地（如：成都、日本）
        days: 行程天数
        budget: 预算（元）
        style: 旅行风格（chill/美食/打卡/出片）
    """
    travel_request = TravelRequest(
        destination=destination,
        days=days,
        budget=budget,
        style=style,
        start_date="",
        departure_city="",
        travelers=1,
        room_type="",
    )

    return Command(update={
        "travel_request": travel_request,
        "current_step": "collecting_date",
        "itinerary": None,
        "messages": [
            ToolMessage(
                content=f"好的！我来帮您规划 {destination} {days}天 {style} 风格旅行。\n\n请问您计划几号出发呢？（例如：2026-04-20）",
                tool_call_id=runtime.tool_call_id
            )
        ]
    })


@tool
def confirm_start_date(start_date: str, runtime: ToolRuntime) -> Command:
    """
    确认出发日期后，继续收集出发城市信息。
    """
    return Command(update={
        "messages": [
            ToolMessage(
                content=f"好的，{start_date} 出发。\n\n请问您从哪个城市出发呢？我可以帮您查询交通方式。",
                tool_call_id=runtime.tool_call_id
            )
        ]
    })


@tool
def confirm_departure_city(departure_city: str, runtime: ToolRuntime) -> Command:
    """
    确认出发城市后，给出交通建议并询问偏好。
    """
    return Command(update={
        "messages": [
            ToolMessage(
                content=f"从 {departure_city} 出发是个好选择！\n\n"
                        f"到成都建议乘坐高铁或飞机。\n\n"
                        f"请问您更倾向于哪种交通方式？（飞机/高铁）",
                tool_call_id=runtime.tool_call_id
            )
        ]
    })


@tool
def confirm_transport(transport: str, runtime: ToolRuntime) -> Command:
    """
    确认交通方式后，询问入住信息。
    """
    return Command(update={
        "messages": [
            ToolMessage(
                content=f"好的，{transport}前往。\n\n请问几位入住？需要什么房型？（例如：2人，大床房）",
                tool_call_id=runtime.tool_call_id
            )
        ]
    })


@tool
def confirm_travelers(travelers: int, room_type: str, runtime: ToolRuntime) -> Command:
    """
    确认入住信息后，开始生成行程。
    """
    return Command(update={
        "current_step": "generating",
        "messages": [
            ToolMessage(
                content="好的，信息已收集完毕！让我为您规划一份详细的行程...\n\n",
                tool_call_id=runtime.tool_call_id
            )
        ]
    })


@tool
def generate_itinerary(runtime: ToolRuntime) -> Command:
    """
    调用 RAG 后端生成最终行程。
    """
    state = runtime.state
    travel_request = state.get("travel_request", {})

    rag_url = get_rag_url()

    try:
        response = requests.post(
            f"{rag_url}/api/generate",
            json={
                "destination": travel_request.get("destination", ""),
                "days": travel_request.get("days", 3),
                "budget": travel_request.get("budget", 5000),
                "style": travel_request.get("style", "chill"),
            },
            timeout=120
        )

        if response.status_code == 200:
            result = response.json()
            if result.get("success"):
                itinerary = result.get("data", {})

                return Command(update={
                    "current_step": "completed",
                    "itinerary": itinerary,
                    "messages": [
                        ToolMessage(
                            content="行程已生成！请查看下方结果。",
                            tool_call_id=runtime.tool_call_id
                        )
                    ]
                })
            else:
                error_msg = result.get("error", "未知错误")
                return Command(update={
                    "messages": [
                        ToolMessage(
                            content=f"生成行程时遇到问题：{error_msg}",
                            tool_call_id=runtime.tool_call_id
                        )
                    ]
                })
        else:
            return Command(update={
                "messages": [
                    ToolMessage(
                        content=f"RAG 后端返回错误：{response.status_code}",
                        tool_call_id=runtime.tool_call_id
                    )
                ]
            })

    except requests.exceptions.ConnectionError:
        return Command(update={
            "messages": [
                ToolMessage(
                    content="无法连接到 RAG 后端服务，请确保后端正在运行（python -m uvicorn src.api.main:app --reload --port 8000）",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })
    except Exception as e:
        return Command(update={
            "messages": [
                ToolMessage(
                    content=f"生成行程时发生错误：{str(e)}",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })


@tool
def get_current_state(runtime: ToolRuntime) -> dict:
    """
    获取当前旅行规划状态。
    """
    state = runtime.state
    return {
        "travel_request": state.get("travel_request", {}),
        "current_step": state.get("current_step", "initial"),
        "itinerary": state.get("itinerary"),
    }


travel_tools = [
    start_travel_planning,
    confirm_start_date,
    confirm_departure_city,
    confirm_transport,
    confirm_travelers,
    generate_itinerary,
    get_current_state,
]
