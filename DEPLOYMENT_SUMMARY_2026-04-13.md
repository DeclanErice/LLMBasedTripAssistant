# TripGenius Agent 部署问题摘要

**日期**: 2026-04-13
**项目**: TripGenius - CopilotKit + LangGraph 旅行规划 Agent

---

## 概述

将 TripGenius 从 FastAPI + HTML 表单迁移到 CopilotKit + LangGraph 对话式 Agent。前端使用 Next.js，后端使用 LangGraph Agent 连接 MiniMax API。

---

## 遇到的问题及解决方案

### 1. `langgraph dev` 端口占用问题

**问题**: `langgraph dev` 报错 `Port 8123 is already in use`，但 `netstat` 找不到占用进程。

**原因**: `langgraph dev` 内部的端口检查机制有缓存问题，且 `turbo` 不会自动清理失败的子进程。

**解决**: 在 `package.json` 中去掉端口参数，让其自动选择端口：
```json
"dev": "langgraph dev --no-browser"
```

**参考文档**: `langgraph dev --help` (命令行帮助)

---

### 2. Next.js `.next/dev/lock` 锁文件问题

**问题**: Next.js 报错 `Unable to acquire lock at .next/dev/lock`

**原因**: 已有另一个 Next.js 进程在运行。

**解决**:
```bash
taskkill /PID <PID> /F
# 或删除锁文件
del /s /q "apps\app\.next\dev\lock"
```

---

### 3. `langgraph.json` 导出变量名错误

**问题**: `ValueError: Could not find graph 'graph' in './main.py'`

**原因**: `langgraph.json` 中配置为 `./main.py:graph`，但文件导出的是 `agent`。

**解决**: 修改 `apps/agent/langgraph.json`:
```json
"graphs": {
  "tripgenius_agent": "./main.py:agent"
}
```

**参考文档**:
- [LangGraph CLI 文档](https://langchain-ai.github.io/langgraph/how-toCLI/)
- [LangGraph Agent 配置](https://docs.copilotkit.ai/reference/v1/sdk/python/LangGraphAgent)

---

### 4. `AgentState` 缺少 `remaining_steps` 字段

**问题**: `ValueError: Missing required key(s) {'remaining_steps'} in state_schema`

**原因**: `create_react_agent` 要求 `state_schema` 必须包含 `messages` 和 `remaining_steps` 字段。

**解决**: 修改 `AgentState` 定义，添加所有必需字段：
```python
class AgentState(TypedDict):
    """旅行规划 Agent 状态"""
    messages: Required[Annotated[list[AnyMessage], add_messages]]
    remaining_steps: int
    travel_request: TravelRequest
    current_step: Literal[...]
    itinerary: Optional[ItineraryResult]
```

**参考文档**:
- [LangGraph create_react_agent 源码](file:///C:\Users\Rin\.openclaw\workspace\projects\tripAssistant\venv\Lib\site-packages\langgraph\prebuilt\chat_agent_executor.py#L539)
- [LangChain AgentState 定义](file:///C:\Users\Rin\.openclaw\workspace\projects\tripAssistant\venv\Lib\site-packages\langchain\agents\middleware\types.py#L350)

---

### 5. `add_messages` 导入路径错误

**问题**: `ModuleNotFoundError: No module named 'langgraph.schema'`

**原因**: `add_messages` 不在 `langgraph.schema`，而在 `langgraph.graph.message`。

**解决**: 修改 `travel.py` 导入：
```python
from langgraph.graph.message import add_messages
```

**参考文档**: [LangChain middleware types 源码](file:///C:\Users\Rin\.openclaw\workspace\projects\tripAssistant\venv\Lib\site-packages\langchain\agents\middleware\types.py#L34)

---

### 6. 前端缺少 npm 依赖

**问题**: `Module not found: Can't resolve 'remark-cjk-friendly-gfm-strikethrough'`

**原因**: CopilotKit 依赖的 markdown 处理包未安装。

**解决**:
```bash
pnpm add remark-cjk-friendly remark-cjk-friendly-gfm-strikethrough remark-gfm remark-math rehype-katex rehype-raw rehype-sanitize
```

**参考文档**: [CopilotKit 官方文档](https://docs.copilotkit.ai/)

---

### 7. Agent 端口与前端配置不一致

**问题**: 前端 `.env` 配置 `AGENT_URL=http://localhost:8124`，但 `langgraph dev` 自动选择了端口 2024。

**解决**: 更新 `trip-genuis/.env`:
```
AGENT_URL=http://localhost:2024
```

**参考文档**: [Next.js 环境变量配置](https://nextjs.org/docs/app/building-your-application/configuring/environment-variables)

---

## 最终配置文件

### `apps/agent/langgraph.json`
```json
{
  "python_version": "3.12",
  "dockerfile_lines": [],
  "dependencies": ["."],
  "package_manager": "uv",
  "graphs": {
    "tripgenius_agent": "./main.py:agent"
  },
  "env": "../../.env"
}
```

### `apps/agent/package.json`
```json
{
  "name": "@repo/agent",
  "version": "0.1.0",
  "private": true,
  "scripts": {
    "dev": "langgraph dev --no-browser"
  }
}
```

### `trip-genuis/.env`
```
AGENT_URL=http://localhost:2024
OPENAI_API_KEY=your_minimax_api_key_here
```

---

## 正确的启动步骤

### 1. 关闭所有相关进程
```bash
taskkill /F /IM node.exe
taskkill /F /IM python.exe
```

### 2. 删除锁文件和缓存
```bash
cd trip-genuis
rm -rf apps/agent/.langgraph_api
rm -rf apps/app/.next
```

### 3. 启动服务
```bash
cd trip-genuis
pnpm dev
```

### 4. 访问地址
- **前端**: http://localhost:3000
- **Agent API**: http://127.0.0.1:2024
- **LangGraph Studio**: https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024

---

## 参考文档链接

### CopilotKit
- [CopilotKit 官方文档](https://docs.copilotkit.ai/)
- [LangGraphAgent 参考](https://docs.copilotkit.ai/reference/v1/sdk/python/LangGraphAgent)
- [LangGraph 集成](https://docs.copilotkit.ai/integrations/langgraph)
- [LangGraph Quickstart](https://docs.copilotkit.ai/integrations/langgraph/quickstart)

### LangGraph
- [LangGraph CLI](https://langchain-ai.github.io/langgraph/how-toCLI/)
- [LangGraph Python SDK](https://langchain-ai.github.io/langgraph/reference/python/)
- [create_react_agent 源码](file:///C:\Users\Rin\.openclaw\workspace\projects\tripAssistant\venv\Lib\site-packages\langgraph\prebuilt\chat_agent_executor.py)

### LangChain
- [AgentState 定义](file:///C:\Users\Rin\.openclaw\workspace\projects\tripAssistant\venv\Lib\site-packages\langchain\agents\middleware\types.py)
- [add_messages 位置](file:///C:\Users\Rin\.openclaw\workspace\projects\tripAssistant\venv\Lib\site-packages\langchain\agents\middleware\types.py#L34)

### Next.js
- [环境变量配置](https://nextjs.org/docs/app/building-your-application/configuring/environment-variables)
- [Next.js 16 文档](https://nextjs.org/blog/next-16)

---

## 当前状态

- [x] Agent 服务启动成功 (端口 2024)
- [x] 前端服务启动成功 (端口 3000)
- [ ] 完整对话流程待测试
- [ ] RAG 后端集成待测试

---

## 待解决问题

1. **Peer dependency 警告**: `@langchain/core` 版本不匹配
   - 警告内容: `unmet peer @langchain/core@^1.1.39: found 0.3.80`
   - 暂不影响运行，可后续解决

2. **前端构建警告**: `remark-cjk-friendly-gfm-strikethrough` 可能需要更多依赖
   - 需要测试是否影响功能

3. **Agent 端口动态变化**: `langgraph dev` 自动选择端口，可能导致配置不一致
   - 建议: 固定一个端口，或使用服务发现

---

## 修改的文件列表

1. `apps/agent/langgraph.json` - 修改 graph 导出变量名
2. `apps/agent/package.json` - 移除端口参数
3. `apps/agent/src/travel.py` - 添加 `remaining_steps`，修正 `add_messages` 导入
4. `trip-genuis/.env` - 更新 AGENT_URL 端口
5. `trip-genuis/apps/app/package.json` - 添加缺失的 npm 依赖

---

*最后更新: 2026-04-13*
