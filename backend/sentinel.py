"""Sentinel Agent — 实时水质监控（三层决策 + MCP 工具 + 历史窗口）。

执行流程：
1. validate_sensor() — 物理范围校验
2. _keyword_model() — 关键词路由（优先级最高）
3. LLM 调用（asyncio.timeout 10s）
4. _safety_check() — 危险操作警告
5. feishu_push — 飞书推送（60min 去重）
6. db.save_decision() — 非阻塞写入

约束（AGENT_CONSTRAINTS.md §2.1 / §4.1 / §4.3 / §4.4）：
- Sentinel 不读 DB 历史，只用 SentinelMemory 内存窗口
- LLM 调用必须有 asyncio.timeout(10) + fallback 规则引擎
- 传感器数据第一行调用 validate_sensor()
- 危险操作经过 _safety_check()
"""

import os
import time
import json
import asyncio
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

from sentinel_safety import validate_sensor, _safety_check
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


def _rule_engine(sensor: dict, wqar: dict) -> dict:
    """纯规则决策（fallback）。简化版本。"""
    risk_level = wqar.get("risk_level", 1)
    actions = []
    
    # 投喂
    feeding = {"total_ratio": 3.0, "skip": False}
    if sensor.get("DO", 99) < 3:
        feeding = {"total_ratio": 0, "skip": True}
        actions.append("立即停止投喂")
    elif sensor.get("molt_peak"):
        feeding["total_ratio"] = 2.1
        actions.append("蜕壳期减少投饵30%")
    
    # 病害
    disease = {"risk": "low", "diseases": []}
    if sensor.get("dead_shrimp"):
        disease = {"risk": "high", "diseases": ["疑似WSSV"]}
        actions.append("立即隔离病虾")
    
    # 捕捞
    harvest = {"recommended": False, "days_to_target": 14}
    
    return {
        "risk_level": risk_level,
        "model_used": "rules",
        "summary": f"风险等级 {risk_level}({RISK_LABELS.get(risk_level, '未知')})",
        "actions": actions,
        "feeding": feeding,
        "disease": disease,
        "harvest": harvest,
    }


class SentinelAgent:
    """实时水质监控 Agent。"""
    
    def __init__(self, feishu_pusher=None, db=None, memory=None):
        self.feishu = feishu_pusher
        self.db = db
        self.memory = memory  # SentinelMemory 实例
        self._push_cooldown = {}
    
    async def analyze(self, sensor: dict, wqar: dict, push_feishu: bool = False) -> dict:
        """分析并返回决策报告。
        
        Args:
            sensor: SDP-1.0 格式传感器数据
            wqar: WQAR-1.0 格式水质评分
            push_feishu: 是否推送飞书
            
        Returns:
            DECISION-1.0 格式报告
        """
        start = time.time()
        pond_id = sensor.get("pond_id", "unknown")
        
        # 1. 传感器校验（第一行）
        sensor = validate_sensor(sensor)
        
        # 2. 历史窗口管理
        if self.memory:
            self.memory.add(sensor, wqar)
            history_context = self.memory.format_context()
        else:
            history_context = ""
        
        # 3. 关键词路由
        model = _keyword_model(sensor, wqar)
        
        # 4. CSI 路由（若无关键词命中）
        if model is None:
            csi = wqar.get("csi", 0)
            if csi <= 20:
                model = "rules"
            elif csi <= 60:
                model = "claude-haiku-4-5-20251001"
            else:
                model = "claude-opus-4-6"
        
        # 5. LLM 或规则引擎
        if model == "rules":
            report = _rule_engine(sensor, wqar)
        else:
            try:
                async with asyncio.timeout(10.0):
                    from anthropic import Anthropic
                    client = Anthropic()
                    prompt = f"传感器数据：{json.dumps(sensor)}\n水质评分：{json.dumps(wqar)}\n历史：{history_context}"
                    system = get_opus_prompt(history_context) if model == "claude-opus-4-6" else get_haiku_prompt(history_context)
                    response = await asyncio.to_thread(
                        lambda: client.messages.create(
                            model=model,
                            max_tokens=500,
                            system=system,
                            messages=[{"role": "user", "content": prompt}]
                        )
                    )
                    result_text = response.content[0].text
                    report = json.loads(result_text)
                    report["model_used"] = model
            except (asyncio.TimeoutError, Exception) as e:
                logger.warning("LLM failed (%s): %s — using rule fallback", model, e)
                report = _rule_engine(sensor, wqar)
        
        # 6. 安全检查
        report["actions"] = _safety_check(report.get("actions", []))
        
        # 7. 飞书推送（去重）
        report["feishu_sent"] = False
        report["feishu_message_id"] = None
        risk_level = report.get("risk_level", 1)
        if push_feishu and risk_level >= 3 and self.feishu and self._should_push(pond_id, "alert"):
            try:
                message_id = await self.feishu.send_alert(report, "red" if risk_level >= 4 else "amber")
                report["feishu_sent"] = message_id is not None
                report["feishu_message_id"] = message_id
            except Exception as e:
                logger.warning("Feishu push failed (non-fatal): %s", e)
        
        # 8. DB 写入（非阻塞）
        if self.db:
            try:
                await self.db.save_decision(pond_id, report)
            except Exception as e:
                logger.warning("DB save_decision failed: %s", e)
        
        report["timestamp"] = time.time()
        report["latency_ms"] = int((time.time() - start) * 1000)
        return report
    
    def _should_push(self, pond_id: str, scenario: str, cooldown_sec: int = 3600) -> bool:
        """飞书推送去重（60分钟）。"""
        key = f"{pond_id}:{scenario}"
        last = self._push_cooldown.get(key, 0.0)
        now = time.time()
        if now - last < cooldown_sec:
            return False
        self._push_cooldown[key] = now
        return True
