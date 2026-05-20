"""
API 路由定义
"""

from typing import Dict, Any
from pydantic import BaseModel, Field

from fastapi import APIRouter, HTTPException
from src.rag import create_rag_chain
from src.llm_client import get_client
from src.embedding import get_or_create_kb

router = APIRouter()


# ============== Request/Response Models ==============

class GenerateRequest(BaseModel):
    """生成行程请求"""
    destination: str = Field(..., description="目的地")
    days: int = Field(default=3, ge=1, le=30, description="行程天数")
    budget: int = Field(default=5000, ge=0, description="预算，单位元")
    style: str = Field(default="chill", description="旅行风格: chill/美食/打卡/出片")
    query: str = Field(default="", description="自然语言查询（可选）")


class GenerateResponse(BaseModel):
    """生成行程响应"""
    success: bool
    data: Dict[str, Any] = None
    error: str = None


class ChatRequest(BaseModel):
    """对话请求"""
    message: str = Field(..., description="用户消息")
    session_id: str = Field(default="default", description="会话ID")


class ChatResponse(BaseModel):
    """对话响应"""
    success: bool
    reply: str = None
    error: str = None


# ============== 全局实例引用 ==============

def get_rag_chain():
    """获取RAG Chain实例"""
    from src.api.main import rag_chain
    return rag_chain


# ============== API 路由 ==============

@router.post("/generate", response_model=GenerateResponse)
async def generate_itinerary(request: GenerateRequest):
    """
    生成旅行行程

    使用RAG流程生成个性化的旅行行程规划
    """
    try:
        rag = get_rag_chain()

        if not rag:
            # 如果RAG Chain未初始化，尝试初始化
            try:
                kb = get_or_create_kb()
                llm = get_client()
                rag = create_rag_chain(kb, llm)
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Failed to initialize RAG: {str(e)}")

        # 构建查询
        query = request.query or f"去{request.destination}{request.days}天{request.style}"

        # 运行RAG流程
        result = rag.run_with_structured_input(
            destination=request.destination,
            days=request.days,
            budget=request.budget,
            style=request.style,
            k=3,
        )

        if not result:
            raise HTTPException(status_code=500, detail="Failed to generate itinerary")

        return GenerateResponse(
            success=True,
            data=result,
        )

    except HTTPException:
        raise
    except Exception as e:
        return GenerateResponse(
            success=False,
            error=str(e),
        )


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    对话式交互

    处理用户自然语言输入，返回生成的行程或对话回复
    """
    try:
        rag = get_rag_chain()

        if not rag:
            return ChatResponse(
                success=False,
                error="Service not initialized",
            )

        # 处理用户消息
        result = rag.run(request.message)

        if result and result.itinerary:
            # 如果生成了行程，返回行程摘要
            itinerary = result.itinerary
            return ChatResponse(
                success=True,
                reply=f"已为您规划{result.request.destination} {result.request.days}日{result.request.style}风格行程：\n\n{itinerary.get('title', '行程规划')}\n\n总预算约{itinerary.get('total_cost', 0)}元。回复「详细」查看完整行程。",
            )
        else:
            return ChatResponse(
                success=True,
                reply="抱歉，暂时无法处理您的请求，请稍后再试。",
            )

    except Exception as e:
        return ChatResponse(
            success=False,
            error=str(e),
        )


@router.get("/destinations")
async def list_destinations():
    """
    获取支持的目的地列表
    """
    # TODO: 从知识库动态获取
    destinations = [
        {"id": "jp", "name": "日本", "name_en": "Japan"},
        {"id": "th", "name": "泰国", "name_en": "Thailand"},
        {"id": "kr", "name": "韩国", "name_en": "Korea"},
        {"id": "cn_yunnan", "name": "云南", "name_en": "Yunnan"},
        {"id": "cn_xizang", "name": "西藏", "name_en": "Tibet"},
        {"id": "cn_xiamen", "name": "厦门", "name_en": "Xiamen"},
        {"id": "cn_chongqing", "name": "重庆", "name_en": "Chongqing"},
        {"id": "cn_chengdu", "name": "成都", "name_en": "Chengdu"},
        {"id": "cn_guangzhou", "name": "广州", "name_en": "Guangzhou"},
        {"id": "cn_qingdao", "name": "青岛", "name_en": "Qingdao"},
    ]
    return {"destinations": destinations}


@router.get("/styles")
async def list_styles():
    """
    获取支持的旅行风格列表
    """
    styles = [
        {"id": "chill", "name": "休闲", "description": "轻松自在，享受慢生活"},
        {"id": "美食", "name": "美食", "description": "品尝当地特色美食"},
        {"id": "打卡", "name": "打卡", "description": "必去网红景点"},
        {"id": "出片", "name": "出片", "description": "寻找最美拍照角度"},
    ]
    return {"styles": styles}
