# 虾塘大亨 · Agent 开发路线图

> 目标：构建三个专业 AI Agent，覆盖养殖决策全链路（实时 → 日度 → 周度）  
> 原则：每个 Agent 独立可测、接口对齐、渐进上线

---

## 架构总览

```
传感器数据 ──→ MCP Server（工具层）──→ Agent 决策层 ──→ 飞书推送
                     │
         ┌───────────┼───────────┐
         ↓           ↓           ↓
   Sentinel       Strategist    Growth
  （实时/5min）   （日度/每晚）  （周度/每周一）
   Node 1-4       Node 5-6      Node 7
```

---

## Phase 0 — MCP Server 完整化（当前缺口）

> 现状：`mcp/tools.py` 是普通 Python 函数，不是标准 MCP 协议  
> 目标：升级为 stdio/SSE 协议的真正 MCP Server，可被任意 Agent 调用

### 任务清单

**0.1 升级 mcp/server.py 为标准 MCP 协议**

```python
# 使用 fastmcp 库
from fastmcp import FastMCP

mcp = FastMCP("虾塘大亨 MCP Server")

@mcp.tool()
def sensor_read(pond_id: str) -> SensorData: ...

@mcp.tool()
def water_quality_score(sensor: dict) -> WQARData: ...

@mcp.tool()
def feeding_recommend(sensor: dict, wqar: dict) -> FeedingData: ...

@mcp.tool()
def disease_assess(sensor: dict, wqar: dict) -> DiseaseData: ...

@mcp.tool()
def harvest_advise(sensor: dict, wqar: dict, market_price: float) -> HarvestData: ...

@mcp.tool()
def market_match(weight_kg: float, region: str = "华东") -> dict: ...

@mcp.tool()
def price_trend(days: int = 30) -> dict: ...  # 读 data/industry_based_price_data.json

@mcp.tool()
def feishu_alert(report: dict, level: str) -> str: ...  # 返回 message_id

@mcp.tool()
def kb_query(query: str, top_k: int = 5) -> list[str]: ...  # 语义搜索知识库
```

**0.2 kb_query 实现知识库语义检索**

```python
# 实现方案（无向量数据库，纯关键词匹配）
def kb_query(query: str, top_k: int = 5) -> list[str]:
    """搜索 knowledge-base/crayfish_kb.md 中的相关规则"""
    # 1. 按标题和关键词分段加载知识库
    # 2. TF-IDF 简单匹配（或直接关键词匹配）
    # 3. 返回最相关的 top_k 条规则文本
```

**0.3 MCP Server 启动方式**

```bash
# stdio 模式（被 Agent 调用）
python mcp/server.py --mode stdio

# HTTP/SSE 模式（调试用）
python mcp/server.py --mode sse --port 8767
```

**验收标准**：`claude mcp add shrimp-tycoon -- python mcp/server.py` 可注册，9个工具全部可用

---

## Phase 1 — Sentinel Agent 完善

> 现状：已实现三层决策 + 关键词触发  
> 目标：接真实 MCP 工具、增加历史上下文、完善系统提示词

### 1.1 接入 MCP 工具

```python
# 当前：直接调 _rule_engine() 函数
# 目标：通过 MCP 工具层调用，解耦

class SentinelAgent:
    def __init__(self, mcp_client=None):
        self.mcp = mcp_client  # fastmcp.Client
    
    async def analyze(self, sensor, wqar, push_feishu=False):
        # 通过 MCP 调用工具
        feeding = await self.mcp.call("feeding_recommend", sensor=sensor, wqar=wqar)
        disease = await self.mcp.call("disease_assess", sensor=sensor, wqar=wqar)
        kb_rules = await self.mcp.call("kb_query", query=self._build_query(sensor, wqar))
        # 组装 LLM prompt...
```

### 1.2 增加历史上下文窗口

```python
# 维持最近 12 个 tick（1小时）的滑动窗口
class SentinelMemory:
    MAX_HISTORY = 12
    
    def add(self, sensor: dict, wqar: dict): ...
    def trend(self, field: str) -> str:  # "上升" / "下降" / "稳定"
        """计算指定字段的近期趋势"""
    def anomaly(self, field: str) -> bool:
        """检测突变（当前值 vs 均值偏差 > 2σ）"""
```

在 LLM prompt 中注入：
```
历史趋势（近1小时）：
- DO: 6.2 → 5.8 → 4.1 → 2.1 [快速下降 ⚠️]
- 水温: 25.4 → 25.3 → 25.2 [稳定]
```

### 1.3 完善系统提示词

```python
SENTINEL_SYSTEM_PROMPT = """
你是虾塘大亨的 Sentinel Agent，一个专业水产养殖AI决策专家。

## 你的职责
1. 分析传感器数据，识别水质异常
2. 给出具体可执行的投喂/病害/紧急处理操作建议
3. 判断是否需要通知养殖户

## 决策原则
- 操作建议必须具体（几台增氧机、投喂减少百分之几、几小时后复测）
- 不确定时给出观察方案，而非激进干预
- WSSV 等高风险病害必须触发飞书告警

## 知识库规则
{kb_rules}

## 历史趋势
{history_context}

## 输出格式
严格 JSON，字段见 DECISION-1.0 schema。
"""
```

### 1.4 验收测试（5个场景全通过）

```bash
python tests/test_sentinel.py
# 测试项：do_drop / wssv / storm / molt / harvest
# 验收：每个场景输出正确的 risk_level + actions + feishu_sent
```

---

## Phase 2 — Strategist Agent（新建）

> 触发：每天 20:00 自动运行（或手动触发）  
> 职责：综合当日数据，生成日报 + 捕捞建议 + 7日市场预测

### 2.1 架构

```
每日 20:00
    ↓
读取当日 Sentinel 决策记录（DB）
    ↓
调用 MCP 工具：
  - harvest_advise（基于均重趋势）
  - market_match（匹配最优收购商）
  - price_trend（7日价格预测）
    ↓
LLM 综合分析（claude-haiku）
    ↓
生成日报 + 飞书推送（每日早7点发给养殖户）
```

### 2.2 输出 Schema

```python
class DailyReport:
    schema: str = "DAILY-1.0"
    date: str
    pond_id: str
    
    # 今日总结
    summary: str                    # 一句话总结
    risk_events: list[str]          # 今日告警事件列表
    water_quality_avg: dict         # 各指标日均值
    
    # 捕捞决策
    harvest: HarvestAdvice          # 是否建议捕捞
    days_to_harvest: int
    
    # 市场情报
    price_today: float
    price_7day_forecast: list[float]
    best_buyer: BuyerMatch | None   # 匹配的收购商
    
    # 明日建议
    tomorrow_actions: list[str]
    feeding_plan: FeedingPlan       # 明日投喂计划
    
    # 推送
    feishu_sent: bool
    feishu_message_id: str | None
```

### 2.3 文件结构

```
agent/
├── sentinel.py       # ✅ 已有
├── strategist.py     # 新建
├── memory.py         # 新建：SentinelMemory + DailyLog
└── prompts/
    ├── sentinel_system.txt   # 新建：从 sentinel.py 提取
    └── strategist_system.txt # 新建
```

### 2.4 strategist.py 核心结构

```python
class StrategistAgent:
    """每日决策Agent，综合分析当日数据生成日报"""
    
    def __init__(self, mcp_client=None, feishu_pusher=None, db=None):
        self.mcp = mcp_client
        self.feishu = feishu_pusher
        self.db = db  # 历史数据存储
    
    async def run_daily(self, pond_id: str, date: str = None) -> DailyReport:
        """主入口：生成当日报告"""
        history = await self.db.get_day_records(pond_id, date)
        harvest_advice = await self.mcp.call("harvest_advise", ...)
        market = await self.mcp.call("market_match", ...)
        price = await self.mcp.call("price_trend", days=7)
        
        report = await self._llm_summarize(history, harvest_advice, market, price)
        
        if report.harvest.recommended or report.risk_events:
            await self.feishu.send_daily_report(report)
        
        return report
    
    async def _llm_summarize(self, ...) -> DailyReport:
        """调用 claude-haiku 综合分析"""
```

### 2.5 飞书日报卡片格式

```
🦞 虾塘大亨 · A03号池 · 日报
📅 2026-03-27

📊 今日水质：优良（CSI均值 18）
⚠️ 告警事件：无
🦐 虾群状态：存活485尾，均重28.5g，再20天可上市

📈 捕捞建议：当前不建议捕捞
   目标体重：35g | 预计日期：4月16日
   
💰 市场行情：¥26.7/kg（稳定）
   7日预测：¥26.2 → 27.1
   推荐买家：华东水产 ¥27.0/kg（距您65km）

🌅 明日计划：
   ① 投喂量 3.0%（06:00 / 18:00）
   ② 观察透明度，关注蜕壳信号
```

---

## Phase 3 — Growth Agent（新建）

> 触发：每周一 09:00 自动运行  
> 职责：分析多塘数据，获客建议，市场拓展，SaaS 续费提醒

### 3.1 职责边界

| 功能 | 说明 |
|------|------|
| 多塘横向对比 | 哪个塘效益最好，为什么 |
| 获客线索 | 周边有哪些潜在养殖户（来自公开数据） |
| 续费提醒 | 哪个用户快到期了 |
| 营销内容 | 生成本周成功案例（供转发给潜在用户） |
| 效益报告 | 本周 AI 节省了多少钱（可量化的 ROI） |

### 3.2 输出 Schema

```python
class WeeklyGrowthReport:
    schema: str = "GROWTH-1.0"
    week: str
    
    # 效益总结
    total_ponds: int
    total_revenue_saved: float      # AI 本周帮节省的钱
    disease_prevented: list[str]    # 预防的病害事件
    
    # 获客
    leads: list[FarmerLead]         # 周边潜在养殖户
    case_study: str                 # 本周成功案例（可分享）
    
    # 续费
    renewals_due: list[str]         # 即将到期的 pond_id
    
    feishu_sent: bool
```

### 3.3 文件结构

```
agent/
└── growth.py    # 新建
```

---

## Phase 4 — 数据持久化（支撑 Strategist/Growth）

> 当前：所有状态在内存中，重启即丢  
> 目标：SQLite 持久化，支持历史查询

### 4.1 数据库 Schema

```sql
-- 传感器读数（每5秒 1条）
CREATE TABLE sensor_readings (
    id INTEGER PRIMARY KEY,
    pond_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    temp REAL, do_val REAL, ph REAL, ammonia REAL,
    transparency REAL, avg_weight REAL, count INTEGER,
    dead_shrimp INTEGER, molt_peak INTEGER
);

-- AI 决策记录
CREATE TABLE decisions (
    id INTEGER PRIMARY KEY,
    pond_id TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    risk_level INTEGER,
    model_used TEXT,
    summary TEXT,
    actions TEXT,  -- JSON
    feishu_sent INTEGER,
    feishu_message_id TEXT
);

-- 日报记录
CREATE TABLE daily_reports (
    id INTEGER PRIMARY KEY,
    pond_id TEXT NOT NULL,
    date TEXT NOT NULL,
    report_json TEXT  -- 完整 DailyReport JSON
);
```

### 4.2 DB 工具类

```python
# backend/db.py（新建）
class PondDB:
    def __init__(self, path: str = "data/pond.db"): ...
    
    async def save_reading(self, sensor: dict): ...
    async def save_decision(self, decision: dict): ...
    async def get_day_records(self, pond_id: str, date: str) -> list: ...
    async def get_trend(self, pond_id: str, field: str, hours: int = 24) -> list: ...
```

---

## Phase 5 — Agent 编排层（多 Agent 协调）

> 目标：三个 Agent 按时序协调运行，共享状态

### 5.1 编排器设计

```python
# agent/orchestrator.py（新建）
class AgentOrchestrator:
    """协调 Sentinel / Strategist / Growth 三个 Agent"""
    
    def __init__(self):
        self.sentinel    = SentinelAgent(...)
        self.strategist  = StrategistAgent(...)
        self.growth      = GrowthAgent(...)
        self.db          = PondDB()
        self.scheduler   = AsyncIOScheduler()
    
    def start(self):
        # Sentinel: 每5秒（由 server.py 的 tick 驱动）
        # Strategist: 每天 20:00
        self.scheduler.add_job(self._daily_run, "cron", hour=20)
        # Growth: 每周一 09:00
        self.scheduler.add_job(self._weekly_run, "cron", day_of_week="mon", hour=9)
        self.scheduler.start()
    
    async def _daily_run(self):
        for pond_id in await self.db.list_active_ponds():
            await self.strategist.run_daily(pond_id)
    
    async def _weekly_run(self):
        await self.growth.run_weekly()
```

### 5.2 状态共享机制

```
Sentinel  ──写──→  DB（sensor_readings + decisions）
                        ↑
Strategist ──读──→  DB（get_day_records）──→ 日报
                        ↑
Growth    ──读──→  DB（get_week_summary）──→ 周报
```

---

## 开发顺序和时间估算

| Phase | 内容 | 工作量 | 依赖 |
|-------|------|--------|------|
| Phase 0 | MCP Server 完整化 | 1天 | — |
| Phase 1 | Sentinel 完善 | 0.5天 | Phase 0 |
| Phase 4 | SQLite 持久化 | 0.5天 | — |
| Phase 2 | Strategist Agent | 1.5天 | Phase 0, 4 |
| Phase 3 | Growth Agent | 1天 | Phase 2, 4 |
| Phase 5 | 编排层 | 0.5天 | Phase 1, 2, 3 |

**总计：~5天（并行可缩短至3天）**

---

## 接下来立刻能做的事

1. **Phase 0** — 升级 MCP Server，实现 `kb_query` 语义检索
2. **Phase 1** — 给 Sentinel 加 SentinelMemory + 完善 system prompt
3. **Phase 4** — 加 `backend/db.py`，Sentinel 每次决策自动存库

这三个可以同时并行开发，互不干扰。

---

*版本：v1.0 | 2026-03-27 | 比赛后产品化路径*
