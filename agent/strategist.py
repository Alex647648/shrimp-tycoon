"""虾塘大亨 · Strategist Agent — 日报生成器。

职责：每日汇总传感器记录和决策，生成 DAILY-1.0 日报，推送飞书。
约束（AGENT_CONSTRAINTS.md §2.2）：
- 不调用 sensor_read（只读 DB）
- 不写 decisions 表
- 不发告警（只发日报）
- LLM 调用必须 asyncio.timeout(10)
- fallback：纯规则汇总
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from pathlib import Path

logger = logging.getLogger("strategist")

PROMPTS_DIR = Path(__file__).parent / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_DIR / "strategist_system.txt"

# 趋势判断阈值
TREND_THRESHOLD = 0.1  # 变化幅度 < 10% 视为"稳定"


class StrategistAgent:
    """Strategist Agent：每日日报生成。

    触发条件：每日 20:00 cron 或 POST /api/strategist/run
    """

    def __init__(self, db, kb_searcher=None, feishu_pusher=None):
        """初始化。

        Args:
            db: PondDB 实例
            kb_searcher: KBSearcher 实例（可选）
            feishu_pusher: FeishuPusher 实例（可选）
        """
        self.db = db
        self.kb_searcher = kb_searcher
        self.feishu_pusher = feishu_pusher
        self._system_prompt = self._load_system_prompt()

    def _load_system_prompt(self) -> str:
        """加载系统提示词文件。"""
        try:
            return SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
        except FileNotFoundError:
            logger.warning("strategist_system.txt not found, using inline fallback")
            return "你是虾塘日报生成专家，请根据数据生成 DAILY-1.0 格式 JSON 日报。"

    async def run_daily(self, pond_id: str, date: str) -> dict:
        """生成指定塘口当日日报。

        Args:
            pond_id: 塘口编号
            date: ISO日期字符串（"2026-03-27"）

        Returns:
            DAILY-1.0 格式字典
        """
        logger.info("Strategist run_daily: pond=%s date=%s", pond_id, date)

        # 1. 读当日记录（不调 sensor_read，只读 DB）
        records = await self.db.get_day_records(pond_id, date)

        # 2. 读趋势
        trends_raw = await self._fetch_trends(pond_id)

        # 3. 知识库查询
        kb_context = await self._query_kb(trends_raw)

        # 4. 构建输入上下文
        context = self._build_context(pond_id, date, records, trends_raw, kb_context)

        # 5. LLM 推理（Haiku + 10s 超时 + fallback）
        report = await self._llm_or_fallback(context, pond_id, date, records, trends_raw)

        # 6. 保存到 DB（§4.6：失败只 warning）
        await self.db.save_daily_report(report)

        # 7. 推送飞书（可选，失败不阻塞）
        if self.feishu_pusher:
            await self._push_feishu(report)

        logger.info("Daily report saved: pond=%s date=%s model=%s",
                    pond_id, date, report.get("model_used"))
        return report

    async def _fetch_trends(self, pond_id: str) -> dict:
        """读取各指标趋势数据。"""
        fields = ["temp", "DO", "pH", "ammonia"]
        trends = {}
        for field in fields:
            trends[field] = await self.db.get_trend(pond_id, field, hours=24)
        return trends

    async def _query_kb(self, trends_raw: dict) -> str:
        """用趋势摘要查询知识库。"""
        if not self.kb_searcher:
            return ""
        try:
            # 构建查询关键词
            query_parts = []
            for field, vals in trends_raw.items():
                if vals:
                    avg = sum(vals) / len(vals)
                    query_parts.append(f"{field} {avg:.1f}")
            query = " ".join(query_parts) if query_parts else "水质管理 日报"
            results = self.kb_searcher.search(query, top_k=3)
            return "\n".join(r["title"] + ": " + r["content"][:200] for r in results)
        except Exception as e:
            logger.warning("KB query failed: %s", e)
            return ""

    def _build_context(self, pond_id: str, date: str, records: list,
                       trends_raw: dict, kb_context: str) -> str:
        """构建 LLM 输入上下文字符串。"""
        sensor_records = [r for r in records if r["type"] == "sensor"]
        decision_records = [r for r in records if r["type"] == "decision"]

        # 传感器汇总
        sensor_summary = "（无传感器数据）"
        if sensor_records:
            last = sensor_records[-1]["data"]
            sensor_summary = (
                f"最新读数：温度={last.get('temp')}°C, "
                f"DO={last.get('do_val')} mg/L, "
                f"pH={last.get('pH')}, "
                f"氨氮={last.get('ammonia')} mg/L, "
                f"透明度={last.get('transparency')} cm"
            )

        # 决策汇总
        decision_summary = "（无决策记录）"
        if decision_records:
            decision_summary = f"今日决策 {len(decision_records)} 条，" + "; ".join(
                d["data"].get("summary", "") for d in decision_records[-3:]
            )

        # 趋势汇总
        trend_summary = self._summarize_trends(trends_raw)

        ctx = (
            f"塘口：{pond_id}  日期：{date}\n"
            f"传感器记录数：{len(sensor_records)}\n"
            f"{sensor_summary}\n"
            f"决策：{decision_summary}\n"
            f"24h趋势：{trend_summary}\n"
        )
        if kb_context:
            ctx += f"\n知识库参考：\n{kb_context}\n"
        return ctx

    def _summarize_trends(self, trends_raw: dict) -> str:
        """将趋势数据转为文字描述。"""
        parts = []
        for field, vals in trends_raw.items():
            label = self._calc_trend_label(vals)
            parts.append(f"{field}:{label}")
        return ", ".join(parts) if parts else "无数据"

    def _calc_trend_label(self, vals: list) -> str:
        """计算趋势标签：上升/下降/稳定/无数据。"""
        if len(vals) < 2:
            return "无数据"
        delta = vals[-1] - vals[0]
        pct = abs(delta) / (abs(vals[0]) + 1e-9)
        if pct < TREND_THRESHOLD:
            return "稳定"
        return "上升" if delta > 0 else "下降"

    async def _llm_or_fallback(self, context: str, pond_id: str, date: str,
                                records: list, trends_raw: dict) -> dict:
        """调用 Haiku LLM，超时或失败 fallback 到规则汇总。"""
        try:
            import anthropic
            client = anthropic.AsyncAnthropic()
            async with asyncio.timeout(10):
                response = await client.messages.create(
                    model="claude-haiku-4-5",
                    max_tokens=1024,
                    system=self._system_prompt,
                    messages=[{"role": "user", "content": context}],
                )
            raw = response.content[0].text.strip()
            # 去掉 markdown 代码块
            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)
            report = json.loads(raw)
            report["schema"] = "DAILY-1.0"
            report["pond_id"] = pond_id
            report["date"] = date
            report.setdefault("model_used", "haiku")
            logger.info("LLM daily report generated: pond=%s", pond_id)
            return report
        except (asyncio.TimeoutError, Exception) as e:
            logger.warning("LLM fallback triggered: %s", e)
            return self._rule_fallback(pond_id, date, records, trends_raw)

    def _rule_fallback(self, pond_id: str, date: str,
                       records: list, trends_raw: dict) -> dict:
        """纯规则汇总日报（LLM 不可用时）。"""
        sensor_records = [r for r in records if r["type"] == "sensor"]
        decision_records = [r for r in records if r["type"] == "decision"]

        # 投喂汇总
        feeding_count = sum(
            1 for d in decision_records
            if "投喂" in (d["data"].get("summary") or "")
        )

        # 趋势标签
        trends_labels = {
            field: self._calc_trend_label(vals)
            for field, vals in trends_raw.items()
        }

        # 病害风险：简单规则
        disease_risk = "low"
        if sensor_records:
            last = sensor_records[-1]["data"]
            do_val = last.get("do_val") or 99
            ammonia = last.get("ammonia") or 0
            if do_val < 3 or ammonia > 0.5:
                disease_risk = "medium"
            if do_val < 1.5 or ammonia > 1.0:
                disease_risk = "high"

        # 建议
        recommendations = ["继续监控各项水质指标"]
        if disease_risk != "low":
            recommendations.append("水质异常，建议增加检测频率")

        return {
            "schema": "DAILY-1.0",
            "pond_id": pond_id,
            "date": date,
            "summary": f"今日共 {len(sensor_records)} 条传感器记录，{len(decision_records)} 条决策记录。",
            "trends": trends_labels,
            "feeding_summary": {"decision_count": feeding_count},
            "disease_risk": disease_risk,
            "harvest_outlook": {"recommended": False, "reason": "规则引擎不做捕捞判断"},
            "recommendations": recommendations,
            "model_used": "rules",
        }

    async def _push_feishu(self, report: dict) -> None:
        """推送日报到飞书（失败不阻塞）。"""
        try:
            summary = report.get("summary", "")
            date = report.get("date", "")
            pond_id = report.get("pond_id", "")
            text = f"📊 【日报】{pond_id} {date}\n{summary}\n风险：{report.get('disease_risk', '-')}"
            await self.feishu_pusher.send_message(text)
        except Exception as e:
            logger.warning("Feishu push failed for daily report: %s", e)
