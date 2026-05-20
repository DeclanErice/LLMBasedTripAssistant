# TripGenius

An AI-powered travel planning assistant built with CopilotKit, LangGraph, and Anthropic Claude API.

[English](#english) | [中文](#中文)

---

## English

### Overview

TripGenius is a conversational AI agent that helps users plan personalized travel itineraries through multi-turn dialogue. Tell the agent your destination, travel dates, budget, and preferences — it collects information step by step and generates a customized travel plan backed by a RAG knowledge base.

### Features

- 🤖 **Multi-turn Conversational Agent** — Natural language interaction for travel planning
- 💬 **Real-time Streaming Responses** — Instant feedback as the agent processes your request
- 📝 **Automated Information Collection** — Step-by-step collection of destination, dates, budget, style, and preferences
- 🎨 **Personalized Itinerary Generation** — AI-generated travel plans tailored to your needs
- 🔗 **RAG-Enhanced Responses** — FAISS vector store + text2vec-base-chinese for accurate destination context

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User Interface                          │
│                   (Next.js + CopilotKit)                    │
│                    http://localhost:3000                     │
└─────────────────────────────────────────────────────────────┘
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│              CopilotRuntime + LangGraphAgent (HTTP)          │
└─────────────────────────────────────────────────────────────┘
                              │ LangGraph Protocol (SSE)
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  Python Agent (LangGraph)  :8123             │
│   Tools: start_planning, confirm_*, generate_itinerary       │
└─────────────────────────────────────────────────────────────┘
                              │ HTTP
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                  RAG Backend (FastAPI)  :8000                │
│   /api/generate  /api/chat  /api/agent                       │
│   LLM: Anthropic Claude  |  Vector DB: FAISS                 │
└─────────────────────────────────────────────────────────────┘
```

### Tech Stack

| Layer | Technology |
|-------|------------|
| Frontend | Next.js 16, React 19, TailwindCSS 4, CopilotKit v1.55 |
| Agent | LangGraph, Python |
| LLM | Anthropic Claude API (claude-haiku-4-5 default) |
| Backend | FastAPI, RAG, FAISS, Sentence Transformers |
| Infrastructure | Turborepo, pnpm workspaces |

### Quick Start

#### Prerequisites

- Node.js 18+, Python 3.12+, pnpm
- Anthropic API Key

#### 1. Install dependencies

```bash
# Python backend
pip install -r requirements.txt

# Frontend
cd trip-genuis && pnpm install
```

#### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env`:

```env
ANTHROPIC_API_KEY=sk-ant-your-key-here
ANTHROPIC_MODEL_NAME=claude-haiku-4-5
AGENT_URL=http://localhost:8123
RAG_BACKEND_URL=http://localhost:8000
API_HOST=0.0.0.0
API_PORT=8000
```

#### 3. Initialize knowledge base

```bash
python scripts/init_db.py
```

#### 4. Start services (3 terminals)

```bash
# Terminal 1: RAG backend
python -m uvicorn src.api.main:app --reload --port 8000

# Terminal 2: LangGraph agent
cd trip-genuis/apps/agent
uvicorn main:app --reload --port 8123

# Terminal 3: Frontend
cd trip-genuis
pnpm dev
```

#### 5. Access

- Frontend: http://localhost:3000
- RAG API: http://localhost:8000
- Agent API: http://localhost:8123

### Troubleshooting

**Port already in use:**
```bash
cd trip-genuis/apps/agent && rm -rf .langgraph_api && pnpm dev
```

**Next.js lock error:**
```bash
taskkill /F /IM node.exe && rm -rf trip-genuis/apps/app/.next && pnpm dev
```

### License

MIT

---

## 中文

### 概述

TripGenius 是一款基于 AI 的旅行规划助手，使用 CopilotKit、LangGraph 和 Anthropic Claude API。通过自然对话帮助用户规划个性化行程，逐步收集目的地、日期、预算等信息后，结合 RAG 知识库生成定制化旅行计划。

### 功能特点

- 🤖 **多轮对话式 Agent** — 通过自然语言交互进行旅行规划
- 💬 **实时流式响应** — Agent 处理请求时即时反馈
- 📝 **自动信息收集** — 逐步收集目的地、日期、预算、风格偏好
- 🎨 **个性化行程生成** — 根据用户需求 AI 生成定制旅行计划
- 🔗 **RAG 增强** — FAISS 向量库 + text2vec-base-chinese 提供精准目的地信息

### 技术栈

| 层级 | 技术 |
|------|------|
| 前端 | Next.js 16, React 19, TailwindCSS 4, CopilotKit v1.55 |
| Agent | LangGraph, Python |
| LLM | Anthropic Claude API（默认 claude-haiku-4-5） |
| 后端 | FastAPI, RAG, FAISS, Sentence Transformers |
| 基础设施 | Turborepo, pnpm workspaces |

### 快速开始

#### 1. 安装依赖

```bash
pip install -r requirements.txt
cd trip-genuis && pnpm install
```

#### 2. 配置环境变量

```bash
cp .env.example .env
```

编辑 `.env`：

```env
ANTHROPIC_API_KEY=sk-ant-你的key
ANTHROPIC_MODEL_NAME=claude-haiku-4-5
AGENT_URL=http://localhost:8123
RAG_BACKEND_URL=http://localhost:8000
```

#### 3. 初始化知识库

```bash
python scripts/init_db.py
```

#### 4. 启动服务（三个终端）

```bash
# 终端 1：RAG 后端
python -m uvicorn src.api.main:app --reload --port 8000

# 终端 2：LangGraph Agent
cd trip-genuis/apps/agent
uvicorn main:app --reload --port 8123

# 终端 3：前端
cd trip-genuis && pnpm dev
```

#### 5. 访问

- 前端：http://localhost:3000
- RAG API：http://localhost:8000
- Agent API：http://localhost:8123

### 项目结构

```
tripAssistant/
├── src/                    # Python RAG 后端
│   ├── api/                # FastAPI 路由
│   ├── rag/                # RAG 核心（解析/检索/生成）
│   └── embedding/          # FAISS + text2vec
├── data/                   # 知识库数据（15个目的地）
├── scripts/                # init_db.py, demo_agent.py
├── trip-genuis/            # 前端 + LangGraph Agent
│   └── apps/
│       ├── app/            # Next.js 前端
│       └── agent/          # Python LangGraph Agent
└── requirements.txt
```

### License

MIT
