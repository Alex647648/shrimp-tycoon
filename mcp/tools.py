"""MCP 工具层 — 9 个工具函数，可被后端直接调用。"""

import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from simulator import PondSimulator, compute_wqar, DEFAULT_SENSOR
from sentinel import _rule_engine, _load_market_price

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


def harvest_advise(sensor: dict, wqar: dict, market_price: float | None = None) -> dict:
    """捕捞建议。"""
    report = _rule_engine(sensor, wqar)
    h = report["harvest"]
    if market_price is not None:
        h["current_price"] = market_price
        total_kg = sensor.get("avg_weight", 0) * sensor.get("count", 0) / 1000
        h["expected_revenue"] = round(total_kg * market_price)
    return h


def market_match(weight_kg: float, region: str = "湖北") -> dict:
    """根据规格和地区匹配市场价格。"""
    data = json.loads(PRICE_PATH.read_text(encoding="utf-8"))
    cp = data["current_price"]
    if weight_kg >= 0.04:
        grade, price = "large", cp["large"]
    elif weight_kg >= 0.025:
        grade, price = "medium", cp["medium"]
    else:
        grade, price = "small", cp["small"]
    return {"region": region, "grade": grade, "price_per_kg": price, "date": cp["date"]}


def price_trend(days: int = 30) -> dict:
    """查询近 N 天价格趋势。"""
    data = json.loads(PRICE_PATH.read_text(encoding="utf-8"))
    prices = data["daily_prices"][-days:]
    current = data["current_price"]["medium"]
    history = [{"date": p["date"], "price": p["medium"]} for p in prices]
    if len(prices) >= 2:
        trend = "rising" if prices[-1]["medium"] > prices[0]["medium"] else ("falling" if prices[-1]["medium"] < prices[0]["medium"] else "stable")
    else:
        trend = "stable"
    return {"current": current, "trend": trend, "history": history}


async def feishu_alert(report: dict, level: str) -> str | None:
    """发送飞书告警，返回 message_id。"""
    from feishu import FeishuPusher
    pusher = FeishuPusher()
    return await pusher.send_alert(report, level)


def kb_query(query: str) -> list[str]:
    """搜索知识库，返回匹配的知识条目。"""
    try:
        text = KB_PATH.read_text(encoding="utf-8")
    except Exception:
        return []
    entries = text.split("---")
    query_lower = query.lower()
    results = []
    for entry in entries:
        if query_lower in entry.lower():
            stripped = entry.strip()
            if stripped:
                results.append(stripped[:500])
    return results[:5]
