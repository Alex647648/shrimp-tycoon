"""Mock 传感器适配器 — 仿真数据（默认模式）。"""

import random
import time


class MockAdapter:
    """生成模拟 SDP-1.0 传感器数据。"""

    def __init__(self, pond_id: str = "A1"):
        self.pond_id = pond_id

    async def read(self, pond_id: str = None) -> dict:
        """返回仿真传感器数据（SDP-1.0 格式）。"""
        pid = pond_id or self.pond_id
        return {
            "schema": "SDP-1.0",
            "pond_id": pid,
            "timestamp": int(time.time()),
            "temp": round(random.uniform(24.0, 28.0), 1),
            "DO": round(random.uniform(4.0, 8.0), 1),
            "pH": round(random.uniform(7.2, 8.2), 1),
            "ammonia": round(random.uniform(0.05, 0.25), 3),
            "transparency": random.randint(25, 45),
            "avg_weight": round(random.uniform(15.0, 40.0), 1),
            "count": random.randint(3000, 6000),
            "source": "mock",
        }
