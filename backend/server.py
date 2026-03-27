"""虾塘大亨 — FastAPI + WebSocket 主入口。启动：python backend/server.py (port 8766)"""

import asyncio
import json
import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware

sys_agent = str(Path(__file__).resolve().parent.parent / "agent")
if sys_agent not in __import__('sys').path:
    __import__('sys').path.insert(0, sys_agent)

from simulator import PondSimulator, compute_wqar, SCENARIOS
from sentinel import SentinelAgent
from feishu import FeishuPusher
from db import PondDB
from orchestrator import AgentOrchestrator
from memory import SentinelMemory

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("server")

PRICE_PATH = Path(__file__).resolve().parent.parent / "data" / "industry_based_price_data.json"
ALERT_MAP = {
    "do_drop": {"title": "🚨 溶解氧骤降告警", "message": "DO值降至2.1mg/L，低于安全阈值3.0mg/L", "actions": ["立即开启增氧机", "减少投饵量"]},
    "wssv": {"title": "🚨 疑似白斑病毒告警", "message": "发现死虾，疑似WSSV感染", "actions": ["立即隔离病虾", "采样送检", "全池消毒"]},
    "storm": {"title": "⚠️ 暴风雨水质突变", "message": "pH骤降至6.9，水温降至23.1°C", "actions": ["投放石灰调节pH", "关注水位变化"]},
    "molt": {"title": "ℹ️ 集中蜕壳期", "message": "检测到蜕壳高峰信号", "actions": ["减少投饵量30%", "避免换水惊扰"]},
    "harvest": {"title": "✅ 可捕捞通知", "message": "平均体重达41.2g，达到上市规格", "actions": ["联系收购商", "准备捕捞设备"]},
}


def _level_for_scenario(name: str) -> str:
    return {"do_drop": "red", "wssv": "red", "storm": "amber", "molt": "green", "harvest": "green"}.get(name, "amber")


app = FastAPI(title="虾塘大亨后端")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

feishu = FeishuPusher()
db = PondDB()
memory = SentinelMemory()
orchestrator = AgentOrchestrator(db=db, feishu_pusher=feishu, memory=memory)
sentinel = orchestrator.sentinel


@app.on_event("startup")
async def startup():
    await db.init()
    logger.info("DB initialized, orchestrator ready")


@app.get("/api/status")
async def api_status():
    return {"status": "ok", "agent_ready": True, "orchestrator": True}


@app.get("/api/health")
async def api_health():
    """系统健康检查（含三 Agent 状态 + 运行统计）。"""
    return orchestrator.health_check()


@app.get("/api/health/summary")
async def api_health_summary():
    """人可读状态摘要。"""
    return {"summary": orchestrator.status_summary()}


@app.post("/api/strategist/run")
async def api_strategist_run(pond_id: str = "A1", date: str = None):
    """手动触发 Strategist 日报。"""
    report = await orchestrator.run_daily_report(pond_id, date)
    return {"status": "ok", "report": report}


@app.post("/api/growth/run")
async def api_growth_run(date: str = None):
    """手动触发 Growth 周报。"""
    report = await orchestrator.run_weekly_report(date)
    return {"status": "ok", "report": report}


@app.get("/api/price")
async def api_price(days: int = Query(default=30)):
    data = json.loads(PRICE_PATH.read_text(encoding="utf-8"))
    prices = data["daily_prices"][-days:]
    current = data["current_price"]["medium"]
    history = [{"date": p["date"], "price": p["medium"]} for p in prices]
    if len(prices) >= 2:
        trend = "rising" if prices[-1]["medium"] > prices[0]["medium"] else ("falling" if prices[-1]["medium"] < prices[0]["medium"] else "stable")
    else:
        trend = "stable"
    return {"current": current, "trend": trend, "history": history}


@app.get("/api/roi")
async def api_roi():
    data = json.loads(PRICE_PATH.read_text(encoding="utf-8"))
    price = data["current_price"].get("large", 26.7)
    survival = 412
    avg_w = 35.0
    total_kg = round(survival * avg_w / 1000, 2)
    total_value = round(total_kg * price)
    return {
        "total_value": float(total_value),
        "roi_multiple": 2.5,
        "survival_count": survival,
        "avg_weight": avg_w,
        "total_kg": total_kg,
        "market_price": price,
        "saas_monthly_fee": 2000,
        "disease_savings": 8000,
    }


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    sim = PondSimulator()
    multiplier = 1
    logger.info("WebSocket client connected")

    async def tick_loop():
        while True:
            try:
                sensor, wqar = sim.tick(multiplier)
                await websocket.send_json({"type": "tick", "sensor": sensor, "wqar": wqar})
            except Exception:
                break
            await asyncio.sleep(5)

    task = asyncio.create_task(tick_loop())
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue
            msg_type = msg.get("type")
            if msg_type == "set_speed":
                multiplier = msg.get("multiplier", 1)
                logger.info("Speed set to %dx", multiplier)
            elif msg_type == "trigger":
                scenario = msg.get("scenario", "")
                push = msg.get("push_feishu", False)
                if scenario == "reset":
                    sim.reset()
                    sensor, wqar = sim.tick(multiplier)
                    await websocket.send_json({"type": "tick", "sensor": sensor, "wqar": wqar})
                    continue
                wqar_ov = sim.apply_scenario(scenario)
                sensor, wqar = sim.tick(multiplier)
                level = _level_for_scenario(scenario)
                alert_info = ALERT_MAP.get(scenario, {"title": scenario, "message": "", "actions": []})
                await websocket.send_json({
                    "type": "alert", "level": level,
                    "data": {"scenario": scenario, "title": alert_info["title"], "message": alert_info["message"], "actions": alert_info["actions"]},
                })
                try:
                    report = await sentinel.analyze(sensor, wqar, push_feishu=push)
                    await websocket.send_json({"type": "decision_ready", "data": report})
                    if report.get("feishu_sent") and report.get("feishu_message_id"):
                        await websocket.send_json({"type": "feishu_sent", "message_id": report["feishu_message_id"], "level": level})
                except Exception as e:
                    logger.error("Sentinel error: %s", e)
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
    finally:
        task.cancel()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=8766, reload=True)
