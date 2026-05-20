"""
Retriever - 多路召回模块
结合向量检索和关键词检索
"""

from typing import List, Dict, Any, Optional


class TravelRetriever:
    """旅行内容检索器"""

    def __init__(self, knowledge_base=None):
        """
        初始化检索器

        Args:
            knowledge_base: 知识库实例
        """
        self.kb = knowledge_base

    def retrieve(
        self,
        query: str,
        destination: Optional[str] = None,
        style: Optional[str] = None,
        budget_level: Optional[str] = None,
        k: int = 5,
    ) -> List[Dict[str, Any]]:
        """
        多路召回检索

        Args:
            query: 用户查询
            destination: 目的地过滤
            style: 风格过滤
            budget_level: 预算等级过滤
            k: 返回数量

        Returns:
            检索结果列表
        """
        if not self.kb:
            return []

        # 1. 向量检索
        search_query = query
        if destination:
            search_query = f"{destination} {search_query}"

        vector_results = self.kb.search(search_query, k=k * 2)

        # 2. 结果过滤和重排序
        filtered_results = self._filter_and_rerank(
            vector_results,
            destination=destination,
            style=style,
            budget_level=budget_level,
        )

        # 3. 返回Top k
        return filtered_results[:k]

    def _filter_and_rerank(
        self,
        results: List[Dict[str, Any]],
        destination: Optional[str] = None,
        style: Optional[str] = None,
        budget_level: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        过滤和重排序结果

        Args:
            results: 原始检索结果
            destination: 目的地过滤条件
            style: 风格过滤条件
            budget_level: 预算等级过滤条件

        Returns:
            过滤后的结果
        """
        scored_results = []

        for result in results:
            score = result.get("_score", 0)

            # 目的地匹配加分
            if destination and destination in result.get("destination", ""):
                score += 0.3

            # 风格匹配加分
            if style and style == result.get("travel_style", ""):
                score += 0.2

            # 预算等级匹配加分
            if budget_level and budget_level == result.get("budget_level", ""):
                score += 0.1

            result["_relevance_score"] = score
            scored_results.append(result)

        # 按相关性分数排序
        scored_results.sort(key=lambda x: x.get("_relevance_score", 0), reverse=True)

        return scored_results

    def retrieve_as_context(
        self,
        query: str,
        destination: Optional[str] = None,
        style: Optional[str] = None,
        budget_level: Optional[str] = None,
        k: int = 3,
    ) -> str:
        """
        检索相关内容并格式化为上下文字符串

        Args:
            query: 用户查询
            destination: 目的地过滤
            style: 风格过滤
            budget_level: 预算等级过滤
            k: 返回数量

        Returns:
            格式化后的上下文
        """
        results = self.retrieve(
            query=query,
            destination=destination,
            style=style,
            budget_level=budget_level,
            k=k,
        )

        if not results:
            return ""

        context_parts = []
        for i, result in enumerate(results):
            part = f"""【行程参考{i+1}】{result.get('title', '未知')}
目的地: {result.get('destination', '未知')}
风格: {result.get('travel_style', '未知')}
预算等级: {result.get('budget_level', '未知')}
行程安排: {result.get('content', '无详细信息')}
花费估算: {result.get('cost_estimate', 0)}元
标签: {', '.join(result.get('tags', []))}
"""
            context_parts.append(part)

        return "\n---\n".join(context_parts)


def create_retriever(knowledge_base=None) -> TravelRetriever:
    """创建检索器工厂函数"""
    return TravelRetriever(knowledge_base)
