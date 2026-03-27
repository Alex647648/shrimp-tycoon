"""飞书推送模块 — 获取 token 并发送告警卡片。"""

import os
import time
import logging
import httpx

logger = logging.getLogger(__name__)

FEISHU_USER_OPEN_ID = "ou_50801fcf36c698da7e26aa530523ec85"
TOKEN_URL = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
MSG_URL = "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id"

LEVEL_EMOJI = {"red": "🔴", "amber": "🟡", "green": "🟢"}


def _build_card(report: dict, level: str) -> dict:
    emoji = LEVEL_EMOJI.get(level, "⚪")
    actions_text = "\n".join(f"• {a}" for a in report.get("actions", []))
    return {
        "msg_type": "interactive",
        "receive_id": FEISHU_USER_OPEN_ID,
        "content": _card_json(emoji, level, report, actions_text),
    }


def _card_json(emoji: str, level: str, report: dict, actions_text: str) -> str:
    import json
    card = {
        "config": {"wide_screen_mode": True},
        "header": {
            "title": {"tag": "plain_text", "content": f"🦞 虾塘大亨 · 告警通知 {emoji}"},
            "template": "red" if level == "red" else ("orange" if level == "amber" else "green"),
        },
        "elements": [
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**风险等级**: {report.get('risk_label', '')} (Level {report.get('risk_level', '')})"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**综合评估**: {report.get('summary', '')}"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**立即操作**:\n{actions_text}"}},
            {"tag": "div", "text": {"tag": "lark_md", "content": f"**模型**: {report.get('model_used', 'rule_engine')} | 延迟: {report.get('latency_ms', 0)}ms | 置信度: {report.get('confidence', 0)}"}},
        ],
    }
    return json.dumps(card, ensure_ascii=False)


class FeishuPusher:
    def __init__(self):
        self.app_id = os.getenv("FEISHU_APP_ID", "")
        self.app_secret = os.getenv("FEISHU_APP_SECRET", "")
        self._token: str | None = None
        self._token_expires: float = 0

    async def get_token(self) -> str:
        if self._token and time.time() < self._token_expires:
            return self._token
        if not self.app_id or not self.app_secret:
            raise ValueError("FEISHU_APP_ID / FEISHU_APP_SECRET not set")
        async with httpx.AsyncClient() as client:
            resp = await client.post(TOKEN_URL, json={
                "app_id": self.app_id,
                "app_secret": self.app_secret,
            })
            data = resp.json()
        if data.get("code") != 0:
            raise RuntimeError(f"Feishu token error: {data}")
        self._token = data["tenant_access_token"]
        self._token_expires = time.time() + data.get("expire", 7200) - 60
        return self._token

    async def send_alert(self, report: dict, level: str) -> str | None:
        """发送告警卡片，返回 message_id 或 None。"""
        try:
            token = await self.get_token()
            payload = _build_card(report, level)
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    MSG_URL,
                    headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=utf-8"},
                    json=payload,
                    timeout=10,
                )
                data = resp.json()
            if data.get("code") == 0:
                mid = data.get("data", {}).get("message_id")
                logger.info("Feishu alert sent: %s", mid)
                return mid
            logger.warning("Feishu send failed: %s", data)
            return None
        except Exception as e:
            logger.warning("Feishu push error: %s", e)
            return None
