"""
Generator - LLM生成模块
负责根据检索结果和用户query生成旅行行程
"""

import json
from typing import Dict, Any, List, Optional


class TravelGenerator:
    """旅行行程生成器"""

    def __init__(self, llm_client):
        """
        初始化生成器

        Args:
            llm_client: LLM客户端（LLMClient）
        """
        self.llm_client = llm_client

    def generate(
        self,
        destination: str,
        days: int,
        budget: int,
        style: str,
        context: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        生成旅行行程

        Args:
            destination: 目的地
            days: 天数
            budget: 预算
            style: 旅行风格
            context: 额外的上下文信息（检索到的内容）

        Returns:
            生成的行程JSON
        """
        system_prompt = """你是一位专业的旅行规划师，擅长根据用户的需求生成个性化的旅行行程。

你需要了解以下旅行风格的特点：
- chill/休闲：轻松自在，享受慢生活，不赶行程
- 美食：重点品尝当地特色美食，可以为了美食特意安排
- 打卡：必去网红景点，拍照留念，行程紧凑
- 出片：寻找最美的拍照角度和景点，摄影之旅

预算等级说明：
- low/穷游：2000-4000元，主打经济实惠
- mid/轻奢：5000-8000元，品质与性价比兼顾
- high/土豪：10000元以上，追求最佳体验

请生成一份详细、实用、有特色的旅行行程规划。"""

        style_tip = self._get_style_tip(style)
        budget_tip = self._get_budget_tip(budget)

        user_prompt = f"""请为我规划一次 {destination} {days}天 {budget}元预算的 {style} 风格旅行。

行程要求：
1. 每天的景点安排要合理，不要太赶
2. 同一天的景点尽量按地理位置就近安排，减少不必要的折返，上午→下午→晚上的顺序要符合实际交通逻辑
3. 包含餐饮推荐（早餐/午餐/晚餐）
4. 每项活动给出大致花费
5. 包含实用的小贴士（注意事项、最佳游览时间等）

{style_tip}

{budget_tip}

"""

        if context:
            user_prompt += f"\n以下是一些相关的旅行参考资料:\n{context}\n"

        user_prompt += """
请以JSON格式返回行程，格式如下:
{
    "title": "行程标题（如：东京5日赏樱之旅）",
    "destination": "目的地",
    "days": 天数,
    "budget": 预算,
    "style": "风格",
    "itinerary": [
        {
            "day": 1,
            "theme": "今日主题",
            "morning": {"spot": "景点", "tips": "建议", "cost": 0},
            "afternoon": {"spot": "景点", "tips": "建议", "cost": 0},
            "evening": {"spot": "活动", "tips": "建议", "cost": 0},
            "food": [{"meal": "早餐", "place": "推荐地点", "cost": 0}, ...],
            "daily_cost": 当日总花费,
            "tips": ["注意事项1", "注意事项2"]
        }
    ],
    "total_cost": 总花费估算,
    "cost_breakdown": {"交通": 0, "住宿": 0, "餐饮": 0, "门票": 0, "其他": 0},
    "highlights": ["行程亮点1", "亮点2"],
    "warnings": ["需要注意的事项"]
}
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response_text = self.llm_client.chat(messages, temperature=0.7, max_tokens=4096)

        # 尝试解析JSON
        try:
            # 尝试提取JSON部分
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1
            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError:
            pass

        # 如果解析失败，返回原始文本
        return {
            "title": f"{destination} {days}日行程",
            "destination": destination,
            "days": days,
            "budget": budget,
            "style": style,
            "raw_response": response_text,
        }

    def _get_style_tip(self, style: str) -> str:
        """获取风格提示"""
        tips = {
            "chill": "风格要求：行程轻松休闲，留出充足的休息和慢慢游玩的时间。",
            "美食": "风格要求：重点安排当地特色美食体验，包括早茶、夜市、路边摊等。",
            "打卡": "风格要求：选择热门必打卡的景点，行程紧凑，拍照优先。",
            "出片": "风格要求：选择风景优美、拍照好看的地点，注意最佳拍摄时间。",
        }
        return tips.get(style, "")

    def _get_budget_tip(self, budget: int) -> str:
        """获取预算提示"""
        if budget < 3000:
            return "预算说明：穷游预算，主打经济实惠，优先选择青旅和当地小吃。"
        elif budget < 6000:
            return "预算说明：中等预算，品质与性价比兼顾，适当享受但不浪费。"
        else:
            return "预算说明：高预算，追求最佳体验，可以选择高端住宿和餐厅。"


def create_generator(llm_client) -> TravelGenerator:
    """创建生成器工厂函数"""
    return TravelGenerator(llm_client)
