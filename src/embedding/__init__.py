"""
Embedding 生成和存储模块
使用 text2vec-base-chinese 生成中文文本向量
使用 FAISS 作为本地向量数据库
"""

import os
import json
import numpy as np
from typing import List, Dict, Any, Optional
from sentence_transformers import SentenceTransformer
import faiss
import pickle

# 配置路径
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "processed")
EMBEDDING_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "embeddings")


class EmbeddingGenerator:
    """文本向量化生成器"""

    def __init__(self, model_name: str = "shibing624/text2vec-base-chinese"):
        """
        初始化embedding模型

        Args:
            model_name: HuggingFace上的模型名称
        """
        self.model = SentenceTransformer(model_name)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def encode(self, texts: List[str], normalize: bool = True) -> np.ndarray:
        """
        生成文本embedding

        Args:
            texts: 文本列表
            normalize: 是否L2归一化

        Returns:
            numpy array of embeddings
        """
        embeddings = self.model.encode(texts, normalize_embeddings=normalize)
        return embeddings

    def encode_query(self, query: str) -> np.ndarray:
        """为查询生成embedding（便捷方法）"""
        return self.encode([query])[0]


class VectorStore:
    """本地向量数据库，使用FAISS"""

    def __init__(self, embedding_dim: int, index_path: Optional[str] = None):
        """
        初始化向量存储

        Args:
            embedding_dim: embedding向量维度
            index_path: 索引文件路径
        """
        self.embedding_dim = embedding_dim
        self.index_path = index_path or os.path.join(EMBEDDING_DIR, "faiss_index.bin")
        self.metadata_path = os.path.join(EMBEDDING_DIR, "metadata.pkl")

        # 创建索引
        self.index = faiss.IndexFlatIP(embedding_dim)  # Inner Product for cosine similarity
        self.metadata: List[Dict[str, Any]] = []

        # 尝试加载已有索引
        self._load()

    def _load(self):
        """加载已有索引"""
        if os.path.exists(self.index_path) and os.path.exists(self.metadata_path):
            self.index = faiss.read_index(self.index_path)
            with open(self.metadata_path, "rb") as f:
                self.metadata = pickle.load(f)
            print(f"Loaded existing index with {self.index.ntotal} vectors")

    def add(self, embeddings: np.ndarray, metadata: List[Dict[str, Any]]):
        """
        添加向量和元数据

        Args:
            embeddings: numpy array of embeddings, shape (n, dim)
            metadata: 元数据列表，与embeddings顺序对应
        """
        if len(embeddings) != len(metadata):
            raise ValueError("embeddings and metadata must have same length")

        # 确保embedding是float32类型
        embeddings = embeddings.astype(np.float32)

        self.index.add(embeddings)
        self.metadata.extend(metadata)

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索最相似的k个结果

        Args:
            query_embedding: 查询向量
            k: 返回结果数量

        Returns:
            搜索结果列表，每项包含metadata和距离
        """
        query_embedding = query_embedding.astype(np.float32).reshape(1, -1)

        # 搜索
        distances, indices = self.index.search(query_embedding, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0 and idx < len(self.metadata):  # valid index
                result = self.metadata[idx].copy()
                result["_score"] = float(dist)
                results.append(result)

        return results

    def save(self):
        """保存索引到磁盘"""
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)

        faiss.write_index(self.index, self.index_path)
        with open(self.metadata_path, "wb") as f:
            pickle.dump(self.metadata, f)

        print(f"Saved index with {self.index.ntotal} vectors to {self.index_path}")


class TravelKnowledgeBase:
    """旅行知识库"""

    def __init__(self):
        self.embedding_generator = EmbeddingGenerator()
        self.vector_store = VectorStore(self.embedding_generator.embedding_dim)

    def load_data(self, data_path: Optional[str] = None):
        """
        加载并索引旅行数据

        Args:
            data_path: JSON数据文件路径
        """
        data_path = data_path or os.path.join(DATA_DIR, "travel_data.json")

        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 构建文本内容
        texts = []
        metadata = []

        for item in data:
            # 构建完整的文本表示
            text_parts = [
                f"目的地: {item.get('destination', '')}",
                f"标题: {item.get('title', '')}",
                f"旅行风格: {item.get('travel_style', '')}",
                f"预算等级: {item.get('budget_level', '')}",
                f"行程天数: {item.get('days', 0)}天",
                f"内容: {item.get('content', '')}",
            ]
            text = "\n".join(text_parts)

            texts.append(text)
            metadata.append({
                "title": item.get("title", ""),
                "destination": item.get("destination", ""),
                "travel_style": item.get("travel_style", ""),
                "budget_level": item.get("budget_level", ""),
                "days": item.get("days", 0),
                "content": item.get("content", ""),
                "tags": item.get("tags", []),
                "cost_estimate": item.get("cost_estimate", 0),
            })

        # 生成embeddings
        print(f"Generating embeddings for {len(texts)} documents...")
        embeddings = self.embedding_generator.encode(texts)

        # 存储
        self.vector_store.add(embeddings, metadata)
        self.vector_store.save()

        print(f"Indexed {len(texts)} documents")

    def search(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        搜索相关内容

        Args:
            query: 查询文本
            k: 返回结果数量

        Returns:
            搜索结果列表
        """
        query_embedding = self.embedding_generator.encode_query(query)
        return self.vector_store.search(query_embedding, k)

    def retrieve(self, query: str, k: int = 5) -> str:
        """
        检索相关内容并格式化为字符串

        Args:
            query: 查询文本
            k: 返回结果数量

        Returns:
            格式化后的上下文字符串
        """
        results = self.search(query, k)

        context_parts = []
        for i, result in enumerate(results):
            part = f"""【参考资料{i+1}】{result['title']}
目的地: {result['destination']}
风格: {result['travel_style']}
预算: {result['budget_level']}
行程: {result['content']}
"""
            context_parts.append(part)

        return "\n---\n".join(context_parts)


def initialize_knowledge_base(data_path: Optional[str] = None) -> TravelKnowledgeBase:
    """初始化知识库"""
    kb = TravelKnowledgeBase()
    kb.load_data(data_path)
    return kb


def get_or_create_kb() -> TravelKnowledgeBase:
    """获取或创建知识库单例"""
    if not hasattr(get_or_create_kb, "_instance"):
        get_or_create_kb._instance = TravelKnowledgeBase()
        # 如果索引不存在，则初始化
        index_path = os.path.join(EMBEDDING_DIR, "faiss_index.bin")
        if not os.path.exists(index_path):
            get_or_create_kb._instance.load_data()
    return get_or_create_kb._instance
