# 🦞 虾塘大亨 · AI智慧水产决策系统

> OPC极限挑战赛 · 赛道二「AI合伙人」参赛项目

**一句话**：不是让农民学AI，是让AI学会养虾。

用 AI 替代养殖决策专家——从传感器数据到飞书告警，全程自动化，零人工干预。

---

## 系统架构

```
传感器/仿真 → MCP Server（9个工具）→ 哨兵Agent（三层决策）→ 飞书推送
                                    ↓
                              策略Agent（日报+捕捞+市场）
```

- **Node 1-4**：传感器 → 水质分析 → 投喂/病害/捕捞决策
- **Node 5-6**：市场对接 → 买家撮合
- **Node 7**：获客引擎（架构预留）
- **具身智能**：DIMOS × 宇树机器狗接口预留

## 商业模型

- SaaS 月费：¥1,800–3,000/塘/月
- 撮合佣金：1.5%
- 目标市场：中国 3,050 万亩虾塘，95% 无专业 AI

## 目录结构

```
├── mcp/              # MCP Server（9个无状态工具）
├── agent/            # 哨兵Agent + 策略Agent
├── backend/          # HTTP + WebSocket API Server
├── frontend/         # 演示前端（待开发）
├── data/             # 价格数据
├── knowledge-base/   # 70条养殖规则 + 54篇参考文献
├── tests/            # 单元测试 + 集成测试
├── INTERFACE_SPEC.md # 前后端接口规范
└── DEV_CONSTRAINTS.md # 开发约束手册
```

## 快速开始

```bash
pip install -r requirements.txt
bash start_demo.sh
```

## 技术栈

- **AI**：Anthropic Claude（Opus/Haiku 三层决策）
- **工具层**：Python FastMCP（MCP协议）
- **后端**：FastAPI + WebSocket
- **推送**：飞书消息卡片
- **具身接口**：DIMOS（宇树机器狗/无人机）

## 架构文档（飞书）

- [比赛版架构](https://feishu.cn/docx/P3jxd3VtWo53jgx2ChScMLFen5f)
- [产品版架构](https://feishu.cn/docx/KBO8dil0HoFMnQxZuxOcSECEnMc)
- [全链路系统设计](https://feishu.cn/docx/ESDbdAfaoopZx2x5IlQcirwLnAf)
- [开发执行手册](https://feishu.cn/docx/QPF5dk31Fos92Ox1yCqctv5unad)
