"""
LLM 客户端封装（Anthropic Claude API）
文档: https://docs.anthropic.com/en/api
"""

import os
import json
from typing import Optional, List, Dict, Any, Generator
import anthropic
from dotenv import load_dotenv

load_dotenv()


class LLMClient:
    """LLM 调用封装（Anthropic Claude）"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model_name = os.getenv("ANTHROPIC_MODEL_NAME", "claude-opus-4-7")

        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        self.client = anthropic.Anthropic(api_key=self.api_key)

    def chat(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 2048,
    ) -> str:
        """
        发送对话请求

        Args:
            messages: 消息列表，支持 system/user/assistant 角色
            model: 模型名称，缺省走环境变量 ANTHROPIC_MODEL_NAME
            max_tokens: 最大输出 token 数

        Returns:
            模型生成的文本
        """
        system_prompt, chat_messages = self._split_messages(messages)

        kwargs: Dict[str, Any] = dict(
            model=model or self.model_name,
            max_tokens=max_tokens,
            messages=chat_messages,
        )
        if system_prompt:
            kwargs["system"] = system_prompt

        response = self.client.messages.create(**kwargs)
        return response.content[0].text if response.content else ""

    def chat_stream(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 2048,
    ) -> Generator[str, None, None]:
        """
        流式对话请求

        Yields:
            生成的文本片段
        """
        system_prompt, chat_messages = self._split_messages(messages)

        kwargs: Dict[str, Any] = dict(
            model=model or self.model_name,
            max_tokens=max_tokens,
            messages=chat_messages,
        )
        if system_prompt:
            kwargs["system"] = system_prompt

        with self.client.messages.stream(**kwargs) as stream:
            for text in stream.text_stream:
                yield text

    def generate_itinerary(
        self,
        destination: str,
        days: int,
        budget: int,
        style: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成旅行行程
        """
        system_prompt = """你是一位专业的旅行规划师，擅长根据用户的需求生成个性化的旅行行程。

旅行风格说明:
- chill: 轻松休闲游，享受慢生活
- 美食: 以品尝当地美食为主要目的
- 打卡: 必去网红景点，拍照留念
- 出片: 摄影之旅，寻找最美角度

请根据用户需求，生成一份详细的行程规划，包含每日的景点、餐饮和注意事项。"""

        user_prompt = f"请为我规划一次 {destination} {days}天 {budget}元预算的 {style} 风格旅行。\n\n"

        if context:
            user_prompt += f"以下是一些相关的旅行信息供参考:\n{context}\n"

        user_prompt += """
请以JSON格式返回行程，格式如下:
{
    "title": "行程标题",
    "destination": "目的地",
    "days": 天数,
    "budget": 预算,
    "style": "风格",
    "itinerary": [
        {
            "day": 1,
            "morning": "上午安排",
            "afternoon": "下午安排",
            "evening": "晚上安排",
            "food": ["推荐美食"],
            "tips": ["小贴士"]
        }
    ],
    "total_cost": 总花费估算,
    "highlights": ["行程亮点"]
}
"""

        create_kwargs: Dict[str, Any] = dict(
            model=self.model_name,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        if self._supports_thinking():
            create_kwargs["thinking"] = {"type": "adaptive"}

        response_text = self.client.messages.create(**create_kwargs)
        text = ""
        for block in response_text.content:
            if block.type == "text":
                text = block.text
                break

        try:
            return json.loads(self._extract_json(text))
        except json.JSONDecodeError:
            pass

        return {"title": f"{destination} {days}日行程", "raw": text}

    def parse_intent(self, user_input: str) -> Dict[str, Any]:
        """
        解析用户输入，提取旅行意图
        """
        prompt = f"""请从以下用户输入中提取旅行相关信息:

"{user_input}"

请以JSON格式返回:
{{
    "destination": "目的地（如无法识别则为空字符串）",
    "days": 天数（如无法识别则为0）,
    "budget": 预算（如无法识别则为0）,
    "style": "风格（chill/美食/打卡/出片，或为空）",
    "original_text": "原始输入"
}}

只返回JSON，不要其他文字。"""

        response = self.client.messages.create(
            model=self.model_name,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text if response.content else ""

        try:
            return json.loads(self._extract_json(text))
        except json.JSONDecodeError:
            return {
                "destination": "",
                "days": 0,
                "budget": 0,
                "style": "",
                "original_text": user_input,
            }

    def _extract_json(self, text: str) -> str:
        """Strip markdown code fences then find the outermost JSON object."""
        import re
        # strip ```json ... ``` or ``` ... ``` fences
        text = re.sub(r"^```[^\n]*\n?", "", text.strip())
        text = re.sub(r"\n?```$", "", text.strip())
        start = text.find("{")
        end = text.rfind("}") + 1
        if start >= 0 and end > start:
            return text[start:end]
        return text

    def _supports_thinking(self) -> bool:
        """Adaptive thinking is only available on Opus 4.6+, Sonnet 4.6+"""
        m = self.model_name.lower()
        return any(x in m for x in ("opus-4", "sonnet-4-6", "sonnet-4-7"))

    def _split_messages(
        self, messages: List[Dict[str, str]]
    ) -> tuple[str, List[Dict[str, str]]]:
        """将 system 消息从消息列表中分离出来"""
        system_parts: List[str] = []
        chat_messages: List[Dict[str, str]] = []
        for msg in messages:
            if msg["role"] == "system":
                system_parts.append(msg["content"])
            else:
                chat_messages.append(msg)
        return "\n\n".join(system_parts), chat_messages


def get_client() -> LLMClient:
    """获取 LLM 客户端单例"""
    return LLMClient()
