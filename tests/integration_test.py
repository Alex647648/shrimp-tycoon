"""全链路集成测试 — 5 个演示场景端到端验证。"""

import sys
import time
import asyncio
import pytest
from pathlib import Path
from unittest.mock import AsyncMock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "agent"))

from db import PondDB
from sentinel import SentinelAgent
from sentinel_safety import validate_sensor
from memory import SentinelMemory
from orchestrator import AgentOrchestrator


async def make_env():
    """初始化 DB + Orchestrator（无飞书）。"""
    db = PondDB(db_path=":memory:")
    await db.init()
    memory = SentinelMemory()
    orch = AgentOrchestrator(db=db, feishu_pusher=None, memory=memory)
    return db, orch


# === 5 个演示场景 ===

@pytest.mark.asyncio
async def test_scenario_do_drop():
    """场景1: 溶解氧骤降 → 高风险决策 → DB 写入。"""
    db, orch = await make_env()
    sensor = {"pond_id": "A1", "temp": 26.5, "DO": 1.2, "pH": 7.8, "ammonia": 0.15}
    wqar = {"csi": 85, "risk_level": 4}
    
    report = await orch.run_sentinel_tick(sensor, wqar, push_feishu=False)
    
    assert report["risk_level"] >= 3
    assert report["model_used"] == "rules"
    assert report["latency_ms"] < 5000
    assert any("停" in a or "增氧" in a for a in report.get("actions", []))


@pytest.mark.asyncio
async def test_scenario_wssv():
    """场景2: 白斑病毒 → 最高风险。"""
    db, orch = await make_env()
    sensor = {"pond_id": "A2", "dead_shrimp": True, "temp": 26, "DO": 5.0, "pH": 7.8}
    wqar = {"csi": 95, "risk_level": 5}
    
    report = await orch.run_sentinel_tick(sensor, wqar, push_feishu=False)
    
    assert report["risk_level"] >= 4
    disease = report.get("disease", {})
    assert disease.get("risk") == "high" or "隔离" in str(report.get("actions", []))


@pytest.mark.asyncio
async def test_scenario_normal():
    """场景3: 正常水质 → 低风险 → 规则引擎。"""
    db, orch = await make_env()
    sensor = {"pond_id": "A3", "temp": 26, "DO": 7.0, "pH": 7.8, "ammonia": 0.1}
    wqar = {"csi": 10, "risk_level": 1}
    
    report = await orch.run_sentinel_tick(sensor, wqar, push_feishu=False)
    
    assert report["risk_level"] <= 2
    assert report["model_used"] == "rules"
    assert report["latency_ms"] < 1000


@pytest.mark.asyncio
async def test_scenario_molt():
    """场景4: 蜕壳期 → 减投。"""
    db, orch = await make_env()
    sensor = {"pond_id": "A4", "molt_peak": True, "temp": 25, "DO": 6.0, "pH": 7.8}
    wqar = {"csi": 30, "risk_level": 2}
    
    report = await orch.run_sentinel_tick(sensor, wqar, push_feishu=False)
    
    feeding = report.get("feeding", {})
    if feeding:
        assert feeding.get("total_ratio", 3.0) <= 3.0


@pytest.mark.asyncio
async def test_daily_report():
    """场景5: Strategist 日报生成。"""
    db, orch = await make_env()
    
    # 先写入一些传感器数据
    await db.save_reading("A1", {"temp": 26, "DO": 6.0, "pH": 7.8, "ammonia": 0.1})
    await db.save_decision("A1", {"risk_level": 1, "actions": ["正常投喂"], "model_used": "rules"})
    
    report = await orch.run_daily_report("A1")
    assert report is not None
    assert report.get("model_used") in ["haiku", "rules"]


# === 性能 + 故障隔离 ===

@pytest.mark.asyncio
async def test_performance_under_30s():
    """全链路延迟 < 30s。"""
    db, orch = await make_env()
    sensor = {"pond_id": "P1", "temp": 26, "DO": 6.0, "pH": 7.8}
    wqar = {"csi": 15, "risk_level": 1}
    
    start = time.time()
    report = await orch.run_sentinel_tick(sensor, wqar, push_feishu=False)
    elapsed = time.time() - start
    
    assert elapsed < 30, f"延迟 {elapsed:.1f}s 超过 30s 限制"


@pytest.mark.asyncio
async def test_feishu_failure_non_blocking():
    """飞书失败不阻断主流程。"""
    db, orch = await make_env()
    # 设置一个会失败的飞书 pusher
    bad_feishu = AsyncMock()
    bad_feishu.send_alert = AsyncMock(side_effect=Exception("Feishu down"))
    orch.sentinel.feishu = bad_feishu
    
    sensor = {"pond_id": "F1", "temp": 26, "DO": 1.0, "pH": 7.8}
    wqar = {"csi": 90, "risk_level": 5}
    
    # 不应抛异常
    report = await orch.run_sentinel_tick(sensor, wqar, push_feishu=True)
    assert report is not None
    assert report["risk_level"] >= 3


@pytest.mark.asyncio
async def test_validate_sensor_integration():
    """传感器校验集成。"""
    sensor = {"temp": 99, "DO": -5, "pH": 7.8}
    validated = validate_sensor(sensor)
    assert validated["temp_val_invalid"] == True
    assert validated["DO_val_invalid"] == True
    assert 0 < validated["temp"] < 45
    assert validated["DO"] >= 0
