"""无人机多光谱航拍适配器（占位）。

未来功能：
- 多光谱航拍 → 水色分析
- 蓝藻/绿藻密度估算
- 虾群密度俯瞰统计
- 塘口面积/水位测量
"""

import time
import logging

logger = logging.getLogger(__name__)


class DroneAdapter:
    """无人机传感器适配器（占位）。"""

    async def read(self, pond_id: str = "A1") -> dict:
        logger.warning("DroneAdapter: 占位模式 — 无人机接口开发中")
        return {
            "schema": "SDP-1.0",
            "pond_id": pond_id,
            "timestamp": int(time.time()),
            "source": "drone_placeholder",
            "_note": "无人机多光谱航拍接口开发中",
        }
