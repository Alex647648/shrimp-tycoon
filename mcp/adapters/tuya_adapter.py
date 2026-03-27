"""
涂鸦 IoT Open API 适配器
文档：https://developer.tuya.com/en/docs/iot/singnature?id=Ka43a5mtx1gsc
支持设备：Tuya 水质检测仪（YY-W9909 等）
覆盖参数：水温 + pH + TDS + EC + 盐度
DO / 氨氮：无 Tuya 原生支持，从 simulator fallback
"""

import hashlib
import hmac
import json
import os
import time
from typing import Optional
import logging

try:
    import requests
except ImportError:
    requests = None  # type: ignore

logger = logging.getLogger("tuya_adapter")

# 涂鸦 API 区域端点
REGION_ENDPOINTS = {
    "cn": "https://openapi.tuyacn.com",
    "us": "https://openapi.tuyaus.com",
    "eu": "https://openapi.tuyaeu.com",
    "in": "https://openapi.tuyain.com",
}

# Tuya DP Code → 内部字段名（+换算）
DP_MAP = {
    "temp_current":    ("temp",         0.1),   # 0.1°C
    "temp_value":      ("temp",         0.1),
    "temperature":     ("temp",         1.0),
    "ph_value":        ("pH",           0.1),   # 0.1 pH
    "tds_value":       ("tds",          1.0),   # mg/L
    "ec_value":        ("ec",           1.0),   # μS/cm
    "salinity_value":  ("salinity",     0.01),  # ppt
    "turbidity_value": ("transparency", 1.0),   # NTU → 近似透明度
    "do_value":        ("DO",           0.1),   # 0.1 mg/L（部分设备）
    "ammonia_value":   ("ammonia",      0.01),  # mg/L（部分设备）
}


class TuyaAdapter:
    """
    从涂鸦云获取设备最新数据，转换为 SDP-1.0 格式。

    使用方法：
        adapter = TuyaAdapter()
        sensor = adapter.read_sensor("your_device_id", pond_id="A03")
    """

    def __init__(self):
        self.client_id     = os.getenv("TUYA_CLIENT_ID", "")
        self.client_secret = os.getenv("TUYA_CLIENT_SECRET", "")
        self.region        = os.getenv("TUYA_REGION", "cn")
        self.base_url      = REGION_ENDPOINTS.get(self.region, REGION_ENDPOINTS["cn"])
        self._token: Optional[str] = None
        self._token_expires: float = 0.0

    # ── 认证 ────────────────────────────────────────────────
    def _sign(self, t: str, method: str, path: str,
              body: str = "", token: str = "") -> str:
        """计算 HmacSHA256 签名（涂鸦规范）"""
        str_to_sign = "\n".join([
            method,
            hashlib.sha256(body.encode()).hexdigest(),
            "",
            path,
        ])
        message = self.client_id + token + t + str_to_sign
        return hmac.new(
            self.client_secret.encode(),
            message.encode(),
            hashlib.sha256,
        ).hexdigest().upper()

    def _headers(self, path: str, method: str = "GET",
                 body: str = "", use_token: bool = True) -> dict:
        t = str(int(time.time() * 1000))
        token = self._token if use_token else ""
        sign = self._sign(t, method, path, body, token)
        return {
            "client_id": self.client_id,
            "sign": sign,
            "t": t,
            "sign_method": "HMAC-SHA256",
            "access_token": token or "",
        }

    def _get_token(self) -> str:
        """获取/刷新 access_token（有效期 7200s，提前 60s 刷新）"""
        if self._token and time.time() < self._token_expires - 60:
            return self._token
        path = "/v1.0/token?grant_type=1"
        headers = self._headers(path, use_token=False)
        resp = requests.get(self.base_url + path, headers=headers, timeout=8)
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"Tuya token error: {data}")
        result = data["result"]
        self._token = result["access_token"]
        self._token_expires = time.time() + result.get("expire_time", 7200)
        logger.info("Tuya token refreshed, expires in %ss", result.get("expire_time"))
        return self._token

    # ── 读取设备状态 ─────────────────────────────────────────
    def get_device_status(self, device_id: str) -> dict:
        """
        GET /v1.0/devices/{device_id}/status
        返回 Tuya 原始 DP 列表：[{"code": "temp_current", "value": 254}, ...]
        """
        self._get_token()
        path = f"/v1.0/devices/{device_id}/status"
        headers = self._headers(path)
        resp = requests.get(self.base_url + path, headers=headers, timeout=8)
        data = resp.json()
        if not data.get("success"):
            raise RuntimeError(f"Tuya device status error: {data}")
        return {dp["code"]: dp["value"] for dp in data["result"]}

    # ── 转换为 SDP-1.0 ──────────────────────────────────────
    def read_sensor(
        self,
        device_id: str,
        pond_id: str = "A03",
        day: int = 45,
        count: int = 485,
        avg_weight: float = 28.5,
        dead_shrimp: bool = False,
        molt_peak: bool = False,
        fallback_DO: float = 6.2,
        fallback_ammonia: float = 0.16,
    ) -> dict:
        """
        读取涂鸦设备数据，合并缺失字段（DO/氨氮使用 fallback），返回 SDP-1.0 dict。

        Args:
            device_id:       涂鸦设备 ID
            pond_id:         塘口编号
            day:             当前养殖天数（从外部传入，传感器无此值）
            count/avg_weight/dead_shrimp/molt_peak: 虾群状态（传感器无法测量，从运营数据补全）
            fallback_DO:     DO fallback 值（涂鸦设备无 DO 时使用）
            fallback_ammonia:氨氮 fallback 值（涂鸦设备无氨氮时使用）

        Returns:
            SDP-1.0 格式 dict（与 simulator.py 输出结构完全一致）
        """
        raw = self.get_device_status(device_id)
        parsed: dict = {}
        for code, value in raw.items():
            if code in DP_MAP:
                field, multiplier = DP_MAP[code]
                parsed[field] = round(value * multiplier, 3)

        return {
            "schema":       "SDP-1.0",
            "pond_id":      pond_id,
            "timestamp":    _iso_now(),
            "temp":         parsed.get("temp",         25.4),
            "DO":           parsed.get("DO",           fallback_DO),
            "pH":           parsed.get("pH",           7.8),
            "ammonia":      parsed.get("ammonia",      fallback_ammonia),
            "transparency": parsed.get("transparency", 38.0),
            "avg_weight":   avg_weight,
            "count":        count,
            "day":          day,
            "dead_shrimp":  dead_shrimp,
            "molt_peak":    molt_peak,
            # 原始 Tuya 数据附带（调试/记录用）
            "_tuya_raw":    raw,
        }

    def is_configured(self) -> bool:
        """检查环境变量是否已配置"""
        return bool(self.client_id and self.client_secret)


# ── 工具函数 ─────────────────────────────────────────────────
def _iso_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S")


# ── 快速测试 ──────────────────────────────────────────────────
if __name__ == "__main__":
    import sys
    device_id = sys.argv[1] if len(sys.argv) > 1 else "DEMO_DEVICE_ID"
    adapter = TuyaAdapter()
    if not adapter.is_configured():
        print("❌ 未配置 TUYA_CLIENT_ID / TUYA_CLIENT_SECRET")
        print("   在 .env 文件中添加这两个变量后重试")
        sys.exit(1)
    result = adapter.read_sensor(device_id)
    print(json.dumps(result, ensure_ascii=False, indent=2))
