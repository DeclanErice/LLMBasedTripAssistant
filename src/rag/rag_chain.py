"""
RAG Chain - 串联整个RAG流程
Query解析 → 检索 → 生成
"""

from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from .query_parser import TravelQueryParser, parse_travel_query
from .retriever import TravelRetriever, create_retriever
from .generator import TravelGenerator, create_generator


@dataclass
class TravelRequest:
    """旅行规划请求"""
    destination: str
    days: int
    budget: int
    style: str
    original_text: str = ""


@dataclass
class TravelResponse:
    """旅行规划响应"""
    request: TravelRequest
    itinerary: Dict[str, Any]
    retrieved_context: str = ""
    debug_info: Dict[str, Any] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "request": {
                "destination": self.request.destination,
                "days": self.request.days,
                "budget": self.request.budget,
                "style": self.request.style,
            },
            "itinerary": self.itinerary,
            "retrieved_context": self.retrieved_context,
            "debug_info": self.debug_info or {},
        }


class RAGChain:
    """RAG流程串联器"""

    def __init__(
        self,
        knowledge_base=None,
        llm_client=None,
    ):
        """
        初始化RAG Chain

        Args:
            knowledge_base: 知识库实例
            llm_client: LLM客户端
        """
        self.query_parser = TravelQueryParser(llm_client)
        self.retriever = create_retriever(knowledge_base)
        self.generator = create_generator(llm_client)

        self.llm_client = llm_client
        self.kb = knowledge_base

    def run(self, user_input: str, k: int = 3) -> TravelResponse:
        """
        执行完整的RAG流程

        Args:
            user_input: 用户输入的自然语言
            k: 检索结果数量

        Returns:
            TravelResponse对象
        """
        # Step 1: Query解析
        parsed = self.query_parser.parse(user_input)

        request = TravelRequest(
            destination=parsed.get("destination", ""),
            days=parsed.get("days", 3),
            budget=parsed.get("budget", 5000),
            style=parsed.get("style", "chill"),
            original_text=user_input,
        )

        debug_info = {"query_parsing": parsed}

        # Step 2: 检索
        context = ""
        if self.retriever and request.destination:
            context = self.retriever.retrieve_as_context(
                query=user_input,
                destination=request.destination,
                style=request.style,
                k=k,
            )
            debug_info["retrieval"] = {"context_length": len(context), "has_context": bool(context)}

        # Step 3: 生成
        itinerary = {}
        if self.generator and self.llm_client:
            try:
                itinerary = self.generator.generate(
                    destination=request.destination,
                    days=request.days,
                    budget=request.budget,
                    style=request.style,
                    context=context,
                )
                debug_info["generation"] = {"success": True, "has_itinerary": bool(itinerary)}
            except Exception as e:
                debug_info["generation"] = {"success": False, "error": str(e)}

        return TravelResponse(
            request=request,
            itinerary=itinerary,
            retrieved_context=context,
            debug_info=debug_info,
        )

    def run_with_structured_input(
        self,
        destination: str,
        days: int,
        budget: int,
        style: str = "chill",
        k: int = 3,
    ) -> Dict[str, Any]:
        """
        使用结构化输入运行RAG流程

        Args:
            destination: 目的地
            days: 天数
            budget: 预算
            style: 风格
            k: 检索结果数量

        Returns:
            行程结果字典
        """
        # 构建查询文本
        query = f"去{destination}{days}天{style}"

        # 检索
        context = ""
        if self.retriever:
            context = self.retriever.retrieve_as_context(
                query=query,
                destination=destination,
                style=style,
                k=k,
            )

        # 生成
        if self.generator:
            itinerary = self.generator.generate(
                destination=destination,
                days=days,
                budget=budget,
                style=style,
                context=context,
            )
            return itinerary

        return {}


def create_rag_chain(knowledge_base=None, llm_client=None) -> RAGChain:
    """创建RAG Chain工厂函数"""
    return RAGChain(knowledge_base, llm_client)
