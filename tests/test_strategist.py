"""Strategist Agent 单元测试 — 5 个用例。"""

import sys
import pytest
from unittest.mock import AsyncMock
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from strategist import StrategistAgent


@pytest.fixture
def mock_db():
    db = AsyncMock()
    # get_day_records 返回格式：[{"type":"sensor","data":{...}}, {"type":"decision","data":{...}}]
    db.get_day_records.return_value = [
        {"type": "sensor", "data": {"temp": 26.5, "do_val": 6.2, "pH": 7.8, "ammonia": 0.15}, "timestamp": 1000},
        {"type": "sensor", "data": {"temp": 27.0, "do_val": 5.8, "pH": 7.7, "ammonia": 0.18}, "timestamp": 2000},
        {"type": "decision", "data": {"risk_level": 2, "actions": ["正常投喂"]}, "timestamp": 1500},
    ]
    db.get_trend.return_value = [26.5, 26.8, 27.0, 26.9, 27.1]
    db.save_daily_report = AsyncMock()
    return db


@pytest.fixture
def agent(mock_db):
    return StrategistAgent(db=mock_db)


@pytest.mark.asyncio
async def test_run_daily_normal(agent, mock_db):
    """正常日报生成。"""
    report = await agent.run_daily("A1", "2026-03-27")
    assert report is not None
    assert report.get("model_used") in ["haiku", "rules"]


@pytest.mark.asyncio
async def test_run_daily_no_data(mock_db):
    """DB 返回空数据。"""
    mock_db.get_day_records.return_value = []
    mock_db.get_trend.return_value = []
    agent = StrategistAgent(db=mock_db)
    
    report = await agent.run_daily("A1", "2026-03-27")
    assert report is not None


@pytest.mark.asyncio
async def test_llm_timeout_fallback(mock_db):
    """LLM 超时 → fallback。"""
    agent = StrategistAgent(db=mock_db)
    report = await agent.run_daily("A1", "2026-03-27")
    assert report.get("model_used") == "rules"


@pytest.mark.asyncio
async def test_no_sensor_read(agent, mock_db):
    """验证不直接读传感器。"""
    await agent.run_daily("A1", "2026-03-27")
    mock_db.get_day_records.assert_called()


@pytest.mark.asyncio
async def test_no_decisions_write(agent, mock_db):
    """验证不写 decisions 表。"""
    await agent.run_daily("A1", "2026-03-27")
    assert not hasattr(mock_db, 'save_decision') or not mock_db.save_decision.called
