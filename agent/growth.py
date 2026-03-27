"""Growth Agent — 周报生成 + 商业效益分析。

触发方式：OpenClaw cron（每周一 08:00 北京时间）
约束（AGENT_CONSTRAINTS.md §2.3）：
- 只读 DB（不写任何表）
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

PRICE_DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "industry_based_price_data.json"
PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "growth_system.txt"


def _load_price_data() -> dict:
    """加载行业价格数据。"""
    try:
        with open(PRICE_DATA_PATH, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.warning("Failed to load price data: %s", e)
        return {}


def _load_prompt() -> str:
    """加载系统提示词。"""
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return "你是虾塘商业效益分析师。生成周报JSON。"


def _rule_weekly(ponds: list, price_data: dict) -> dict:
    """纯规则周报（fallback）。"""
    summaries = []
    for p in ponds:
        summaries.append({
            "pond_id": p.get("pond_id", "unknown"),
            "avg_weight": p.get("avg_weight", 0),
            "survival_rate": p.get("survival_rate", 0.9),
            "roi_estimate": round(p.get("avg_weight", 0) * 0.04, 2),
            "status": "healthy" if p.get("avg_weight", 0) > 20 else "growing",
        })

    prices = price_data.get("prices", [])
    avg_price = sum(p.get("price", 0) for p in prices[-7:]) / max(len(prices[-7:]), 1) if prices else 42.0

    return {
        "schema": "GROWTH-1.0",
        "date": datetime.now().strftime("%Y-%m-%d"),
        "ponds_summary": summaries,
        "market_overview": {
            "avg_price": round(avg_price, 1),
            "trend": "稳定",
            "best_sell_window": "待分析",
        },
        "recommendations": ["继续观察市场价格走势", "关注天气变化对产量影响"],
        "model_used": "rules",
    }


class GrowthAgent:
    """商业效益分析 Agent。"""

    def __init__(self, db=None, feishu_pusher=None):
        self.db = db
        self.feishu = feishu_pusher
        self.price_data = _load_price_data()

    async def run_weekly(self, date: str = None) -> dict:
        """生成周报。"""
        start = time.time()
        date = date or datetime.now().strftime("%Y-%m-%d")

        # 读取活跃塘口
        ponds_data = []
        if self.db:
            try:
                ponds = await self.db.list_active_ponds()
                for pid in ponds:
                    records = await self.db.get_day_records(pid, date)
                    ponds_data.append({"pond_id": pid, **records})
            except Exception as e:
                logger.warning("DB read failed: %s", e)

        # LLM 或 fallback
        try:
            async with asyncio.timeout(10.0):
                from anthropic import Anthropic
                client = Anthropic()
                prompt_text = _load_prompt()
                user_msg = f"塘口数据：{json.dumps(ponds_data, ensure_ascii=False)}\n价格数据：{json.dumps(self.price_data, ensure_ascii=False)[:2000]}"
                response = await asyncio.to_thread(
                    lambda: client.messages.create(
                        model="claude-haiku-4-5-20251001",
                        max_tokens=800,
                        system=prompt_text,
                        messages=[{"role": "user", "content": user_msg}]
                    )
                )
                report = json.loads(response.content[0].text)
                report["model_used"] = "haiku"
        except Exception as e:
            logger.warning("LLM failed: %s — using rule fallback", e)
            report = _rule_weekly(ponds_data, self.price_data)

        report["latency_ms"] = int((time.time() - start) * 1000)

        # 飞书推送
        if self.feishu:
            try:
                await self.feishu.send_weekly_report(report)
            except Exception as e:
                logger.warning("Feishu push failed: %s", e)

        return report

    async def run_daily_outreach(self) -> dict:
        """每日获客检查（简化版）。"""
        return {
            "schema": "OUTREACH-1.0",
            "date": datetime.now().strftime("%Y-%m-%d"),
            "leads_checked": 0,
            "new_leads": [],
            "recommendations": ["暂无新线索"],
            "model_used": "rules",
        }
