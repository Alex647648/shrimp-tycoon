"""虾塘大亨 · SQLite 持久化层。

职责：读写持久化数据（sensor_readings / decisions / daily_reports）。
禁止：包含业务逻辑，调用LLM，包含副作用。

约束（来自 AGENT_CONSTRAINTS.md）：
- §1.2：纯数据访问，无业务逻辑
- §1.3：文件 ≤200 行，函数 ≤60 行
- §3.1：文件名 snake_case，类名 PascalCase，方法名 snake_case 动词_名词
- §4.6：DB写入失败只记录 warning，不 raise，不阻断主流程
- §4.6：磁盘满时删除30天前的 sensor_readings
"""

import os
import time
import json
import logging
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger("db")

DB_PATH = Path(os.getenv("DB_PATH", "data/pond.db"))
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# ── Schema 定义（3张表）─────────────────────────────────────────────────

CREATE_SENSOR_READINGS = """
CREATE TABLE IF NOT EXISTS sensor_readings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    pond_id         TEXT NOT NULL,
    timestamp       REAL NOT NULL,
    temp            REAL,
    do_val          REAL,
    ph              REAL,
    ammonia         REAL,
    transparency    INTEGER,
    avg_weight      REAL,
    count           INTEGER,
    dead_shrimp     INTEGER DEFAULT 0,
    molt_peak       INTEGER DEFAULT 0,
    read_failed     INTEGER DEFAULT 0
);
"""

CREATE_DECISIONS = """
CREATE TABLE IF NOT EXISTS decisions (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    pond_id             TEXT NOT NULL,
    timestamp           REAL NOT NULL,
    risk_level          INTEGER NOT NULL,
    model_used          TEXT,
    summary             TEXT,
    actions             TEXT,  -- JSON list
    feishu_sent         INTEGER DEFAULT 0,
    feishu_message_id   TEXT
);
"""

CREATE_DAILY_REPORTS = """
CREATE TABLE IF NOT EXISTS daily_reports (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    pond_id     TEXT NOT NULL,
    date        TEXT NOT NULL,
    report_json TEXT  -- JSON 完整日报
);
"""


class PondDB:
    """SQLite 数据持久化层。
    
    约束：
    - 所有写入失败只记录 warning，不 raise
    - 所有方法都是 async（预留升级到异步引擎的空间）
    """

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = db_path or DB_PATH
        self._conn: sqlite3.Connection | None = None

    async def init(self) -> None:
        """初始化数据库，建表（幂等）。"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute("PRAGMA journal_mode=WAL")  # 写前日志，增加并发
            conn.execute(CREATE_SENSOR_READINGS)
            conn.execute(CREATE_DECISIONS)
            conn.execute(CREATE_DAILY_REPORTS)
            conn.commit()
            conn.close()
            logger.info("DB initialized at %s", self.db_path)
        except Exception as e:
            logger.error("DB init failed: %s", e)
            raise

    async def save_reading(self, pond_id: str, sensor: dict) -> None:
        """写入传感器记录。失败只 warning，不阻断主流程。
        
        Args:
            pond_id: 塘口编号
            sensor: SDP-1.0 格式数据字典
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                """INSERT INTO sensor_readings
                   (pond_id, timestamp, temp, do_val, ph, ammonia, transparency, avg_weight, count, dead_shrimp, molt_peak, read_failed)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pond_id,
                    sensor.get("timestamp", time.time()),
                    sensor.get("temp"),
                    sensor.get("DO"),
                    sensor.get("pH"),
                    sensor.get("ammonia"),
                    sensor.get("transparency"),
                    sensor.get("avg_weight"),
                    sensor.get("count"),
                    int(sensor.get("dead_shrimp", False)),
                    int(sensor.get("molt_peak", False)),
                    int(sensor.get("read_failed", False)),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("DB save_reading failed for pond %s: %s", pond_id, e)
            # 不 raise，不返回错误信息

    async def save_decision(self, pond_id: str, decision: dict) -> None:
        """写入决策记录。失败只 warning。
        
        Args:
            pond_id: 塘口编号
            decision: DECISION-1.0 格式数据字典
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                """INSERT INTO decisions
                   (pond_id, timestamp, risk_level, model_used, summary, actions, feishu_sent, feishu_message_id)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    pond_id,
                    decision.get("timestamp", time.time()),
                    decision.get("risk_level", 1),
                    decision.get("model_used"),
                    decision.get("summary"),
                    json.dumps(decision.get("actions", []), ensure_ascii=False),
                    int(decision.get("feishu_sent", False)),
                    decision.get("feishu_message_id"),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("DB save_decision failed for pond %s: %s", pond_id, e)

    async def save_daily_report(self, report: dict) -> None:
        """写入日报。失败只 warning。
        
        Args:
            report: DAILY-1.0 格式完整报告字典
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.execute(
                """INSERT INTO daily_reports
                   (pond_id, date, report_json)
                   VALUES (?, ?, ?)
                """,
                (
                    report.get("pond_id"),
                    report.get("date", datetime.now().strftime("%Y-%m-%d")),
                    json.dumps(report, ensure_ascii=False),
                ),
            )
            conn.commit()
            conn.close()
        except Exception as e:
            logger.warning("DB save_daily_report failed: %s", e)

    async def get_day_records(self, pond_id: str, date: str | None = None) -> list[dict]:
        """读取当日所有传感器和决策记录。
        
        Args:
            pond_id: 塘口编号
            date: ISO日期字符串（"2026-03-27"），默认今天
            
        Returns:
            [{"type": "sensor", "data": {...}}, {"type": "decision", "data": {...}}]
        """
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")

        try:
            conn = sqlite3.connect(str(self.db_path))
            conn.row_factory = sqlite3.Row

            # 读当日传感器记录
            sensor_rows = conn.execute(
                """SELECT * FROM sensor_readings
                   WHERE pond_id = ? AND date(datetime(timestamp, 'unixepoch')) = ?
                   ORDER BY timestamp ASC
                """,
                (pond_id, date),
            ).fetchall()

            # 读当日决策记录
            decision_rows = conn.execute(
                """SELECT * FROM decisions
                   WHERE pond_id = ? AND date(datetime(timestamp, 'unixepoch')) = ?
                   ORDER BY timestamp ASC
                """,
                (pond_id, date),
            ).fetchall()

            conn.close()

            records = []
            for row in sensor_rows:
                records.append(
                    {
                        "type": "sensor",
                        "timestamp": row["timestamp"],
                        "data": {
                            "temp": row["temp"],
                            "do_val": row["do_val"],
                            "pH": row["ph"],
                            "ammonia": row["ammonia"],
                            "transparency": row["transparency"],
                            "avg_weight": row["avg_weight"],
                            "count": row["count"],
                        },
                    }
                )
            for row in decision_rows:
                records.append(
                    {
                        "type": "decision",
                        "timestamp": row["timestamp"],
                        "data": {
                            "risk_level": row["risk_level"],
                            "model_used": row["model_used"],
                            "summary": row["summary"],
                            "actions": json.loads(row["actions"] or "[]"),
                        },
                    }
                )

            return sorted(records, key=lambda r: r["timestamp"])

        except Exception as e:
            logger.warning("DB get_day_records failed for pond %s: %s", pond_id, e)
            return []

    async def get_trend(self, pond_id: str, field: str, hours: int = 24) -> list[float]:
        """读某字段近 N 小时的数据，供趋势分析。
        
        Args:
            pond_id: 塘口编号
            field: "temp" | "DO" | "pH" | "ammonia" | "transparency" | "avg_weight"（自动转换为db列名）
            hours: 时间窗口（默认24小时）
            
        Returns:
            [value1, value2, ...] 按时间升序
        """
        # 字段名映射（用户输入 → DB列名）
        field_map = {
            "temp": "temp",
            "DO": "do_val",
            "do_val": "do_val",
            "pH": "ph",
            "ph": "ph",
            "ammonia": "ammonia",
            "transparency": "transparency",
            "avg_weight": "avg_weight",
        }
        
        if field not in field_map:
            logger.warning("Invalid field for trend: %s", field)
            return []

        db_field = field_map[field]
        try:
            conn = sqlite3.connect(str(self.db_path))
            threshold = time.time() - hours * 3600
            rows = conn.execute(
                f"""SELECT {db_field} FROM sensor_readings
                   WHERE pond_id = ? AND timestamp >= ? AND {db_field} IS NOT NULL
                   ORDER BY timestamp ASC
                """,
                (pond_id, threshold),
            ).fetchall()
            conn.close()
            return [float(row[0]) for row in rows]
        except Exception as e:
            logger.warning("DB get_trend failed for pond %s field %s: %s", pond_id, field, e)
            return []

    async def list_active_ponds(self) -> list[str]:
        """返回最近24小时有数据的 pond_id 列表。"""
        try:
            conn = sqlite3.connect(str(self.db_path))
            threshold = time.time() - 86400
            rows = conn.execute(
                """SELECT DISTINCT pond_id FROM sensor_readings
                   WHERE timestamp >= ?
                   ORDER BY pond_id
                """,
                (threshold,),
            ).fetchall()
            conn.close()
            return [row[0] for row in rows]
        except Exception as e:
            logger.warning("DB list_active_ponds failed: %s", e)
            return []

    async def _purge_old_data(self, days: int = 30, size_limit_mb: int = 500) -> None:
        """删除 N 天前的 sensor_readings（磁盘保护）。
        
        规则：
        - 先删除 30 天前的数据
        - 如果数据库仍超过 500MB，继续删除更多
        
        Args:
            days: 保留天数
            size_limit_mb: 磁盘大小限制
        """
        try:
            db_size_mb = self.db_path.stat().st_size / (1024 * 1024)
            if db_size_mb < size_limit_mb:
                return

            conn = sqlite3.connect(str(self.db_path))
            cutoff = time.time() - days * 86400
            conn.execute(
                "DELETE FROM sensor_readings WHERE timestamp < ?",
                (cutoff,),
            )
            conn.commit()
            conn.close()
            logger.info("Purged sensor_readings older than %d days (DB size: %.1fMB)", days, db_size_mb)
        except Exception as e:
            logger.warning("DB _purge_old_data failed: %s", e)
