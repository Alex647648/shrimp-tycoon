"""虾塘大亨 · PondDB 单元测试

测试覆盖：
- test_init_creates_tables     初始化建表
- test_save_and_read_reading   传感器数据写入与查询
- test_save_decision           决策记录写入
- test_get_day_records         当日记录聚合查询
- test_list_active_ponds       活跃塘口列表

约束（AGENT_CONSTRAINTS.md §6.2）：
- 所有测试使用临时 SQLite 文件（tmpdir），不依赖真实 DB
- 无外部 API 调用，无网络依赖
"""

import asyncio
import json
import sqlite3
import time
from pathlib import Path
import pytest

# 引入被测模块
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from backend.db import PondDB


# ── 工具函数 ──────────────────────────────────────────────────────────────

def _make_db(tmp_path: Path) -> PondDB:
    """创建使用临时路径的 PondDB 实例。"""
    return PondDB(db_path=tmp_path / "test_pond.db")


def _make_sensor(pond_id: str = "A1", ts: float | None = None) -> dict:
    """构造一条标准 SDP-1.0 传感器数据。"""
    return {
        "pond_id": pond_id,
        "timestamp": ts or time.time(),
        "temp": 26.5,
        "DO": 6.2,
        "pH": 7.8,
        "ammonia": 0.05,
        "transparency": 45,
        "avg_weight": 12.3,
        "count": 5000,
        "dead_shrimp": False,
        "molt_peak": False,
        "read_failed": False,
    }


def _make_decision(pond_id: str = "A1", ts: float | None = None) -> dict:
    """构造一条标准 DECISION-1.0 决策数据。"""
    return {
        "pond_id": pond_id,
        "timestamp": ts or time.time(),
        "risk_level": 2,
        "model_used": "rule_engine",
        "summary": "水质正常，建议继续观察",
        "actions": ["维持当前投喂量", "检查增氧机"],
        "feishu_sent": False,
        "feishu_message_id": None,
    }


# ── 测试用例 ──────────────────────────────────────────────────────────────

def test_init_creates_tables(tmp_path):
    """test_init_creates_tables: init() 应创建三张核心表。"""
    db = _make_db(tmp_path)
    asyncio.run(db.init())

    conn = sqlite3.connect(str(db.db_path))
    tables = {row[0] for row in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()}
    conn.close()

    assert "sensor_readings" in tables, "sensor_readings 表应存在"
    assert "decisions" in tables, "decisions 表应存在"
    assert "daily_reports" in tables, "daily_reports 表应存在"


def test_save_and_read_reading(tmp_path):
    """test_save_and_read_reading: 传感器数据写入后可以从 DB 直接读取。"""
    db = _make_db(tmp_path)
    asyncio.run(db.init())

    sensor = _make_sensor("B2")
    asyncio.run(db.save_reading("B2", sensor))

    conn = sqlite3.connect(str(db.db_path))
    row = conn.execute(
        "SELECT pond_id, temp, do_val, ph FROM sensor_readings WHERE pond_id='B2'"
    ).fetchone()
    conn.close()

    assert row is not None, "应能查到写入的传感器记录"
    assert row[0] == "B2"
    assert abs(row[1] - 26.5) < 0.01, "temp 应正确写入"
    assert abs(row[2] - 6.2) < 0.01, "DO 应正确写入"
    assert abs(row[3] - 7.8) < 0.01, "pH 应正确写入"


def test_save_decision(tmp_path):
    """test_save_decision: 决策记录写入后可从 DB 直接读取，actions 应为 JSON 列表。"""
    db = _make_db(tmp_path)
    asyncio.run(db.init())

    decision = _make_decision("C3")
    asyncio.run(db.save_decision("C3", decision))

    conn = sqlite3.connect(str(db.db_path))
    row = conn.execute(
        "SELECT pond_id, risk_level, model_used, actions FROM decisions WHERE pond_id='C3'"
    ).fetchone()
    conn.close()

    assert row is not None, "应能查到写入的决策记录"
    assert row[0] == "C3"
    assert row[1] == 2, "risk_level 应正确写入"
    assert row[2] == "rule_engine", "model_used 应正确写入"

    actions = json.loads(row[3])
    assert isinstance(actions, list), "actions 应为 JSON 列表"
    assert len(actions) == 2, "actions 应有两条"


def test_get_day_records(tmp_path):
    """test_get_day_records: 当日记录应包含 sensor 和 decision，按时间升序。"""
    db = _make_db(tmp_path)
    asyncio.run(db.init())

    # 写入今天的数据
    ts_base = time.time()
    sensor = _make_sensor("D4", ts=ts_base)
    decision = _make_decision("D4", ts=ts_base + 1)
    asyncio.run(db.save_reading("D4", sensor))
    asyncio.run(db.save_decision("D4", decision))

    records = asyncio.run(db.get_day_records("D4"))

    assert len(records) >= 2, "应至少有 sensor 和 decision 各一条"

    types = [r["type"] for r in records]
    assert "sensor" in types, "应包含 sensor 类型记录"
    assert "decision" in types, "应包含 decision 类型记录"

    # 验证按时间升序
    timestamps = [r["timestamp"] for r in records]
    assert timestamps == sorted(timestamps), "记录应按时间升序排列"


def test_list_active_ponds(tmp_path):
    """test_list_active_ponds: 写入多塘数据后，list_active_ponds 应返回所有活跃塘口。"""
    db = _make_db(tmp_path)
    asyncio.run(db.init())

    # 写入三个塘的数据
    for pond_id in ["E1", "E2", "E3"]:
        asyncio.run(db.save_reading(pond_id, _make_sensor(pond_id)))

    active = asyncio.run(db.list_active_ponds())

    assert "E1" in active, "E1 应在活跃塘口列表中"
    assert "E2" in active, "E2 应在活跃塘口列表中"
    assert "E3" in active, "E3 应在活跃塘口列表中"
    assert len(active) >= 3, "应至少有三个活跃塘口"
