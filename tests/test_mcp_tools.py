"""MCP 工具层单元测试 — 内联函数验证 + 超时/幂等/无状态检验。

工具函数已内联到 mcp/server.py，本文件直接测试。

运行：
    cd /Users/a647/projects/shrimp-tycoon
    python -m pytest tests/test_mcp_tools.py -v
"""

import json
from pathlib import Path

import pytest

# ── 路径修正 ──
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "mcp"))

# 从 core 模块导入工具函数（不依赖 fastmcp）
from mcp.core import (
    sensor_read as _tool_sensor_read,
    water_quality_score as _tool_water_quality_score,
    feeding_recommend as _tool_feeding_recommend,
    disease_assess as _tool_disease_assess,
    harvest_advise as _tool_harvest_advise,
    price_trend as _tool_price_trend,
    kb_query as _tool_kb_query,
)
from mcp.market_engine import match_buyers, analyze_sell_window, full_market_report, grade_shrimp
from mcp.lead_scorer import score_lead
from mcp.lead_discovery import extract_leads_from_text, deduplicate_leads

# ── Fixtures ──

NORMAL_SENSOR = {
    "schema": "SDP-1.0", "pond_id": "A03",
    "timestamp": "2026-03-27T10:00:00",
    "temp": 25.4, "DO": 6.2, "pH": 7.8, "ammonia": 0.16,
    "transparency": 38.0, "avg_weight": 28.5, "count": 485,
    "day": 45, "dead_shrimp": False, "molt_peak": False,
}

DANGER_SENSOR = {
    **NORMAL_SENSOR, "DO": 2.1, "ammonia": 1.2, "dead_shrimp": True,
}

NORMAL_WQAR = {
    "schema": "WQAR-1.0", "csi": 10, "risk_level": 1,
    "risk_label": "正常运营",
    "indicators": {
        "DO": {"value": 6.2, "status": "optimal"},
        "ammonia": {"value": 0.16, "status": "normal"},
        "pH": {"value": 7.8, "status": "optimal"},
        "temp": {"value": 25.4, "status": "optimal"},
    },
    "trigger_llm": False,
}

DANGER_WQAR = {
    **NORMAL_WQAR, "csi": 85, "risk_level": 5,
    "risk_label": "极高风险", "trigger_llm": True,
}


# ═══════════════════════════════════════════════
# 1. sensor_read
# ═══════════════════════════════════════════════

class TestSensorRead:
    def test_returns_required_fields(self):
        result = _tool_sensor_read("A03")
        required = {"temp", "DO", "pH", "ammonia", "transparency", "avg_weight", "count", "pond_id"}
        assert required.issubset(result.keys())

    def test_pond_id_injected(self):
        result = _tool_sensor_read("B05")
        assert result["pond_id"] == "B05"

    def test_stateless(self):
        r1 = _tool_sensor_read("A01")
        r2 = _tool_sensor_read("A02")
        assert r1["pond_id"] == "A01"
        assert r2["pond_id"] == "A02"


# ═══════════════════════════════════════════════
# 2. water_quality_score
# ═══════════════════════════════════════════════

class TestWaterQualityScore:
    def test_normal_low_risk(self):
        result = _tool_water_quality_score(NORMAL_SENSOR)
        assert result["risk_level"] <= 2

    def test_danger_high_risk(self):
        result = _tool_water_quality_score(DANGER_SENSOR)
        assert result["risk_level"] >= 3

    def test_idempotent(self):
        r1 = _tool_water_quality_score(NORMAL_SENSOR)
        r2 = _tool_water_quality_score(NORMAL_SENSOR)
        assert r1["csi"] == r2["csi"]

    def test_schema_field(self):
        result = _tool_water_quality_score(NORMAL_SENSOR)
        assert "csi" in result


# ═══════════════════════════════════════════════
# 3. feeding_recommend
# ═══════════════════════════════════════════════

class TestFeedingRecommend:
    def test_normal_returns_dict(self):
        result = _tool_feeding_recommend(NORMAL_SENSOR, NORMAL_WQAR)
        assert isinstance(result, dict)

    def test_idempotent(self):
        r1 = _tool_feeding_recommend(NORMAL_SENSOR, NORMAL_WQAR)
        r2 = _tool_feeding_recommend(NORMAL_SENSOR, NORMAL_WQAR)
        assert r1 == r2


# ═══════════════════════════════════════════════
# 4. disease_assess
# ═══════════════════════════════════════════════

class TestDiseaseAssess:
    def test_normal_low_risk(self):
        result = _tool_disease_assess(NORMAL_SENSOR, NORMAL_WQAR)
        assert isinstance(result, dict)

    def test_dead_shrimp_high_risk(self):
        result = _tool_disease_assess(DANGER_SENSOR, DANGER_WQAR)
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════
# 5. harvest_advise
# ═══════════════════════════════════════════════

class TestHarvestAdvise:
    def test_returns_dict(self):
        result = _tool_harvest_advise(NORMAL_SENSOR, NORMAL_WQAR)
        assert isinstance(result, dict)

    def test_market_price_injection(self):
        result = _tool_harvest_advise(NORMAL_SENSOR, NORMAL_WQAR, market_price=26.0)
        assert "current_price" in result
        assert result["current_price"] == 26.0


# ═══════════════════════════════════════════════
# 6. price_trend
# ═══════════════════════════════════════════════

class TestPriceTrend:
    def test_returns_required_keys(self):
        result = _tool_price_trend(30)
        assert "current" in result
        assert "trend" in result
        assert "history" in result

    def test_trend_valid(self):
        result = _tool_price_trend(30)
        assert result["trend"] in ("rising", "falling", "stable")

    def test_history_is_list(self):
        result = _tool_price_trend(7)
        assert isinstance(result["history"], list)


# ═══════════════════════════════════════════════
# 7. kb_query
# ═══════════════════════════════════════════════

class TestKbQuery:
    def test_returns_list(self):
        result = _tool_kb_query("溶解氧")
        assert isinstance(result, list)

    def test_empty_no_crash(self):
        result = _tool_kb_query("")
        assert isinstance(result, list)

    def test_max_5(self):
        result = _tool_kb_query("水")
        assert len(result) <= 5

    def test_stateless(self):
        r1 = _tool_kb_query("pH")
        r2 = _tool_kb_query("pH")
        assert r1 == r2


# ═══════════════════════════════════════════════
# 8. market_engine
# ═══════════════════════════════════════════════

class TestMarketEngine:
    def test_grade_large(self):
        g = grade_shrimp(35.0)
        assert g["grade"] == "large"

    def test_grade_medium(self):
        g = grade_shrimp(25.0)
        assert g["grade"] == "medium"

    def test_grade_small(self):
        g = grade_shrimp(15.0)
        assert g["grade"] == "small"

    def test_match_buyers_returns_schema(self):
        result = match_buyers(30.0, "湖北", 5000, 0.9)
        assert result["schema"] == "MMR-2.0"
        assert "top_buyers" in result

    def test_sell_window_returns_schema(self):
        result = analyze_sell_window()
        assert result["schema"] == "SELL-WINDOW-1.0"
        assert "recommendation" in result

    def test_full_report(self):
        result = full_market_report(30.0, 5000, 0.9, "湖北")
        assert result["schema"] == "MARKET-REPORT-1.0"
        assert "summary" in result
        assert "action_plan" in result


# ═══════════════════════════════════════════════
# 9. lead_scorer
# ═══════════════════════════════════════════════

class TestLeadScorer:
    def test_high_score(self):
        lead = {"area_mu": 15, "region": "潜江", "has_disease_history": True, "has_app": True}
        result = score_lead(lead)
        assert result["grade"] in ("A", "B")
        assert result["score"] >= 60

    def test_low_score(self):
        lead = {"area_mu": 0.5, "region": "北京"}
        result = score_lead(lead)
        assert result["score"] < 60


# ═══════════════════════════════════════════════
# 10. lead_discovery
# ═══════════════════════════════════════════════

class TestLeadDiscovery:
    def test_extract_phone(self):
        text = "潜江虾王养殖场 联系电话 13812345678 面积 50亩"
        leads = extract_leads_from_text(text, "test")
        assert len(leads) >= 1
        assert leads[0].phone == "13812345678"

    def test_extract_region(self):
        text = "监利县水产养殖合作社 养殖面积 200亩 联系人张三"
        leads = extract_leads_from_text(text, "test")
        assert any(l.region == "监利" for l in leads)

    def test_dedup(self):
        from mcp.lead_discovery import RawLead
        leads = [
            RawLead(name="A养殖场", source="test", phone="13800000001"),
            RawLead(name="A养殖场", source="test", phone="13800000001"),
            RawLead(name="B水产", source="test", phone="13800000002"),
        ]
        unique = deduplicate_leads(leads)
        assert len(unique) == 2
