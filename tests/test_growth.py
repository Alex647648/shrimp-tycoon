"""Growth Agent 单元测试 — 4 个用例。"""

import sys
import pytest
from unittest.mock import AsyncMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from growth import GrowthAgent


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.list_active_ponds.return_value = ["A1", "A2"]
    db.get_day_records.return_value = {
        "sensor": [{"temp": 26, "DO": 6.0, "avg_weight": 25.5}],
        "decision": [],
    }
    return db


@pytest.fixture
def agent(mock_db):
    return GrowthAgent(db=mock_db)


@pytest.mark.asyncio
async def test_run_weekly_normal(agent):
    """正常周报生成。"""
    report = await agent.run_weekly("2026-03-27")
    assert report.get("model_used") in ["haiku", "rules"]
    assert "market_overview" in report or report.get("schema") == "GROWTH-1.0"


@pytest.mark.asyncio
async def test_run_weekly_no_ponds():
    """无活跃塘口。"""
    db = AsyncMock()
    db.list_active_ponds.return_value = []
    agent = GrowthAgent(db=db)
    
    report = await agent.run_weekly("2026-03-27")
    assert report is not None


@pytest.mark.asyncio
async def test_no_operation_advice(agent):
    """输出不含种养操作关键词。"""
    report = await agent.run_weekly("2026-03-27")
    forbidden = ["增氧", "停食", "消毒", "换水", "投药"]
    recommendations = str(report.get("recommendations", []))
    for kw in forbidden:
        assert kw not in recommendations, f"Growth 不应包含操作建议: {kw}"


@pytest.mark.asyncio
async def test_llm_timeout_fallback(agent):
    """LLM 不可用 → fallback。"""
    report = await agent.run_weekly("2026-03-27")
    assert report.get("model_used") == "rules"


@pytest.mark.asyncio
async def test_daily_outreach(agent):
    """每日获客检查。"""
    report = await agent.run_daily_outreach()
    assert report.get("schema") == "OUTREACH-1.0"
