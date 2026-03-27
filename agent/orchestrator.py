"""Agent 编排层 — 三 Agent 调度 + 健康检查 + 状态汇总。

Sentinel: 由 server.py tick 驱动（每 5 分钟）
Strategist: cron 0 22 * * *（PDT）= 北京 06:00
Growth 周报: cron 0 0 * * 1（PDT）= 北京 08:00
Growth 触达: cron 0 1 * * *（PDT）= 北京 09:00

约束：三个 Agent 不互相调用，单向数据流。
"""

import time
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """三 Agent 编排器。"""

    def __init__(self, db=None, feishu_pusher=None, memory=None):
        self.db = db
        self.feishu = feishu_pusher
        self._boot_time = time.time()

        from sentinel import SentinelAgent
        from strategist import StrategistAgent
        from growth import GrowthAgent

        self.sentinel = SentinelAgent(feishu_pusher=feishu_pusher, db=db, memory=memory)
        self.strategist = StrategistAgent(db=db, feishu_pusher=feishu_pusher)
        self.growth = GrowthAgent(db=db, feishu_pusher=feishu_pusher)
        self._stats = {"sentinel_ticks": 0, "daily_reports": 0, "weekly_reports": 0, "errors": 0}

    # ── 单塘操作 ──

    async def run_sentinel_tick(self, sensor: dict, wqar: dict,
                                 push_feishu: bool = True) -> dict:
        """Sentinel 单次 tick。"""
        self._stats["sentinel_ticks"] += 1
        return await self.sentinel.analyze(sensor, wqar, push_feishu=push_feishu)

    async def run_daily_report(self, pond_id: str, date: str = None) -> dict:
        """触发 Strategist 日报。"""
        logger.info("Orchestrator: daily report for %s", pond_id)
        self._stats["daily_reports"] += 1
        return await self.strategist.run_daily(pond_id, date)

    async def run_weekly_report(self, date: str = None) -> dict:
        """触发 Growth 周报。"""
        logger.info("Orchestrator: weekly report")
        self._stats["weekly_reports"] += 1
        return await self.growth.run_weekly(date)

    async def run_daily_outreach(self, crm=None) -> dict:
        """触发 Growth 每日获客。"""
        return await self.growth.run_daily_outreach(crm=crm)

    # ── 多塘操作 ──

    async def run_all_ponds_daily(self, pond_ids: list[str] = None,
                                   date: str = None) -> list[dict]:
        """为所有活跃塘口生成日报（Strategist）。"""
        if pond_ids is None and self.db:
            try:
                pond_ids = await self.db.list_active_ponds()
            except Exception as e:
                logger.error("Failed to list ponds: %s", e)
                pond_ids = []

        tasks = [self.run_daily_report(pid, date) for pid in (pond_ids or [])]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        reports = []
        for pid, r in zip(pond_ids or [], results):
            if isinstance(r, Exception):
                logger.error("Daily report error for %s: %s", pid, r)
                self._stats["errors"] += 1
                reports.append({"pond_id": pid, "error": str(r)})
            else:
                reports.append(r)
        return reports

    async def run_sentinel_batch(self, pond_sensors: list[dict],
                                  wqar_list: list[dict],
                                  push_feishu: bool = True) -> list[dict]:
        """多塘并发 Sentinel 分析。"""
        return await self.sentinel.run_batch(pond_sensors, wqar_list, push_feishu)

    # ── 系统健康 ──

    def health_check(self) -> dict:
        """系统健康检查。"""
        uptime = time.time() - self._boot_time
        return {
            "status": "healthy",
            "uptime_seconds": int(uptime),
            "uptime_human": _format_uptime(uptime),
            "agents": {
                "sentinel": "active",
                "strategist": "active",
                "growth": "active",
            },
            "db_connected": self.db is not None,
            "feishu_connected": self.feishu is not None,
            "stats": dict(self._stats),
            "timestamp": datetime.now().isoformat(),
        }

    def status_summary(self) -> str:
        """生成人可读的状态摘要。"""
        h = self.health_check()
        s = h["stats"]
        return (
            f"🦞 虾塘大亨系统状态\n"
            f"运行时间：{h['uptime_human']}\n"
            f"Agent：Sentinel ✅ | Strategist ✅ | Growth ✅\n"
            f"DB：{'✅ 已连接' if h['db_connected'] else '❌ 未连接'}\n"
            f"飞书：{'✅ 已连接' if h['feishu_connected'] else '❌ 未连接'}\n"
            f"统计：哨兵 {s['sentinel_ticks']} 次 | 日报 {s['daily_reports']} 份 | "
            f"周报 {s['weekly_reports']} 份 | 错误 {s['errors']} 次"
        )


def _format_uptime(seconds: float) -> str:
    h, rem = divmod(int(seconds), 3600)
    m, s = divmod(rem, 60)
    if h > 0:
        return f"{h}h{m}m"
    return f"{m}m{s}s"
