# 🦞 虾塘大亨 · AI 智慧水产决策系统

> **OPC极限挑战赛 · 赛道二「AI合伙人」参赛项目**
>
> 不是让农民学 AI，是让 AI 学会养虾。

三个 AI Agent 协作的虾塘智能管理系统——从传感器数据到飞书告警到商业增长，全程自动化，零人工干预。

---

## ✨ 核心亮点

| 亮点 | 描述 |
|------|------|
| 🧠 **三层智能路由** | CSI≤20→规则引擎（零成本）→ CSI 21-60→Haiku（快速）→ CSI>60→Opus（深度推理），自动降级 fallback |
| 🤖 **三 Agent 协作** | 哨兵（实时告警）+ 策略（每日日报）+ 增长（周报+获客），单向数据流，职责严格隔离 |
| 🔌 **12 个 MCP 工具** | 标准 FastMCP 协议，无状态、幂等、≤5s 超时，Claude 直接调用 |
| 📡 **可插拔传感器** | Mock 仿真 / 涂鸦 IoT 真实传感器 / DIMOS 机器狗 / 无人机，`.env` 一键切换 |
| 🛡️ **工程级安全** | 传感器物理校验 + 危险操作人工确认 + 飞书推送去重 + LLM 强制 10s 超时 |
| 📚 **知识驱动决策** | 70 条养殖规则 + 54 篇学术参考 + TF-IDF 检索引擎 |
| 🦾 **具身智能接口** | DIMOS × 宇树机器狗巡塘 + 无人机多光谱航拍（预留） |
| ✅ **32 个单元测试** | Sentinel 9 + Strategist 5 + Growth 5 + DB 5 + 集成 8，全绿 |
| 🚀 **OpenClaw 开箱即用** | `setup.sh` 一键安装：MCP 注册 + Skill 安装 + Cron 调度，说一句话就能用 |

---

## 🚀 OpenClaw 开箱即用

虾塘大亨是一个完整的 **OpenClaw 原生 AI Agent 系统**。安装后，你的 Claude 自动获得虾塘管理能力——不需要手动启动任何服务，说一句话即可触发。

### 安装（3 分钟）

```bash
git clone https://github.com/Alex647648/shrimp-tycoon.git
cd shrimp-tycoon
./setup.sh
```

`setup.sh` 自动完成以下 6 步：
1. ✅ 安装 Python 依赖
2. ✅ 创建 `.env` 配置模板
3. ✅ 初始化 SQLite 数据库
4. ✅ 注册 MCP Server（12 个工具）
5. ✅ 安装 OpenClaw Skill（`~/.agents/skills/shrimp-tycoon/`）
6. ✅ 添加 3 个 Cron 任务（日报/周报/获客）

### 对话即操作

安装后，直接跟 Claude 说：

| 你说 | Claude 做的事 |
|------|--------------|
| 「查一下 A03 塘」 | 调用 `sensor_read` → `water_quality_score` → 返回水质评分 |
| 「现在该捕捞吗」 | 调用 `harvest_advise` + `market_match` → 给出捕捞建议 + 匹配买家 |
| 「帮我跑今天的日报」 | 读 DB → `price_trend` → `web_search` 实时行情 → 生成日报 → 飞书推送 |
| 「找 3 个潜在客户」 | `web_search` × 3 源 → `lead_score` ICP 评分 → 推荐清单 |
| 「生成本月 ROI 报告」 | 读 DB 决策记录 → 统计节省成本 → 计算 ROI |
| 「机器狗去巡 A03 塘」 | `sensor_read(adapter=dimos)` → DIMOS 控制宇树机器狗 |
| 「系统状态怎么样」 | `GET /api/health` → 三 Agent 运行统计 |

### 自动运行（Cron 调度）

安装后，以下任务自动执行：

| 任务 | 时间（北京） | 做什么 |
|------|-------------|--------|
| 📊 **策略日报** | 每天 06:00 | 读 DB → 趋势分析 → 捕捞建议 → 买家匹配 → 飞书日报卡片 |
| 📈 **增长周报** | 周一 08:00 | 多塘 ROI → 市场分析 → 获客线索 → CRM 更新 → 飞书周报 |
| 🤝 **客户触达** | 每天 09:00 | 读 CRM → A/B 级线索 → 按阶段模板 → 自动跟进 |

### 飞书推送效果

**告警卡片（Sentinel → 实时推送）：**
```
🚨 A01 号池 · 溶解氧骤降告警

DO 值降至 1.2mg/L，低于安全阈值 3.0mg/L
风险等级：5/5（极高风险）

📋 操作建议：
  1. 立即开启全部增氧机
  2. 停止一切投喂
  3. 检查增氧设备运转

⏱ 决策耗时：12ms | 模型：rules
```

**日报卡片（Strategist → 每天 06:00）：**
```
🌅 A03 号池 · 每日报告 · 2026-03-27

📊 水质：综合评分 82/100（良好）
🦞 虾群：均重 28.5g，预计 14 天可捕
💰 行情：潜江大虾 ¥26.7/kg（↓ 季节性）

📋 今日重点：
  1. 按计划投喂（07:00/19:00）
  2. 关注氨氮，若 >0.2 考虑换水
  3. 距捕捞窗口：14 天

🎣 捕捞：暂不建议，再等 14 天
🤝 买家：武汉新发展水产（4.8⭐）报价 ¥27.0/kg
```

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                    Layer A · 决策层                               │
│                                                                  │
│  ┌──────────┐    ┌──────────────┐    ┌──────────────┐           │
│  │  🛡️ 哨兵  │    │  📊 策略      │    │  📈 增长      │           │
│  │ Sentinel │    │ Strategist   │    │ Growth       │           │
│  │ (实时)    │    │ (cron 日报)  │    │ (cron 周报)  │           │
│  │          │    │              │    │              │           │
│  │ 三层路由  │    │ DB→趋势→    │    │ ROI→买家→   │           │
│  │ 规则/    │    │ 日报→飞书    │    │ 获客→CRM    │           │
│  │ Haiku/   │    │              │    │              │           │
│  │ Opus     │    │              │    │              │           │
│  └────┬─────┘    └──────┬───────┘    └──────┬───────┘           │
│       │                 │                    │                   │
├───────┼─────────────────┼────────────────────┼───────────────────┤
│       ▼                 ▼                    ▼                   │
│                    Layer B · 工具层（MCP Server · 12 工具）       │
│                                                                  │
│  sensor_read · water_quality_score · feeding_recommend           │
│  disease_assess · harvest_advise · kb_query                      │
│  market_match · price_trend · lead_score                         │
│  crm_write · feishu_push · audit_log                            │
│                                                                  │
│  特性：无状态 | 幂等 | ≤5s 超时 | FastMCP stdio 协议             │
│                                                                  │
├──────────────────────────────────────────────────────────────────┤
│                    Layer C · 数据层                               │
│                                                                  │
│  ┌────────────┐  ┌──────────────┐  ┌────────────────────┐       │
│  │ SQLite WAL  │  │ 知识库(70条) │  │ 行业价格+买家数据  │       │
│  │ 3 表        │  │ TF-IDF 检索  │  │ JSON 只读          │       │
│  └────────────┘  └──────────────┘  └────────────────────┘       │
│                                                                  │
│  升级路径：→ PostgreSQL + TimescaleDB + Redis                    │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

### 数据流（单向，不可逆）

```
传感器 → Sentinel → DB → Strategist → 飞书日报
                                 ↓
                              Growth → 飞书周报 + CRM
```

---

## 🤖 三个 Agent 详细设计

### 🛡️ 哨兵 Agent（Sentinel）— 实时守护每一口塘

**核心能力：**
- 三层智能路由：CSI≤20→规则引擎（0ms）→ CSI 21-60→Haiku（<2s）→ CSI>60→Opus（<15s）
- 10 条关键词触发规则（优先级高于 CSI 路由）
- 12-tick 滑动窗口历史感知（趋势分析 + 2σ 异常检测）
- 多塘并发分析（`run_batch()`）

**关键词触发（Opus 级别）：**
- 发现死虾（`dead_shrimp`）
- DO < 1.5（致命缺氧）
- 水温 < 10°C 或 > 32°C（极端温度）
- pH < 6.5 或 > 9.0（致死 pH）
- 氨氮 > 1.0（中毒风险）

**安全机制：**
- `validate_sensor()` 物理范围校验（异常值自动标记不抛出）
- `_safety_check()` 危险操作自动附加「⚠️ 需人工确认」
- 飞书推送 60 分钟去重（同一塘口同一事件不重复）
- LLM 10s 强制超时 + 规则引擎 fallback（永不卡死）

**增强版规则引擎覆盖场景：**
| 场景 | 触发条件 | 风险等级 | 自动操作 |
|------|---------|---------|---------|
| 溶解氧骤降 | DO < 1.5 | 5 | 开增氧机+停食+设备检查 |
| 白斑病毒 | dead_shrimp | 5 | 隔离+送检+消毒 |
| 暴雨水质突变 | pH < 6.5 | 4 | 投放石灰+监控水位 |
| 氨氮超标 | ammonia > 1.0 | 5 | 紧急换水+沸石粉+停食 |
| 蜕壳期 | molt_peak | 2 | 减投 30%+补钙 |
| 捕捞窗口 | avg_weight ≥ 35g | 1 | 建议联系收购商 |

### 📊 策略 Agent（Strategist）— 每日决策参谋

**执行流程：**
1. 读 DB 当日 sensor + decision 记录
2. 知识库 TF-IDF 检索匹配规则
3. MCP 工具：`harvest_advise` + `market_match` + `price_trend`
4. LLM 生成 DAILY-1.0 日报（Haiku + 10s 超时 + fallback）
5. 飞书推送日报卡片

**DAILY-1.0 输出包含：**
- 水质趋势（DO/pH/氨氮/温度 7 天变化）
- 投喂汇总（总量/比率/跳过次数）
- 病害风险评估
- 捕捞窗口判断 + 天数预估
- 买家匹配推荐
- 可执行建议（≤5 条）

**边界约束：**
- ❌ 不直接读传感器（只读 DB）
- ❌ 不写 decisions 表
- ❌ 不发紧急告警

### 📈 增长 Agent（Growth）— 让塘口变成生意

Growth Agent 覆盖完整获客闭环：**线索发现 → ICP 评分 → CRM 入库 → 自动触达 → 转化跟进**。

#### 🔍 线索自动发现（`mcp/lead_discovery.py`）

从 **10 个来源** 自动搜索潜在客户：

| # | 来源 | 搜索方式 | 示例查询 |
|---|------|---------|---------|
| 1 | 水产协会名录 | web_search | "全国水产流通协会 会员名录" |
| 2 | 天眼查/企查查 | web_search | "小龙虾养殖 企业 site:tianyancha.com" |
| 3 | 美团/饿了么 | web_search | "小龙虾 餐饮 供应商招募" |
| 4 | 抖音/快手达人 | web_search | "小龙虾养殖 抖音达人 粉丝过万" |
| 5 | 展会名片 OCR | web_search | "2026 水产养殖展会 参展商名录" |
| 6 | 行业媒体 | web_search | "水产前沿 养殖户采访" |
| 7 | 微信公众号 | web_search | "小龙虾养殖 公众号 技术交流群" |
| 8 | 1688 批发 | web_search | "小龙虾 活虾 批发 site:1688.com" |
| 9 | 农业农村部 | web_search | "湖北省 小龙虾 养殖户 统计" |
| 10 | 客户转介绍 | CRM 内部 | 成交客户推荐链 |

**MCP 工具调用流程（两步）：**

```
Step 1: lead_discover(sources="all")
  → 返回搜索任务清单（20+ 条查询）

Step 2: 对每条查询执行 web_search(query)
  → 把结果传给 lead_process(results_json)
  → 自动提取：企业名/手机号/邮箱/地域/面积
  → 自动 ICP 评分 + 去重 + 写入 CRM
```

**信息提取能力：**
- 手机号正则：`1[3-9]\d{9}`
- 邮箱正则：标准 email 格式
- 地域识别：潜江/监利/洪湖/盱眙 等 10+ 核心产区
- 面积提取：`XXX亩` / `XXX公顷` 自动转换
- 企业名：`XX养殖场` / `XX水产` / `XX合作社` 模式匹配

#### 📊 ICP 评分（`mcp/lead_scorer.py`）

100 分制，4 维度加权：

| 维度 | 权重 | 满分条件 |
|------|------|---------|
| 养殖规模 | 40% | >10 亩 = 100 分 |
| 地理位置 | 20% | 核心产区 = 100 分 |
| 管理水平 | 20% | 有病害史(最需AI) + 员工≥3 |
| 接受度 | 20% | 用过 App + 咨询过专家 |

评级：A（≥80）→ B（≥60）→ C（≥40）→ D（<40）

#### 💾 CRM 存储（`mcp/crm.py`）

SQLite 两表：

```sql
leads:    id / name / region / area_mu / score / grade / source / status / created_at / meta
outreach: id / lead_id / day / channel / message / sent_at / response
```

#### 📨 5 步触达序列

| 天数 | 渠道 | 内容 |
|------|------|------|
| Day 1 | 微信 | 首触：自我介绍 + AI 年省 24 万价值点 |
| Day 3 | 微信 | ROI 计算器 PDF（个性化节省金额） |
| Day 7 | 微信 | 成功案例：湖北养殖户用 AI 增收 ¥12,000 |
| Day 14 | 微信 | 免费试用邀请（1 塘口 30 天） |
| Day 21 | 电话 | 试用跟进 + 付费引导 |

**执行逻辑：** 每日 cron → 读 CRM 中 `status=new` 线索 → 计算入库天数 → 匹配对应阶段模板 → 填充变量 → 记录 outreach 日志

#### 📈 周报能力（GROWTH-1.0）

- 多塘 ROI 对比（产值/成本/利润/ROI 倍数）
- 市场价格趋势分析
- 买家智能匹配（按规格+地域+评分排序，`data/buyers.json`）
- AI 节省成本估算（替代人工值班 ¥10 万 + 顾问 ¥6 万 + 病害预防 ¥8 万）

#### 🎯 漏斗目标

```
线索发现(10源) → 月新增500 → ICP筛选A/B级 →
试用75个(15%) → 付费30个(40%)
CAC ≤ ¥250 | LTV = ¥28,800 | LTV/CAC = 115×
```

**边界约束：**
- ❌ 只读种养 DB，不写种养表
- ❌ 不给种养操作建议
- ❌ 不自动扣费/续费
- ✅ CRM 表可写（线索+触达记录）

---

## 🔌 14 个 MCP 工具

| 工具 | 功能 | Schema | 写 DB | 调 LLM | 调飞书 |
|------|------|--------|-------|--------|--------|
| `sensor_read` | 读传感器（Mock/Tuya/DIMOS） | SDP-1.0 | ❌ | ❌ | ❌ |
| `water_quality_score` | CSI 水质综合评分 | WQAR-1.0 | ❌ | ❌ | ❌ |
| `feeding_recommend` | 投喂建议 | DFP-1.0 | ❌ | ❌ | ❌ |
| `disease_assess` | 病害评估 | DRAR-1.0 | ❌ | ❌ | ❌ |
| `harvest_advise` | 捕捞建议 | HDR-1.0 | ❌ | ❌ | ❌ |
| `kb_query` | 知识库 TF-IDF 检索 | KB-1.0 | ❌ | ❌ | ❌ |
| `market_match` | 市场匹配 | MMR-1.0 | ❌ | ❌ | ❌ |
| `price_trend` | 价格趋势 | — | ❌ | ❌ | ❌ |
| `lead_score` | ICP 评分 | LEAD-1.0 | ❌ | ❌ | ❌ |
| `lead_discover` | 🆕 线索发现（生成搜索任务） | LEAD-DISCOVER-1.0 | ❌ | ❌ | ❌ |
| `lead_process` | 🆕 线索处理（提取+评分+CRM） | LEAD-PROCESS-1.0 | ✅ | ❌ | ❌ |
| `crm_write` | CRM 写入 | — | ✅ | ❌ | ❌ |
| `feishu_push` | 飞书推送 | — | ❌ | ❌ | ✅ |
| `audit_log` | 审计日志 | — | ✅ | ❌ | ❌ |

**工具权限矩阵（Agent × 工具）：**

| | sensor | wqar | feed | disease | harvest | kb | market | price | lead_score | lead_discover | lead_process | crm | feishu | audit |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Sentinel | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Strategist | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ |
| Growth | ❌ | ❌ | ❌ | ❌ | ❌ | ❌ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

---

## 📁 项目结构

```
shrimp-tycoon/
│
├── skill/SKILL.md                    ← ⭐ OpenClaw 行为定义（最核心）
├── setup.sh                          ← 一键安装（pip+DB+MCP+Skill+Cron）
├── clawhub.json                      ← ClawhHub 市场发布元数据
├── docker-compose.yml                ← 产品版 Docker 部署
├── .env.example                      ← 配置模板
├── requirements.txt
│
├── agent/                            # Layer A · 决策层
│   ├── orchestrator.py               # 三 Agent 编排器 + 健康检查
│   ├── strategist.py                 # 策略 Agent（日报 + DAILY-1.0）
│   ├── growth.py                     # 增长 Agent（周报 + ROI + 获客 + 触达序列）
│   ├── memory.py                     # SentinelMemory（12-tick 滑动窗口 + 2σ 异常）
│   └── prompts/
│       ├── sentinel_system.txt       # Sentinel Haiku/Opus 提示词
│       ├── strategist_system.txt     # Strategist 日报提示词
│       └── growth_system.txt         # Growth 周报提示词
│
├── backend/                          # API 层 + 哨兵
│   ├── server.py                     # FastAPI + WebSocket 主入口 (port 8766)
│   ├── sentinel.py                   # 哨兵 Agent（三层路由 + 关键词 + 多塘并发）
│   ├── sentinel_safety.py            # 传感器校验 + 危险操作安全检查
│   ├── sentinel_prompts.py           # Haiku/Opus 系统提示词生成
│   ├── db.py                         # SQLite WAL（3 表 + 异步读写）
│   ├── simulator.py                  # 虾塘仿真器（5 个演示场景）
│   └── feishu.py                     # 飞书消息推送（token 刷新 + 卡片）
│
├── mcp/                              # Layer B · 工具层
│   ├── server.py                     # FastMCP Server（12 工具 · stdio）
│   ├── kb_searcher.py                # 知识库 TF-IDF 检索引擎
│   ├── lead_scorer.py                # ICP 评分模型（100分4维度）
│   ├── crm.py                        # CRM 读写（leads + outreach）
│   ├── tools.py                      # 工具实现
│   └── adapters/                     # 传感器适配器（可插拔）
│       ├── mock_adapter.py           # 仿真传感器（默认）
│       ├── tuya_adapter.py           # 涂鸦 IoT 智能水质仪
│       ├── dimos_adapter.py          # DIMOS × 宇树机器狗
│       └── drone_adapter.py          # 无人机多光谱（占位）
│
├── data/                             # Layer C · 数据层
│   ├── industry_based_price_data.json  # 行业价格数据（只读）
│   └── buyers.json                   # 买家数据库（5 条示例）
│
├── knowledge-base/                   # 知识库
│   ├── crayfish_kb.md                # 70 条养殖规则
│   └── references.md                 # 54 篇学术参考文献
│
├── frontend/                         # 前端（React + Vite + TS + Tailwind v3）
│   └── src/
│       ├── components/               # 8 个组件（Liquid Glass 风格）
│       ├── hooks/                    # useWebSocket, useShrimpData
│       └── types/api.ts
│
├── tests/                            # 测试套件（32 用例全绿）
│   ├── test_sentinel.py              # 哨兵 9 用例
│   ├── test_strategist.py            # 策略 5 用例
│   ├── test_growth.py                # 增长 5 用例
│   ├── test_db.py                    # 数据库 5 用例
│   ├── test_mcp_tools.py             # MCP 38 用例
│   └── integration_test.py           # 全链路 8 用例
│
└── scripts/
    └── create_pitch_deck.py          # 路演 PPT 生成脚本
```

---

## 📡 传感器适配器

| 模式 | 硬件 | 环境变量 | 状态 |
|------|------|---------|------|
| `mock` | 无（内置仿真） | `SENSOR_MODE=mock` | ✅ 已实现 |
| `tuya` | 涂鸦 IoT 水质仪（爱鱼者 YY-W9909） | `SENSOR_MODE=tuya` + TUYA_* | ✅ 已实现 |
| `dimos` | 宇树 Go2 机器狗 via DIMOS MCP | `SENSOR_MODE=dimos` + DIMOS_MCP_URL | 🔌 占位 |
| `drone` | 无人机多光谱航拍 | `SENSOR_MODE=drone` | 🔌 占位 |

**DIMOS 机器狗集成路径：**
```
Sentinel → sensor_read(adapter=dimos)
    → DimosMCPAdapter → JSON-RPC → DIMOS MCP Server
    → WebRTC → 宇树 Go2 → 巡塘采样
    → 水温/DO/pH/氨氮/摄像头画面
```

---

## 🔧 API 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/status` | 系统状态 |
| GET | `/api/health` | 三 Agent 健康检查（含运行统计） |
| GET | `/api/health/summary` | 人可读状态摘要 |
| GET | `/api/price?days=30` | 市场价格历史 |
| GET | `/api/roi` | ROI 分析 |
| POST | `/api/strategist/run?pond_id=A1` | 手动触发日报 |
| POST | `/api/growth/run` | 手动触发周报 |
| WS | `/ws` | 实时数据流 + 场景触发 |

---

## 🛡️ 工程约束

- **三层架构**：决策层 / 工具层 / 数据层严格隔离，不可跨层调用
- **单向数据流**：Sentinel → DB → Strategist → DB → Growth
- **MCP 工具**：无状态、幂等、≤5s 超时、不写 DB（crm_write/audit_log 除外）
- **LLM 调用**：`asyncio.timeout(10)` 强制超时 + 规则引擎 fallback（永不卡死）
- **飞书推送**：失败不 raise、不阻塞主流程、60min 同事件去重
- **传感器校验**：`validate_sensor()` 物理范围校验，异常值标记不抛出
- **危险操作**：清塘/排水/停增氧 → 自动附加「⚠️ 需人工确认」
- **代码规范**：Agent ≤200 行、MCP ≤250 行、函数 ≤60 行

---

## 💰 商业模型

**AI 替代的岗位 & 年省费用：**

| 原岗位 | 替代方案 | 年省 |
|--------|---------|------|
| 24h 值班技术员 | 🛡️ 哨兵 Agent | ¥8-12 万/塘 |
| 养殖顾问 | 📊 策略 Agent | ¥5-8 万/塘 |
| 销售 + 市场分析师 | 📈 增长 Agent | ¥10-15 万/塘 |
| **合计** | **三 Agent** | **¥23-35 万/塘/年** |

**目标市场**：中国 3,050 万亩虾塘，95% 无专业 AI 覆盖。

---

## 🗺️ 升级路径

```
阶段 0（当前 · 比赛版）
  └─ 单塘仿真 + 三 Agent + 飞书推送 + Demo

阶段 1（赛后 2 周 · MVP）
  └─ 对接 1-2 个真实塘口（涂鸦 IoT）
  └─ ClawhHub 正式发布（clawhub install shrimp-tycoon）

阶段 2（赛后 2 月 · Beta）
  └─ 多塘 + 多租户（tenant_id 隔离）
  └─ 飞书双向交互（虾农可回复反馈）
  └─ DIMOS × 宇树机器狗（自主巡塘）

阶段 3（赛后 6 月 · 商业化）
  └─ 批量接入养殖户（目标 100 塘）
  └─ PostgreSQL + TimescaleDB + Redis
  └─ Docker Compose 生产部署

阶段 4（Year 2 · 生态）
  └─ 微信小程序（虾农端）
  └─ 无人机多光谱航拍
  └─ API 开放平台（第三方集成）
```

---

## 🛠️ 技术栈

| 层 | 技术 |
|----|------|
| AI 推理 | Anthropic Claude（Opus / Haiku 三层路由） |
| Agent 框架 | OpenClaw（Skill + Cron + MCP） |
| 工具协议 | FastMCP（MCP 标准协议 · stdio） |
| 后端 | FastAPI + WebSocket + asyncio |
| 数据库 | SQLite WAL → PostgreSQL + TimescaleDB |
| 前端 | React + Vite + TypeScript + Tailwind CSS v3 |
| 推送 | 飞书消息卡片 API |
| 传感器 | 涂鸦 IoT Open API / DIMOS MCP |
| 知识库 | TF-IDF 检索 + 70 条养殖规则 |
| 测试 | pytest + pytest-asyncio（32 用例） |
| 部署 | Docker Compose（产品版） |

---

## 🧪 运行测试

```bash
# 核心测试（32 用例）
python -m pytest tests/test_sentinel.py tests/test_strategist.py \
  tests/test_growth.py tests/test_db.py tests/integration_test.py -v

# 全量测试
python -m pytest tests/ -v
```

---

## 📄 License

MIT

---

> **🦞 让每一口虾塘，都有一个 AI 合伙人。**
