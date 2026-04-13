# TripGenius

An AI-powered travel planning assistant built with CopilotKit, LangGraph, and MiniMax API. Plan your perfect trip through natural conversation.

[English](#english) | [中文](#中文)

---

## English

### Overview

TripGenius is a conversational AI agent that helps users plan personalized travel itineraries through multi-turn dialogue. Simply tell the agent your destination, travel dates, budget, and preferences, and it will collect the necessary information step by step before generating a customized travel plan.

### Features

- 🤖 **Multi-turn Conversational Agent** - Natural language interaction for travel planning
- 💬 **Real-time Streaming Responses** - Instant feedback as the agent processes your request
- 📝 **Automated Information Collection** - Step-by-step collection of destination, dates, budget, style, and preferences
- 🎨 **Personalized Itinerary Generation** - AI-generated travel plans tailored to your needs
- 🔗 **RAG-Enhanced Responses** - Retrieval-augmented generation for accurate destination information

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                          │
│                   (Next.js + CopilotKit)                   │
│                    http://localhost:3000                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   CopilotRuntime                            │
│              + LangGraphAgent (HTTP)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ LangGraph Protocol (SSE)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Python Agent (LangGraph)                   │
│                    port: 2024 (auto)                        │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  State: travel_request, current_step, itinerary    │    │
│  │  Tools: start_planning, confirm_date, confirm_     │    │
│  │         departure, confirm_transport, confirm_    │    │
│  │         travelers, generate_itinerary             │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   RAG Backend (FastAPI)                      │
│                     port: 8000                               │
│              /api/generate - Itinerary Generation            │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, TailwindCSS 4, CopilotKit v1.55 |
| Agent | LangGraph, Python, MiniMax API (OpenAI-compatible) |
| Backend | FastAPI, RAG, FAISS, Sentence Transformers |
| Infrastructure | Turborepo, pnpm workspaces |

### Quick Start

#### Prerequisites

- Node.js 18+
- Python 3.12+
- pnpm
- MiniMax API Key

#### 1. Install Dependencies

```bash
pnpm install
```

#### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env`:

```env
AGENT_URL=http://localhost:2024
RAG_BACKEND_URL=http://localhost:8000
OPENAI_BASE_URL=https://api.minimax.io/v1
OPENAI_MODEL_NAME=MiniMax-M2.7
OPENAI_API_KEY=your_minimax_api_key_here
```

#### 3. Start Services

**Option A: Start All Services (Recommended)**

```bash
# Terminal 1: Start RAG Backend
cd trip-genuis
python -m uvicorn src.api.main:app --port 8000 --reload

# Terminal 2: Start Frontend + Agent
pnpm dev
```

**Option B: Frontend Only (for UI testing)**

```bash
pnpm dev
# Agent will start automatically via langgraph dev
```

#### 4. Access the Application

- **Frontend**: http://localhost:3000
- **LangGraph Studio**: https://smith.langchain.com/studio (for agent debugging)

### Conversation Flow

```
User: I want to go to Chengdu for 7 days, food tour, budget 5000
Agent: Great! Let me plan a 7-day food tour in Chengdu. When do you plan to depart?

User: April 20th
Agent: April 20th departure. Which city will you be traveling from?

User: Shanghai
Agent: Shanghai is a great origin! For travel to Chengdu, I recommend flights or high-speed rail. Which do you prefer?

User: Flight
Agent: Flying it is. How many guests will be staying? What room type do you need?

User: 2 people, one king bed room
Agent: Got it! Let me collect all the details and create your personalized itinerary...

[Itinerary Result]
```

### Project Structure

```
trip-genuis/
├── apps/
│   ├── app/                    # Next.js Frontend
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── page.tsx          # Main page
│   │   │   │   └── api/copilotkit/   # CopilotKit API route
│   │   │   └── components/           # UI components
│   │   └── package.json
│   └── agent/                   # LangGraph Python Agent
│       ├── main.py                     # Agent entry point
│       ├── langgraph.json              # LangGraph configuration
│       └── src/
│           └── travel.py                # Travel planning tools & state
├── src/                         # RAG Backend (FastAPI)
│   ├── api/main.py
│   └── rag/
├── package.json                  # Turborepo workspace root
├── turbo.json
└── pnpm-workspace.yaml
```

### Configuration Files

| File | Purpose |
|------|---------|
| `apps/agent/langgraph.json` | LangGraph agent configuration |
| `apps/agent/main.py` | Agent entry point (exports `agent`) |
| `apps/app/src/app/api/copilotkit/[[...slug]]/route.ts` | CopilotKit API route |
| `.env` | Environment variables (not committed) |

### Troubleshooting

#### Port Already in Use

If you see `Port 8123/2024 is already in use`, clean up the langgraph cache:

```bash
cd apps/agent
rm -rf .langgraph_api
pnpm dev
```

#### Module Not Found Errors

If you encounter missing npm packages:

```bash
pnpm add remark-cjk-friendly remark-cjk-friendly-gfm-strikethrough remark-gfm remark-math rehype-katex rehype-raw rehype-sanitize
```

#### Next.js Lock Error

If `.next/dev/lock` error occurs:

```bash
taskkill /F /IM node.exe
rm -rf apps/app/.next
pnpm dev
```

### License

MIT

---

## 中文

### 概述

TripGenius 是一款基于人工智能的旅行规划助手，由 CopilotKit、LangGraph 和 MiniMax API 提供支持。通过自然对话的方式，帮助用户规划个性化的旅行行程。只需告诉 Agent 你的目的地、旅行日期、预算和偏好，它会逐步收集所需信息，然后生成定制化的旅行计划。

### 功能特点

- 🤖 **多轮对话式 Agent** - 通过自然语言交互进行旅行规划
- 💬 **实时流式响应** - Agent 处理请求时即时反馈
- 📝 **自动信息收集** - 逐步收集目的地、日期、预算、风格偏好等信息
- 🎨 **个性化行程生成** - 根据用户需求 AI 生成定制化旅行计划
- 🔗 **RAG 增强响应** - 检索增强生成，提供准确的目的地信息

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                      用户界面                               │
│                   (Next.js + CopilotKit)                   │
│                    http://localhost:3000                    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   CopilotRuntime                            │
│              + LangGraphAgent (HTTP)                        │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ LangGraph 协议 (SSE)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Python Agent (LangGraph)                    │
│                    端口: 2024 (自动选择)                     │
│  ┌─────────────────────────────────────────────────────┐    │
│  │  状态: travel_request, current_step, itinerary      │    │
│  │  工具: start_planning, confirm_date, confirm_       │    │
│  │        departure, confirm_transport, confirm_       │    │
│  │        travelers, generate_itinerary                │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
                              │
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                   RAG 后端 (FastAPI)                       │
│                     端口: 8000                              │
│              /api/generate - 行程生成                       │
└─────────────────────────────────────────────────────────────┘
```

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 16, React 19, TailwindCSS 4, CopilotKit v1.55 |
| Agent | LangGraph, Python, MiniMax API (OpenAI 兼容) |
| 后端 | FastAPI, RAG, FAISS, Sentence Transformers |
| 基础设施 | Turborepo, pnpm workspaces |

### 快速开始

#### 前置要求

- Node.js 18+
- Python 3.12+
- pnpm
- MiniMax API Key

#### 1. 安装依赖

```bash
pnpm install
```

#### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```env
AGENT_URL=http://localhost:2024
RAG_BACKEND_URL=http://localhost:8000
OPENAI_BASE_URL=https://api.minimax.io/v1
OPENAI_MODEL_NAME=MiniMax-M2.7
OPENAI_API_KEY=your_minimax_api_key_here
```

#### 3. 启动服务

**方式一：启动所有服务（推荐）**

```bash
# 终端 1: 启动 RAG 后端
cd trip-genuis
python -m uvicorn src.api.main:app --port 8000 --reload

# 终端 2: 启动前端 + Agent
pnpm dev
```

**方式二：仅启动前端（仅测试 UI）**

```bash
pnpm dev
# Agent 会通过 langgraph dev 自动启动
```

#### 4. 访问应用

- **前端**: http://localhost:3000
- **LangGraph Studio**: https://smith.langchain.com/studio (用于 Agent 调试)

### 对话示例

```
用户: 我想去成都7天美食之旅，预算5000
Agent: 好的！我来帮您规划成都 7天 美食风格旅行。请问您计划几号出发呢？

用户: 4月20日
Agent: 4月20日出发。请问您从哪个城市出发呢？

用户: 上海
Agent: 从上海出发是个好选择！到成都建议乘坐高铁或飞机。请问您更倾向于哪种交通方式？

用户: 飞机
Agent: 好的，飞机前往。请问几位入住？需要什么房型？

用户: 2人，大床房
Agent: 好的，信息已收集完毕！让我为您规划一份详细的行程...

[行程结果]
```

### 项目结构

```
trip-genuis/
├── apps/
│   ├── app/                    # Next.js 前端
│   │   ├── src/
│   │   │   ├── app/
│   │   │   │   ├── page.tsx          # 主页面
│   │   │   │   └── api/copilotkit/   # CopilotKit API 路由
│   │   │   └── components/           # UI 组件
│   │   └── package.json
│   └── agent/                   # LangGraph Python Agent
│       ├── main.py                     # Agent 入口
│       ├── langgraph.json              # LangGraph 配置
│       └── src/
│           └── travel.py                # 旅行规划工具和状态
├── src/                         # RAG 后端 (FastAPI)
│   ├── api/main.py
│   └── rag/
├── package.json                  # Turborepo 工作区根目录
├── turbo.json
└── pnpm-workspace.yaml
```

### 配置文件说明

| 文件 | 说明 |
|------|------|
| `apps/agent/langgraph.json` | LangGraph Agent 配置 |
| `apps/agent/main.py` | Agent 入口文件（导出 `agent`） |
| `apps/app/src/app/api/copilotkit/[[...slug]]/route.ts` | CopilotKit API 路由 |
| `.env` | 环境变量（不提交到 Git） |

### 常见问题

#### 端口被占用

如果遇到 `Port 8123/2024 is already in use`，清理 langgraph 缓存：

```bash
cd apps/agent
rm -rf .langgraph_api
pnpm dev
```

#### 模块找不到

如果遇到 npm 包缺失错误：

```bash
pnpm add remark-cjk-friendly remark-cjk-friendly-gfm-strikethrough remark-gfm remark-math rehype-katex rehype-raw rehype-sanitize
```

#### Next.js 锁文件错误

如果出现 `.next/dev/lock` 错误：

```bash
taskkill /F /IM node.exe
rm -rf apps/app/.next
pnpm dev
```

### License

MIT
