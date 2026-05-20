"""
TripGenius 初始化脚本
用于初始化向量数据库和知识库
"""

import os
import sys

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.embedding import TravelKnowledgeBase
from src.llm_client import LLMClient
from dotenv import load_dotenv


def main():
    """初始化知识库"""
    load_dotenv()

    print("=" * 50)
    print("TripGenius 初始化脚本")
    print("=" * 50)

    # 1. 初始化知识库
    print("\n[1/2] 初始化向量数据库...")
    try:
        kb = TravelKnowledgeBase()
        data_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "data", "processed", "travel_data.json"
        )
        kb.load_data(data_path)
        print("✅ 向量数据库初始化完成")
    except Exception as e:
        print(f"❌ 向量数据库初始化失败: {e}")
        return

    # 2. 测试LLM连接
    print("\n[2/2] 测试 LLM API 连接...")
    try:
        client = LLMClient()
        response = client.chat(
            messages=[{"role": "user", "content": "你好，请回复OK"}],
            temperature=0
        )
        print(f"✅ LLM API 连接成功: {response[:50]}")
    except Exception as e:
        print(f"⚠️ LLM API 连接失败: {e}")
        print("请检查.env文件中的API Key配置")

    print("\n" + "=" * 50)
    print("初始化完成！可以启动服务了:")
    print("  python -m uvicorn src.api.main:app --reload --port 8000")
    print("=" * 50)


if __name__ == "__main__":
    main()
