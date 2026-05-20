# TripGenius - AI Travel Guide Generator

## Project Overview

**Product Name**: TripGenius (暂定)
**Target Users**: Chinese young people (18-35) planning trips within China and abroad
**Core Value**: Personalized travel itinerary generation based on preferences, budget, and real-time data

---

## 1. System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        User Interface                            │
│                  (WeChat Mini App / App / Web)                 │
└─────────────────────────────────────────────────────────────────┘
                                  │
                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                      API Gateway Layer                            │
│              (FastAPI / Flask + Rate Limiting + Auth)              │
└─────────────────────────────────────────────────────────────────┘
                                  │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
          ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │   Travel     │ │    LLM        │ │   Real-time  │
          │   RAG Engine │ │   Gateway     │ │   Data API   │
          └──────────────┘ └──────────────┘ └──────────────┘
                    │               │               │
                    ▼               ▼               ▼
          ┌──────────────┐ ┌──────────────┐ ┌──────────────┐
          │  Vector DB   │ │   LLM API    │ │  External    │
          │  (Pinecone)  │ │ (GPT-4/MiniMax)│ │  APIs       │
          └──────────────┘ └──────────────┘ └──────────────┘
                                                  │
                        ┌─────────────────────────┼─────────────────────────┐
                        ▼                         ▼                         ▼
              ┌──────────────┐         ┌──────────────┐         ┌──────────────┐
              │  Flight API  │         │  Hotel API   │         │  小红书数据    │
              │ (Skyscanner/  │         │ (Booking.com/│         │   爬虫数据     │
              │  Google Flights)│         │   携程)      │         │               │
              └──────────────┘         └──────────────┘         └──────────────┘
```

---

## 2. 小红书数据采集方案 (OCR + LLM 决策)

### 2.1 技术方案

采用 **浏览器自动化 + OCR + LLM智能决策** 的方案

#### 工具栈

| 组件 | 工具 | 成本说明 |
|------|------|----------|
| **浏览器控制** | Playwright | 开源免费 |
| **OCR识别** | PaddleOCR (本地) | 算力成本，无API费用 |
| **元素定位** | OpenCV + 模板匹配 | 开源免费 |
| **截图** | Playwright screenshot | 免费 |
| **LLM决策** | GPT-4/MiniMax | 按Token计费 |

#### 成本说明

```
PaddleOCR: 本地运行，无API费用
- 成本 = GPU/CPU算力 (自建服务器约¥500/月)
- 或使用云GPU (约¥0.5/小时)

LLM调用:
- GPT-4: 约¥0.1/千Token
- MiniMax: 约¥0.01/千Token
- 每次搜索约消耗5000-10000 Token
- 成本 ≈ ¥0.0005-0.001/次
```

---

## 2.2 核心流程 (LLM决策版)

```
┌─────────────────────────────────────────────────────────────────┐
│                        主流程                                     │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. 打开小红书网页                                               │
│     ↓                                                            │
│  2. OCR扫描页面 → 定位搜索框坐标                                  │
│     ↓                                                            │
│  3. 模拟输入关键字 → 等待结果加载                                 │
│     ↓                                                            │
│  4. 截图 → OCR识别搜索结果列表                                    │
│     ↓                                                            │
│  5. 🤖 LLM决策: "哪个结果最值得点击?"                             │
│     ↓                                                            │
│  6. 根据决策坐标 → 模拟点击进入详情页                             │
│     ↓                                                            │
│  7. 详情页截图 → OCR提取正文内容                                  │
│     ↓                                                            │
│  8. LLM解析 → 结构化数据 (地点/预算/风格)                         │
│     ↓                                                            │
│  9. 返回上一页 → 重复4-8 → 收集多条数据                           │
│     ↓                                                            │
│  10. 数据整理入库                                                 │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2.3 LLM决策Prompt

```python
DECISION_PROMPT = """
你是一个专业的攻略筛选助手。以下是小红书OCR识别的搜索结果列表:

{ocr_results}

每条结果包含: 标题、点赞数、评论片段

请根据以下标准选择最佳攻略:
1. 点赞数 > 1000
2. 评论内容积极正面
3. 发布时间 < 1年内
4. 内容完整度高 (有行程安排/具体地点)

请返回JSON格式:
{{
    "index": 0-9的数字,
    "reason": "选择理由",
    "expected_content": "预期内容类型"
}}

只返回JSON，不要其他文字。
"""
```

---

## 2.4 代码实现

```python
from playwright.sync_api import sync_playwright
from paddleocr import PaddleOCR
import openai
import json

class SmartXHSCollector:
    def __init__(self):
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.page = self.browser.new_page()
        self.ocr = PaddleOCR(use_angle_cls=True, use_gpu=False)
        self.llm = OpenAI()
    
    def find_element_by_ocr(self, target_text):
        """OCR定位页面元素"""
        screenshot = self.page.screenshot()
        result = self.ocr.ocr(screenshot)
        
        for line in result:
            bbox = line[0]
            text = line[1][0]
            if target_text in text:
                x = (bbox[0][0] + bbox[2][0]) / 2
                y = (bbox[0][1] + bbox[2][1]) / 2
                return x, y
        return None
    
    def ocr_page(self):
        """OCR识别当前页面"""
        screenshot = self.page.screenshot()
        result = self.ocr.ocr(screenshot)
        
        items = []
        for line in result:
            bbox, (text, confidence) = line
            if confidence > 0.6:
                items.append({
                    'text': text,
                    'bbox': bbox,
                    'confidence': confidence
                })
        return items
    
    def extract_results_list(self, ocr_items):
        """从OCR结果提取搜索列表"""
        results = []
        for i, item in enumerate(ocr_items):
            text = item['text']
            likes = re.findall(r'(\d+\.?\d*万?)赞', text)
            titles = re.findall(r'([^赞\n]{5,50})', text)
            
            results.append({
                'index': i,
                'text': text[:100],
                'bbox': item['bbox'],
                'likes': likes[0] if likes else '未知',
                'title': titles[0] if titles else '未知'
            })
        return results
    
    def llm_decide(self, results):
        """LLM决定点击哪个"""
        formatted = '\n'.join([
            f"{r['index']}. {r['title']} - {r['likes']}赞"
            for r in results
        ])
        
        prompt = f"""
你是攻略筛选专家。OCR识别到以下结果:

{formatted}

返回JSON: {{"index": 数字, "reason": "理由"}}
"""
        
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        return json.loads(response.choices[0].message.content)
    
    def click_target(self, ocr_items, target_idx):
        """根据OCR索引点击"""
        if target_idx < len(ocr_items):
            bbox = ocr_items[target_idx]['bbox']
            x = (bbox[0][0] + bbox[2][0]) / 2
            y = (bbox[0][1] + bbox[2][1]) / 2
            self.page.mouse.click(x, y)
            return True
        return False
    
    def collect_detail(self):
        """收集详情页内容"""
        self.page.wait_for_timeout(2000)
        screenshot = self.page.screenshot()
        result = self.ocr.ocr(screenshot)
        
        content = '\n'.join([line[1][0] for line in result])
        
        structured_prompt = f"""
从以下小红书笔记内容提取结构化信息:

{content[:3000]}

返回JSON:
{{
    "location": "地点",
    "budget_level": "low/mid/high",
    "travel_style": ["chill", "美食", "打卡"],
    "key_spots": ["景点1", "景点2"],
    "restaurant_tips": ["餐厅推荐"],
    "best_season": "推荐季节"
}}
"""
        
        response = self.llm.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": structured_prompt}]
        )
        
        return json.loads(response.choices[0].message.content)
    
    def run(self, keyword, num_samples=10):
        """采集主流程"""
        all_data = []
        
        # 1. 打开小红书
        self.page.goto('https://www.xiaohongshu.com')
        self.page.wait_for_load_state('networkidle')
        
        # 2. 定位搜索框并输入
        search_pos = self.find_element_by_ocr('搜索')
        if search_pos:
            self.page.mouse.click(*search_pos)
            self.page.keyboard.type(keyword)
            self.page.keyboard.press('Enter')
            self.page.wait_for_timeout(3000)
        
        # 3. 循环采集
        for _ in range(num_samples):
            ocr_items = self.ocr_page()
            results = self.extract_results_list(ocr_items)
            
            # LLM决策
            decision = self.llm_decide(results)
            
            # 点击目标
            self.click_target(ocr_items, decision['index'])
            self.page.wait_for_timeout(2000)
            
            # 收集详情
            detail = self.collect_detail()
            all_data.append(detail)
            
            # 返回
            self.page.go_back()
            self.page.wait_for_timeout(1000)
        
        self.browser.close()
        return all_data
```

---

## 2.5 成本估算

| 项目 | 成本 |
|------|------|
| PaddleOCR | ¥0 (本地运行，无API费) |
| GPT-4 决策 | ¥0.0005/次 |
| GPT-4 解析 | ¥0.002/次 |
| **单条数据** | **¥0.0025** |
| **1000条数据** | **¥2.5** |

---

## 2.6 法律风险

```
⚠️ 重要提示:
- 小红书ToS禁止未经授权的数据抓取
- 即使技术可行，仍存在法律风险
- 建议仅用于个人学习/小规模测试

替代方案:
1. 官方开放平台 (如有)
2. 用户UGC自愿分享
3. 穷游/马蜂窝公开数据
```

---

## 3. Module Definitions

### 3.1 Data Collection Module (数据采集层)

#### 3.1.1 小红书爬虫系统 (OCR + LLM方案)

| Component | Function | Tech Stack |
|-----------|----------|------------|
| **Spider Core** | 浏览器自动化操作 | Python (Playwright) |
| **OCR Engine** | 文本识别 + 元素定位 | PaddleOCR |
| **LLM Decision** | 智能筛选最佳攻略 | GPT-4/MiniMax |
| **Anti-Detection** | 绕过反爬机制 | Proxy, UA rotation |

#### 3.1.2 官方数据源

| Source | Data Type | API/Method |
|--------|-----------|------------|
| 马蜂窝 | 景点介绍、攻略 | 官方API / 爬虫 |
| 携程 | 景点、酒店评论 | 开放平台API |
| 大众点评 | 餐厅、商户 | 官方API |
| 旅游局官网 | 官方景点信息 | Web scraping |

---

### 3.2 Data Processing Module (数据处理层)

#### 3.2.1 Text Embedding Pipeline

```
Raw Text → Cleaning → Chunking → Embedding → Vector DB

Cleaning: 去广告、去水印、标准化
Chunking: 512 tokens, 50 tokens overlap
Embedding: text-embedding-3-small / BGE-large-zh
```

#### 3.2.2 Knowledge Base Structure

| Collection | Description | Chunk Size |
|-----------|-------------|------------|
| `destinations` | 目的地基本信息 | 512 |
| `attractions` | 景点详细攻略 | 768 |
| `restaurants` | 餐厅推荐 | 512 |
| `hotels` | 酒店评价 | 512 |
| `itineraries` | 完整攻略范例 | 1024 |
| `tips` | 实用小贴士 | 256 |

---

### 3.3 RAG Engine Module (RAG引擎层)

#### 3.3.1 LangChain Pipeline

```python
from langchain.prompts import PromptTemplate
from langchain.chains import RetrievalQA
from langchain.retrievers import MultiQueryRetriever

# Query理解
User Input: "我想去日本看樱花，5天预算1万"
    ↓
LLM解析:
{
    "destination": "日本",
    "purpose": "赏樱",
    "duration": 5,
    "budget": 10000,
    "currency": "CNY"
}

# 多路召回
retriever = MultiQueryRetriever(
    retriever=vectorstore.as_retriever(search_kwargs={"k": 10}),
    llm=llm,
    queries=[
        "日本樱花景点推荐",
        "日本5天行程安排",
        "日本1万预算住宿"
    ]
)

# 生成
prompt = """
你是一位专业的旅行规划师。根据以下信息为用户规划一次日本赏樱之旅。
...
"""
```

---

### 3.4 LLM Gateway Module (LLM网关层)

#### 3.4.1 Multi-Model Support

| Model | Use Case | Pros |
|-------|-----------|------|
| **GPT-4** | 复杂行程规划 | 效果好，贵 |
| **GPT-3.5-turbo** | 简单问答 | 便宜，快速 |
| **MiniMax** | 中文生成 | 便宜，中文好 |
| **Qwen** | 简单对话 | 开源，部署灵活 |

#### 3.4.2 Prompt Template System

```python
TRAVEL_STYLE_PROMPTS = {
    "chill": "你是一位轻松的旅行博主，擅长发现小众但品质感十足的地方...",
    "出片": "你是一位摄影旅行达人，关注每一个能拍出美照的打卡点...",
    "美食": "你是一位美食家，对各地特色美食如数家珍...",
    "打卡": "你是一位网红景点专家，精通必打卡的热门目的地..."
}

BUDGET_PROMPTS = {
    "穷游": "预算有限但想玩得精彩? 教你花小钱玩转...",
    "轻奢": "追求品质但不浪费，这套攻略让你值回票价...",
    "土豪": "最好的体验，最优的服务，只需要..."
}
```

---

### 3.5 Real-Time Data Module (实时数据层)

#### 3.5.1 Flight API Integration

| API | 覆盖范围 | 费用 |
|-----|---------|------|
| Skyscanner API | 全球 | 按调用收费 |
| Google Flights | 全球 | 免费 (limited) |
| 携程API | 中国出发 | 商业合作 |
| Amadeus | 全球 | 按调用 |

#### 3.5.2 Hotel API Integration

| API | 覆盖范围 | 费用 |
|-----|---------|------|
| Booking.com Affiliate | 全球 | 佣金分成 |
| Agoda API | 亚太 | 佣金分成 |
| 携程酒店云 | 中国 | 商业合作 |

---

## 4. Key Technical Challenges & Solutions

### 4.1 小红书数据获取

| Challenge | Solution |
|-----------|----------|
| 反爬机制 | Proxy pool + UA rotation + request throttling |
| 数据量大 | Incremental crawling + distributed workers |
| 内容质量 | LLM辅助清洗 + 人工抽检 |
| **法律风险** | ⚠️ 仅个人学习使用 |

### 4.2 实时价格获取

| Challenge | Solution |
|-----------|----------|
| API费用高 | 缓存 + 按需调用 |
| 实时性要求 | 价格缓存1小时，过期提示刷新 |
| 链接跳转 | Affiliate合作获取佣金 |

---

## 5. Data Schema

### 5.1 Destination

```sql
CREATE TABLE destinations (
    id SERIAL PRIMARY KEY,
    name_cn VARCHAR(100),
    name_en VARCHAR(100),
    country VARCHAR(50),
    region VARCHAR(50),
    description TEXT,
    best_season VARCHAR(50),
    avg_budget_day DECIMAL(10,2),
    tags TEXT[],
    popularity_score FLOAT,
    embedding_id VARCHAR(100),
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

### 5.2 Itinerary

```sql
CREATE TABLE itineraries (
    id SERIAL PRIMARY KEY,
    destination_id INT,
    user_id INT,
    title VARCHAR(200),
    duration_days INT,
    budget_level VARCHAR(20),
    content JSONB,
    is_public BOOLEAN DEFAULT FALSE,
    likes_count INT,
    created_at TIMESTAMP
);
```

---

## 6. Project Roadmap

### Phase 1: MVP (4-6 weeks)
- [ ] 小红书数据爬虫 + 清洗 (OCR+LLM方案)
- [ ] 基础Vector DB搭建
- [ ] 简单RAG流程
- [ ] 单轮对话生成
- [ ] 微信小程序demo

### Phase 2: Enhancement (6-8 weeks)
- [ ] 多轮对话支持
- [ ] 实时价格API集成
- [ ] 旅行风格偏好
- [ ] User Profile系统

### Phase 3: Commercial (8-10 weeks)
- [ ] 预订链接Affiliate
- [ ] 社区UGC
- [ ] 付费会员
- [ ] 运营数据分析

---

## 7. Tech Stack

| Layer | Technology |
|-------|-------------|
| **Frontend** | React / Flutter / WeChat Mini Program |
| **Backend** | Python (FastAPI) / Node.js |
| **Database** | PostgreSQL + Redis |
| **Vector DB** | Pinecone / Milvus / Qdrant |
| **LLM** | OpenAI GPT-4 / MiniMax |
| **RAG** | LangChain / LlamaIndex |
| **Crawling** | Playwright + PaddleOCR |
| **Deployment** | Docker / Vercel |
| **Analytics** | Amplitude / Mixpanel |

---

## 8. Cost Estimation (MVP)

| Item | Monthly Cost (CNY) |
|------|-------------------|
| Server (with GPU for OCR) | 3,000 - 8,000 |
| Vector DB (Pinecone) | 500 - 2,000 |
| LLM API (GPT-4) | 2,000 - 8,000 |
| Data Storage | 500 - 1,000 |
| **Total** | **6,000 - 19,000/月** |

---

## 9. Monetization

1. **Affiliate佣金**: 机票、酒店、景点门票
2. **付费会员**: 高级功能、解锁更多行程
3. **企业B端**: 定制化旅行规划API
4. **广告**: 品牌合作推广

---

*Created: 2026-04-11*
*Status: Planning Stage*
