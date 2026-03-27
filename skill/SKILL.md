# 🦞 虾塘大亨 · AI 智慧水产决策系统

## 概述
三 Agent 协作的虾塘智能管理系统：实时监控 → 日报分析 → 商业增长。

## Agent 职责

### 哨兵 Agent（Sentinel）— 实时
- 每 5 分钟分析水质传感器数据
- 三层智能路由：CSI≤20→规则 | CSI 21-60→Haiku | CSI>60→Opus
- 危险信号推送飞书告警（60min 去重）
- 10 秒超时 + 规则引擎 fallback

### 策略 Agent（Strategist）— 每日
- 汇总当日传感器+决策数据
- 生成 DAILY-1.0 日报（趋势+投喂+病害+捕捞）
- 推送飞书日报

### 增长 Agent（Growth）— 每周
- 多塘 ROI 对比分析
- 市场价格匹配
- ICP 评分获客

## MCP 工具（12 个）
sensor_read · water_quality_score · feeding_recommend · disease_assess · harvest_advise · market_match · price_trend · kb_query · feishu_push · lead_score · crm_write · audit_log

## 安装
```bash
git clone https://github.com/Alex647648/shrimp-tycoon.git
cd shrimp-tycoon
./setup.sh
```

## 配置
填写 `.env`：
```
ANTHROPIC_API_KEY=sk-ant-...
FEISHU_APP_ID=cli_...
FEISHU_APP_SECRET=...
SENSOR_MODE=mock  # mock/tuya/dimos
```

## 启动
```bash
# 后端
cd backend && python server.py

# MCP Server
python mcp/server.py
```
