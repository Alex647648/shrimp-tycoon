# 虾塘大亨 · Agent 开发执行路径 v1.0

> 严格对齐 AGENT_CONSTRAINTS.md，每步标注适用约束条款。
> 执行顺序不可打乱——有依赖关系的 Phase 必须按顺序完成。

---

## 总体执行顺序

```
Step 1: 基础设施（无依赖，最先做）
  1A — backend/db.py          （Phase 4 前置）
  1B — backend/db_test        （验收DB）

Step 2: MCP Server 升级（无依赖，可与1并行）
  2A — mcp/server.py          （Phase 0 核心）
  2B — mcp/kb_searcher.py     （kb_query 子模块）
  2C — tests/test_mcp_tools.py

Step 3: Sentinel 完善（依赖 Step 1）
  3A — agent/memory.py        （SentinelMemory）
  3B — backend/sentinel.py 更新（接MCP + 历史窗口 + 系统提示词）
  3C — tests/test_sentinel.py

Step 4: Strategist Agent（依赖 Step 1, 2, 3）
  4A — agent/strategist.py
  4B — agent/prompts/strategist_system.txt
  4C — tests/test_strategist.py

Step 5: Growth Agent（依赖 Step 1, 4）
  5A — agent/growth.py
  5B — agent/prompts/growth_system.txt
  5C — tests/test_growth.py

Step 6: 编排层（依赖 Step 3, 4, 5）
  6A — agent/orchestrator.py
  6B — server.py 集成 orchestrator
  6C — 全链路集成测试
```

---

## Step 1A — backend/db.py

### 任务
新建 SQLite 持久化层，供所有 Agent 读写历史数据。

### 约束锚点
- §1.2 存储层职责：读写持久化数据，**禁止包含业务逻辑**
- §1.3 文件 ≤ 200 行；单函数 ≤ 60 行
- §3.1 文件名 snake_case：`db.py` ✅
- §3.2 类名 PascalCase：`PondDB` ✅
- §3.3 方法名 snake_case 动词_名词：`save_reading`, `get_day_records` ✅
- §4.6 DB 写入失败：记录 warning，**不 raise，不阻塞主流程**
- §4.6 磁盘满：sensor_readings 超 500MB 时删除 30 天前数据

### 文件结构

```python
# backend/db.py（目标 ≤ 150 行）

import aiosqlite
import asyncio
import json
import logging
from pathlib import Path

logger = logging.getLogger("db")
DB_PATH = Path(os.getenv("DB_PATH", "data/pond.db"))

# --- Schema 定义（3张表）---
CREATE_SENSOR_READINGS = """..."""
CREATE_DECISIONS = """..."""
CREATE_DAILY_REPORTS = """..."""

class PondDB:
    async def init(self) -> None:
        """建表（幂等）"""

    async def save_reading(self, pond_id: str, sensor: dict) -> None:
        """写 sensor_readings，失败只 warning"""

    async def save_decision(self, pond_id: str, decision: dict) -> None:
        """写 decisions，失败只 warning"""

    async def save_daily_report(self, report: dict) -> None:
        """写 daily_reports"""

    async def get_day_records(self, pond_id: str, date: str) -> list[dict]:
        """读当日所有 sensor + decision 记录"""

    async def get_trend(self, pond_id: str, field: str, hours: int = 24) -> list[float]:
        """读某字段近 N 小时数据，供趋势分析"""

    async def list_active_ponds(self) -> list[str]:
        """返回最近24h有数据的 pond_id 列表"""

    async def _purge_old_data(self) -> None:
        """删除30天前的 sensor_readings（磁盘保护）"""
```

### 验收标准
```bash
python -c "
import asyncio
from backend.db import PondDB
db = PondDB()
asyncio.run(db.init())
print('✅ DB init OK')
"
```

---

## Step 1B — tests/test_db.py

### 约束锚点
- §6.1 必须有单元测试
- §6.2 禁止真实调用外部 API（DB 本身无外部依赖，可直接测）

### 测试用例
1. `test_save_and_read_reading` — 写一条 sensor，读回来比较
2. `test_save_decision` — 写一条 decision，字段完整性检查
3. `test_get_day_records` — 写多条，按 pond_id + date 过滤
4. `test_db_write_failure_nonfatal` — mock aiosqlite 抛异常，主流程不崩溃
5. `test_list_active_ponds` — 写数据后调用，返回正确 pond_id

---

## Step 2A — mcp/server.py（升级为标准MCP协议）

### 任务
用 fastmcp 库把 `mcp/tools.py` 的普通函数包装成标准 MCP Server。

### 约束锚点
- §1.2 MCP工具层：**禁止写DB / 调LLM / 发飞书**（纯计算+查询）
- §2.4 每个工具必须：幂等、无状态、超时≤5s
- §1.3 文件 ≤ 250 行（MCP工具文件上限）
- §3.4 工具命名 snake_case 动词_名词
- §3.5 输出 Schema：WQAR-1.0 / SDP-1.0 等

### 9个工具列表与约束映射

| 工具名 | 读数据来源 | 写DB | 调LLM | 调飞书 |
|--------|-----------|------|-------|--------|
| `sensor_read` | Tuya API / simulator | ❌ | ❌ | ❌ |
| `water_quality_score` | 纯计算 | ❌ | ❌ | ❌ |
| `feeding_recommend` | 纯计算 | ❌ | ❌ | ❌ |
| `disease_assess` | 纯计算 | ❌ | ❌ | ❌ |
| `harvest_advise` | 价格文件(只读) | ❌ | ❌ | ❌ |
| `market_match` | 内置买家数据 | ❌ | ❌ | ❌ |
| `price_trend` | 价格文件(只读) | ❌ | ❌ | ❌ |
| `feishu_alert` | 无 | ❌ | ❌ | ✅（唯一例外） |
| `kb_query` | knowledge-base(只读) | ❌ | ❌ | ❌ |

> ⚠️ `feishu_alert` 是唯一允许发飞书的工具。内部必须调用 FeishuPusher，不能直接 requests.post。

### 启动命令
```bash
# stdio 模式（被 Agent 调用）
python mcp/server.py --mode stdio

# SSE 调试模式
python mcp/server.py --mode sse --port 8767
```

### 验收标准
```bash
# 注册到 claude
claude mcp add shrimp-tycoon -- python mcp/server.py
# 验证9个工具全部出现
claude mcp list
```

---

## Step 2B — mcp/kb_searcher.py（kb_query 实现）

### 任务
实现知识库关键词检索，从 crayfish_kb.md 中返回 top_k 相关规则。

### 约束锚点
- §1.3 文件 ≤ 200 行
- §2.4 工具无状态：每次调用重新加载（或启动时缓存一次）
- **knowledge-base/ 目录只读**，不能写入
- 不引入向量数据库（避免依赖爆炸），用 TF-IDF 或关键词匹配

### 实现方案

```python
# mcp/kb_searcher.py

class KBSearcher:
    """知识库关键词检索，启动时加载一次 crayfish_kb.md"""

    def __init__(self, kb_path: Path):
        self._sections: list[dict] = []   # {title, content, keywords}
        self._load(kb_path)

    def _load(self, path: Path) -> None:
        """按 ## 标题分段加载知识库"""

    def search(self, query: str, top_k: int = 5) -> list[str]:
        """
        1. 中文分词（split by 标点/空格）
        2. 计算 query token 与每段 keywords 的 Jaccard 相似度
        3. 返回 top_k 段 content 文本
        """
```

---

## Step 2C — tests/test_mcp_tools.py

### 约束锚点
- §6.1 每个工具必须有测试
- §6.2 mock 飞书 API（feishu_alert 不能真实推送）

### 测试用例（9个工具各至少1个）
1. `test_sensor_read_returns_valid_schema` — 验证 SDP-1.0 字段完整性
2. `test_water_quality_score_normal` — 正常水质 → csi<20, risk_level=1
3. `test_water_quality_score_do_low` — DO=1.5 → risk_level≥4
4. `test_feeding_recommend_molt_peak` — molt_peak=True → total_ratio 减少30%
5. `test_disease_assess_wssv` — dead_shrimp=True → diseases含"WSSV"
6. `test_harvest_advise_ready` — avg_weight=36, risk_level=1 → recommended=True
7. `test_market_match_returns_buyer` — 返回至少一个买家 + price字段
8. `test_price_trend_returns_history` — 返回 days=7 的价格列表
9. `test_feishu_alert_mocked` — mock requests → feishu_alert 返回 message_id

---

## Step 3A — agent/memory.py（SentinelMemory）

### 任务
实现最近 12 个 tick（1小时）的滑动历史窗口，供 Sentinel 注入趋势上下文。

### 约束锚点
- §1.3 文件 ≤ 200 行，函数 ≤ 60 行
- §3.2 类名 `SentinelMemory` ✅
- §3.3 方法名：`add()`, `trend()`, `anomaly()`, `format_context()` ✅
- §2.1 Sentinel 不读取历史 DB——历史由 SentinelMemory 维护在内存中（短期窗口）

### 核心接口

```python
class SentinelMemory:
    MAX_HISTORY = 12   # 12个tick = 约1小时

    def add(self, sensor: dict, wqar: dict) -> None:
        """追加一条记录，超出 MAX_HISTORY 时丢弃最旧的"""

    def trend(self, field: str) -> str:
        """返回 "上升" / "下降" / "稳定"（基于线性回归斜率）"""

    def anomaly(self, field: str) -> bool:
        """当前值偏离近期均值超过 2σ → True"""

    def format_context(self) -> str:
        """生成注入 LLM prompt 的历史趋势文本"""
        # 输出示例：
        # 历史趋势（近1小时）：
        # - DO: 6.2 → 5.8 → 4.1 → 2.1 [快速下降 ⚠️]
        # - 水温: 25.4 → 25.3 → 25.2 [稳定]
```

---

## Step 3B — backend/sentinel.py 更新

### 任务
在现有 Sentinel（211行）基础上增加3项能力：
1. 接入 MCP 工具（解耦 _rule_engine 直接调用）
2. 注入 SentinelMemory 历史上下文
3. 完善系统提示词（提取到 agent/prompts/sentinel_system.txt）
4. 增加 `validate_sensor()` 和 `_safety_check()` 两个保护函数

### 约束锚点（高优先级）
- §4.1 LLM 调用：**必须** `asyncio.timeout(10)` + fallback 规则引擎
- §4.3 传感器校验：进入 analyze() 第一行调用 `validate_sensor()`
- §4.4 安全红线：actions 列表必须经过 `_safety_check()`
- §4.2 飞书推送失败：try/except，不 raise
- §4.2 飞书去重：`_should_push(pond_id, scenario)` 60分钟冷却
- §2.1 Sentinel 不调 market_match 工具
- §2.1 Sentinel 不读 DB 历史（由 SentinelMemory 内存窗口提供）
- §1.3 总行数控制：拆分后 sentinel.py ≤ 200 行，系统提示词提取到 .txt 文件

### 拆分方案（当前211行，增量后超限）

```
backend/
├── sentinel.py          ← 主逻辑（≤ 200 行）
├── sentinel_prompts.py  ← 系统提示词常量（≤ 50 行）
└── sentinel_safety.py   ← validate_sensor + _safety_check（≤ 60 行）
```

### validate_sensor 必须实现

```python
# backend/sentinel_safety.py
VALID_RANGES = {
    "temp":         (0, 45),
    "DO":           (0, 20),
    "pH":           (3, 12),
    "ammonia":      (0, 10),
    "transparency": (0, 200),
    "avg_weight":   (0, 200),
}
DANGEROUS_KEYWORDS = ["清塘", "全部排水", "停止增氧", "超量用药", "大量投药"]

def validate_sensor(sensor: dict) -> dict: ...
def _safety_check(actions: list[str]) -> list[str]: ...
```

### 更新后 analyze() 骨架

```python
async def analyze(self, sensor: dict, wqar: dict, push_feishu: bool = False) -> dict:
    # 1. 传感器校验（新增，§4.3）
    sensor = validate_sensor(sensor)

    # 2. 关键词触发路由（已有）
    kw_model = _keyword_model(sensor, wqar)
    ...

    # 3. actions 安全检查（新增，§4.4）
    report["actions"] = _safety_check(report["actions"])

    # 4. 飞书推送（更新去重逻辑，§4.2）
    if push_feishu and self.feishu and rl >= 3:
        if _should_push(pond_id, scenario):
            ...

    # 5. 写 DB（非阻塞，§4.6）
    if self.db:
        await self.db.save_decision(pond_id, report)  # 内部 try/except

    return report
```

---

## Step 3C — tests/test_sentinel.py

### 5个场景测试（严格 mock 外部依赖）

```python
# 5个场景 × 至少 3个断言
@patch("backend.sentinel.anthropic.AsyncAnthropic")
@patch("backend.feishu.requests.post")
async def test_do_drop(mock_feishu, mock_anthropic):
    """DO=1.5 → 关键词触发 Opus → risk_level≥4 → feishu推送"""
    sensor = {..., "DO": 1.5}
    report = await agent.analyze(sensor, wqar, push_feishu=True)
    assert report["risk_level"] >= 4
    assert any("增氧" in a for a in report["actions"])
    assert report["model_used"] == "claude-opus-4-6"

# 同理：test_wssv / test_storm / test_molt / test_harvest
```

### 额外验证
- `test_validate_sensor_filters_invalid` — DO=999 → 标记 do_val_invalid=True，不触发告警
- `test_safety_check_dangerous` — actions含"清塘" → 加「⚠️【需人工确认】」
- `test_feishu_dedup` — 60分钟内同一事件不重复推送
- `test_llm_timeout_fallback` — mock anthropic 超时10s → fallback 规则引擎

---

## Step 4A — agent/strategist.py

### 任务
每日 20:00 运行，读取当日 DB 记录，生成 DAILY-1.0 报告并推送飞书日报。

### 约束锚点
- §2.2 Strategist **不能**直接读传感器（必须经 DB）
- §2.2 Strategist **不能**写 decisions 表
- §2.2 Strategist **不能**发紧急告警（只发日报）
- §4.1 LLM 调用：`asyncio.timeout(10)` + fallback（简化版日报）
- §1.3 文件 ≤ 200 行

### 模块结构

```
agent/
├── strategist.py              ← 主逻辑（≤ 200 行）
└── prompts/
    └── strategist_system.txt  ← 系统提示词（单独文件）
```

### 核心接口

```python
class StrategistAgent:
    def __init__(self, db: PondDB, mcp_client, feishu: FeishuPusher):
        # 注意：不接受 sensor 参数（§2.2）
        ...

    async def run_daily(self, pond_id: str, date: str | None = None) -> dict:
        """主入口，返回 DAILY-1.0 报告"""
        history = await self.db.get_day_records(pond_id, date)   # 读DB
        harvest = await self.mcp.call("harvest_advise", ...)
        market  = await self.mcp.call("market_match", ...)
        price   = await self.mcp.call("price_trend", days=7)
        report  = await self._llm_summarize(history, harvest, market, price)
        report  = self._validate_schema(report)
        await self.db.save_daily_report(report)                   # 写DB
        if self._should_push(report):
            await self.feishu.send_daily_report(report)
        return report

    async def _llm_summarize(self, ...) -> dict:
        """调用 haiku，超时fallback到 _rule_summarize"""

    def _rule_summarize(self, history, harvest, market, price) -> dict:
        """纯规则生成简化日报（LLM fallback）"""

    def _validate_schema(self, report: dict) -> dict:
        """确保 DAILY-1.0 所有必填字段存在"""

    def _should_push(self, report: dict) -> bool:
        """有告警事件或捕捞建议时推送"""
```

---

## Step 4B — agent/prompts/strategist_system.txt

系统提示词单独文件，内容：
- 角色定义：每日综合决策专家
- 输出格式：严格 JSON（DAILY-1.0 schema）
- 数据参考：今日平均水质、告警次数、均重趋势、市场价格
- 决策原则：捕捞建议必须基于均重≥35g + 价格趋势 + 风险等级

---

## Step 4C — tests/test_strategist.py

### 测试用例
1. `test_run_daily_normal` — mock DB返回正常数据 → 输出 DAILY-1.0 schema 完整
2. `test_run_daily_no_data` — DB空 → 输出简化日报，不崩溃
3. `test_llm_timeout_fallback` — mock anthropic 超时 → 走 _rule_summarize
4. `test_no_sensor_direct_access` — Strategist 没有 sensor_read 调用
5. `test_no_decisions_write` — Strategist 不写 decisions 表

---

## Step 5A — agent/growth.py

### 任务
每周一 09:00 运行，读取多塘一周数据，生成 GROWTH-1.0 报告。

### 约束锚点
- §2.3 Growth 只读所有 DB 表，**不能发操作建议**，**不能自动续费**
- §2.3 Growth 不读传感器
- §4.1 LLM fallback 同前
- §1.3 文件 ≤ 200 行

### 核心接口

```python
class GrowthAgent:
    async def run_weekly(self) -> dict:
        """主入口，返回 GROWTH-1.0 报告"""
        ponds = await self.db.list_active_ponds()
        week_data = [await self.db.get_week_summary(p) for p in ponds]
        report = await self._llm_analyze(week_data)
        await self.db.save_growth_report(report)
        await self.feishu.send_weekly_report(report)
        return report
```

---

## Step 6A — agent/orchestrator.py

### 任务
编排三个 Agent，管理定时任务，统一启动/停止。

### 约束锚点
- §1.1 单向数据流：Sentinel 不调 Strategist，Strategist 不调 Growth
- §5.1 Sentinel 由 server.py tick 驱动（不在 orchestrator 中定时）
- §1.3 文件 ≤ 200 行

### 核心结构

```python
class AgentOrchestrator:
    def __init__(self, db, mcp_client, feishu):
        self.sentinel   = SentinelAgent(feishu_pusher=feishu, db=db)
        self.strategist = StrategistAgent(db=db, mcp_client=mcp_client, feishu=feishu)
        self.growth     = GrowthAgent(db=db, mcp_client=mcp_client, feishu=feishu)
        self.scheduler  = AsyncIOScheduler()

    def start(self):
        # Sentinel：不在这里定时，由 server.py tick 驱动
        self.scheduler.add_job(self._daily_run,  "cron", hour=20, minute=0)
        self.scheduler.add_job(self._weekly_run, "cron", day_of_week="mon", hour=9)
        self.scheduler.start()

    async def _daily_run(self):
        for pond_id in await self.db.list_active_ponds():
            await self.strategist.run_daily(pond_id)

    async def _weekly_run(self):
        await self.growth.run_weekly()
```

---

## Step 6B — server.py 集成更新

### 更新内容
1. 启动时初始化 `PondDB` + `AgentOrchestrator`
2. 每次 tick 时调用 `orchestrator.sentinel.analyze()`
3. 增加手动触发端点：
   - `POST /api/strategist/run` — 手动触发日报
   - `POST /api/growth/run` — 手动触发周报

### 约束锚点
- §1.2 API层：**禁止包含决策逻辑**（只调用 Agent 的 public 方法）
- §5.3 WS handler 内部异常不得断开连接

---

## Step 6C — 全链路集成测试

### 测试场景

```bash
# 1. 启动后端
cd ~/projects/shrimp-tycoon
source .venv/bin/activate
python backend/server.py

# 2. 触发5个场景，验证输出
python tests/integration_test.py

# 3. 手动触发日报
curl -X POST http://localhost:8766/api/strategist/run

# 4. 验证飞书推送（需真实 .env）
# 647手机上收到告警 + 日报
```

### 集成测试验收清单
- [ ] `do_drop` 场景 → Sentinel risk=5, Opus调用, 飞书告警推送
- [ ] `wssv` 场景 → dead_shrimp=True, actions含WSSV, 安全红线未触发
- [ ] `molt` 场景 → molt_peak, 投喂减少30%, 飞书amber
- [ ] `harvest` 场景 → avg_weight≥35, harvest.recommended=True
- [ ] `reset` 场景 → 状态回到 risk=1，无告警
- [ ] 日报手动触发 → 数据库有记录，飞书收到日报

---

## 开发前检查清单（每个文件动工前必过）

```
□ 函数 ≤ 60 行？
□ 文件 ≤ 200 行（或对应类型上限）？
□ 所有外部调用有 try/except + fallback？
□ LLM 调用有 asyncio.timeout(10)？
□ 飞书推送失败不 raise？
□ 危险操作经过 _safety_check()？
□ 传感器数据经过 validate_sensor()？
□ 新增接口在 INTERFACE_SPEC.md 中描述？
□ 单元测试 mock 了所有外部 API？
□ 提交信息格式：<type>(<scope>): <description>？
```

---

## 文件结构（完成后）

```
~/projects/shrimp-tycoon/
├── backend/
│   ├── server.py              ← 更新（集成 orchestrator）
│   ├── sentinel.py            ← 更新（MCP + 历史窗口 + 校验）
│   ├── sentinel_prompts.py    ← 新建（系统提示词）
│   ├── sentinel_safety.py     ← 新建（validate_sensor + _safety_check）
│   ├── simulator.py           ← 不变
│   ├── feishu.py              ← 不变
│   └── db.py                  ← 新建（Step 1A）
├── agent/
│   ├── memory.py              ← 新建（Step 3A）
│   ├── strategist.py          ← 新建（Step 4A）
│   ├── growth.py              ← 新建（Step 5A）
│   ├── orchestrator.py        ← 新建（Step 6A）
│   └── prompts/
│       ├── sentinel_system.txt   ← 新建
│       ├── strategist_system.txt ← 新建
│       └── growth_system.txt     ← 新建
├── mcp/
│   ├── server.py              ← 新建（Step 2A，标准MCP协议）
│   ├── kb_searcher.py         ← 新建（Step 2B）
│   ├── tools.py               ← 已有（迁移到 server.py 注册）
│   └── adapters/
│       └── tuya_adapter.py    ← 已有
├── tests/
│   ├── test_db.py             ← 新建（Step 1B）
│   ├── test_mcp_tools.py      ← 新建（Step 2C）
│   ├── test_sentinel.py       ← 新建（Step 3C）
│   ├── test_strategist.py     ← 新建（Step 4C）
│   ├── test_growth.py         ← 新建（Step 5C）
│   └── integration_test.py    ← 新建（Step 6C）
├── AGENT_ROADMAP.md           ← 已有
├── AGENT_CONSTRAINTS.md       ← 已有
└── DEV_PLAN.md                ← 本文件
```

---

*版本：v1.0 | 2026-03-27 | 严格对齐 AGENT_CONSTRAINTS.md v1.0*
