"""虾塘仿真状态引擎 — 管理虾塘当前状态，按 multiplier 推进时间。"""

import copy
import random
from datetime import datetime, timedelta

DEFAULT_SENSOR = {
    "schema": "SDP-1.0",
    "pond_id": "A03",
    "timestamp": "",
    "temp": 25.4,
    "DO": 6.2,
    "pH": 7.8,
    "ammonia": 0.16,
    "transparency": 38.0,
    "avg_weight": 28.5,
    "count": 485,
    "day": 45,
    "dead_shrimp": False,
    "molt_peak": False,
}

SCENARIOS = {
    "do_drop": {
        "sensor": {"DO": 2.1, "temp": 24.5},
        "wqar": {"csi": 60, "risk_level": 4, "risk_label": "高风险"},
    },
    "wssv": {
        "sensor": {"dead_shrimp": True, "count": 420},
        "wqar": {"csi": 80, "risk_level": 5, "risk_label": "极高风险"},
    },
    "storm": {
        "sensor": {"pH": 6.9, "temp": 23.1, "transparency": 15},
        "wqar": {"csi": 45, "risk_level": 3, "risk_label": "中等风险"},
    },
    "molt": {
        "sensor": {"molt_peak": True},
        "wqar": {"csi": 25, "risk_level": 2, "risk_label": "轻微风险"},
    },
    "harvest": {
        "sensor": {"avg_weight": 41.2, "count": 478},
        "wqar": {"csi": 12, "risk_level": 1, "risk_label": "正常运营"},
    },
}

_STATUS_THRESHOLDS = {
    "temp": [(22, 28, "optimal", "最适范围"), (18, 32, "normal", "正常"), (10, 37, "caution", "偏离"), (0, 100, "warning", "异常")],
    "DO": [(5, 99, "optimal", "充足"), (4, 5, "normal", "正常"), (3, 4, "caution", "偏低"), (1, 3, "warning", "危险"), (0, 1, "danger", "极危险")],
    "pH": [(7.5, 8.5, "optimal", "最佳范围"), (7.0, 9.0, "normal", "正常"), (6.5, 9.5, "caution", "偏离"), (0, 14, "warning", "异常")],
    "ammonia": [(0, 0.1, "optimal", "安全"), (0.1, 0.2, "normal", "正常"), (0.2, 0.3, "caution", "接近警戒"), (0.3, 0.5, "warning", "超标"), (0.5, 99, "danger", "严重超标")],
}


def _indicator_status(key: str, value: float) -> dict:
    for lo, hi, status, label in _STATUS_THRESHOLDS.get(key, []):
        if lo <= value <= hi:
            return {"value": value, "status": status, "label": label}
    return {"value": value, "status": "normal", "label": "未知"}


def compute_wqar(sensor: dict) -> dict:
    """根据传感器数据计算 WQAR（水质分析报告）。"""
    scores = []
    weights = {"DO": 35, "ammonia": 25, "pH": 20, "temp": 20}
    status_score = {"optimal": 0, "normal": 10, "caution": 40, "warning": 70, "danger": 100}
    indicators = {}
    for key in ["temp", "DO", "pH", "ammonia"]:
        ind = _indicator_status(key, round(sensor[key], 2))
        indicators[key] = ind
        scores.append(status_score.get(ind["status"], 50) * weights[key] / 100)
    csi = min(100, max(0, int(sum(scores))))
    if csi <= 20:
        risk_level, risk_label = 1, "正常运营"
    elif csi <= 40:
        risk_level, risk_label = 2, "轻微风险"
    elif csi <= 60:
        risk_level, risk_label = 3, "中等风险"
    elif csi <= 80:
        risk_level, risk_label = 4, "高风险"
    else:
        risk_level, risk_label = 5, "极高风险"
    trigger_llm = csi > 20
    return {
        "schema": "WQAR-1.0",
        "csi": csi,
        "risk_level": risk_level,
        "risk_label": risk_label,
        "indicators": indicators,
        "trigger_llm": trigger_llm,
    }


class PondSimulator:
    def __init__(self):
        self.sensor = copy.deepcopy(DEFAULT_SENSOR)
        self.sensor["timestamp"] = datetime.now().isoformat(timespec="seconds")
        self._base_time = datetime.now()
        self._scenario_override: dict | None = None

    def apply_scenario(self, name: str) -> dict | None:
        """应用场景覆盖，返回 wqar override 或 None。"""
        sc = SCENARIOS.get(name)
        if not sc:
            return None
        self.sensor.update(sc["sensor"])
        self._scenario_override = sc.get("wqar")
        return self._scenario_override

    def reset(self):
        self.sensor = copy.deepcopy(DEFAULT_SENSOR)
        self.sensor["timestamp"] = datetime.now().isoformat(timespec="seconds")
        self._base_time = datetime.now()
        self._scenario_override = None

    def tick(self, multiplier: int = 1) -> tuple[dict, dict]:
        """推进一个时间步，返回 (sensor, wqar)。"""
        self._base_time += timedelta(seconds=5 * multiplier)
        self.sensor["timestamp"] = self._base_time.isoformat(timespec="seconds")
        if not self._scenario_override:
            self.sensor["temp"] += random.uniform(-0.1, 0.1)
            self.sensor["DO"] += random.uniform(-0.05, 0.05)
            self.sensor["pH"] += random.uniform(-0.02, 0.02)
            self.sensor["ammonia"] += random.uniform(-0.005, 0.005)
            self.sensor["ammonia"] = max(0.0, self.sensor["ammonia"])
            self.sensor["transparency"] += random.uniform(-0.3, 0.3)
            growth = 0.002 * multiplier
            self.sensor["avg_weight"] += growth
            self.sensor["day"] += max(1, multiplier // 17280)
        wqar = compute_wqar(self.sensor)
        if self._scenario_override:
            wqar.update(self._scenario_override)
        sensor_out = copy.deepcopy(self.sensor)
        sensor_out["temp"] = round(sensor_out["temp"], 1)
        sensor_out["DO"] = round(sensor_out["DO"], 1)
        sensor_out["pH"] = round(sensor_out["pH"], 1)
        sensor_out["ammonia"] = round(sensor_out["ammonia"], 2)
        sensor_out["transparency"] = round(sensor_out["transparency"], 1)
        sensor_out["avg_weight"] = round(sensor_out["avg_weight"], 1)
        return sensor_out, wqar
