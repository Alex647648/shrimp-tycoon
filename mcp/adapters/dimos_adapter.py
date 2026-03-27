"""DIMOS × 宇树机器狗 传感器适配器（占位实现）。

集成路径：
  哨兵 Agent → sensor_read(adapter=dimos)
       ↓
  DimosMCPAdapter
       ↓ JSON-RPC
  DIMOS MCP Server（对方部署）
       ↓ WebRTC
  宇树 Go2 机器狗
       ↓ 巡塘采样
  水温 / DO / pH / 氨氮 / 摄像头画面

环境变量：
  DIMOS_MCP_URL=http://host:port
"""

import os
import time
import logging

logger = logging.getLogger(__name__)

DIMOS_MCP_URL = os.getenv("DIMOS_MCP_URL", "http://localhost:9090")


class DimosAdapter:
    """DIMOS MCP 传感器适配器。"""

    def __init__(self, pond_id: str = "A1"):
        self.pond_id = pond_id
        self.mcp_url = DIMOS_MCP_URL

    async def read(self, pond_id: str = None) -> dict:
        """通过 DIMOS MCP 读取真实传感器数据。

        产品版实现：
        1. POST {mcp_url}/tools/sensor_read
        2. 解析 SDP-1.0 响应
        3. 附加 camera_frame（如有）

        当前：返回占位数据 + 提示。
        """
        pid = pond_id or self.pond_id
        logger.warning(
            "DimosAdapter: 占位模式 — 请配置 DIMOS_MCP_URL 并部署 DIMOS MCP Server"
        )

        return {
            "schema": "SDP-1.0",
            "pond_id": pid,
            "timestamp": int(time.time()),
            "temp": 26.0,
            "DO": 6.0,
            "pH": 7.8,
            "ammonia": 0.15,
            "transparency": 35,
            "source": "dimos_placeholder",
            "camera_frame": None,
            "_note": f"DIMOS 占位数据。配置 DIMOS_MCP_URL={self.mcp_url} 后接入真实机器狗。",
        }

    async def patrol(self, pond_id: str = None, route: str = "default") -> dict:
        """（占位）派遣机器狗巡塘。"""
        return {
            "status": "not_implemented",
            "message": "请部署 DIMOS MCP Server 并配置 DIMOS_MCP_URL",
        }
