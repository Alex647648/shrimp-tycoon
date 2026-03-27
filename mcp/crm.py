"""CRM 读写模块 — Growth Agent 专用。

比赛版：SQLite 文件存储
产品版：PostgreSQL + 多租户
"""

import json
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

logger = logging.getLogger(__name__)

DEFAULT_CRM_PATH = Path(__file__).resolve().parent.parent / "data" / "crm.db"


class CRM:
    """轻量级 CRM（SQLite）。"""

    def __init__(self, db_path: str = None):
        self.db_path = db_path or str(DEFAULT_CRM_PATH)

    def init(self):
        """建表。"""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                region TEXT,
                area_mu REAL,
                score INTEGER DEFAULT 0,
                grade TEXT DEFAULT 'D',
                source TEXT,
                status TEXT DEFAULT 'new',
                created_at TEXT,
                updated_at TEXT,
                meta TEXT DEFAULT '{}'
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS outreach (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                lead_id INTEGER REFERENCES leads(id),
                day INTEGER,
                channel TEXT,
                message TEXT,
                sent_at TEXT,
                response TEXT
            )
        """)
        conn.commit()
        conn.close()

    def add_lead(self, lead: dict) -> int:
        """新增线索。"""
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()
        cur = conn.execute(
            "INSERT INTO leads (name, region, area_mu, score, grade, source, created_at, updated_at, meta) VALUES (?,?,?,?,?,?,?,?,?)",
            (lead.get("name", ""), lead.get("region", ""), lead.get("area_mu", 0),
             lead.get("score", 0), lead.get("grade", "D"), lead.get("source", ""),
             now, now, json.dumps(lead.get("meta", {}), ensure_ascii=False)),
        )
        conn.commit()
        lead_id = cur.lastrowid
        conn.close()
        return lead_id

    def list_leads(self, status: str = None, limit: int = 50) -> list:
        """查询线索。"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        if status:
            rows = conn.execute("SELECT * FROM leads WHERE status=? ORDER BY score DESC LIMIT ?", (status, limit)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM leads ORDER BY score DESC LIMIT ?", (limit,)).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def log_outreach(self, lead_id: int, day: int, channel: str, message: str) -> int:
        """记录触达。"""
        conn = sqlite3.connect(self.db_path)
        now = datetime.now().isoformat()
        cur = conn.execute(
            "INSERT INTO outreach (lead_id, day, channel, message, sent_at) VALUES (?,?,?,?,?)",
            (lead_id, day, channel, message, now),
        )
        conn.commit()
        oid = cur.lastrowid
        conn.close()
        return oid
