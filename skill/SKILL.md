# 🦞 shrimp-tycoon — AI 智慧水产 Agent

> 让每一口虾塘，都有一个 AI 合伙人。

## 触发条件
用户提到以下关键词时自动激活：
虾塘 / 养殖 / 水质 / 投喂 / 捕捞 / 日报 / 周报 / 虾群 / 溶解氧 / DO / pH / 氨氮 /
aquaculture / shrimp / 白斑 / WSSV / 蜕壳 / 增长报告 / 获客 / CRM

## 依赖检查（首次使用时自动校验）
```
✅ claude mcp list 包含 shrimp-tycoon（12 个工具）
✅ data/pond.db 存在（setup.sh 自动初始化）
✅ .env 已填：ANTHROPIC_API_KEY / FEISHU_APP_ID / FEISHU_APP_SECRET
```

## 三个 Agent 说明

### 🛡️ 哨兵 Agent（Sentinel）— 实时守护
- **触发**：每 5 分钟自动 / 传感器异常事件
- **能力**：三层智能路由（规则→Haiku→Opus）+ 关键词触发 + 10s 超时 fallback
- **输出**：DECISION-1.0 即时决策 + 飞书告警（60min 去重）
- **安全**：传感器物理校验 + 危险操作人工确认

### 📊 策略 Agent（Strategist）— 每日洞察
- **触发**：cron `0 22 * * *`（PDT）= 北京 06:00
- **能力**：读 DB 当日数据 → 趋势分析 → 生成 DAILY-1.0 日报
- **输出**：投喂/病害/捕捞/建议 → 飞书日报卡片

### 📈 增长 Agent（Growth）— 商业增长
- **触发**：周报 cron `0 0 * * 1` / 获客 cron `0 1 * * *`
- **能力**：多塘 ROI → 买家匹配 → ICP 评分 → 触达序列
- **输出**：GROWTH-1.0 周报 + OUTREACH-1.0 获客任务

## 按需触发（用户说 → 我做）

| 用户说 | 操作 |
|--------|------|
| "查一下 A03 塘" | `sensor_read` + `water_quality_score` → 输出 WQAR |
| "现在该捕捞吗" | `harvest_advise` + `market_match` → 捕捞决策 + 买家 |
| "帮我跑今天的日报" | 立刻执行策略 Agent 全流程 |
| "生成本周周报" | 立刻执行增长 Agent 周报 |
| "找 3 个潜在客户" | `web_search` × 3 源 + `lead_score` → 推荐清单 |
| "生成本月 ROI 报告" | 读 DB decisions → 统计节省成本 + 增益 |
| "机器狗去巡 A03 塘" | `sensor_read(adapter=dimos)` → DIMOS 控制机器狗 |
| "系统状态" | GET `/api/health` → 三 Agent 健康检查 |

## MCP 工具清单（17 个）

| 工具 | 功能 | 谁用 |
|------|------|------|
| `sensor_read` | 读传感器（Mock/Tuya/DIMOS） | Sentinel |
| `water_quality_score` | CSI 水质评分 | Sentinel, Strategist |
| `feeding_recommend` | 投喂建议 | Sentinel |
| `disease_assess` | 病害评估 | Sentinel |
| `harvest_advise` | 捕捞建议 | Strategist |
| `kb_query` | 知识库检索（70 规则） | All |
| `market_match` | 买家智能匹配（MMR-2.0） | Growth |
| `sell_window` | 最佳出货窗口分析 | Growth |
| `market_report` | 一站式市场撮合报告 | Growth |
| `price_trend` | 价格趋势 | Strategist, Growth |
| `lead_score` | ICP 评分 | Growth |
| `lead_discover` | 线索自动发现（10 个来源） | Growth |
| `lead_process` | 线索处理（提取+评分+CRM） | Growth |
| `crm_write` | CRM 写入 | Growth |
| `feishu_push` | 飞书推送 | All |
| `audit_log` | 审计日志 | All |

## 传感器模式（SENSOR_MODE）
- `mock`：仿真数据（默认，无需硬件）
- `tuya`：涂鸦 IoT 智能水质仪（爱鱼者 YY-W9909）
- `dimos`：DIMOS × 宇树机器狗巡塘
- `drone`：无人机多光谱航拍（开发中）

## 飞书卡片格式

### 告警（Sentinel）
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

### 日报（Strategist）
```
🌅 A03 号池 · 每日报告 · 2026-03-27

📊 水质：综合评分 82/100（良好）
🦞 虾群：均重 28.5g，预计 14 天可捕
💰 行情：潜江大虾 ¥26.7/kg（↓ 季节性）

📋 今日重点：
  1. 按计划投喂（07:00/19:00）
  2. 关注氨氮，若 >0.2 考虑换水
  3. 距捕捞窗口：14 天

🎣 捕捞建议：暂不建议，再等 14 天价格可能回升
🤝 匹配买家：武汉新发展水产（评分 4.8⭐）报价 ¥27.0/kg
```

## OpenClaw cron 配置

安装后自动注册（`setup.sh` 执行）：

```bash
# 策略 Agent 日报（北京 06:00）
openclaw cron add --cron "0 22 * * *" \
  "策略Agent：为所有活跃虾塘生成今日日报，读 data/pond.db，推飞书"

# 增长 Agent 周报（北京 08:00 周一）
openclaw cron add --cron "0 0 * * 1" \
  "增长Agent：生成本周获客任务清单，web_search线索，更新CRM"

# 增长 Agent 触达（北京 09:00 每天）
openclaw cron add --cron "0 1 * * *" \
  "增长Agent：执行今日客户触达序列，发送跟进消息"
```

## 快速安装

```bash
git clone https://github.com/Alex647648/shrimp-tycoon.git
cd shrimp-tycoon
./setup.sh    # pip + DB + MCP注册 + skill安装 + cron添加
# 编辑 .env 填入 API keys
python backend/server.py
```
