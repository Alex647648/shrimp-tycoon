"""Growth Agent — 周报 + 获客 + ROI 分析 + 触达序列。

触发方式：
- 周报：OpenClaw cron 每周一 08:00 北京时间
- 获客：OpenClaw cron 每天 09:00 北京时间
约束（AGENT_CONSTRAINTS.md §2.3）：
- 只读 DB（不写任何种养表）
- 不给种养操作建议（只做商业分析）
- LLM 必须 asyncio.timeout(10) + 规则 fallback
"""

import os
import json
import time
import asyncio
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

BASE = Path(__file__).resolve().parent.parent
PRICE_PATH = BASE / "data" / "industry_based_price_data.json"
BUYERS_PATH = BASE / "data" / "buyers.json"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "growth_system.txt"


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
        return {}


def _load_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return "你是虾塘商业效益分析师。生成周报JSON。"


def _calc_roi(ponds: list, price_data: dict) -> dict:
    """多塘 ROI 计算。"""
    total_kg = 0.0
    total_value = 0.0
    current = price_data.get("current_price", {}).get("medium", 24.0)

    for p in ponds:
        w = p.get("avg_weight", 0)
        cnt = p.get("count", 0)
        survival = p.get("survival_rate", 0.9)
        kg = w * cnt * survival / 1000
        total_kg += kg
        total_value += kg * current

    cost_per_mu = 8000  # 每亩成本估算
    pond_count = max(len(ponds), 1)
    total_cost = cost_per_mu * pond_count
    profit = total_value - total_cost

    return {
        "total_kg": round(total_kg, 1),
        "total_value": round(total_value),
        "total_cost": total_cost,
        "profit": round(profit),
        "roi_multiple": round(total_value / max(total_cost, 1), 2),
        "market_price": current,
        "ai_savings": {
            "sentinel_replace": 100000,
            "strategist_replace": 60000,
            "disease_prevention": 80000,
            "total_annual": 240000,
        },
    }


def _match_buyers(ponds: list, buyers_data: dict) -> list:
    """匹配买家（按规格和地域）。"""
    buyers = buyers_data.get("buyers", [])
    avg_w = sum(p.get("avg_weight", 0) for p in ponds) / max(len(ponds), 1)
    grade = "large" if avg_w >= 30 else "medium" if avg_w >= 20 else "small"

    matched = []
    for b in buyers:
        if b.get("preferred_grade") == grade or grade == "medium":
            matched.append({
                "name": b["name"],
                "region": b.get("region", ""),
                "price_range": b.get("price_range", {}),
                "rating": b.get("rating", 0),
                "match_reason": "规格匹配" if b.get("preferred_grade") == grade else "通用买家",
            })
    return sorted(matched, key=lambda x: x.get("rating", 0), reverse=True)[:3]


def _rule_weekly(ponds: list, price_data: dict, buyers_data: dict) -> dict:
    """增强版规则周报。"""
    roi = _calc_roi(ponds, price_data)
    buyers = _match_buyers(ponds, buyers_data)

    summaries = []
    for p in ponds:
        summaries.append({
            "pond_id": p.get("pond_id", "unknown"),
            "avg_weight": p.get("avg_weight", 0),
            "survival_rate": p.get("survival_rate", 0.9),
            "status": "可捕捞" if p.get("avg_weight", 0) >= 35 else "生长中",
        })

    prices = price_data.get("daily_prices", [])
    recent = prices[-7:] if prices else []
    if len(recent) >= 2:
        trend = "上涨" if recent[-1].get("medium", 0) > recent[0].get("medium", 0) else "下跌"
    else:
        trend = "稳定"

    recs = []
    if any(s["status"] == "可捕捞" for s in summaries):
        recs.append("有塘口达到捕捞规格，建议本周联系买家锁定价格")
    if trend == "上涨":
        recs.append("市场价格上涨中，可适当推迟捕捞等待更高价位")
    elif trend == "下跌":
        recs.append("市场价格下行，建议尽快出货避免损失")
    recs.append("关注天气预报，暴雨前后价格波动较大")
    if roi["profit"] > 0:
        recs.append("当前预估利润¥{}，ROI {:.1f}×".format(roi["profit"], roi["roi_multiple"]))

    return {
        "schema": "GROWTH-1.0",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "ponds_summary": summaries,
        "roi": roi,
        "matched_buyers": buyers,
        "market_overview": {
            "avg_price": roi["market_price"],
            "trend": trend,
            "best_sell_window": "本周" if trend == "下跌" else "观望",
        },
        "recommendations": recs[:5],
        "model_used": "rules",
    }


# ── 触达序列模板 ──
OUTREACH_SEQUENCE = [
    {"day": 1, "channel": "微信", "template": "您好，我是虾塘大亨团队。我们的AI系统帮助养殖户年均节省24万元人工成本，想了解下您的养殖情况。"},
    {"day": 3, "channel": "微信", "template": "发送ROI计算报告：{name}养殖场，预估年节省¥{savings}，附PDF。"},
    {"day": 7, "channel": "微信", "template": "成功案例：湖北{region}养殖户使用AI后，病害损失减少60%，年增收¥12,000。"},
    {"day": 14, "channel": "微信", "template": "邀请免费试用：1个塘口，30天全功能体验，无需绑卡。"},
    {"day": 21, "channel": "电话", "template": "试用跟进 + 付费引导。"},
]


class GrowthAgent:
    """商业效益分析 + 获客 Agent。"""

    def __init__(self, db=None, feishu_pusher=None):
        self.db = db
        self.feishu = feishu_pusher
        self.price_data = _load_json(PRICE_PATH)
        self.buyers_data = _load_json(BUYERS_PATH)

    async def run_weekly(self, date: str = None) -> dict:
        """生成周报（ROI + 市场 + 买家匹配）。"""
        start = time.time()
        date = date or datetime.now().strftime("%Y-%m-%d")

        ponds_data = await self._load_ponds(date)

        try:
            async with asyncio.timeout(10.0):
                from anthropic import Anthropic
                client = Anthropic()
                user_msg = (
                    f"塘口数据：{json.dumps(ponds_data, ensure_ascii=False)}\n"
                    f"价格：{json.dumps(self.price_data, ensure_ascii=False)[:2000]}\n"
                    f"买家库：{json.dumps(self.buyers_data, ensure_ascii=False)[:1000]}"
                )
                resp = await asyncio.to_thread(
                    lambda: client.messages.create(
                        model="claude-haiku-4-5-20251001", max_tokens=800,
                        system=_load_prompt(),
                        messages=[{"role": "user", "content": user_msg}],
                    )
                )
                report = json.loads(resp.content[0].text)
                report["model_used"] = "haiku"
        except Exception as e:
            logger.warning("LLM failed: %s — rule fallback", e)
            report = _rule_weekly(ponds_data, self.price_data, self.buyers_data)

        report["latency_ms"] = int((time.time() - start) * 1000)

        if self.feishu:
            try:
                await self.feishu.send_weekly_report(report)
            except Exception as e:
                logger.warning("Feishu push failed: %s", e)

        return report

    async def run_lead_discovery(self, crm=None, search_fn=None,
                                 sources: list[str] = None) -> dict:
        """线索自动发现（周一 cron 触发）。

        OpenClaw 模式：返回搜索任务清单，Claude 用 web_search 执行
        独立模式：传入 search_fn，自动搜索+提取+评分+写CRM
        """
        from mcp.lead_discovery import LeadDiscovery
        discovery = LeadDiscovery(crm=crm)
        return await discovery.run_full_cycle(search_fn=search_fn, sources=sources)

    async def run_daily_outreach(self, crm=None) -> dict:
        """每日获客触达（读 CRM → 评分 → 生成触达任务）。"""
        from mcp.lead_scorer import score_lead

        today = datetime.now().strftime("%Y-%m-%d")
        leads = []
        tasks_generated = []

        if crm:
            leads = crm.list_leads(status="new", limit=20)

        # 评分
        scored = []
        for lead in leads:
            result = score_lead(lead)
            scored.append({**lead, **result})

        # 筛选 A/B 级线索
        qualified = [s for s in scored if s.get("grade") in ("A", "B")]

        # 生成触达任务
        for lead in qualified[:10]:
            lead_id = lead.get("id", 0)
            # 判断该线索的触达阶段（简化：按创建天数）
            created = lead.get("created_at", today)
            try:
                days_since = (datetime.now() - datetime.fromisoformat(created)).days
            except Exception:
                days_since = 0

            for step in OUTREACH_SEQUENCE:
                if step["day"] == days_since + 1:
                    msg = step["template"].format(
                        name=lead.get("name", ""),
                        savings=240000,
                        region=lead.get("region", "湖北"),
                    )
                    tasks_generated.append({
                        "lead_name": lead.get("name"),
                        "lead_grade": lead.get("grade"),
                        "day": step["day"],
                        "channel": step["channel"],
                        "message": msg,
                    })
                    if crm:
                        crm.log_outreach(lead_id, step["day"], step["channel"], msg)

        return {
            "schema": "OUTREACH-1.0",
            "date": today,
            "leads_checked": len(leads),
            "qualified": len(qualified),
            "tasks_generated": tasks_generated,
            "funnel": {
                "total_leads": len(leads),
                "qualified": len(qualified),
                "target_trial": int(len(qualified) * 0.15),
                "target_paid": int(len(qualified) * 0.06),
            },
            "model_used": "rules",
        }

    async def _load_ponds(self, date: str) -> list:
        """从 DB 读取活跃塘口数据。"""
        ponds_data = []
        if self.db:
            try:
                ponds = await self.db.list_active_ponds()
                for pid in ponds:
                    records = await self.db.get_day_records(pid, date)
                    ponds_data.append({"pond_id": pid, **(records if isinstance(records, dict) else {})})
            except Exception as e:
                logger.warning("DB read failed: %s", e)
        return ponds_data
