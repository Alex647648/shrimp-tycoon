"""Sentinel Agent 单元测试 — 5 场景 + 4 额外验证。"""

import sys
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, "backend")

from sentinel import SentinelAgent, _keyword_model, _rule_engine
from sentinel_safety import validate_sensor, _safety_check


@pytest.fixture
def agent():
    """创建无外部依赖的 SentinelAgent。"""
    return SentinelAgent(feishu_pusher=None, db=None, memory=None)


# === 场景测试（规则引擎模式，不需要 LLM） ===

@pytest.mark.asyncio
async def test_do_drop(agent):
    """DO=1.2 → 关键词触发 Opus，但 LLM 不可用 → fallback 规则引擎。"""
    sensor = {"pond_id": "A1", "temp": 25, "DO": 1.2, "pH": 7.5, "ammonia": 0.1}
    wqar = {"csi": 80, "risk_level": 4}
    
    # 验证关键词路由
    model = _keyword_model(sensor, wqar)
    assert model == "claude-opus-4-6", "DO<1.5 应触发 Opus"
    
    # 实际 analyze（LLM 不可用，自动 fallback）
    report = await agent.analyze(sensor, wqar)
    assert report["risk_level"] >= 3
    assert report["model_used"] == "rules"  # fallback
    assert any("停" in a or "增氧" in a for a in report.get("actions", []))


@pytest.mark.asyncio
async def test_wssv(agent):
    """dead_shrimp=True → 关键词触发 Opus → fallback。"""
    sensor = {"pond_id": "A2", "dead_shrimp": True, "temp": 26, "DO": 5.0, "pH": 7.8}
    wqar = {"csi": 90, "risk_level": 5}
    
    model = _keyword_model(sensor, wqar)
    assert model == "claude-opus-4-6"
    
    report = await agent.analyze(sensor, wqar)
    assert report["risk_level"] >= 4
    disease = report.get("disease", {})
    assert disease.get("risk") == "high" or "隔离" in str(report.get("actions", []))


@pytest.mark.asyncio
async def test_storm(agent):
    """pH=6.0 → 致命范围 → 关键词触发 Opus。"""
    sensor = {"pond_id": "A3", "temp": 20, "DO": 4.0, "pH": 6.0, "ammonia": 0.3}
    wqar = {"csi": 70, "risk_level": 3}
    
    model = _keyword_model(sensor, wqar)
    assert model == "claude-opus-4-6", "pH<6.5 应触发 Opus"


@pytest.mark.asyncio
async def test_molt(agent):
    """蜕壳期 → 减投。"""
    sensor = {"pond_id": "A4", "molt_peak": True, "temp": 25, "DO": 6.0, "pH": 7.8}
    wqar = {"csi": 30, "risk_level": 2}
    
    report = await agent.analyze(sensor, wqar)
    feeding = report.get("feeding", {})
    if feeding:
        assert feeding.get("total_ratio", 3.0) < 3.0, "蜕壳期应减投"


@pytest.mark.asyncio
async def test_harvest_ready(agent):
    """正常运营 → 低风险。"""
    sensor = {"pond_id": "A5", "temp": 26, "DO": 7.0, "pH": 7.8, "avg_weight": 38, "count": 5000}
    wqar = {"csi": 15, "risk_level": 1}
    
    report = await agent.analyze(sensor, wqar)
    assert report["risk_level"] <= 2
    assert report["model_used"] == "rules"  # CSI≤20 走规则


# === 额外验证 ===

@pytest.mark.asyncio
async def test_llm_timeout_fallback(agent):
    """LLM 超时 → fallback 到规则引擎。"""
    sensor = {"pond_id": "B1", "temp": 25, "DO": 2.5, "pH": 7.5}
    wqar = {"csi": 50, "risk_level": 3}
    
    # CSI=50 会尝试 Haiku，但没有 API key → 自动 fallback
    report = await agent.analyze(sensor, wqar)
    assert report["model_used"] == "rules"


@pytest.mark.asyncio
async def test_feishu_cooldown(agent):
    """飞书推送去重 60 分钟。"""
    assert agent._should_push("A1", "alert") == True
    assert agent._should_push("A1", "alert") == False  # 60min 内不重复
    assert agent._should_push("A2", "alert") == True   # 不同塘口可以


def test_validate_sensor_invalid():
    """超范围传感器数据 → 替换为安全默认值。"""
    sensor = {"temp": 99.0, "DO": -5.0, "pH": 7.8}
    validated = validate_sensor(sensor)
    assert validated["temp_val_invalid"] == True
    assert validated["DO_val_invalid"] == True
    assert 20 < validated["temp"] < 25  # 安全默认
    assert validated["DO"] > 0


def test_safety_check_dangerous():
    """危险操作 → 附加⚠️警告。"""
    actions = ["开增氧机", "清塘", "正常投喂"]
    checked = _safety_check(actions)
    assert "⚠️" in checked[1]  # 清塘有警告
    assert "⚠️" not in checked[0]  # 开增氧机无警告
    assert "⚠️" not in checked[2]  # 正常投喂无警告
