# AG-UI 快速配置指南

## Step 1: 初始化项目

### 前端 (React + CopilotKit)

```bash
# 使用官方 CLI 初始化
npx create-ag-ui@latest my-agent-app
# 或
npx create-ag-ui-app my-agent-app

# 进入目录
cd my-agent-app

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

访问 `http://localhost:3000` 查看初始界面。

### 后端 (Python FastAPI)

```bash
# 在项目根目录创建后端目录
mkdir -p server
cd server

# 创建虚拟环境
python -m venv venv
venv\Scripts\activate  # Windows

# 安装 AG-UI Python SDK
pip install ag-ui-protocol

# 安装 FastAPI 和 uvicorn
pip install fastapi uvicorn python-dotenv
```

## Step 2: 配置后端 (Python FastAPI)

创建 `server/main.py`:

```python
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from ag_ui.core import (
    RunAgentInput,
    EventType,
    RunStartedEvent,
    TextMessageStartEvent,
    TextMessageContentEvent,
    TextMessageEndEvent,
    RunFinishedEvent,
)
from ag_ui.encoder import EventEncoder
from dotenv import load_dotenv
import os

load_dotenv()

app = FastAPI(title="TripGenius Agent")

@app.post("/api/agent")
async def agent_endpoint(input_data: RunAgentInput, request: Request):
    encoder = EventEncoder(accept=request.headers.get("accept"))

    async def events():
        # 1. 发送 RunStartedEvent
        yield encoder.encode(RunStartedEvent(
            type=EventType.RUN_STARTED,
            thread_id=input_data.thread_id,
            run_id=input_data.run_id
        ))

        # 2. 获取用户消息
        user_message = input_data.messages[-1].content if input_data.messages else ""

        # 3. 处理并生成回复 (这里先用一个简单的例子)
        yield encoder.encode(TextMessageStartEvent(
            type=EventType.TEXT_MESSAGE_START,
            message_id="msg_1",
            role="assistant"
        ))

        # 模拟流式输出
        response_text = f"收到您的消息: {user_message}\n请问您计划什么时候出发？"
        for char in response_text:
            yield encoder.encode(TextMessageContentEvent(
                type=EventType.TEXT_MESSAGE_CONTENT,
                message_id="msg_1",
                delta=char
            ))

        yield encoder.encode(TextMessageEndEvent(
            type=EventType.TEXT_MESSAGE_END,
            message_id="msg_1"
        ))

        # 4. 发送 RunFinishedEvent
        yield encoder.encode(RunFinishedEvent(
            type=EventType.RUN_FINISHED,
            thread_id=input_data.thread_id,
            run_id=input_data.run_id
        ))

    return StreamingResponse(
        events(),
        media_type=encoder.get_content_type()
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

## Step 3: 配置前端环境变量

在 `my-agent-app` 目录创建 `.env.local`:

```env
NEXT_PUBLIC_AGENT_URL=http://localhost:8000/api/agent
```

## Step 4: 连接前后端

查看 `my-agent-app/src/app.tsx` 或 `src/App.tsx`，找到 CopilotKit 配置：

```typescript
import { CopilotProvider } from "@copilotkit/react-core"
import {agent} from "./agent" // 你的 agent 配置

export function App() {
  return (
    <CopilotProvider agent={agent}>
      {/* 你的应用内容 */}
    </CopilotProvider>
  )
}
```

## Step 5: 测试

1. **启动后端**:
```bash
cd server
python main.py
```

2. **启动前端** (另一个终端):
```bash
cd my-agent-app
npm run dev
```

3. **访问**: `http://localhost:3000/copilotkit`

---

## 关键概念

### AG-UI 事件流

| 事件 | 作用 |
|-----|------|
| `RUN_STARTED` | 会话开始 |
| `TEXT_MESSAGE_START` | 消息开始 |
| `TEXT_MESSAGE_CONTENT` | 流式输出内容 |
| `TEXT_MESSAGE_END` | 消息结束 |
| `RUN_FINISHED` | 会话结束 |

### 前端调用方式

```typescript
import { useAgentRuntime } from "@copilotkit/react-core"

// 在组件中
const runtime = useAgentRuntime({
  agentId: "your-agent-id",
})

// 发送消息
await runtime.generate({
  input: "我想去成都"
})
```

---

## 依赖版本要求

- **Node.js**: 22.13.0 或更高
- **Python**: 3.9+
- **ag-ui-protocol**: 最新版本
- **pnpm** (可选，npm 也可以)
