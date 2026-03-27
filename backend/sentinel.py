"""Sentinel Agent — 实时水质监控（三层决策 + MCP 工具 + 历史窗口）。

执行流程：
1. validate_sensor() — 物理范围校验
2. _keyword_model() — 关键词路由（优先级最高）
3. LLM 调用（asyncio.timeout 10s）
4. _safety_check() — 危险操作警告
5. feishu_push — 飞书推送（60min 去重）
6. db.save_decision() — 非阻塞写入
"""

import os
import time
import json
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from sentinel_safety import validate_sensor, _safety_check, VALID_RANGES
from sentinel_prompts import get_haiku_prompt, get_opus_prompt

KB_PATH = Path(__file__).resolve().parent.parent / "knowledge-base" / "crayfish_kb.md"

RISK_LABELS = {1: "正常运营", 2: "轻微风险", 3: "中等风险", 4: "高风险", 5: "极高风险"}

# 关键词触发规则（优先级从高到低）
KEYWORD_TRIGGERS = [
    (lambda s, w: s.get("dead_shrimp"), "claude-opus-4-6", "dead_shrimp"),
    (lambda s, w: s.get("DO", 99) < 1.5, "claude-opus-4-6", "DO<1.5_critical"),
    (lambda s, w: s.get("temp", 25) < 10 or s.get("temp", 25) > 32, "claude-opus-4-6", "temp_extreme"),
    (lambda s, w: s.get("pH", 7.5) < 6.5 or s.get("pH", 7.5) > 9.0, "claude-opus-4-6", "pH_lethal"),
    (lambda s, w: s.get("ammonia", 0) > 1.0, "claude-opus-4-6", "ammonia_toxic"),
    (lambda s, w: s.get("DO", 99) < 3.0, "claude-haiku-4-5-20251001", "DO<3.0"),
    (lambda s, w: s.get("ammonia", 0) > 0.5, "claude-haiku-4-5-20251001", "ammonia_high"),
    (lambda s, w: s.get("molt_peak") and w.get("csi", 0) > 25, "claude-haiku-4-5-20251001", "molt_stress"),
    (lambda s, w: s.get("transparency", 99) < 20, "claude-haiku-4-5-20251001", "turbidity"),
]


def _keyword_model(sensor: dict, wqar: dict) -> str | None:
    """检查关键词触发，返回模型名或 None。"""
    for condition, model, tag in KEYWORD_TRIGGERS:
        try:
            if condition(sensor, wqar):
                logger.info("Keyword trigger: %s → %s", tag, model)
                return model
        except Exception:
            pass
    return None


def _rule_engine(sensor: dict, wqar: dict, memory=None) -> dict:
    """增强版规则决策引擎（覆盖全部 5 种演示场景 + 组合情况）。"""
    csi = wqar.get("csi", 0)
    risk_level = wqar.get("risk_level", 1)
    actions = []
    alerts = []

    # ── 溶解氧 ──
    do_val = sensor.get("DO", 8.0)
    if do_val < 1.5:
        risk_level = max(risk_level, 5)
        actions.extend(["立即开启全部增氧机", "停止一切投喂", "检查增氧设备运转"])
        alerts.append("🚨 溶解氧极低（{:.1f}mg/L），虾群面临窒息风险".format(do_val))
    elif do_val < 3.0:
        risk_level = max(risk_level, 4)
        actions.extend(["立即开启增氧机", "减少投喂量50%"])
        alerts.append("⚠️ 溶解氧偏低（{:.1f}mg/L），浮头风险".format(do_val))
    elif do_val < 4.0:
        risk_level = max(risk_level, 3)
        actions.append("开启备用增氧机")

    # ── 温度 ──
    temp = sensor.get("temp", 25.0)
    if temp < 10 or temp > 35:
        risk_level = max(risk_level, 5)
        actions.append("紧急降温/升温处理" if temp > 35 else "紧急保温处理")
        alerts.append("🚨 水温极端（{}°C）".format(temp))
    elif temp < 18 or temp > 32:
        risk_level = max(risk_level, 3)
        actions.append("密切监控水温变化")

    # ── pH ──
    ph = sensor.get("pH", 7.5)
    if ph < 6.5:
        risk_level = max(risk_level, 4)
        actions.append("投放生石灰调节pH（每亩10-15kg）")
        alerts.append("⚠️ pH 过低（{:.1f}），酸化风险".format(ph))
    elif ph > 9.0:
        risk_level = max(risk_level, 4)
        actions.append("换水1/3 + 投放有机酸降pH")
        alerts.append("⚠️ pH 过高（{:.1f}），碱中毒风险".format(ph))

    # ── 氨氮 ──
    ammonia = sensor.get("ammonia", 0.1)
    if ammonia > 1.0:
        risk_level = max(risk_level, 5)
        actions.extend(["紧急换水50%", "投放沸石粉吸附氨氮", "停食"])
        alerts.append("🚨 氨氮中毒风险（{:.2f}mg/L）".format(ammonia))
    elif ammonia > 0.5:
        risk_level = max(risk_level, 3)
        actions.extend(["换水20-30%", "投放硝化菌"])
    elif ammonia > 0.3:
        risk_level = max(risk_level, 2)
        actions.append("加强水质监测频率")

    # ── 病害（死虾/WSSV）──
    disease = {"risk": "low", "suspects": [], "actions": []}
    if sensor.get("dead_shrimp"):
        risk_level = max(risk_level, 5)
        disease = {
            "risk": "high",
            "suspects": ["疑似WSSV（白斑综合征）", "细菌性感染"],
            "actions": ["立即隔离病虾", "采样送检PCR", "全池泼洒聚维酮碘"],
        }
        actions.extend(["立即隔离病虾区域", "采样送检", "周边塘口预防消毒"])
        alerts.append("🚨 发现死虾，疑似病毒感染")

    # ── 蜕壳期 ──
    molt_peak = sensor.get("molt_peak", False)
    feeding = {"action": "正常投喂", "total_ratio": 3.0, "skip": False, "notes": ""}
    if molt_peak:
        feeding = {
            "action": "减量投喂",
            "total_ratio": 2.1,
            "skip": False,
            "notes": "蜕壳期减少投饵30%，避免换水惊扰",
        }
        actions.append("蜕壳期：减投30% + 泼洒补钙产品")
        if risk_level < 2:
            risk_level = 2
    elif do_val < 3.0 or ammonia > 1.0:
        feeding = {"action": "停食", "total_ratio": 0, "skip": True, "notes": "水质恶化，停食观察"}
    elif do_val < 4.0 or ammonia > 0.5:
        feeding = {"action": "减量投喂", "total_ratio": 1.5, "skip": False, "notes": "水质偏差，减投50%"}

    # ── 捕捞判断 ──
    avg_weight = sensor.get("avg_weight", 0)
    count = sensor.get("count", 0)
    harvest = {"recommended": False, "days_to_target": 14, "reason": ""}
    if avg_weight >= 35:
        harvest = {
            "recommended": True,
            "days_to_target": 0,
            "reason": "均重{:.1f}g，达到上市规格（≥35g）".format(avg_weight),
        }
        if risk_level <= 2:
            actions.append("建议联系收购商，进入捕捞窗口")
    elif avg_weight >= 25:
        days_left = int((35 - avg_weight) / 1.5) + 1
        harvest = {
            "recommended": False,
            "days_to_target": days_left,
            "reason": "均重{:.1f}g，预计{}天达标".format(avg_weight, days_left),
        }

    # ── 趋势异常补充（如有 memory）──
    if memory:
        for field in ["DO", "pH", "ammonia", "temp"]:
            if memory.anomaly(field):
                trend = memory.trend(field)
                alerts.append("📊 {} 异常波动（趋势：{}）".format(field, trend))
                if risk_level < 3:
                    risk_level = 3

    # ── 去重 actions ──
    seen = set()
    unique_actions = []
    for a in actions:
        if a not in seen:
            seen.add(a)
            unique_actions.append(a)

    summary_parts = []
    if alerts:
        summary_parts.append(alerts[0])
    else:
        summary_parts.append("风险等级 {}（{}）".format(risk_level, RISK_LABELS.get(risk_level, "未知")))

    return {
        "schema": "DECISION-1.0",
        "risk_level": risk_level,
        "model_used": "rules",
        "summary": "；".join(summary_parts)[:100],
        "alerts": alerts,
        "actions": unique_actions[:5],
        "feeding": feeding,
        "disease": disease,
        "harvest": harvest,
    }


class SentinelAgent:
    """实时水质监控 Agent。"""

    def __init__(self, feishu_pusher=None, db=None, memory=None):
        self.feishu = feishu_pusher
        self.db = db
        self.memory = memory
        self._push_cooldown = {}

    async def analyze(self, sensor: dict, wqar: dict, push_feishu: bool = False) -> dict:
        """分析单塘传感器数据，返回 DECISION-1.0 报告。"""
        start = time.time()
        pond_id = sensor.get("pond_id", "unknown")

        # 1. 传感器校验
        sensor = validate_sensor(sensor)

        # 2. 历史窗口
        if self.memory:
            self.memory.add(sensor, wqar)
            history_context = self.memory.format_context()
        else:
            history_context = ""

        # 3. 关键词路由
        model = _keyword_model(sensor, wqar)

        # 4. CSI 路由
        if model is None:
            csi = wqar.get("csi", 0)
            if csi <= 20:
                model = "rules"
            elif csi <= 60:
                model = "claude-haiku-4-5-20251001"
            else:
                model = "claude-opus-4-6"

        # 5. 执行决策
        if model == "rules":
            report = _rule_engine(sensor, wqar, self.memory)
        else:
            try:
                async with asyncio.timeout(10.0):
                    from anthropic import Anthropic
                    client = Anthropic()
                    prompt = (
                        f"传感器数据：{json.dumps(sensor, ensure_ascii=False)}\n"
                        f"水质评分：{json.dumps(wqar, ensure_ascii=False)}\n"
                        f"历史上下文：\n{history_context}"
                    )
                    system = get_opus_prompt(history_context) if "opus" in model else get_haiku_prompt(history_context)
                    response = await asyncio.to_thread(
                        lambda: client.messages.create(
                            model=model, max_tokens=500, system=system,
                            messages=[{"role": "user", "content": prompt}],
                        )
                    )
                    report = json.loads(response.content[0].text)
                    report["model_used"] = model
            except Exception as e:
                logger.warning("LLM failed (%s): %s — rule fallback", model, e)
                report = _rule_engine(sensor, wqar, self.memory)

        # 6. 安全检查
        report["actions"] = _safety_check(report.get("actions", []))

        # 7. 飞书推送
        report["feishu_sent"] = False
        report["feishu_message_id"] = None
        risk_level = report.get("risk_level", 1)
        if push_feishu and risk_level >= 3 and self.feishu:
            if self._should_push(pond_id, "alert"):
                try:
                    mid = await self.feishu.send_alert(report, "red" if risk_level >= 4 else "amber")
                    report["feishu_sent"] = mid is not None
                    report["feishu_message_id"] = mid
                except Exception as e:
                    logger.warning("Feishu push failed (non-fatal): %s", e)

        # 8. DB 写入
        if self.db:
            try:
                await self.db.save_decision(pond_id, report)
            except Exception as e:
                logger.warning("DB save_decision failed: %s", e)

        report["pond_id"] = pond_id
        report["timestamp"] = time.time()
        report["latency_ms"] = int((time.time() - start) * 1000)
        return report

    async def run_batch(self, pond_sensors: list[dict], wqar_list: list[dict],
                        push_feishu: bool = True) -> list[dict]:
        """多塘并发分析（产品版）。"""
        tasks = [
            self.analyze(s, w, push_feishu=push_feishu)
            for s, w in zip(pond_sensors, wqar_list)
        ]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        reports = []
        for r in results:
            if isinstance(r, Exception):
                logger.error("Batch analyze error: %s", r)
                reports.append({"error": str(r), "model_used": "error"})
            else:
                reports.append(r)
        return reports

    def _should_push(self, pond_id: str, scenario: str, cooldown_sec: int = 3600) -> bool:
        """飞书推送去重（60分钟）。"""
        key = f"{pond_id}:{scenario}"
        last = self._push_cooldown.get(key, 0.0)
        now = time.time()
        if now - last < cooldown_sec:
            return False
        self._push_cooldown[key] = now
        return True
