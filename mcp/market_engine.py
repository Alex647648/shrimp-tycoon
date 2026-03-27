"""市场撮合引擎 — 从"养好虾"到"卖好虾"的最后一公里。

三大能力：
1. 买家智能匹配（规格+地域+评分+历史成交）
2. 最佳出货窗口（价格趋势+天气+节假日+库存压力）
3. 撮合推荐（综合排序+预期收益计算+报价比较）

数据源：
- data/buyers.json — 买家数据库
- data/industry_based_price_data.json — 行业价格+趋势
- 知识库 KB-E/F/G 相关条目
"""

import json
import logging
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

BASE = Path(__file__).resolve().parent.parent
BUYERS_PATH = BASE / "data" / "buyers.json"
PRICE_PATH = BASE / "data" / "industry_based_price_data.json"


def _load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning("Failed to load %s: %s", path, e)
        return {}


def grade_shrimp(avg_weight: float) -> dict:
    """按均重分级。

    行业标准：
    - 大虾（4钱以上）：≥30g → 高端餐饮/电商
    - 中虾（2-4钱）：20-30g → 批发/餐饮连锁
    - 小虾（2钱以下）：<20g → 加工厂/调味虾
    """
    if avg_weight >= 30:
        return {
            "grade": "large", "label": "大虾（4钱+）",
            "target_channel": ["高端餐饮", "电商平台", "精品超市"],
            "premium": True,
        }
    elif avg_weight >= 20:
        return {
            "grade": "medium", "label": "中虾（2-4钱）",
            "target_channel": ["批发市场", "餐饮连锁", "夜市大排档"],
            "premium": False,
        }
    else:
        return {
            "grade": "small", "label": "小虾（2钱以下）",
            "target_channel": ["加工厂", "调味虾生产", "虾尾加工"],
            "premium": False,
        }


def match_buyers(avg_weight: float, region: str = "",
                 count: int = 0, survival_rate: float = 0.9) -> dict:
    """买家智能匹配。

    匹配逻辑：
    1. 按规格筛选（grade 匹配）
    2. 按地域排序（同省优先，减少物流损耗）
    3. 按评分排序（历史信誉）
    4. 计算预期收益

    Returns:
        MMR-2.0 schema 市场匹配报告
    """
    buyers_data = _load_json(BUYERS_PATH)
    price_data = _load_json(PRICE_PATH)
    buyers = buyers_data.get("buyers", [])
    current_price = price_data.get("current_price", {})

    # 分级
    grading = grade_shrimp(avg_weight)
    grade = grading["grade"]

    # 预估产量
    total_kg = round(avg_weight * count * survival_rate / 1000, 1) if count > 0 else 0

    # 匹配买家
    matched = []
    for b in buyers:
        score = 0
        reasons = []

        # 规格匹配（最重要）
        if b.get("preferred_grade") == grade:
            score += 50
            reasons.append("规格匹配")
        elif grade == "medium":
            score += 30
            reasons.append("通用规格")
        else:
            score += 10

        # 地域匹配
        buyer_region = b.get("region", "")
        if region and buyer_region:
            if buyer_region in region or region in buyer_region:
                score += 25
                reasons.append("同地域（物流优势）")
            else:
                score += 10

        # 评分
        rating = b.get("rating", 3.0)
        score += int(rating * 5)  # 4.8分 → +24
        if rating >= 4.5:
            reasons.append("高信誉买家")

        # 采购量匹配
        monthly_vol = b.get("monthly_volume_kg", 0)
        if total_kg > 0 and monthly_vol > 0:
            vol_ratio = total_kg / monthly_vol
            if 0.05 <= vol_ratio <= 0.5:
                score += 15
                reasons.append("采购量适配")

        # 价格范围
        price_range = b.get("price_range", {})
        grade_price = current_price.get(grade, 24.0)
        if price_range.get("min", 0) <= grade_price <= price_range.get("max", 999):
            score += 10
            reasons.append("价格区间匹配")

        expected_revenue = round(total_kg * price_range.get("max", grade_price)) if total_kg > 0 else 0

        matched.append({
            "buyer_id": b.get("id"),
            "name": b["name"],
            "region": buyer_region,
            "type": b.get("type", ""),
            "rating": rating,
            "match_score": score,
            "match_reasons": reasons,
            "price_range": price_range,
            "expected_revenue": expected_revenue,
            "monthly_volume_kg": monthly_vol,
            "tags": b.get("tags", []),
        })

    # 按匹配分排序
    matched.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "schema": "MMR-2.0",
        "grading": grading,
        "total_kg": total_kg,
        "matched_count": len(matched),
        "top_buyers": matched[:5],
        "best_match": matched[0] if matched else None,
    }


def analyze_sell_window(price_data: dict = None) -> dict:
    """最佳出货窗口分析。

    考虑因素：
    1. 价格趋势（近7天/30天）
    2. 季节性规律（6-8月旺季，9月后下跌）
    3. 节假日效应（端午/中秋前涨价）
    4. 库存压力（养殖天数越长成本越高）
    """
    if price_data is None:
        price_data = _load_json(PRICE_PATH)

    daily = price_data.get("daily_prices", [])
    current = price_data.get("current_price", {})

    # 7天趋势
    recent_7 = daily[-7:] if len(daily) >= 7 else daily
    recent_30 = daily[-30:] if len(daily) >= 30 else daily

    if len(recent_7) >= 2:
        trend_7d = "上涨" if recent_7[-1].get("medium", 0) > recent_7[0].get("medium", 0) else \
                   "下跌" if recent_7[-1].get("medium", 0) < recent_7[0].get("medium", 0) else "持平"
        change_7d = recent_7[-1].get("medium", 0) - recent_7[0].get("medium", 0)
    else:
        trend_7d = "数据不足"
        change_7d = 0

    if len(recent_30) >= 2:
        trend_30d = "上涨" if recent_30[-1].get("medium", 0) > recent_30[0].get("medium", 0) else \
                    "下跌" if recent_30[-1].get("medium", 0) < recent_30[0].get("medium", 0) else "持平"
    else:
        trend_30d = "数据不足"

    # 季节性判断
    month = datetime.now().month
    season_advice = _season_advice(month)

    # 综合建议
    if trend_7d == "上涨" and trend_30d == "上涨":
        recommendation = "观望"
        reason = "价格持续上涨，可以再等等"
        urgency = "low"
    elif trend_7d == "下跌" and trend_30d == "下跌":
        recommendation = "尽快出货"
        reason = "价格持续下行，越等越亏"
        urgency = "high"
    elif trend_7d == "下跌" and trend_30d == "上涨":
        recommendation = "本周出货"
        reason = "短期回调，但长期看涨，建议锁定当前价格"
        urgency = "medium"
    else:
        recommendation = "择机出货"
        reason = "价格波动中，关注未来 3 天走势"
        urgency = "medium"

    return {
        "schema": "SELL-WINDOW-1.0",
        "current_price": current,
        "trend_7d": {"direction": trend_7d, "change": round(change_7d, 1)},
        "trend_30d": {"direction": trend_30d},
        "season": season_advice,
        "recommendation": recommendation,
        "reason": reason,
        "urgency": urgency,
    }


def full_market_report(avg_weight: float, count: int,
                       survival_rate: float = 0.9,
                       region: str = "湖北") -> dict:
    """完整市场撮合报告（一站式）。

    合并：分级 + 买家匹配 + 出货窗口 + 收益预估。
    """
    price_data = _load_json(PRICE_PATH)

    # 买家匹配
    match_result = match_buyers(avg_weight, region, count, survival_rate)

    # 出货窗口
    sell_window = analyze_sell_window(price_data)

    # 收益预估
    total_kg = match_result["total_kg"]
    current = price_data.get("current_price", {})
    grade = match_result["grading"]["grade"]
    unit_price = current.get(grade, 24.0)

    best_buyer = match_result.get("best_match")
    best_price = best_buyer["price_range"].get("max", unit_price) if best_buyer else unit_price

    revenue_now = round(total_kg * unit_price)
    revenue_best = round(total_kg * best_price)

    return {
        "schema": "MARKET-REPORT-1.0",
        "summary": _generate_summary(match_result, sell_window, revenue_now, revenue_best),
        "grading": match_result["grading"],
        "production": {
            "avg_weight": avg_weight,
            "count": count,
            "survival_rate": survival_rate,
            "total_kg": total_kg,
        },
        "pricing": {
            "market_price": unit_price,
            "best_buyer_price": best_price,
            "revenue_at_market": revenue_now,
            "revenue_at_best": revenue_best,
            "premium": revenue_best - revenue_now,
        },
        "buyers": match_result["top_buyers"][:3],
        "sell_window": sell_window,
        "action_plan": _action_plan(match_result, sell_window),
    }


def _season_advice(month: int) -> dict:
    """季节性建议。"""
    if month in (6, 7, 8):
        return {"season": "旺季", "advice": "需求旺盛，价格通常较高", "emoji": "🔥"}
    elif month in (4, 5):
        return {"season": "上市初期", "advice": "早虾价格高但量少", "emoji": "🌱"}
    elif month in (9, 10):
        return {"season": "尾季", "advice": "价格回落，大虾仍有溢价", "emoji": "🍂"}
    else:
        return {"season": "淡季", "advice": "供应少，库存虾/冻虾为主", "emoji": "❄️"}


def _generate_summary(match, window, rev_now, rev_best) -> str:
    """生成一句话总结。"""
    grade_label = match["grading"]["label"]
    best = match.get("best_match")
    buyer_name = best["name"] if best else "暂无"
    rec = window["recommendation"]
    return f"规格{grade_label}，推荐买家{buyer_name}，建议{rec}（预期收益¥{rev_best:,}）"


def _action_plan(match, window) -> list[str]:
    """生成可执行行动计划。"""
    actions = []
    best = match.get("best_match")
    urgency = window.get("urgency", "medium")

    if best:
        actions.append(f"联系 {best['name']}（{best['region']}，评分 {best['rating']}⭐）")
        if best.get("price_range"):
            actions.append(f"报价参考：¥{best['price_range'].get('min', 0)}-{best['price_range'].get('max', 0)}/kg")

    if urgency == "high":
        actions.append("⚠️ 价格下行中，建议 3 天内完成交易")
    elif urgency == "low":
        actions.append("价格上涨中，可以等 3-5 天观察")

    if match["matched_count"] > 1:
        second = match["top_buyers"][1] if len(match["top_buyers"]) > 1 else None
        if second:
            actions.append(f"备选买家：{second['name']}（{second['region']}）")

    actions.append("准备捕捞设备和运输冷链")
    return actions[:5]
