"""Agent 编排层 — 三 Agent 调度（Sentinel 实时 + Strategist 日报 + Growth 周报）。

Sentinel: 由 server.py tick 驱动（每 5 分钟）
Strategist: 每天 20:00 北京时间（cron 或手动触发）
Growth: 每周一 08:00 北京时间（cron 或手动触发）

约束：
- Sentinel ≠ Strategist ≠ Growth（单向数据流）
- 三个 Agent 不互相调用
"""

import logging
import asyncio
from pathlib import Path

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """三 Agent 编排器。"""

    def __init__(self, db=None, feishu_pusher=None, memory=None):
        self.db = db
        self.feishu = feishu_pusher

        # 延迟导入避免循环依赖
        from sentinel import SentinelAgent
        from strategist import StrategistAgent
        from growth import GrowthAgent

        self.sentinel = SentinelAgent(
            feishu_pusher=feishu_pusher, db=db, memory=memory
        )
        self.strategist = StrategistAgent(db=db, feishu_pusher=feishu_pusher)
        self.growth = GrowthAgent(db=db, feishu_pusher=feishu_pusher)

    async def run_sentinel_tick(self, sensor: dict, wqar: dict,
                                 push_feishu: bool = True) -> dict:
        """Sentinel 单次 tick（由 server.py 驱动）。"""
        return await self.sentinel.analyze(sensor, wqar, push_feishu=push_feishu)

    async def run_daily_report(self, pond_id: str, date: str = None) -> dict:
        """触发 Strategist 日报。"""
        logger.info("Orchestrator: triggering daily report for %s", pond_id)
        return await self.strategist.run_daily(pond_id, date)

    async def run_weekly_report(self, date: str = None) -> dict:
        """触发 Growth 周报。"""
        logger.info("Orchestrator: triggering weekly report")
        return await self.growth.run_weekly(date)

    async def run_daily_outreach(self) -> dict:
        """触发 Growth 每日获客。"""
        return await self.growth.run_daily_outreach()
