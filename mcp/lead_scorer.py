"""ICP 评分模型 — Growth Agent 用。

100分制，4维度加权：
- 养殖规模（40%）
- 地理位置（20%）
- 管理水平（20%）
- 接受度（20%）
"""

import logging

logger = logging.getLogger(__name__)

# 核心产区
CORE_REGIONS = {"潜江", "监利", "洪湖", "荆州", "仙桃", "武汉", "岳阳", "益阳", "常德", "盱眙"}


def score_lead(lead: dict) -> dict:
    """对单条线索进行 ICP 评分。

    Args:
        lead: {"name", "area_mu", "region", "has_disease_history", "has_app", "source"}

    Returns:
        {"score": 0-100, "grade": "A/B/C/D", "breakdown": {...}}
    """
    s_scale = _score_scale(lead.get("area_mu", 0))
    s_geo = _score_geo(lead.get("region", ""))
    s_mgmt = _score_mgmt(lead)
    s_accept = _score_accept(lead)

    total = round(s_scale * 0.4 + s_geo * 0.2 + s_mgmt * 0.2 + s_accept * 0.2)
    grade = "A" if total >= 80 else "B" if total >= 60 else "C" if total >= 40 else "D"

    return {
        "score": total,
        "grade": grade,
        "breakdown": {
            "scale": s_scale,
            "geo": s_geo,
            "mgmt": s_mgmt,
            "accept": s_accept,
        },
    }


def _score_scale(area_mu: float) -> int:
    if area_mu > 10:
        return 100
    elif area_mu > 5:
        return 60
    elif area_mu > 1:
        return 30
    return 10


def _score_geo(region: str) -> int:
    if any(r in region for r in CORE_REGIONS):
        return 100
    return 30


def _score_mgmt(lead: dict) -> int:
    score = 30  # 基础
    if lead.get("has_disease_history"):
        score += 40  # 最需要 AI
    if lead.get("employee_count", 0) >= 3:
        score += 30
    return min(score, 100)


def _score_accept(lead: dict) -> int:
    score = 20
    if lead.get("has_app"):
        score += 40
    if lead.get("has_consulted_expert"):
        score += 40
    return min(score, 100)
