# 🦞 虾塘大亨 · AI 智慧水产决策系统

> **OPC极限挑战赛 · 赛道二「AI合伙人」参赛项目**
>
> 不是让农民学 AI，是让 AI 学会养虾。

用 AI 替代养殖决策专家——从传感器数据到飞书告警，全程自动化，零人工干预。

---

## ✨ 核心亮点

| 亮点 | 描述 |
|------|------|
| 🧠 **三层智能路由** | CSI≤20→规则引擎（零成本）→ CSI 21-60→Haiku（快速）→ CSI>60→Opus（深度推理），自动降级 fallback |
| 🤖 **三 Agent 协作** | 哨兵（实时）+ 策略（日报）+ 增长（周报），单向数据流，职责分离 |
| 🔌 **12 个 MCP 工具** | 标准 FastMCP 协议，无状态、幂等、≤5s 超时，即插即用 |
| 📡 **真实传感器接入** | 涂鸦 IoT 智能水质仪 / Mock / DIMOS 三种适配器，ENV 一键切换 |
| 🛡️ **工程级安全** | 传感器物理校验 + 危险操作人工确认 + 飞书推送去重 + LLM 强制超时 |
| 📚 **知识驱动决策** | 70 条养殖规则 + 54 篇学术参考 + TF-IDF 检索引擎 |
| 🤖 **具身智能预留** | DIMOS × 宇树机器狗接口（自动巡塘 + 投喂执行） |
| ✅ **32 个单元测试** | Sentinel 9 + Strategist 5 + Growth 5 + DB 5 + 集成 8，全绿 |

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    Layer A · 决策层                          │
│                                                             │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐      │
│  │  哨兵     │    │  策略         │    │  增长         │      │
│  │ Sentinel │    │ Strategist   │    │ Growth       │      │
│  │ (实时)    │    │ (每日 cron)  │    │ (每周 cron)  │      │
│  └────┬─────┘    └──────┬───────┘    └──────┬───────┘      │
│       │                 │                    │              │
├───────┼─────────────────┼────────────────────┼──────────────┤
│       ▼                 ▼                    ▼              │
│                    Layer B · 工具层                          │
│                                                             │
│  sensor_read · water_quality_score · feeding_recommend      │
│  disease_assess · harvest_advise · market_match             │
│  price_trend · kb_query · feishu_push                       │
│  lead_score · crm_write · audit_log                         │
│                                                             │
│  特性：无状态 | 幂等 | ≤5s 超时 | FastMCP stdio 协议        │
│                                                             │
├─────────────────────────────────────────────────────────────┤
│                    Layer C · 数据层                          │
│                                                             │
│  SQLite (WAL) → PostgreSQL + TimescaleDB + Redis            │
│  70 条养殖规则 · 行业价格数据 · 传感器历史                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 数据流（单向，不可逆）

```
传感器/仿真 → MCP 工具 → 哨兵 Agent → DB
                                       ↓
                                  策略 Agent → DB → 飞书日报
                                                     ↓
                                                增长 Agent → 飞书周报
```

---

## 🤖 三个 Agent

### 🛡️ 哨兵 Agent（Sentinel）— 实时监控

| 特性 | 详情 |
|------|------|
| 触发 | 每 5 分钟自动分析 |
| 路由 | 关键词触发 → CSI 分级 → 模型选择 |
| 推送 | 飞书即时告警（60min 去重） |
| 安全 | 传感器校验 + 危险操作警告 |
| Fallback | LLM 10s 超时 → 规则引擎 |

**关键词触发规则（10 条）**：
- `dead_shrimp` → Opus（最高优先级）
- `DO < 1.5` → Opus（致命缺氧）
- `temp < 10 或 > 32` → Opus（极端温度）
- `pH < 6.5 或 > 9.0` → Opus（致死 pH）
- `ammonia > 1.0` → Opus（氨氮中毒）
- `DO < 3.0` → Haiku（浮头信号）
- `ammonia > 0.5` → Haiku
- `molt_peak + CSI > 25` → Haiku（蜕壳应激）
- `transparency < 20` → Haiku（水质恶化）

### 📊 策略 Agent（Strategist）— 每日决策

| 特性 | 详情 |
|------|------|
| 触发 | 每天 20:00 北京时间（cron） |
| 输入 | 当日传感器 + 决策记录 + 7天趋势 |
| 输出 | DAILY-1.0 日报（投喂/病害/捕捞/建议） |
| 约束 | 不读传感器、不写决策、不发告警 |

### 📈 增长 Agent（Growth）— 商业增长

| 特性 | 详情 |
|------|------|
| 触发 | 每周一 08:00 北京时间（cron） |
| 输入 | 多塘一周数据 + 行业价格 |
| 输出 | GROWTH-1.0 周报（ROI + 市场 + 获客） |
| 约束 | 只读 DB、不给操作建议 |

---

## 🔌 12 个 MCP 工具

| 工具 | 功能 | Schema |
|------|------|--------|
| `sensor_read` | 读取传感器数据 | SDP-1.0 |
| `water_quality_score` | 水质综合评分 | WQAR-1.0 |
| `feeding_recommend` | 投喂建议 | DFP-1.0 |
| `disease_assess` | 病害评估 | DRAR-1.0 |
| `harvest_advise` | 捕捞建议 | HDR-1.0 |
| `market_match` | 市场匹配 | MMR-1.0 |
| `price_trend` | 价格趋势 | — |
| `kb_query` | 知识库查询 | KB-1.0 |
| `feishu_push` | 飞书推送 | — |
| `lead_score` | ICP 评分 | LEAD-1.0 |
| `crm_write` | CRM 写入 | — |
| `audit_log` | 审计日志 | — |

**工具权限矩阵**：

| Agent | 可用工具 | 禁用工具 |
|-------|---------|---------|
| Sentinel | sensor_read, water_quality_score, feeding_recommend, disease_assess, harvest_advise, kb_query, feishu_push, audit_log | market_match, lead_score, crm_write, price_trend |
| Strategist | water_quality_score, feeding_recommend, disease_assess, harvest_advise, kb_query, feishu_push, price_trend, audit_log | sensor_read |
| Growth | market_match, price_trend, lead_score, crm_write, feishu_push, audit_log | sensor_read |

---

## 📁 项目结构

```
shrimp-tycoon/
├── agent/                          # 决策层（Layer A）
│   ├── memory.py                   # SentinelMemory 12-tick 滑动窗口
│   ├── orchestrator.py             # 三 Agent 编排器
│   ├── strategist.py               # 策略 Agent（日报生成）
│   ├── growth.py                   # 增长 Agent（周报 + 获客）
│   └── prompts/                    # 系统提示词
│       ├── strategist_system.txt   # Strategist Haiku 提示词
│       └── growth_system.txt       # Growth Haiku 提示词
│
├── backend/                        # API 层 + 哨兵
│   ├── server.py                   # FastAPI + WebSocket 主入口 (port 8766)
│   ├── sentinel.py                 # 哨兵 Agent（三层路由 + MCP + Memory）
│   ├── sentinel_safety.py          # 传感器校验 + 危险操作检查
│   ├── sentinel_prompts.py         # Haiku/Opus 系统提示词
│   ├── db.py                       # SQLite 持久化（WAL 模式）
│   ├── simulator.py                # 虾塘仿真器（5 个演示场景）
│   └── feishu.py                   # 飞书消息推送
│
├── mcp/                            # 工具层（Layer B）
│   ├── server.py                   # FastMCP Server（12 工具，stdio 模式）
│   ├── tools.py                    # 工具实现
│   ├── kb_searcher.py              # 知识库 TF-IDF 检索引擎
│   └── adapters/                   # 传感器适配器
│       └── tuya_adapter.py         # 涂鸦 IoT 智能水质仪
│
├── data/                           # 数据层（Layer C）
│   └── industry_based_price_data.json  # 行业价格数据
│
├── knowledge-base/                 # 知识库
│   ├── crayfish_kb.md              # 70 条养殖规则
│   └── references.md               # 54 篇学术参考文献
│
├── frontend/                       # 前端（React + Vite + TypeScript + Tailwind）
│   ├── src/
│   │   ├── components/             # 8 个组件
│   │   └── ...
│   └── package.json
│
├── tests/                          # 测试套件（32 用例全绿）
│   ├── test_sentinel.py            # 哨兵测试（9 用例）
│   ├── test_strategist.py          # 策略测试（5 用例）
│   ├── test_growth.py              # 增长测试（5 用例）
│   ├── test_db.py                  # 数据库测试（5 用例）
│   ├── test_mcp_tools.py           # MCP 工具测试（38 用例）
│   └── integration_test.py         # 全链路集成测试（8 用例）
│
├── skill/                          # OpenClaw Skill
│   └── SKILL.md                    # 即插即用说明
│
├── scripts/
│   └── create_pitch_deck.py        # 路演 PPT 生成脚本
│
├── setup.sh                        # 一键安装脚本
├── requirements.txt                # Python 依赖
└── README.md                       # 本文件
```

---

## 🚀 快速开始

### 1. 克隆 & 安装

```bash
git clone https://github.com/Alex647648/shrimp-tycoon.git
cd shrimp-tycoon
./setup.sh
```

### 2. 配置环境变量

```bash
# 编辑 .env
ANTHROPIC_API_KEY=sk-ant-...       # Claude API Key
FEISHU_APP_ID=cli_...              # 飞书应用 ID
FEISHU_APP_SECRET=...              # 飞书应用密钥
SENSOR_MODE=mock                   # mock / tuya / dimos
```

### 3. 启动

```bash
# 后端 API（port 8766）
cd backend && python server.py

# MCP Server（stdio 模式）
python mcp/server.py

# 前端（port 5173）
cd frontend && npm run dev
```

### 4. API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 系统状态 |
| GET | `/api/price?days=30` | 市场价格 |
| GET | `/api/roi` | ROI 分析 |
| POST | `/api/strategist/run?pond_id=A1` | 手动触发日报 |
| POST | `/api/growth/run` | 手动触发周报 |
| WS | `/ws` | 实时数据 + 场景触发 |

### 5. 运行测试

```bash
# 核心测试（32 用例）
python -m pytest tests/test_sentinel.py tests/test_strategist.py tests/test_growth.py tests/test_db.py tests/integration_test.py -v

# 全量测试
python -m pytest tests/ -v
```

---

## 📡 传感器适配器

| 模式 | 说明 | 环境变量 |
|------|------|---------|
| `mock` | 内置仿真器（默认） | `SENSOR_MODE=mock` |
| `tuya` | 涂鸦 IoT 智能水质仪（爱鱼者 YY-W9909） | `SENSOR_MODE=tuya` + TUYA_* |
| `dimos` | DIMOS × 宇树机器狗 MCP 接口 | `SENSOR_MODE=dimos` |

---

## 🛡️ 工程约束

- **三层架构不可混淆**：决策层 / 工具层 / 数据层严格隔离
- **单向数据流**：Sentinel → DB → Strategist → DB → Growth
- **MCP 工具**：无状态、幂等、≤5s 超时、不写 DB（crm_write/audit_log 除外）
- **LLM 调用**：`asyncio.timeout(10)` 强制超时 + 规则引擎 fallback
- **飞书推送**：失败不 raise、不阻塞主流程、60min 去重
- **传感器校验**：`validate_sensor()` 物理范围校验，失败标记不抛出
- **危险操作**：清塘/排水/停增氧 → 自动附加「⚠️ 需人工确认」
- **代码规范**：Agent ≤200 行、MCP ≤250 行、函数 ≤60 行

---

## 💰 商业模型

| 收入来源 | 定价 |
|---------|------|
| SaaS 月费 | ¥1,800–3,000 / 塘 / 月 |
| 撮合佣金 | 1.5% |

**目标市场**：中国 3,050 万亩虾塘，95% 无专业 AI 覆盖。

**AI 替代的岗位**：

| 岗位 | 替代方案 | 年省费用 |
|------|---------|---------|
| 24h 值班技术员 | 哨兵 Agent | ¥8-12 万/塘 |
| 养殖顾问 | 策略 Agent | ¥5-8 万/塘 |
| 销售经理 + 市场分析师 | 增长 Agent | ¥10-15 万/塘 |

---

## 🗺️ 升级路径

```
比赛版（当前）          产品版                    企业版
─────────────────    ─────────────────────    ─────────────────
SQLite              → PostgreSQL + TimescaleDB → 分布式集群
Mock 传感器          → 涂鸦 IoT 真实接入       → 多品牌传感器
单塘                → 多塘 + 多租户           → 区域级管理
飞书推送             → 微信 + 短信 + App       → 全渠道
规则 + Haiku/Opus   → Fine-tuned 模型         → 自适应学习
—                   → Docker Compose          → K8s
—                   → DIMOS 机器狗巡塘        → 无人机编队
```

---

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| AI 推理 | Anthropic Claude（Opus / Haiku 三层路由） |
| 工具协议 | FastMCP（MCP 标准协议） |
| 后端 | FastAPI + WebSocket + asyncio |
| 数据库 | SQLite（WAL 模式）→ PostgreSQL |
| 前端 | React + Vite + TypeScript + Tailwind CSS v3 |
| 推送 | 飞书消息卡片 API |
| 传感器 | 涂鸦 IoT Open API / DIMOS MCP |
| 测试 | pytest + pytest-asyncio |
| 部署 | Docker Compose（产品版） |

---

## 📄 License

MIT

---

> **🦞 让每一口虾塘，都有一个 AI 合伙人。**
