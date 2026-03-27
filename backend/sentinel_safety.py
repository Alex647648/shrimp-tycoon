"""Sentinel 安全校验模块 — 传感器数据校验 + 危险操作检查。

约束（AGENT_CONSTRAINTS.md §4.3 / §4.4）：
- validate_sensor()：物理范围校验，失败标记而非抛出
- _safety_check()：危险操作加警告，不删除决策
"""

import logging

logger = logging.getLogger("sentinel_safety")

# 物理可能范围（§4.3）
VALID_RANGES = {
    "temp":         (0.0,   45.0),   # 摄氏度
    "DO":           (0.0,   20.0),   # mg/L
    "pH":           (3.0,   12.0),
    "ammonia":      (0.0,   10.0),   # mg/L
    "transparency": (0.0,   200.0),  # cm
    "avg_weight":   (0.0,   200.0),  # g
    "count":        (0.0,   100000.0),
}

# 安全默认值（范围中点）
SAFE_DEFAULTS = {k: (v[0] + v[1]) / 2 for k, v in VALID_RANGES.items()}

# 危险操作关键词（§4.4）
DANGEROUS_KEYWORDS = [
    "清塘", "全部排水", "停止增氧", "停增氧",
    "大量投药", "超量用药", "倒塘",
    "drain", "emergency_stop", "kill_all",
]

WARNING_SUFFIX = "\n⚠️【需人工确认，请勿自动执行】"


def validate_sensor(sensor: dict) -> dict:
    """物理范围校验。
    
    失败不抛出，而是标记字段并用安全默认值替换。
    调用者通过 {field}_val_invalid 字段知道哪些数据有问题。
    
    Args:
        sensor: 原始传感器数据字典
        
    Returns:
        验证后的字典（原值副本）
        
    Example:
        sensor = {"temp": 99.0, "DO": 6.2}  # temp 超范围
        validated = validate_sensor(sensor)
        # validated["temp"] = 22.5（安全默认）
        # validated["temp_val_invalid"] = True
    """
    result = dict(sensor)
    
    for field, (lo, hi) in VALID_RANGES.items():
        val = sensor.get(field)
        if val is None:
            continue
            
        if not (lo <= val <= hi):
            result[f"{field}_val_invalid"] = True
            result[f"{field}_original"] = val
            result[field] = SAFE_DEFAULTS[field]
            logger.warning(
                "Sensor field %s out of range: %s (valid: %s–%s) → replaced with %s",
                field, val, lo, hi, SAFE_DEFAULTS[field]
            )
    
    return result


def _safety_check(actions: list[str]) -> list[str]:
    """扫描操作列表，危险操作附加人工确认警告。
    
    不删除操作，只附加警告。保留决策完整性，但阻止自动执行。
    
    Args:
        actions: 操作列表
        
    Returns:
        附加警告后的操作列表
        
    Example:
        actions = ["开增氧机", "清塘"]
        checked = _safety_check(actions)
        # checked[1] = "清塘\n⚠️【需人工确认，请勿自动执行】"
    """
    checked = []
    for action in actions:
        if any(kw in action for kw in DANGEROUS_KEYWORDS):
            action = action + WARNING_SUFFIX
            logger.warning("High-risk action detected: %s", action[:80])
        checked.append(action)
    return checked
