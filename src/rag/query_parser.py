"""
Query Parser - 解析用户输入，提取旅行意图
"""

import re
from typing import Dict, Any


class TravelQueryParser:
    """旅行查询解析器"""

    def __init__(self, llm_client=None):
        self.llm_client = llm_client

    def parse(self, user_input: str) -> Dict[str, Any]:
        """
        解析用户输入

        Args:
            user_input: 用户输入的自然语言

        Returns:
            结构化的意图信息
        """
        # 简单的规则解析作为fallback
        result = self._rule_based_parse(user_input)

        # 如果LLM可用，可以进一步增强
        if self.llm_client:
            try:
                llm_result = self.llm_client.parse_intent(user_input)
                # 合并结果
                for key, value in llm_result.items():
                    if value and value != 0 and value != "":
                        result[key] = value
            except Exception as e:
                print(f"LLM parse failed, using rule-based: {e}")

        return result

    def _rule_based_parse(self, text: str) -> Dict[str, Any]:
        """
        基于规则的解析

        Args:
            text: 用户输入文本

        Returns:
            结构化的意图信息
        """
        result = {
            "destination": "",
            "days": 0,
            "budget": 0,
            "style": "",
            "original_text": text,
        }

        # 目的地识别 - 常见目的地
        destinations = [
            "日本", "东京", "大阪", "京都", "北海道", "冲绳",
            "泰国", "曼谷", "普吉岛", "清迈",
            "韩国", "首尔", "济州岛",
            "美国", "纽约", "洛杉矶", "旧金山",
            "欧洲", "法国", "巴黎", "意大利", "罗马",
            "新加坡", "马来西亚", "吉隆坡",
            "中国", "北京", "上海", "广州", "深圳",
            "云南", "大理", "丽江", "昆明", "香格里拉",
            "西藏", "拉萨", "新疆", "成都", "重庆",
            "厦门", "福州", "杭州", "苏州", "南京",
            "西安", "桂林", "阳朔", "青岛", "大连",
            "哈尔滨", "雪乡", "长白山",
            "张家界", "凤凰", "峨眉山", "九寨沟",
        ]

        for dest in destinations:
            if dest in text:
                result["destination"] = dest
                break

        # 天数识别
        day_patterns = [
            (r"(\d+)天", 1),
            (r"(\d+)晚", 1),
            (r"(\d+)夜", 1),
            (r"三日", 3),
            (r"两日", 2),
            (r"四日", 4),
            (r"五日", 5),
            (r"一周|七天", 7),
        ]

        for pattern, default in day_patterns:
            match = re.search(pattern, text)
            if match:
                if match.groups():
                    result["days"] = int(match.group(1))
                else:
                    result["days"] = default
                break

        # 预算识别
        budget_patterns = [
            (r"(\d+)\s*万\s*元", lambda m: int(m.group(1)) * 10000),
            (r"(\d+)\s*千\s*元", lambda m: int(m.group(1)) * 1000),
            (r"(\d+)\s*元", lambda m: int(m.group(1))),
            (r"预算\s*(\d+)", lambda m: int(m.group(1))),
            (r"(\d+)k", lambda m: int(m.group(1)) * 1000),
            (r"穷游", 2000),
            (r"轻奢", 8000),
            (r"土豪|奢华", 15000),
        ]

        for pattern, handler in budget_patterns:
            match = re.search(pattern, text)
            if match:
                if callable(handler):
                    result["budget"] = handler(match)
                else:
                    result["budget"] = handler
                break

        # 风格识别
        style_keywords = {
            "chill": ["chill", "休闲", "轻松", "慢生活", "度假"],
            "美食": ["美食", "吃货", "觅食", "好吃的"],
            "打卡": ["打卡", "必去", "网红", "热门"],
            "出片": ["出片", "摄影", "拍照", "拍照好看"],
        }

        text_lower = text.lower()
        for style, keywords in style_keywords.items():
            if any(kw in text_lower for kw in keywords):
                result["style"] = style
                break

        return result


def parse_travel_query(user_input: str, llm_client=None) -> Dict[str, Any]:
    """解析用户输入的便捷函数"""
    parser = TravelQueryParser(llm_client)
    return parser.parse(user_input)
