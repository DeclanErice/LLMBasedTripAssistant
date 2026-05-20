# TripGenius V2 - Multi-Agent Architecture

> 基于 Y-66/Traveler 多智能体协作模式 + LangGraph Team 架构升级

---

## 核心升级点

| 原架构 | 新架构 (V2) |
|--------|-------------|
| 单 Agent + 6 Tools | **Multi-Agent Team** (4个专职 Agent) |
| 简单状态机 | **Team Orchestration** (Agent 间协作) |
| 无记忆系统 | **Memory System** (用户偏好持久化) |
| 固定 Tool calling | **Skills Plugin** (可插拔技能) |
| 单一路由 | **Workflow Pipeline** (Research → Budget → Plan) |
| 仅 RAG 检索 | **MCP Integration** (实时天气/交通/酒店) |

---

## 1. 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              User Interface                                   │
│                    (Next.js + CopilotKit / Web / App)                       │
└─────────────────────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Team Orchestrator                                   │
│                        (LangGraph Team Manager)                              │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    Agent Team Collaboration                          │  │
│  │                                                                      │  │
│  │   ┌──────────────┐    ┌──────────────┐    ┌──────────────┐        │  │
│  │   │   Planner    │◄──►│  Researcher  │◄──►│Budget Analyst│        │  │
│  │   │  Agent      │    │   Agent      │    │   Agent      │        │  │
│  │   │ (主规划师)  │    │  (研究员)    │    │  (预算师)    │        │  │
│  │   └──────────────┘    └──────────────┘    └──────────────┘        │  │
│  │          │                                                            │  │
│  │          ▼                                                            │  │
│  │   ┌──────────────┐    ┌──────────────┐                              │  │
│  │   │   Validator  │    │   Memory     │                              │  │
│  │   │   Agent      │    │   Store      │                              │  │
│  │   │  (校验师)    │    │ (偏好记忆)   │                              │  │
│  │   └──────────────┘    └──────────────┘                              │  │
│  │                                                                      │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                    │                    │
                    ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          Skills & Tools Layer                                │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Intent      │  │   Budget     │  │    Local     │  │  Validation  │  │
│  │  Analysis    │  │  Optimizer   │  │   Expert     │  │    Skill     │  │
│  │  Skill       │  │  Skill       │  │  Skill       │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│  │ Weather MCP  │  │  Flight MCP  │  │   Hotel MCP  │                     │
│  │   Server    │  │   Server     │  │   Server     │                     │
│  └──────────────┘  └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
                    │                    │                    │
                    ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Knowledge & Data Layer                              │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Vector DB  │  │  SQLite/PG   │  │   RAG API   │  │   MCP       │  │
│  │   (FAISS)   │  │   (Memory)   │  │  (FastAPI)  │  │   Servers   │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Multi-Agent Team 设计

### 2.1 Agent 职责定义

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Agent Team Overview                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                         🧑‍💼 Planner Agent (主规划师)                     │  │
│  │                                                                      │  │
│  │  职责:                                                               │  │
│  │  - 理解用户旅行需求 (目的地/日期/人数/预算/偏好)                       │  │
│  │  - 分解任务并分配给其他 Agent                                          │  │
│  │  - 整合最终行程输出                                                   │  │
│  │  - 管理对话状态和流程                                                 │  │
│  │                                                                      │  │
│  │  Tools: intent_classification, task_decompose, itinerary_format        │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                    │                                         │
│           ┌───────────────────────┼───────────────────────┐                │
│           ▼                       ▼                       ▼                 │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    🤖 Researcher Agent (研究员)                       │  │
│  │                                                                      │  │
│  │  职责:                                                               │  │
│  │  - 目的地深度调研 (景点/美食/文化/安全)                               │  │
│  │  - RAG检索最新攻略和笔记                                              │  │
│  │  - 查询实时数据 (天气/开放时间/门票价格)                               │  │
│  │                                                                      │  │
│  │  Tools: rag_retrieve, weather_query, attraction_search, restaurant_q  │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    💰 Budget Analyst Agent (预算师)                   │  │
│  │                                                                      │  │
│  │  职责:                                                               │  │
│  │  - 机票酒店价格查询和比价                                             │  │
│  │  - 每日预算分配优化                                                   │  │
│  │  - 高性价比推荐 (穷游/轻奢/土豪)                                      │  │
│  │  - 费用明细清单                                                       │  │
│  │                                                                      │  │
│  │  Tools: flight_search, hotel_search, budget_allocate, cost_estimate    │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐  │
│  │                    ✅ Validator Agent (校验师)                         │  │
│  │                                                                      │  │
│  │  职责:                                                               │  │
│  │  - 行程逻辑验证 (时间冲突/交通衔接)                                   │  │
│  │  - 预算超支预警                                                       │  │
│  │  - 偏好匹配度检查                                                     │  │
│  │  - 输出质量评分                                                       │  │
│  │                                                                      │  │
│  │  Tools: schedule_validate, budget_check, preference_match, quality_score │  │
│  └─────────────────────────────────────────────────────────────────────┘  │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2.2 Agent 间通信协议

```python
from typing import TypedDict
from langgraph.graph import StateGraph, Team

# Agent 之间的消息格式
class AgentMessage(TypedDict):
    sender: str          # "planner" | "researcher" | "budget" | "validator"
    recipient: str        # "planner" | "researcher" | "budget" | "validator" | "team"
    content: dict         # 消息内容
    type: str            # "request" | "response" | "broadcast"
    timestamp: float

# Planner -> Researcher
{
    "sender": "planner",
    "recipient": "researcher",
    "content": {
        "task": "research_destination",
        "destination": "成都",
        "duration": 5,
        "focus": ["美食", "景点", "当地文化"],
        "user_preferences": {...}
    },
    "type": "request"
}

# Researcher -> Planner
{
    "sender": "researcher", 
    "recipient": "planner",
    "content": {
        "status": "completed",
        "findings": {
            "attractions": [...],
            "restaurants": [...],
            "weather_tips": "...",
            "estimated_budget_range": "¥2000-4000"
        }
    },
    "type": "response"
}
```

---

## 3. Workflow Pipeline

### 3.1 标准工作流 (Research → Budget → Plan)

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           Travel Planning Workflow                           │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Phase 1: Intent Understanding (Planner)                            │   │
│  │                                                                      │   │
│  │  User: "我想去成都5天美食之旅，预算5000"                              │   │
│  │                                                                      │   │
│  │  1. 意图分类 (美食/商务/亲子/蜜月)                                   │   │
│  │  2. 实体提取 (目的地=成都, 天数=5, 预算=5000)                          │   │
│  │  3. 缺失信息询问 (出发地? 人数? 住宿偏好?)                              │   │
│  │  4. 生成任务分解                                                     │   │
│  │                                                                      │   │
│  │  Output: { intent, entities, task_list }                              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│                                      ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Phase 2: Research (Researcher)                                      │   │
│  │                                                                      │   │
│  │  并行任务:                                                           │   │
│  │  ├── 景点调研 (RAG检索 + 小红书笔记)                                  │   │
│  │  ├── 美食攻略 (RAG检索 + 点评数据)                                     │   │
│  │  ├── 实时天气 (MCP Weather API)                                       │   │
│  │  └── 交通信息 (MCP Route API)                                         │   │
│  │                                                                      │   │
│  │  Output: { attractions, restaurants, weather, transport }               │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│                                      ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Phase 3: Budget Planning (Budget Analyst)                           │   │
│  │                                                                      │   │
│  │  并行任务:                                                           │   │
│  │  ├── 机票查询 (MCP Flight API)                                       │   │
│  │  ├── 酒店查询 (MCP Hotel API)                                        │   │
│  │  ├── 预算分配 (交通/住宿/餐饮/门票/购物)                              │   │
│  │  └── 性价比推荐                                                     │   │
│  │                                                                      │   │
│  │  Output: { flights, hotels, budget_breakdown, recommendations }     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│                                      ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Phase 4: Itinerary Generation (Planner)                             │   │
│  │                                                                      │   │
│  │  1. 整合 Researcher + Budget Analyst 的结果                           │   │
│  │  2. 按天编排行程 (景点顺序/时间安排/交通衔接)                           │   │
│  │  3. 嵌入餐厅推荐和预约链接                                            │   │
│  │  4. 生成每日预算明细                                                  │   │
│  │                                                                      │   │
│  │  Output: { daily_itinerary, budget_summary, booking_links }          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│                                      ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Phase 5: Validation (Validator)                                      │   │
│  │                                                                      │   │
│  │  检查项:                                                             │   │
│  │  ├── 时间冲突检测 (同一时段多个活动?)                                  │   │
│  │  ├── 交通衔接验证 (景点间通勤时间合理?)                                │   │
│  │  ├── 预算超支预警 (是否超过用户预算?)                                 │   │
│  │  ├── 偏好匹配度 (是否包含用户喜欢的类型?)                             │   │
│  │  └── 质量评分 (完整性/实用性/个性化)                                  │   │
│  │                                                                      │   │
│  │  Output: { warnings, suggestions, quality_score }                     │   │
│  │                                                                      │   │
│  │  如果 warnings > 阈值 → 返回 Phase 4 重新生成                          │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                      │                                     │
│                                      ▼                                     │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  Final Output: 校验通过的完整行程                                     │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Skills Plugin System

### 4.1 内置 Skills

```python
from langchain.tools import tool
from langchain.prompts import ChatPromptTemplate

# ===================== Intent Analysis Skill =====================
@tool
def analyze_travel_intent(user_message: str) -> dict:
    """分析用户旅行意图和提取关键实体"""
    prompt = """
    从用户消息中提取旅行相关信息:
    
    用户消息: {user_message}
    
    返回JSON格式:
    {{
        "intent": "美食/观光/商务/亲子/蜜月/探险/购物",
        "destination": "目的地城市/国家",
        "duration": 天数,
        "budget": 预算数字,
        "currency": "CNY/SGD/USD",
        "travelers": 人数,
        "departure_city": 出发城市,
        "preferences": ["吃货", "拍照", "休闲", "网红打卡"],
        "missing_info": ["出发城市", "人数"],
        "confidence": 0.0-1.0
    }}
    """
    # 调用 LLM 提取

# ===================== Budget Optimizer Skill =====================
@tool  
def optimize_budget(total_budget: float, duration: int, style: str) -> dict:
    """优化预算分配"""
    # 预算分配比例
    allocations = {
        "穷游": {"transport": 0.3, "stay": 0.2, "food": 0.3, "entrance": 0.1, "shopping": 0.1},
        "轻奢": {"transport": 0.25, "stay": 0.3, "food": 0.25, "entrance": 0.1, "shopping": 0.1},
        "土豪": {"transport": 0.2, "stay": 0.4, "food": 0.2, "entrance": 0.1, "shopping": 0.1}
    }
    ratios = allocations.get(style, allocations["轻奢"])
    return {category: total_budget * ratio for category, ratio in ratios.items()}

# ===================== Local Expert Skill =====================
@tool
def get_local_insider_tips(destination: str, topic: str) -> list:
    """获取当地人才知道的小众tips"""
    prompt = """
    你是一个精通{destination}的当地导游。
    给出关于{topic}的5个小众但实用的建议:
    - 不要去网红店排2小时
    - 本地人常去的宝藏地点
    - 省钱又好吃的馆子
    - 容易被游客忽略的细节
    - 预约/购票技巧
    """
    # RAG 检索 + LLM 生成

# ===================== Validation Skill =====================
@tool
def validate_itinerary(itinerary: dict, user_preferences: dict) -> dict:
    """验证行程逻辑和偏好匹配度"""
    checks = {
        "time_conflicts": [],      # 时间冲突
        "transport_gaps": [],      # 交通空白
        "budget_issues": [],      # 预算问题
        "preference_gaps": [],     # 偏好缺失
        "quality_score": 0.0      # 质量评分
    }
    
    # 逐项检查...
    
    return {
        "passed": len(checks["time_conflicts"]) == 0,
        "warnings": [c for c in checks.values() if c],
        "quality_score": checks["quality_score"]
    }
```

### 4.2 Skill 注册机制

```python
class SkillRegistry:
    """可插拔的 Skill 注册中心"""
    
    def __init__(self):
        self.skills = {}
    
    def register(self, name: str, skill_func: callable, description: str):
        """注册新 Skill"""
        self.skills[name] = {
            "func": skill_func,
            "description": description,
            "agent": None  # 哪个 Agent 可用
        }
    
    def get_skill(self, name: str) -> callable:
        return self.skills.get(name, {}).get("func")
    
    def list_skills(self) -> list:
        return [{"name": k, **v} for k, v in self.skills.items()]

# 使用示例
registry = SkillRegistry()
registry.register("intent_analysis", analyze_travel_intent, "分析用户旅行意图")
registry.register("budget_optimizer", optimize_budget, "优化预算分配")
registry.register("local_expert", get_local_insider_tips, "当地人Tips")
registry.register("validator", validate_itinerary, "行程校验")
```

---

## 5. MCP Integration (Model Context Protocol)

### 5.1 MCP Server 架构

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           MCP Client (Agent端)                              │
│                                                                             │
│  from langchain_mcp_adapters import MCPClient                              │
│                                                                             │
│  mcp_client = MCPClient({"weather": {...}, "flight": {...}})               │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      │ MCP Protocol
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                          MCP Servers (外部服务)                            │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Weather    │  │   Flight     │  │   Hotel      │  │    Route     │  │
│  │   Server     │  │   Server     │  │   Server     │  │   Server     │  │
│  │              │  │              │  │              │  │              │  │
│  │ - 实况天气    │  │ - 机票查询    │  │ - 酒店查询    │  │ - 路线规划   │  │
│  │ - 预报        │  │ - 价格对比    │  │ - 价格对比    │  │ - 通勤时间   │  │
│  │ - 穿衣建议    │  │ - 预订链接    │  │ - 预订链接    │  │ - 导航       │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  └──────────────┘  │
│                                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐                     │
│  │   Attraction │  │  Restaurant  │  │    News      │                     │
│  │   Server     │  │   Server     │  │   Server     │                     │
│  │              │  │              │  │              │                     │
│  │ - 景点门票    │  │ - 餐厅推荐    │  │ - 实时新闻    │                     │
│  │ - 开放时间    │  │ - 预约排队    │  │ - 活动事件    │                     │
│  │ - 评论评分    │  │ - 预订座位    │  │ - 节日提醒    │                     │
│  └──────────────┘  └──────────────┘  └──────────────┘                     │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 5.2 MCP Tool 定义示例

```python
# ===================== Weather MCP =====================
{
    "name": "get_weather",
    "description": "获取目的地天气预报和穿衣建议",
    "input_schema": {
        "destination": "string",
        "date": "string (YYYY-MM-DD)",
        "include_tips": "boolean (default: true)"
    },
    "output_schema": {
        "temperature": "number",
        "weather": "string (晴/雨/阴...)",
        "clothing_tips": "string",
        "activity_suggestions": "string"
    }
}

# ===================== Flight MCP =====================
{
    "name": "search_flights",
    "description": "搜索机票并返回性价比推荐",
    "input_schema": {
        "from_city": "string",
        "to_city": "string", 
        "date": "string (YYYY-MM-DD)",
        "budget_range": "object {min, max}",
        "sort_by": "string (price/duration/stops)"
    },
    "output_schema": {
        "flights": [
            {
                "airline": "string",
                "price": "number",
                "duration": "number (分钟)",
                "stops": "number",
                "booking_url": "string"
            }
        ],
        "recommendation": "string"
    }
}

# ===================== Hotel MCP =====================
{
    "name": "search_hotels",
    "description": "搜索酒店并返回推荐",
    "input_schema": {
        "destination": "string",
        "checkin": "string",
        "checkout": "string",
        "guests": "number",
        "budget_per_night": "number",
        "amenities": "array (wifi/parking/pool...)"
    },
    "output_schema": {
        "hotels": [
            {
                "name": "string",
                "rating": "number",
                "price_per_night": "number",
                "location": "string",
                "highlights": "array",
                "booking_url": "string"
            }
        ],
        "recommendation": "string"
    }
}
```

---

## 6. Memory System

### 6.1 用户偏好 Memory

```python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# SQLite 本地存储 (生产可换 PostgreSQL)
engine = create_engine("sqlite:///data/memory.db")
Session = sessionmaker(bind=engine)

class UserMemory:
    """用户偏好记忆系统"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.session = Session()
    
    def save_preference(self, category: str, key: str, value: any):
        """保存用户偏好"""
        pref = UserPreference(
            user_id=self.user_id,
            category=category,  # travel_style, budget, diet, ...
            key=key,
            value=str(value),
            updated_at=datetime.now()
        )
        self.session.merge(pref)
        self.session.commit()
    
    def get_preferences(self, categories: list = None) -> dict:
        """获取用户偏好"""
        query = self.session.query(UserPreference).filter(
            UserPreference.user_id == self.user_id
        )
        if categories:
            query = query.filter(UserPreference.category.in_(categories))
        
        prefs = query.all()
        return {p.category + "." + p.key: p.value for p in prefs}
    
    def add_conversation_turn(self, role: str, content: str):
        """记录对话历史"""
        turn = ConversationHistory(
            user_id=self.user_id,
            role=role,  # user / assistant
            content=content,
            timestamp=datetime.now()
        )
        self.session.add(turn)
        self.session.commit()
    
    def get_conversation_history(self, limit: int = 10) -> list:
        """获取最近对话历史"""
        turns = self.session.query(ConversationHistory).filter(
            ConversationHistory.user_id == self.user_id
        ).order_by(
            ConversationHistory.timestamp.desc()
        ).limit(limit).all()
        
        return [{"role": t.role, "content": t.content} for t in reversed(turns)]

# 数据模型
class UserPreference(Base):
    __tablename__ = "user_preferences"
    user_id = Column(String, primary_key=True)
    category = Column(String, primary_key=True)
    key = Column(String, primary_key=True)
    value = Column(String)
    updated_at = Column(DateTime)

class ConversationHistory(Base):
    __tablename__ = "conversation_history"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, index=True)
    role = Column(String)
    content = Column(Text)
    timestamp = Column(DateTime)
```

### 6.2 Memory 提取与使用

```python
class MemoryExtractionSkill:
    """从对话中提取用户偏好到 Memory"""
    
    def extract_and_save(self, user_message: str, memory: UserMemory):
        """分析消息并更新 Memory"""
        prompt = f"""
        从用户消息中提取可记忆的偏好信息:
        
        用户消息: {user_message}
        
        返回JSON:
        {{
            "preferences": [
                {{"category": "travel_style", "key": "preferred", "value": "chill/active"}},
                {{"category": "diet", "key": "restriction", "value": "素食/无辣/清真"}},
                {{"category": "accommodation", "key": "type", "value": "民宿/酒店/青旅"}},
                {{"category": "transport", "key": "preference", "value": "飞机/高铁/自驾"}}
            ],
            "quick_facts": ["不喜欢排队", "早起型", "路痴"]
        }}
        """
        
        result = llm.invoke(prompt)
        
        for pref in result.get("preferences", []):
            memory.save_preference(
                category=pref["category"],
                key=pref["key"],
                value=pref["value"]
            )
        
        # 快速记忆关键词
        for fact in result.get("quick_facts", []):
            memory.save_preference("quick_facts", fact, "true")
        
        return result
```

---

## 7. 项目结构 (V2)

```
TripGeniusV2/
├── apps/
│   ├── app/                        # Next.js 前端
│   │   └── src/
│   │       ├── app/
│   │       │   └── page.tsx       # CopilotKit 集成
│   │       └── components/
│   │
│   └── agent/                     # LangGraph Agent
│       ├── main.py                 # Agent 入口
│       ├── langgraph.json
│       └── src/
│           ├── team/               # Multi-Agent Team
│           │   ├── __init__.py
│           │   ├── planner.py      # Planner Agent
│           │   ├── researcher.py   # Researcher Agent
│           │   ├── budget.py      # Budget Analyst Agent
│           │   ├── validator.py    # Validator Agent
│           │   └── state.py       # Team State
│           │
│           ├── skills/             # Skills Plugin
│           │   ├── intent.py
│           │   ├── budget_optimizer.py
│           │   ├── local_expert.py
│           │   └── validator.py
│           │
│           ├── mcp/                # MCP Clients
│           │   ├── weather.py
│           │   ├── flight.py
│           │   └── hotel.py
│           │
│           ├── memory/             # Memory System
│           │   ├── user_memory.py
│           │   └── models.py
│           │
│           └── tools/              # Shared Tools
│               └── shared.py
│
├── src/
│   └── rag_backend/               # RAG 后端服务
│       ├── api/
│       │   └── main.py           # FastAPI
│       └── rag/
│           ├── embed.py
│           └── query.py
│
├── data/                          # 本地数据
│   ├── memory.db                  # SQLite (Memory)
│   ├── chroma/                   # Vector DB
│   └── knowledge_docs/           # RAG 知识库
│
├── skills/                        # 独立 Skill 包
│   ├── budget_skill/
│   ├── intent_skill/
│   └── validation_skill/
│
├── pyproject.toml
├── turbo.json
└── pnpm-workspace.yaml
```

---

## 8. 技术栈对比

| 层级 | 原架构 (V1) | 新架构 (V2) |
|------|-------------|-------------|
| **Agent Framework** | LangGraph (单 Agent) | **LangGraph Team** (多 Agent) |
| **Agent 协作** | Tool Calling | **Team Protocol** (Agent 间通信) |
| **状态管理** | 简单 State | **Shared State + Memory** |
| **Skills** | Hard-coded Tools | **Plugin System** (可插拔) |
| **外部数据** | 仅 RAG | **MCP Integration** (实时 API) |
| **用户记忆** | 无 | **SQLite/PG Memory** |
| **工作流** | 单步执行 | **Pipeline Workflow** (5 阶段) |
| **输出校验** | 无 | **Validator Agent** |

---

## 9. 迁移路径建议

### Phase 1: 基础设施 (1-2 weeks)
- [ ] 搭建 LangGraph Team 框架
- [ ] 实现 Agent 间通信协议
- [ ] 基础 Memory System

### Phase 2: Agent 实现 (2-3 weeks)
- [ ] 实现 Planner Agent (整合现有 logic)
- [ ] 实现 Researcher Agent (现有 RAG)
- [ ] 实现 Budget Analyst Agent (新增)
- [ ] 实现 Validator Agent (新增)

### Phase 3: MCP 集成 (1-2 weeks)
- [ ] 接入 Weather MCP
- [ ] 接入 Flight/Hotel MCP
- [ ] MCP Server 部署

### Phase 4: Skills 系统 (1 week)
- [ ] Skill Registry 实现
- [ ] 迁移现有 Tools 到 Skills
- [ ] 新增 Specialized Skills

### Phase 5: 优化 (1 week)
- [ ] Team 协作调优
- [ ] Memory 效果优化
- [ ] Pipeline 流程优化

---

## 10. 参考项目

- **Y-66/Traveler**: https://github.com/Y-66/Traveler (Agno 框架，多 Agent 协作)
- **Agno Documentation**: https://docs.agno.com (Agent / Team / Workflow / MCP / Skills)

---

*Updated: 2026-04-14*
*Based on: Y-66/Traveler Multi-Agent Architecture*
