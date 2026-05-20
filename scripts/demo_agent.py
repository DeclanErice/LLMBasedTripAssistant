"""
Agent demo: Claude uses generate_itinerary as a tool.
Run: python scripts/demo_agent.py
"""
import sys, json
sys.path.insert(0, ".")

from dotenv import load_dotenv
load_dotenv()

from src.llm_client import LLMClient

# ── example input ──────────────────────────────────────────────────────────────
EXAMPLE_INPUT = "帮我规划一个成都3天美食之旅，预算3000元"

# ── tool definition ────────────────────────────────────────────────────────────
TOOLS = [
    {
        "name": "generate_itinerary",
        "description": (
            "根据目的地、天数、预算和风格生成详细旅行行程。"
            "当用户提出旅行规划请求时调用此工具。"
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "destination": {
                    "type": "string",
                    "description": "旅行目的地，如 成都、东京",
                },
                "days": {
                    "type": "integer",
                    "description": "旅行天数",
                },
                "budget": {
                    "type": "integer",
                    "description": "总预算（人民币元）",
                },
                "style": {
                    "type": "string",
                    "enum": ["chill", "美食", "打卡", "出片"],
                    "description": "旅行风格",
                },
            },
            "required": ["destination", "days", "budget", "style"],
        },
    }
]

SYSTEM = (
    "你是一位专业旅行规划助手。"
    "当用户提出旅行规划需求时，调用 generate_itinerary 工具生成行程，"
    "然后用简洁友好的中文向用户介绍这份行程的亮点。"
)


def run_agent(user_input: str) -> None:
    wrapper = LLMClient()
    client = wrapper.client

    print(f"用户: {user_input}\n")
    print("=" * 60)

    messages = [{"role": "user", "content": user_input}]

    # ── agentic loop ───────────────────────────────────────────────────────────
    while True:
        response = client.messages.create(
            model=wrapper.model_name,
            max_tokens=4096,
            system=SYSTEM,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    print(f"[agent] calling tool: {block.name}")
                    print(f"[agent] args: {json.dumps(block.input, ensure_ascii=False)}\n")

                    result = wrapper.generate_itinerary(**block.input)

                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": json.dumps(result, ensure_ascii=False),
                    })

            messages.append({"role": "user", "content": tool_results})

        elif response.stop_reason == "end_turn":
            print("[agent] final response:\n")
            for block in response.content:
                if hasattr(block, "text"):
                    print(block.text)
            break

        else:
            print(f"[agent] unexpected stop_reason: {response.stop_reason}")
            break


if __name__ == "__main__":
    run_agent(EXAMPLE_INPUT)
