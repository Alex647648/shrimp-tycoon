"""SentinelMemory — 短期记忆模块，为 Sentinel Agent 提供历史感知能力。

设计原则：
- 最大保留 MAX_HISTORY=12 个 tick 的历史数据
- 支持趋势分析（上升/下降/稳定）
- 支持 2σ 异常检测
- 生成可注入 LLM 的文本上下文
- 无状态持久化，随 Agent 生命周期存在
"""

import math
import logging
from collections import deque
from typing import Deque

logger = logging.getLogger(__name__)

MAX_HISTORY = 12  # 最多保存 12 个 tick


class SentinelMemory:
    """Sentinel Agent 短期记忆，滑动窗口存储 sensor + wqar 历史。

    用法：
        memory = SentinelMemory()
        memory.add(sensor, wqar)
        trend = memory.trend("DO")         # "上升" / "下降" / "稳定"
        is_anomaly = memory.anomaly("pH")  # True / False
        context = memory.format_context()  # 注入 LLM 的文本
    """

    def __init__(self, max_history: int = MAX_HISTORY):
        self._max = max_history
        self._history: Deque[dict] = deque(maxlen=max_history)

    # ── 公开接口 ────────────────────────────────────────────────────────────

    def add(self, sensor: dict, wqar: dict) -> None:
        """追加一条记录，超限时自动删除最旧一条。"""
        entry = {
            "sensor": dict(sensor),
            "wqar": dict(wqar),
            "timestamp": sensor.get("timestamp", ""),
        }
        self._history.append(entry)
        logger.debug(
            "SentinelMemory.add: len=%d/%d  ts=%s",
            len(self._history), self._max, entry["timestamp"],
        )

    def trend(self, field: str) -> str:
        """分析指定传感器字段的近期趋势。

        Returns:
            "上升" | "下降" | "稳定"
        """
        values = self._extract_values(field)
        if len(values) < 2:
            return "稳定"
        return _compute_trend(values)

    def anomaly(self, field: str) -> bool:
        """检测最新值是否偏离历史均值 2σ 以上。

        特殊情况：若历史标准差为零（所有历史值完全相同），
        则当最新值偏离均值超过均值的 10% 时，也视为异常。

        Returns:
            True 表示异常，False 表示正常
        """
        values = self._extract_values(field)
        if len(values) < 3:
            return False
        latest = values[-1]
        # 用除最新值外的历史计算基准
        history = values[:-1]
        mean = _mean(history)
        std = _std(history, mean)

        if std < 1e-9:
            # 历史方差为零（全相同值），用绝对偏差比率判断
            if abs(mean) < 1e-9:
                # 均值也接近零，用绝对差值判断
                is_anomaly = abs(latest - mean) > 0.5
            else:
                # 偏离超过均值 10% 视为异常
                is_anomaly = abs(latest - mean) / abs(mean) > 0.10
        else:
            z = abs(latest - mean) / std
            is_anomaly = z > 2.0

        if is_anomaly:
            logger.info(
                "SentinelMemory.anomaly: field=%s latest=%.3f mean=%.3f std=%.3f",
                field, latest, mean, std,
            )
        return is_anomaly

    def format_context(self) -> str:
        """生成适合注入 LLM 的文本描述，包含近期趋势和异常信号。"""
        if not self._history:
            return "（暂无历史数据）"

        n = len(self._history)
        lines = [f"## 近 {n} 个 tick 历史摘要"]

        # 关键指标趋势
        key_fields = ["DO", "temp", "pH", "ammonia"]
        trend_lines = []
        anomaly_lines = []

        for field in key_fields:
            values = self._extract_values(field)
            if not values:
                continue
            t = _compute_trend(values) if len(values) >= 2 else "稳定"
            latest = values[-1]
            trend_lines.append(f"  - {field}: 最新={latest:.2f}，趋势={t}")

            if self.anomaly(field):
                anomaly_lines.append(f"  ⚠️ {field} 出现异常波动（偏离历史均值 2σ）")

        if trend_lines:
            lines.append("### 指标趋势")
            lines.extend(trend_lines)

        if anomaly_lines:
            lines.append("### 异常信号")
            lines.extend(anomaly_lines)

        # 风险等级变化
        risk_vals = [e["wqar"].get("risk_level", 1) for e in self._history]
        if risk_vals:
            max_risk = max(risk_vals)
            latest_risk = risk_vals[-1]
            lines.append(
                f"### 风险状态: 当前={latest_risk}，本段最高={max_risk}"
            )

        # CSI 统计
        csi_vals = [e["wqar"].get("csi", 0) for e in self._history]
        if csi_vals:
            avg_csi = _mean(csi_vals)
            lines.append(f"### CSI 均值={avg_csi:.1f}，最新={csi_vals[-1]}")

        return "\n".join(lines)

    # ── 只读属性 ────────────────────────────────────────────────────────────

    @property
    def size(self) -> int:
        """当前历史记录数量。"""
        return len(self._history)

    @property
    def is_full(self) -> bool:
        """是否已满（达到 max_history）。"""
        return len(self._history) >= self._max

    def latest(self) -> dict | None:
        """返回最新一条记录，无历史时返回 None。"""
        return dict(self._history[-1]) if self._history else None

    def clear(self) -> None:
        """清空所有历史记录。"""
        self._history.clear()

    # ── 私有辅助 ────────────────────────────────────────────────────────────

    def _extract_values(self, field: str) -> list[float]:
        """从历史中提取指定字段的数值序列（按时间排列，最旧在前）。"""
        values = []
        for entry in self._history:
            val = entry["sensor"].get(field)
            if isinstance(val, (int, float)) and not math.isnan(float(val)):
                values.append(float(val))
        return values


# ── 工具函数 ────────────────────────────────────────────────────────────────

def _mean(values: list[float]) -> float:
    return sum(values) / len(values) if values else 0.0


def _std(values: list[float], mean: float | None = None) -> float:
    """总体标准差。"""
    if len(values) < 2:
        return 0.0
    if mean is None:
        mean = _mean(values)
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance)


def _compute_trend(values: list[float], threshold: float = 0.05) -> str:
    """用首尾均值比较判断趋势。

    threshold: 相对变化比例的阈值，小于此视为稳定。
    """
    if len(values) < 2:
        return "稳定"
    # 前半段均值 vs 后半段均值
    mid = len(values) // 2
    first_half = values[:mid] if mid > 0 else values[:1]
    second_half = values[mid:]
    avg_first = _mean(first_half)
    avg_second = _mean(second_half)
    if avg_first == 0:
        return "稳定"
    change_ratio = (avg_second - avg_first) / abs(avg_first)
    if change_ratio > threshold:
        return "上升"
    elif change_ratio < -threshold:
        return "下降"
    else:
        return "稳定"
