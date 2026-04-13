# TripGenius Frontend

基于 CopilotKit + LangGraph 的旅行规划 Agent 前端。

## 功能

- 🤖 多轮对话式旅行规划 Agent
- 💬 实时流式响应
- 📝 自动收集旅行信息（目的地、天数、预算、风格、出发日期等）
- 🎨 生成个性化行程

## 架构

```
Frontend (Next.js + CopilotChat)
    ↓ HTTP
API Route (/api/copilotkit)
    ↓
CopilotRuntime
    ↓ LangGraphAgent
Python Agent (port 8123)
    ↓ HTTP
RAG Backend (port 8000)
```

## 快速开始

### 1. 安装依赖

```bash
pnpm install
```

### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：
```env
OPENAI_API_KEY=your-openai-api-key-here
AGENT_URL=http://localhost:8123
```

### 3. 启动服务

需要先启动后端服务，参见顶层 README。

```bash
pnpm dev
```

## 技术栈

- Next.js 16
- React 19
- TailwindCSS 4
- CopilotKit v1.55
- TypeScript

## 对话示例

```
用户: 我想去成都7天美食之旅，预算5000
Agent: 好的！我来帮您规划成都 7天 美食风格旅行。请问您计划几号出发呢？

用户: 4月20日
Agent: 好的，4月20日出发。请问您从哪个城市出发呢？

用户: 上海
Agent: 从上海出发是个好选择！到成都建议乘坐高铁或飞机。请问您更倾向于哪种交通方式？

用户: 飞机
Agent: 好的，飞机前往。请问几位入住？需要什么房型？

用户: 2人，大床房
Agent: 好的，信息已收集完毕！让我为您规划一份详细的行程...

[行程结果]
```

## License

MIT
