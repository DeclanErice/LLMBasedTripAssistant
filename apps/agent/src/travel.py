"""
旅行规划 Agent 状态和工具
"""

from langchain.tools import ToolRuntime, tool
from langchain.messages import ToolMessage, AnyMessage
from langgraph.types import Command
from langgraph.graph.message import add_messages
from typing import TypedDict, Literal, Optional, Required, Annotated
import requests
import os
import uuid


DEFAULT_DAYS = 3
DEFAULT_BUDGET = 5000
DEFAULT_STYLE = "chill"
SUPPORTED_STYLES = {"chill", "美食", "打卡", "出片"}


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
    plan_id: str
    destination: str
    days: int
    budget: int
    style: str
    budget_mode: Literal["fixed", "flexible"]
    start_date: str
    departure_city: str
    transport: str
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
    active_plan_id: str
    plans: dict[str, TravelRequest]
    itineraries: dict[str, ItineraryResult]
    travel_request: TravelRequest
    missing_slots: list[str]
    current_step: Literal[
        "initial",
        "collecting_days",
        "collecting_budget",
        "collecting_style",
        "collecting_date",
        "collecting_departure",
        "collecting_transport",
        "collecting_travelers",
        "generating",
        "completed",
    ]
    itinerary: Optional[ItineraryResult]


def get_rag_url() -> str:
    """获取 RAG 后端 URL"""
    return os.getenv("RAG_BACKEND_URL", "http://localhost:8000")


def _tool_call_id(runtime: Optional[ToolRuntime]) -> str:
    return getattr(runtime, "tool_call_id", "")


def _sanitize_days(days: Optional[int]) -> int:
    if days is None or days < 1 or days > 30:
        return DEFAULT_DAYS
    return days


def _sanitize_budget(budget: Optional[int]) -> int:
    if budget is None or budget <= 0:
        return DEFAULT_BUDGET
    return budget


def _normalize_style(style: Optional[str]) -> str:
    if style in SUPPORTED_STYLES:
        return style
    return DEFAULT_STYLE


def _next_question(destination: str, missing_slots: list[str]) -> tuple[str, str]:
    if not missing_slots:
        return "请问您计划几号出发呢？（例如：2026-04-20）", "collecting_date"

    slot = missing_slots[0]
    if slot == "days":
        return f"好的！我来帮您规划 {destination} 旅行。\n\n请问您计划玩几天呢？", "collecting_days"
    if slot == "budget":
        return "收到。您的整体预算是多少？（单位：元）", "collecting_budget"
    if slot == "style":
        return "明白。您喜欢什么风格的旅行？\n可选项：chill / 美食 / 打卡 / 出片", "collecting_style"

    return "请问您计划几号出发呢？（例如：2026-04-20）", "collecting_date"


def _remove_slot(missing_slots: list[str], slot: str) -> list[str]:
    return [item for item in missing_slots if item != slot]


def _update_request_value(runtime: Optional[ToolRuntime], key: str, value) -> dict:
    state = runtime.state if runtime else {}
    travel_request = dict(state.get("travel_request", {}))
    travel_request[key] = value
    return travel_request


def _progress_slot_collection(
    runtime: Optional[ToolRuntime],
    removed_slot: str,
    travel_request: dict,
    success_message: str,
) -> Command:
    state = runtime.state if runtime else {}
    current_missing = list(state.get("missing_slots", []))
    missing_slots = _remove_slot(current_missing, removed_slot)
    next_prompt, next_step = _next_question(travel_request.get("destination", ""), missing_slots)

    return Command(update={
        "travel_request": travel_request,
        "missing_slots": missing_slots,
        "current_step": next_step,
        "messages": [
            ToolMessage(
                content=f"{success_message}\n\n{next_prompt}",
                tool_call_id=_tool_call_id(runtime),
            )
        ],
    })


@tool
def start_travel_planning(
    destination: str,
    days: Optional[int] = None,
    budget: Optional[int] = None,
    style: Optional[str] = None,
    budget_mode: Literal["fixed", "flexible"] = "fixed",
    runtime: ToolRuntime = None,
) -> Command:
    """
    开始旅行规划。调用此工具后，Agent 会逐步收集信息并生成行程。

    Args:
        destination: 目的地（如：成都、日本）
        days: 行程天数（可选）
        budget: 预算（元，可选）
        style: 旅行风格（chill/美食/打卡/出片，可选）
        budget_mode: 预算模式（fixed/flexible）
    """
    if not destination:
        return Command(update={
            "messages": [
                ToolMessage(
                    content="好的，您想去哪里旅行呢？请告诉我目的地。",
                    tool_call_id=_tool_call_id(runtime),
                )
            ]
        })

    missing_slots: list[str] = []
    if days is None:
        missing_slots.append("days")
    if budget is None and budget_mode != "flexible":
        missing_slots.append("budget")
    if style is None:
        missing_slots.append("style")

    normalized_days = _sanitize_days(days)
    normalized_budget = _sanitize_budget(budget)
    normalized_style = _normalize_style(style)
    plan_id = str(uuid.uuid4())

    travel_request = TravelRequest(
        plan_id=plan_id,
        destination=destination,
        days=normalized_days,
        budget=normalized_budget,
        style=normalized_style,
        budget_mode=budget_mode,
        start_date="",
        departure_city="",
        transport="",
        travelers=1,
        room_type="",
    )

    next_prompt, next_step = _next_question(destination, missing_slots)

    if not missing_slots:
        summary = (
            f"好的！我来帮您规划 {destination} {normalized_days}天 {normalized_style} 风格旅行，"
            f"预算约 {normalized_budget} 元。\n\n{next_prompt}"
        )
    else:
        summary = next_prompt

    return Command(update={
        "active_plan_id": plan_id,
        "plans": {plan_id: travel_request},
        "itineraries": {},
        "travel_request": travel_request,
        "missing_slots": missing_slots,
        "current_step": next_step,
        "itinerary": None,
        "messages": [
            ToolMessage(
                content=summary,
                tool_call_id=_tool_call_id(runtime),
            )
        ]
    })


@tool
def confirm_days(days: int, runtime: ToolRuntime) -> Command:
    """确认天数并继续补全缺失信息。"""
    normalized_days = _sanitize_days(days)
    travel_request = _update_request_value(runtime, "days", normalized_days)
    return _progress_slot_collection(runtime, "days", travel_request, f"好的，行程天数记录为 {normalized_days} 天。")


@tool
def confirm_budget(
    budget: Optional[int] = None,
    budget_mode: Literal["fixed", "flexible"] = "fixed",
    runtime: ToolRuntime = None,
) -> Command:
    """确认预算并继续补全缺失信息。"""
    travel_request = dict(runtime.state.get("travel_request", {})) if runtime else {}

    if budget_mode == "flexible":
        travel_request["budget_mode"] = "flexible"
        travel_request["budget"] = DEFAULT_BUDGET
        message = "明白，预算按灵活模式处理，我会给您高性价比方案。"
    else:
        normalized_budget = _sanitize_budget(budget)
        travel_request["budget_mode"] = "fixed"
        travel_request["budget"] = normalized_budget
        message = f"好的，预算记录为 {normalized_budget} 元。"

    return _progress_slot_collection(runtime, "budget", travel_request, message)


@tool
def confirm_style(style: str, runtime: ToolRuntime) -> Command:
    """确认旅行风格并继续补全缺失信息。"""
    normalized_style = _normalize_style(style)
    travel_request = _update_request_value(runtime, "style", normalized_style)
    return _progress_slot_collection(runtime, "style", travel_request, f"好的，旅行风格记录为 {normalized_style}。")


@tool
def confirm_start_date(start_date: str, runtime: ToolRuntime) -> Command:
    """
    确认出发日期后，继续收集出发城市信息。
    """
    travel_request = _update_request_value(runtime, "start_date", start_date)
    return Command(update={
        "travel_request": travel_request,
        "current_step": "collecting_departure",
        "messages": [
            ToolMessage(
                content=f"好的，{start_date} 出发。\n\n请问您从哪个城市出发呢？我可以帮您查询交通方式。",
                tool_call_id=_tool_call_id(runtime),
            )
        ]
    })


@tool
def confirm_departure_city(departure_city: str, runtime: ToolRuntime) -> Command:
    """
    确认出发城市后，给出交通建议并询问偏好。
    """
    travel_request = _update_request_value(runtime, "departure_city", departure_city)
    destination = travel_request.get("destination", "目的地")
    return Command(update={
        "travel_request": travel_request,
        "current_step": "collecting_transport",
        "messages": [
            ToolMessage(
                content=f"从 {departure_city} 出发是个好选择！\n\n"
                        f"到{destination}建议乘坐高铁或飞机。\n\n"
                        f"请问您更倾向于哪种交通方式？\n"
                        f"可选项：飞机 / 高铁",
                tool_call_id=_tool_call_id(runtime),
            )
        ]
    })


@tool
def confirm_transport(transport: str, runtime: ToolRuntime) -> Command:
    """
    确认交通方式后，询问入住信息。
    """
    travel_request = _update_request_value(runtime, "transport", transport)
    return Command(update={
        "travel_request": travel_request,
        "current_step": "collecting_travelers",
        "messages": [
            ToolMessage(
                content=f"好的，{transport}前往。\n\n请问几位入住？\n房型可选：大床房 / 双床房 / 家庭房",
                tool_call_id=_tool_call_id(runtime),
            )
        ]
    })


@tool
def confirm_travelers(travelers: int, room_type: str, runtime: ToolRuntime) -> Command:
    """
    确认入住信息后，开始生成行程。
    """
    state = runtime.state if runtime else {}
    travel_request = dict(state.get("travel_request", {}))
    travel_request["travelers"] = travelers if travelers > 0 else 1
    travel_request["room_type"] = room_type

    return Command(update={
        "travel_request": travel_request,
        "current_step": "generating",
        "messages": [
            ToolMessage(
                content="好的，信息已收集完毕！让我为您规划一份详细的行程...\n\n",
                tool_call_id=_tool_call_id(runtime),
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
                active_plan_id = state.get("active_plan_id", "")
                plan_itineraries = dict(state.get("itineraries", {}))
                if active_plan_id:
                    plan_itineraries[active_plan_id] = itinerary

                return Command(update={
                    "current_step": "completed",
                    "itinerary": itinerary,
                    "itineraries": plan_itineraries,
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
        "active_plan_id": state.get("active_plan_id", ""),
        "plans": state.get("plans", {}),
        "itineraries": state.get("itineraries", {}),
        "travel_request": state.get("travel_request", {}),
        "missing_slots": state.get("missing_slots", []),
        "current_step": state.get("current_step", "initial"),
        "itinerary": state.get("itinerary"),
    }


travel_tools = [
    start_travel_planning,
    confirm_days,
    confirm_budget,
    confirm_style,
    confirm_start_date,
    confirm_departure_city,
    confirm_transport,
    confirm_travelers,
    generate_itinerary,
    get_current_state,
]
