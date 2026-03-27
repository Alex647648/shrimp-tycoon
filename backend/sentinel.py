"""Sentinel Agent — 三层决策：规则引擎 → LLM 推理 → 飞书推送。"""

import os
import time
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

KB_PATH = Path(__file__).resolve().parent.parent / "knowledge-base" / "crayfish_kb.md"
PRICE_PATH = Path(__file__).resolve().parent.parent / "data" / "industry_based_price_data.json"

RISK_LABELS = {1: "正常运营", 2: "轻微风险", 3: "中等风险", 4: "高风险", 5: "极高风险"}


def _load_kb_excerpt(max_lines: int = 200) -> str:
    try:
        lines = KB_PATH.read_text(encoding="utf-8").splitlines()[:max_lines]
        return "\n".join(lines)
    except Exception:
        return ""


def _load_market_price() -> float:
    try:
        data = json.loads(PRICE_PATH.read_text(encoding="utf-8"))
        return float(data["current_price"]["medium"])
    except Exception:
        return 26.7


def _rule_engine(sensor: dict, wqar: dict) -> dict:
    """纯规则决策。"""
    start = time.time()
    csi = wqar.get("csi", 0)
    rl = wqar.get("risk_level", 1)
    actions = []
    summary_parts = []

    # 投喂决策
    feeding = {"total_ratio": 3.0, "morning": None, "evening": None, "skip": False}
    if sensor.get("DO", 99) < 3:
        feeding = {"total_ratio": 0, "morning": None, "evening": None, "skip": True}
        actions.append("立即停止投喂")
    elif sensor.get("molt_peak"):
        feeding = {"total_ratio": 2.1, "morning": None, "evening": None, "skip": False}
        actions.append("蜕壳期减少投饵量30%")
    elif 22 <= sensor.get("temp", 25) <= 28 and sensor.get("DO", 5) > 5:
        feeding["total_ratio"] = 3.0

    # 病害评估
    disease = {"risk": "low", "diseases": [], "herb_formula": None, "alert": False}
    if sensor.get("dead_shrimp"):
        disease = {"risk": "high", "diseases": ["疑似WSSV白斑病"], "herb_formula": None, "alert": True}
        actions.append("立即隔离病虾，采样送检")
        summary_parts.append("发现死虾，疑似WSSV感染")
    if sensor.get("ammonia", 0) > 0.5:
        disease["risk"] = "high"
        disease["diseases"].append("氨中毒风险")
        disease["alert"] = True
        actions.append("立即换水1/3，施用沸石粉")
        summary_parts.append(f"氨氮严重超标({sensor['ammonia']}mg/L)")

    if sensor.get("DO", 99) < 3:
        actions.insert(0, "立即开启增氧机至最大功率")
        summary_parts.append(f"溶解氧骤降至{sensor['DO']}mg/L")

    # 捕捞建议
    price = _load_market_price()
    harvest = {"recommended": False, "days_to_target": 25, "current_price": price, "price_trend": "stable", "expected_revenue": 0}
    avg_w = sensor.get("avg_weight", 0)
    if avg_w >= 35 and rl <= 2:
        total_kg = avg_w * sensor.get("count", 0) / 1000
        harvest = {"recommended": True, "days_to_target": 0, "current_price": price, "price_trend": "stable", "expected_revenue": round(total_kg * price)}
        actions.append("建议安排捕捞出塘")
    else:
        days_left = max(0, int((35 - avg_w) / 0.15))
        total_kg = avg_w * sensor.get("count", 0) / 1000
        harvest["days_to_target"] = days_left
        harvest["expected_revenue"] = round(total_kg * price)

    if not summary_parts:
        summary_parts.append(f"养殖状态{RISK_LABELS.get(rl, '未知')}，CSI={csi}")
    if not actions:
        actions.append("维持当前管理方案")

    latency = int((time.time() - start) * 1000)
    return {
        "schema": "DECISION-1.0", "risk_level": rl,
        "risk_label": RISK_LABELS.get(rl, "未知"),
        "model_used": "rule_engine", "latency_ms": latency,
        "confidence": 0.95, "summary": "；".join(summary_parts),
        "actions": actions, "feeding": feeding, "disease": disease,
        "harvest": harvest, "feishu_sent": False, "feishu_message_id": None,
    }


async def _llm_analyze(sensor: dict, wqar: dict, model: str) -> dict:
    """调用 Anthropic API 进行深度推理，超时/失败 fallback 到规则引擎。"""
    import anthropic

    api_key = os.getenv("ANTHROPIC_API_KEY", "")
    if not api_key:
        logger.warning("ANTHROPIC_API_KEY not set, falling back to rule engine")
        return _rule_engine(sensor, wqar)

    kb = _load_kb_excerpt()
    system_prompt = (
        "你是虾塘大亨的 Sentinel Agent，一个专业的水产养殖AI决策系统。\n"
        "基于以下知识库和传感器数据，输出 JSON 决策报告。\n\n"
        f"## 知识库摘要\n{kb[:3000]}\n\n"
        "## 输出格式要求\n"
        "严格输出 JSON，包含字段：risk_level(int 1-5), risk_label(str), confidence(float 0-1), "
        "summary(str), actions(list[str]), feeding({total_ratio,morning,evening,skip}), "
        "disease({risk,diseases,herb_formula,alert}), harvest({recommended,days_to_target,"
        "current_price,price_trend,expected_revenue})"
    )
    user_prompt = f"当前传感器数据：{json.dumps(sensor, ensure_ascii=False)}\n水质分析：{json.dumps(wqar, ensure_ascii=False)}"

    start = time.time()
    try:
        client = anthropic.AsyncAnthropic(api_key=api_key)
        resp = await client.messages.create(
            model=model, max_tokens=1024, system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        latency = int((time.time() - start) * 1000)
        text = resp.content[0].text
        text = text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        result = json.loads(text)
        result["schema"] = "DECISION-1.0"
        result["model_used"] = model
        result["latency_ms"] = latency
        result.setdefault("confidence", 0.85)
        result["feishu_sent"] = False
        result["feishu_message_id"] = None
        return result
    except Exception as e:
        logger.warning("LLM call failed (%s): %s — falling back to rule engine", model, e)
        return _rule_engine(sensor, wqar)


class SentinelAgent:
    def __init__(self, feishu_pusher=None):
        self.feishu = feishu_pusher

    async def analyze(self, sensor: dict, wqar: dict, push_feishu: bool = False) -> dict:
        csi = wqar.get("csi", 0)
        rl = wqar.get("risk_level", 1)

        if csi <= 20:
            report = _rule_engine(sensor, wqar)
        elif csi > 60 or rl >= 4:
            report = await _llm_analyze(sensor, wqar, "claude-opus-4-6")
        else:
            report = await _llm_analyze(sensor, wqar, "claude-haiku-4-5-20251001")

        if push_feishu and self.feishu and rl >= 3:
            level = "red" if rl >= 4 else "amber"
            mid = await self.feishu.send_alert(report, level)
            report["feishu_sent"] = mid is not None
            report["feishu_message_id"] = mid

        return report
