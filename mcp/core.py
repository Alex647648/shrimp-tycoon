"""MCP 核心工具函数 — 无外部依赖，可独立测试。

server.py 的 FastMCP 工具调用这些函数。
测试直接导入本模块，不需要 fastmcp。
"""

import json
from pathlib import Path
import sys

# 添加 backend 到路径
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))

from simulator import PondSimulator, compute_wqar, DEFAULT_SENSOR
from sentinel import _rule_engine

KB_PATH = Path(__file__).resolve().parent.parent / "knowledge-base" / "crayfish_kb.md"
PRICE_PATH = Path(__file__).resolve().parent.parent / "data" / "industry_based_price_data.json"

_sim = PondSimulator()


def sensor_read(pond_id: str = "A03") -> dict:
    """读取虾塘传感器数据。"""
    sensor, _ = _sim.tick()
    sensor["pond_id"] = pond_id
    return sensor


def water_quality_score(sensor: dict) -> dict:
    """根据传感器数据计算水质综合评分。"""
    return compute_wqar(sensor)


def feeding_recommend(sensor: dict, wqar: dict) -> dict:
    """投喂建议。"""
    report = _rule_engine(sensor, wqar)
    return report["feeding"]


def disease_assess(sensor: dict, wqar: dict) -> dict:
    """病害评估。"""
    report = _rule_engine(sensor, wqar)
    return report["disease"]


def harvest_advise(sensor: dict, wqar: dict, market_price=None) -> dict:
    """捕捞建议。"""
    report = _rule_engine(sensor, wqar)
    h = report["harvest"]
    if market_price is not None:
        h["current_price"] = market_price
        total_kg = sensor.get("avg_weight", 0) * sensor.get("count", 0) / 1000
        h["expected_revenue"] = round(total_kg * market_price)
    return h


def price_trend(days: int = 30) -> dict:
    """查询近 N 天价格趋势。"""
    data = json.loads(PRICE_PATH.read_text(encoding="utf-8"))
    prices = data["daily_prices"][-days:]
    current = data["current_price"]["medium"]
    history = [{"date": p["date"], "price": p["medium"]} for p in prices]
    if len(prices) >= 2:
        trend = ("rising" if prices[-1]["medium"] > prices[0]["medium"]
                 else "falling" if prices[-1]["medium"] < prices[0]["medium"]
                 else "stable")
    else:
        trend = "stable"
    return {"current": current, "trend": trend, "history": history}


def kb_query(query: str) -> list[str]:
    """搜索知识库，返回匹配的知识条目。"""
    try:
        text = KB_PATH.read_text(encoding="utf-8")
    except Exception:
        return []
    entries = text.split("---")
    q = query.lower()
    results = []
    for entry in entries:
        if q in entry.lower():
            s = entry.strip()
            if s:
                results.append(s[:500])
    return results[:5]
