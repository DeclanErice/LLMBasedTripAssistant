# TripGenius Architecture V2 - 进阶问题详解

> 基于 v2 架构的深度扩展，讨论面试可能涉及的进阶场景

---

## 问题一：用户未提供部分数据时的容错处理

### 场景

实际用户可能只提供部分信息：
- "我想去成都" → 没给天数/预算/风格
- "去成都玩3天" → 没给预算/风格
- "成都美食之旅" → 只给了目的地和风格

### 解决方案

#### 方案一：参数可选 + 默认值

```python
@tool
def start_travel_planning(
    destination: str,
    days: int = None,
    budget: int = None,
    style: str = None,
    runtime: ToolRuntime = None
) -> Command:
    
    # 只有必填的目的地缺失时才要求输入
    if not destination:
        return Command(update={
            "messages": [ToolMessage(
                content="好的，您想去哪里旅行呢？请告诉我目的地～"
            )]
        })
    
    # 构建 travel_request，缺失字段用默认值
    travel_request = TravelRequest(
        destination=destination,
        days=days or 3,           # 兜底默认值
        budget=budget or 5000,    # 兜底默认值
        style=style or "chill",   # 兜底默认值
        start_date="",
        departure_city="",
        travelers=1,
        room_type="",
    )
    
    # 根据缺失了多少信息，决定问什么
    missing_info = []
    if not days:
        missing_info.append("行程天数")
    if not budget:
        missing_info.append("预算")
    if not style:
        missing_info.append("旅行风格")
    
    if missing_info:
        prompt = f"好的！我来帮您规划 {destination} 旅行。\n\n"
        if "天数" in missing_info:
            prompt += "请问您计划玩几天呢？\n"
        if "预算" in missing_info:
            prompt += "您的整体预算是多少？（单位：元）\n"
        if "风格" in missing_info:
            prompt += "您喜欢什么风格的旅行？\n可选项：chill / 美食 / 打卡 / 出片\n"
    else:
        prompt = f"好的！{destination} {days}天 {style}风格，预算{budget}元。\n"
        prompt += "请问您计划几号出发呢？"
    
    return Command(update={
        "travel_request": travel_request,
        "current_step": "collecting_date",
        "messages": [ToolMessage(content=prompt)]
    })
```

#### 方案二：LLM 智能推断

```python
elif "不在意预算" in user_input or "随便" in user_input:
    # LLM 智能推断：根据目的地和天数估算合理预算
    budget = estimate_reasonable_budget(destination, days, style)
```

**面试加分点**：
- 不强制用户填所有字段，提供默认值快速启动
- 渐进式询问，先问关键信息（天数），再问次要信息（预算）
- 智能默认值，根据目的地自动调整预算

---

## 问题二：多计划记忆冲突管理

### 场景

```
对话历史：
[用户] 我想去成都，7天，美食风格
[Agent] 好的！正在为您规划7天成都美食之旅...
[Agent] 行程已生成：Day1 锦里... Day7 ...

[用户] 那东京呢？3天够吗？
[Agent] ？？？
  - 理解为"东京3天"是成都行程的补充？
  - 还是理解为开启新计划？
  - 还是理解为修改原计划为东京？
```

### 解决方案

#### 多计划状态 + Plan ID

```python
from typing import Optional
import uuid

class TravelRequest(TypedDict):
    plan_id: str              # 唯一计划ID
    destination: str
    days: int
    budget: int
    style: str
    start_date: str
    departure_city: str
    travelers: int
    room_type: str

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    remaining_steps: int
    
    # 多计划支持
    active_plan_id: str                      # 当前活跃的计划ID
    plans: dict[str, TravelRequest]         # 所有计划 {plan_id: request}
    itineraries: dict[str, ItineraryResult] # 所有行程 {plan_id: result}
    
    current_step: str
    itinerary: Optional[ItineraryResult]    # 当前计划的行程
```

#### 意图检测 + 自动上下文切换

```python
SYSTEM_PROMPT = """
你是专业的旅行规划师。用户可能随时改变目的地。

检测规则：
1. 如果用户提到新的地名（东京、上海、巴黎...），
   且与当前目的地不同 → 创建新计划
2. 如果用户只是修改参数（多几天、预算低点）→ 更新当前计划
3. 如果用户说"取消"、"算了" → 询问是否要开启新计划

当需要创建新计划时，返回格式：
[NEW_PLAN] 目的地: xxx, 天数: xxx, 预算: xxx, 风格: xxx

当只是修改当前计划时，返回格式：
[UPDATE_PLAN] 修改内容: xxx

当不确定时，优先询问用户。
"""
```

#### 计划管理工具

```python
@tool
def handle_destination_change(destination: str, days: int, 
                                budget: int, style: str,
                                runtime: ToolRuntime) -> Command:
    """检测到新目的地时调用此工具"""
    
    state = runtime.state
    current_plan_id = state.get("active_plan_id")
    current_plan = state.get("plans", {}).get(current_plan_id, {})
    
    # 如果目的地变了，创建新计划
    if current_plan.get("destination") != destination:
        new_plan_id = str(uuid.uuid4())
        new_plan = TravelRequest(
            plan_id=new_plan_id,
            destination=destination,
            days=days or 3,
            budget=budget or 5000,
            style=style or "chill",
            start_date="",
            departure_city="",
            travelers=1,
            room_type=""
        )
        
        return Command(update={
            "active_plan_id": new_plan_id,
            "plans": {**state.get("plans", {}), new_plan_id: new_plan},
            "current_step": "collecting_date",
            "messages": [ToolMessage(
                content=f"好的，为您开启新的{destination}计划！\n\n"
                        f"目前记录：目的地-{destination}，天数-{days or 3}天\n"
                        f"请问您计划几号出发呢？"
            )]
        })

@tool
def list_travel_plans(runtime: ToolRuntime) -> Command:
    """列出所有旅行计划"""
    state = runtime.state
    plans = state.get("plans", {})
    active_id = state.get("active_plan_id", "")
    
    if not plans:
        return Command(update={
            "messages": [ToolMessage(content="您还没有创建任何旅行计划。")]
        })
    
    plan_summaries = []
    for plan_id, plan in plans.items():
        marker = "✅ 当前" if plan_id == active_id else "📋"
        summary = f"{marker} {plan['destination']} - {plan['days']}天"
        if plan_id == active_id and state.get("itineraries", {}).get(plan_id):
            summary += " [行程已生成]"
        plan_summaries.append(summary)
    
    return Command(update={
        "messages": [ToolMessage(content="您的旅行计划：\n" + "\n".join(plan_summaries))]
    })

@tool
def switch_plan(destination: str, runtime: ToolRuntime) -> Command:
    """切换到指定目的地的计划，如果不存在则创建"""
    state = runtime.state
    plans = state.get("plans", {})
    
    # 查找匹配的计划
    for plan_id, plan in plans.items():
        if plan["destination"].lower() in destination.lower():
            existing_itinerary = state.get("itineraries", {}).get(plan_id)
            return Command(update={
                "active_plan_id": plan_id,
                "current_step": "completed" if existing_itinerary else "initial",
                "itinerary": existing_itinerary,
                "messages": [ToolMessage(
                    content=f"已切换到 {plan['destination']} {plan['days']}天计划。"
                            + (f"\n\n您的行程已生成，请查看。" if existing_itinerary else "")
                )]
            })
    
    # 没找到，创建新计划
    new_plan_id = str(uuid.uuid4())
    new_plan = TravelRequest(
        plan_id=new_plan_id,
        destination=destination,
        days=3, budget=5000, style="chill",
        start_date="", departure_city="", travelers=1, room_type=""
    )
    
    return Command(update={
        "active_plan_id": new_plan_id,
        "plans": {**plans, new_plan_id: new_plan},
        "current_step": "initial",
        "messages": [ToolMessage(
            content=f"未找到 {destination} 相关计划，已为您创建新计划。请问您计划玩几天呢？"
        )]
    })
```

### 数据流转（多计划场景）

```
对话1：
[用户] 我想去成都，7天
[Agent] 
  - active_plan_id: "plan_001"
  - plans["plan_001"]: {destination: "成都", days: 7}
  - 返回行程

对话2：
[用户] 那东京呢？3天够吗？
[Agent] LLM 检测到新目的地
[Agent] 
  - 创建 plan_002: {destination: "东京", days: 3}
  - active_plan_id: "plan_002"
  - plans = {plan_001, plan_002}
[Agent] 返回："好的，为您开启东京计划！3天...请问您计划几号出发？"

对话3：
[用户] 切换回成都
[Agent] 
  - active_plan_id: "plan_001"
  - 显示成都行程
```

---

## 面试可能问的问题

### Q: 为什么不用 conversation_id 来隔离不同计划？

回答：
1. 同一对话中用户会自然地对比计划（"成都 vs 东京"），完全隔离反而不方便
2. 用户可能说"成都的行程不错，东京也想去"——需要跨计划上下文
3. `plan_id` 方案更灵活：同一对话内管理多计划，但每次操作只针对当前激活的计划

### Q: 如何防止状态污染？

```python
# 每次读取/写入时明确指定 plan_id
def get_active_plan(state: AgentState) -> TravelRequest:
    plan_id = state["active_plan_id"]
    return state["plans"][plan_id]

def update_active_plan(state: AgentState, updates: dict) -> Command:
    plan_id = state["active_plan_id"]
    updated_plan = {**state["plans"][plan_id], **updates}
    return Command(update={
        "plans": {**state["plans"], plan_id: updated_plan}
    })
```

### Q: 如何保证生成质量？

回答：
1. **RAG 提供真实知识库**：先检索相关景点、餐厅信息
2. **Prompt 约束**：强调"只基于检索结果生成"
3. **Output Schema 校验**：行程有固定结构（每日行程、费用明细）
4. **降级策略**：RAG 检索质量差时，LLM 基于通用知识生成

### Q: 工具调用的决策是怎么做的？

回答：
1. 靠 LLM 的 **Function Calling** 能力
2. 每个工具的 **Docstring** 就是 LLM 的决策依据
3. `Literal` 类型限制 + `TypedDict` 结构化状态让调用更可靠

---

## 与当前架构融合（落地版）

> 目标：将上面的进阶问题与当前已实现架构对齐，不做大改造，优先可上线。

### 当前架构基线（代码现状）

- 前端：Next.js + CopilotKit（对话入口）
- Agent：LangGraph 单 Agent + 多工具收集参数
- 后端：FastAPI RAG 服务（`/api/generate`）
- 数据：FAISS 检索 + 本地知识库

这意味着：当前并不是完整 Team 多智能体，而是「单 Agent 编排 + RAG 生成」。因此，进阶能力应先以单 Agent 方式接入。

### 融合问题一：缺失参数容错（直接适配当前单 Agent）

建议改造点：

1. 在 `start_travel_planning` 中只强制目的地；`days/budget/style` 允许为空并给默认值。
2. `current_step` 从固定流程改为「缺啥问啥」，避免机械追问。
3. 增加 `missing_slots`（或等价字段）到状态里，用于控制下一问。
4. 当用户表达“随便/不在意预算”时，写入 `budget_mode = flexible`，而不是立即逼问预算。

建议状态扩展：

```python
class TravelRequest(TypedDict):
    destination: str
    days: int
    budget: int
    style: str
    budget_mode: Literal["fixed", "flexible"]
    start_date: str
    departure_city: str
    travelers: int
    room_type: str

class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    remaining_steps: int
    travel_request: TravelRequest
    missing_slots: list[str]   # ["days", "budget", "style", ...]
    current_step: str
    itinerary: Optional[ItineraryResult]
```

最小收益：

- 提升首轮成功率（用户不必一次说全）
- 减少流失（提问更自然）
- 不改变前后端接口即可上线

### 融合问题二：多计划冲突（以轻量方案并入当前架构）

建议改造点：

1. 先引入 `active_plan_id + plans`，不必立刻拆分多 Agent。
2. 每次写入都只更新 `active_plan_id` 对应计划，避免状态污染。
3. 新目的地触发 `new_plan` 分支；“改预算/改天数”触发 `update_plan` 分支。
4. 增加两个小工具：`list_travel_plans`、`switch_plan`，让用户可显式切换。

建议状态扩展：

```python
class AgentState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    remaining_steps: int
    active_plan_id: str
    plans: dict[str, TravelRequest]
    itineraries: dict[str, ItineraryResult]
    current_step: str
    itinerary: Optional[ItineraryResult]
```

最小收益：

- 支持“成都和东京对比”类真实对话
- 避免单状态被覆盖导致错答
- 仍保持当前单 Agent 结构，复杂度可控

### 与 V2 目标架构的关系

你可以把这两项看作 V2 的前置能力，不冲突：

- 缺失参数容错：属于 Planner Agent 的核心能力
- 多计划管理：属于 Memory/State 层能力

先在单 Agent 中做正确，再迁移到 Team 架构时只需把「状态协议和工具」平移给 Planner/Memory 即可。

### 推荐分阶段实施（结合当前项目约束）

#### Phase A（本周可做）

1. 上线缺失参数容错 + 渐进式询问
2. 增加 `missing_slots` 与 `budget_mode`
3. 保持现有 `/api/generate` 接口不变

#### Phase B（下一步）

1. 上线多计划最小闭环：`active_plan_id/plans/switch/list`
2. 加计划级日志与调试字段（plan_id 打点）

#### Phase C（确认收益后）

1. 再评估是否拆为 Planner/Researcher/Validator 多 Agent
2. 拆分标准：复杂度显著上升、工具调用冲突频繁、质量回退难定位

### 成功验收指标（建议）

- 首轮补全率：用户首条消息缺字段时，能否在 2-3 轮内补齐
- 计划切换准确率：多目的地会话中，是否命中正确计划
- 重新生成率：因状态混乱导致重来比例是否下降
- 用户中断率：在参数收集阶段是否下降
