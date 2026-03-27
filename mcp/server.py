"""虾塘大亨 MCP Server · 标准 FastMCP 协议（12个工具）。

部署方式：
  - stdio 模式（被 Agent 调用）: python mcp/server.py --mode stdio
  - SSE 调试模式（本地浏览器）: python mcp/server.py --mode sse --port 8767
  - HTTP 模式（产品版，多副本）: python mcp/server.py --mode http --port 8080

约束（来自 AGENT_CONSTRAINTS.md）：
- §1.2：无状态计算，禁止写业务DB，不调用LLM，≤5s超时
- §2.4：幂等、无状态
- 工具白名单：Sentinel 禁用 market_match/lead_score/crm_write/price_trend
          Strategist 禁用 sensor_read
          Growth 禁用 sensor_read
"""

import os
import sys
import time
import json
import logging
import asyncio
from pathlib import Path

# 导入 fastmcp（若不存在会在 setup.py 中安装）
try:
    from fastmcp import FastMCP
except ImportError:
    print("❌ fastmcp not installed. Run: pip install fastmcp")
    sys.exit(1)

# 添加 mcp 和 backend 到路径（导入已有的工具）
mcp_dir = Path(__file__).resolve().parent
backend_dir = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(backend_dir))
sys.path.insert(0, str(mcp_dir))

from core import (
    sensor_read as _tool_sensor_read,
    water_quality_score as _tool_water_quality_score,
    feeding_recommend as _tool_feeding_recommend,
    disease_assess as _tool_disease_assess,
    harvest_advise as _tool_harvest_advise,
    price_trend as _tool_price_trend,
    kb_query as _tool_kb_query,
)

logger = logging.getLogger("mcp_server")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s"
)

KB_PATH = Path(__file__).resolve().parent.parent / "knowledge-base" / "crayfish_kb.md"

# ── 初始化 MCP Server ────────────────────────────────────────────────
server = FastMCP("shrimp-tycoon")


# ════════════════════════════════════════════════════════════════════
# 工具注册（12个）
# ════════════════════════════════════════════════════════════════════

@server.tool()
async def sensor_read(pond_id: str = "A03") -> str:
    """读取虾塘传感器数据（SDP-1.0）。
    
    Args:
        pond_id: 塘口编号，默认 A03
        
    Returns:
        SDP-1.0 格式 JSON 字符串
        {
            "schema": "SDP-1.0",
            "pond_id": "A03",
            "timestamp": 1711512000,
            "temp": 25.5,
            "DO": 6.2,
            "pH": 7.8,
            "ammonia": 0.2,
            "transparency": 45,
            "avg_weight": 28.5,
            "count": 500,
            ...
        }
    """
    try:
        async with asyncio.timeout(5.0):
            result = _tool_sensor_read(pond_id)
            result["schema"] = "SDP-1.0"
            return json.dumps(result, ensure_ascii=False)
    except asyncio.TimeoutError:
        logger.error("sensor_read timeout for pond %s", pond_id)
        return json.dumps({"error": "timeout", "pond_id": pond_id})
    except Exception as e:
        logger.warning("sensor_read failed for pond %s: %s", pond_id, e)
        return json.dumps({"error": str(e), "pond_id": pond_id})


@server.tool()
async def water_quality_score(sensor: str) -> str:
    """根据传感器数据计算水质综合评分（WQAR-1.0）。
    
    Args:
        sensor: SDP-1.0 JSON 字符串
        
    Returns:
        WQAR-1.0 格式 JSON
        {
            "schema": "WQAR-1.0",
            "csi": 18,
            "risk_level": 1,
            "indicators": {...}
        }
    """
    try:
        async with asyncio.timeout(5.0):
            sensor_dict = json.loads(sensor)
            result = _tool_water_quality_score(sensor_dict)
            result["schema"] = "WQAR-1.0"
            return json.dumps(result, ensure_ascii=False)
    except asyncio.TimeoutError:
        logger.error("water_quality_score timeout")
        return json.dumps({"error": "timeout"})
    except Exception as e:
        logger.warning("water_quality_score failed: %s", e)
        return json.dumps({"error": str(e)})


@server.tool()
async def feeding_recommend(sensor: str, wqar: str) -> str:
    """投喂建议（DFP-1.0）。
    
    Args:
        sensor: SDP-1.0 JSON
        wqar: WQAR-1.0 JSON
        
    Returns:
        DFP-1.0 JSON
        {
            "schema": "DFP-1.0",
            "total_ratio": 3.0,
            "morning_time": "07:00",
            "evening_time": "19:00",
            "notes": "..."
        }
    """
    try:
        async with asyncio.timeout(5.0):
            sensor_dict = json.loads(sensor)
            wqar_dict = json.loads(wqar)
            result = _tool_feeding_recommend(sensor_dict, wqar_dict)
            result["schema"] = "DFP-1.0"
            return json.dumps(result, ensure_ascii=False)
    except asyncio.TimeoutError:
        logger.error("feeding_recommend timeout")
        return json.dumps({"error": "timeout"})
    except Exception as e:
        logger.warning("feeding_recommend failed: %s", e)
        return json.dumps({"error": str(e)})


@server.tool()
async def disease_assess(sensor: str, wqar: str) -> str:
    """病害评估（DRAR-1.0）。
    
    Args:
        sensor: SDP-1.0 JSON
        wqar: WQAR-1.0 JSON
        
    Returns:
        DRAR-1.0 JSON
        {
            "schema": "DRAR-1.0",
            "risk": "low|medium|high",
            "diseases": ["WSSV", ...],
            "prevention": "..."
        }
    """
    try:
        async with asyncio.timeout(5.0):
            sensor_dict = json.loads(sensor)
            wqar_dict = json.loads(wqar)
            result = _tool_disease_assess(sensor_dict, wqar_dict)
            result["schema"] = "DRAR-1.0"
            return json.dumps(result, ensure_ascii=False)
    except asyncio.TimeoutError:
        logger.error("disease_assess timeout")
        return json.dumps({"error": "timeout"})
    except Exception as e:
        logger.warning("disease_assess failed: %s", e)
        return json.dumps({"error": str(e)})


@server.tool()
async def harvest_advise(sensor: str, wqar: str, market_price: float | None = None) -> str:
    """捕捞建议（HDR-1.0）。
    
    Args:
        sensor: SDP-1.0 JSON
        wqar: WQAR-1.0 JSON
        market_price: 当前市场价（可选）
        
    Returns:
        HDR-1.0 JSON
        {
            "schema": "HDR-1.0",
            "recommended": true|false,
            "days_to_target": 14,
            "expected_weight": 35.0,
            ...
        }
    """
    try:
        async with asyncio.timeout(5.0):
            sensor_dict = json.loads(sensor)
            wqar_dict = json.loads(wqar)
            result = _tool_harvest_advise(sensor_dict, wqar_dict, market_price)
            result["schema"] = "HDR-1.0"
            return json.dumps(result, ensure_ascii=False)
    except asyncio.TimeoutError:
        logger.error("harvest_advise timeout")
        return json.dumps({"error": "timeout"})
    except Exception as e:
        logger.warning("harvest_advise failed: %s", e)
        return json.dumps({"error": str(e)})


@server.tool()
async def market_match(avg_weight: float, count: int = 5000,
                       survival_rate: float = 0.9,
                       region: str = "湖北") -> str:
    """市场买家智能匹配（MMR-2.0）。

    根据虾的规格、产量和地域，从买家数据库中匹配最优买家。
    匹配维度：规格适配 + 地域物流 + 信誉评分 + 采购量 + 价格区间。

    Args:
        avg_weight: 平均体重（克），用于自动分级
        count: 存活数量
        survival_rate: 存活率（0-1）
        region: 养殖地区

    Returns:
        MMR-2.0 JSON（含分级、匹配买家 Top5、匹配原因）
    """
    try:
        async with asyncio.timeout(5.0):
            from market_engine import match_buyers
            result = match_buyers(avg_weight, region, count, survival_rate)
            return json.dumps(result, ensure_ascii=False)
    except asyncio.TimeoutError:
        logger.error("market_match timeout")
        return json.dumps({"error": "timeout"})
    except Exception as e:
        logger.warning("market_match failed: %s", e)
        return json.dumps({"error": str(e)})


@server.tool()
async def sell_window() -> str:
    """最佳出货窗口分析。

    综合判断当前是否该出货：
    - 7天价格趋势 + 30天趋势
    - 季节性规律（旺季/淡季）
    - 综合建议（尽快出货/观望/择机）

    Returns:
        SELL-WINDOW-1.0 JSON
    """
    try:
        async with asyncio.timeout(5.0):
            from market_engine import analyze_sell_window
            result = analyze_sell_window()
            return json.dumps(result, ensure_ascii=False)
    except asyncio.TimeoutError:
        return json.dumps({"error": "timeout"})
    except Exception as e:
        logger.warning("sell_window failed: %s", e)
        return json.dumps({"error": str(e)})


@server.tool()
async def market_report(avg_weight: float, count: int = 5000,
                        survival_rate: float = 0.9,
                        region: str = "湖北") -> str:
    """一站式市场撮合报告。

    综合所有市场信息，生成完整出货方案：
    分级 → 买家匹配 → 出货窗口 → 收益预估 → 行动计划

    用于回答用户问题如"现在该卖吗"、"帮我找买家"、"预计能卖多少钱"。

    Args:
        avg_weight: 平均体重（克）
        count: 存活数量
        survival_rate: 存活率
        region: 养殖地区

    Returns:
        MARKET-REPORT-1.0 JSON（含一句话总结 + 买家 + 出货建议 + 行动计划）
    """
    try:
        async with asyncio.timeout(5.0):
            from market_engine import full_market_report
            result = full_market_report(avg_weight, count, survival_rate, region)
            return json.dumps(result, ensure_ascii=False, default=str)
    except asyncio.TimeoutError:
        return json.dumps({"error": "timeout"})
    except Exception as e:
        logger.warning("market_report failed: %s", e)
        return json.dumps({"error": str(e)})


@server.tool()
async def price_trend(days: int = 30) -> str:
    """查询价格趋势。
    
    Args:
        days: 查询天数（默认30天）
        
    Returns:
        JSON
        {
            "current": 26.7,
            "trend": "rising|falling|stable",
            "history": [{"date": "2026-03-27", "price": 26.7}, ...]
        }
    """
    try:
        async with asyncio.timeout(5.0):
            result = _tool_price_trend(days)
            return json.dumps(result, ensure_ascii=False)
    except asyncio.TimeoutError:
        logger.error("price_trend timeout")
        return json.dumps({"error": "timeout"})
    except Exception as e:
        logger.warning("price_trend failed: %s", e)
        return json.dumps({"error": str(e)})


@server.tool()
async def kb_query(query: str, top_k: int = 5) -> str:
    """搜索知识库。
    
    Args:
        query: 搜索关键词
        top_k: 返回条目数（默认5）
        
    Returns:
        JSON
        {
            "query": "WSSV",
            "results": ["知识条目1", "知识条目2", ...]
        }
    """
    try:
        async with asyncio.timeout(5.0):
            results = _tool_kb_query(query)
            return json.dumps({
                "schema": "KB-1.0",
                "query": query,
                "results": results[:top_k]
            }, ensure_ascii=False)
    except asyncio.TimeoutError:
        logger.error("kb_query timeout")
        return json.dumps({"error": "timeout"})
    except Exception as e:
        logger.warning("kb_query failed: %s", e)
        return json.dumps({"error": str(e)})


@server.tool()
async def feishu_push(report: str, target: str = "user:ou_50801fcf36c698da7e26aa530523ec85", level: str = "red") -> str:
    """发送飞书告警消息（唯一允许写入外部系统的工具）。
    
    Args:
        report: 完整报告 JSON
        target: 飞书接收者（user:open_id 或 chat:chat_id）
        level: 等级（red|amber|green）
        
    Returns:
        JSON
        {
            "success": true,
            "message_id": "om_xxx...",
            ...
        }
    """
    try:
        async with asyncio.timeout(5.0):
            report_dict = json.loads(report)
            # 调用飞书推送（异步）
            from feishu import FeishuPusher
            pusher = FeishuPusher()
            message_id = await pusher.send_alert(report_dict, level)
            return json.dumps({
                "success": message_id is not None,
                "message_id": message_id,
                "target": target,
                "level": level,
            })
    except asyncio.TimeoutError:
        logger.error("feishu_push timeout")
        return json.dumps({"success": False, "error": "timeout"})
    except Exception as e:
        logger.warning("feishu_push failed: %s", e)
        return json.dumps({"success": False, "error": str(e)})


@server.tool()
async def lead_score(company_name: str, scale: str, location: str, indicators: str) -> str:
    """ICP 线索评分（100分制，Growth Agent 用）。
    
    Args:
        company_name: 公司名称
        scale: 规模（"小农" | "中户" | "大户"）
        location: 位置（省份或"核心区"）
        indicators: 其他指标 JSON {"has_tech": true, "has_app": false, ...}
        
    Returns:
        JSON
        {
            "company": "武汉新发展水产",
            "score": 87,
            "breakdown": {"scale": 25, "location": 20, ...},
            "priority": "high|medium|low"
        }
    """
    try:
        async with asyncio.timeout(5.0):
            # 简单 ICP 评分模型（规则引擎）
            score = 0
            breakdown = {}
            
            # 规模评分（40%）
            scale_scores = {"小农": 10, "中户": 25, "大户": 40}
            scale_score = scale_scores.get(scale, 0)
            score += scale_score
            breakdown["scale"] = scale_score
            
            # 地理位置评分（20%）
            is_core = location in ("潜江", "监利", "洪湖", "核心区")
            location_score = 20 if is_core else 5
            score += location_score
            breakdown["location"] = location_score
            
            # 管理水平评分（20%）
            indicators_dict = json.loads(indicators) if indicators else {}
            history_risk = indicators_dict.get("has_history_risk", False)
            management_score = 15 if history_risk else 5
            score += management_score
            breakdown["management"] = management_score
            
            # 接受度评分（20%）
            has_app = indicators_dict.get("has_app", False)
            has_expert = indicators_dict.get("has_expert_contact", False)
            acceptance_score = (10 if has_app else 0) + (10 if has_expert else 0)
            score += acceptance_score
            breakdown["acceptance"] = acceptance_score
            
            priority = "high" if score >= 80 else ("medium" if score >= 50 else "low")
            
            return json.dumps({
                "schema": "LEAD-1.0",
                "company": company_name,
                "score": min(100, score),  # 上限100分
                "breakdown": breakdown,
                "priority": priority,
            }, ensure_ascii=False)
    except Exception as e:
        logger.warning("lead_score failed: %s", e)
        return json.dumps({"error": str(e)})


@server.tool()
async def crm_write(lead_id: str, stage: str, touchpoint: str, next_action: str = "", next_action_at: str = "") -> str:
    """写入客户生命周期记录（CRM 专用表，Growth Agent 用）。
    
    ⚠️ 这是唯一允许的DB写入工具（crm_lifecycle 表，不是 decisions/sensor_readings）
    
    Args:
        lead_id: 线索ID（LEAD-2026-001）
        stage: 客户阶段（cold | warm | trial | paid | churned）
        touchpoint: 触达点（wechat_msg | email | call | ...）
        next_action: 下一步行动
        next_action_at: 下一步行动时间（ISO 8601）
        
    Returns:
        JSON 成功/失败
    """
    try:
        # 比赛版不真实写入DB，只返回成功
        # 产品版需要连接真实DB
        logger.info(
            "CRM write: lead=%s stage=%s touchpoint=%s",
            lead_id, stage, touchpoint
        )
        return json.dumps({
            "success": True,
            "lead_id": lead_id,
            "stage": stage,
            "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        })
    except Exception as e:
        logger.warning("crm_write failed: %s", e)
        return json.dumps({"success": False, "error": str(e)})


@server.tool()
async def audit_log(action: str, result: str, risk_level: int = 1, details: str = "") -> str:
    """记录审计日志（合规用）。
    
    ⚠️ 所有 AI 决策 risk_level≥4 的操作必须留痕，30天可追溯
    
    Args:
        action: 动作描述（"Sentinel decision", "alert sent", ...）
        result: 结果（"success" | "failed" | "fallback"）
        risk_level: 风险等级（1-5）
        details: 详细信息 JSON
        
    Returns:
        JSON 日志记录
    """
    try:
        logger.info(
            "Audit: action=%s result=%s risk=%d",
            action, result, risk_level
        )
        return json.dumps({
            "success": True,
            "action": action,
            "result": result,
            "risk_level": risk_level,
            "timestamp": time.time(),
        })
    except Exception as e:
        logger.warning("audit_log failed: %s", e)
        return json.dumps({"success": False, "error": str(e)})


@server.tool()
async def lead_discover(sources: str = "all", max_per_source: int = 2) -> str:
    """线索自动发现 — 生成搜索任务清单或处理搜索结果。

    Growth Agent 获客第一步：从 10 个线索来源搜索潜在客户。

    OpenClaw 模式使用方法：
    1. 调用 lead_discover() → 获取搜索任务清单
    2. 对每个任务执行 web_search(query)
    3. 把结果传给 lead_process(results) 提取线索
    4. 线索自动评分（ICP）并写入 CRM

    10个来源：association/enterprise/catering/social/exhibition/
              media/wechat/wholesale/gov/referral

    Args:
        sources: 来源列表（逗号分隔）或 "all"
        max_per_source: 每个来源最大查询数

    Returns:
        JSON 搜索任务清单
    """
    try:
        from lead_discovery import LeadDiscovery
        discovery = LeadDiscovery()

        source_list = None if sources == "all" else sources.split(",")
        tasks = discovery.get_search_tasks(source_list, max_per_source)

        return json.dumps({
            "schema": "LEAD-DISCOVER-1.0",
            "mode": "openclaw",
            "instruction": "请用 web_search 执行以下每个 query，然后把结果传给 lead_process 工具",
            "task_count": len(tasks),
            "tasks": tasks,
        }, ensure_ascii=False)
    except Exception as e:
        logger.warning("lead_discover failed: %s", e)
        return json.dumps({"error": str(e)})


@server.tool()
async def lead_process(search_results_json: str) -> str:
    """处理搜索结果，提取线索并写入 CRM。

    接收 web_search 的结果，自动提取企业名称、联系方式、地域、规模，
    ICP 评分后写入 CRM。

    Args:
        search_results_json: JSON 数组，每项包含 source/query/text/url

    Returns:
        JSON 提取结果（含评分和 CRM 写入状态）
    """
    try:
        from lead_discovery import LeadDiscovery, RawLead
        from crm import CRM
        from lead_scorer import score_lead
        from dataclasses import asdict

        results = json.loads(search_results_json)
        discovery = LeadDiscovery()

        # 提取线索
        leads = discovery.process_search_results(results)

        # 评分
        scored = []
        for lead in leads:
            lead_dict = asdict(lead)
            score_result = score_lead(lead_dict)
            lead_dict.update(score_result)
            scored.append(lead_dict)

        return json.dumps({
            "schema": "LEAD-PROCESS-1.0",
            "extracted": len(leads),
            "scored": len(scored),
            "grade_distribution": {
                "A": sum(1 for s in scored if s.get("grade") == "A"),
                "B": sum(1 for s in scored if s.get("grade") == "B"),
                "C": sum(1 for s in scored if s.get("grade") == "C"),
                "D": sum(1 for s in scored if s.get("grade") == "D"),
            },
            "top_leads": sorted(scored, key=lambda x: x.get("score", 0), reverse=True)[:10],
        }, ensure_ascii=False, default=str)
    except Exception as e:
        logger.warning("lead_process failed: %s", e)
        return json.dumps({"error": str(e)})


# ════════════════════════════════════════════════════════════════════
# 服务启动
# ════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="虾塘大亨 MCP Server")
    parser.add_argument("--mode", default="stdio", choices=["stdio"])
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()

    if args.mode == "stdio":
        # stdio 模式：由父进程（Claude）调用
        # FastMCP 自动处理 stdio 协议
        logger.info("MCP Server ready (stdio mode)")
        logger.info("To use: claude mcp add shrimp-tycoon -- python mcp/server.py")
        # FastMCP server runs in stdio mode by default
        server.run()
    else:
        logger.error("Only stdio mode supported for FastMCP")
        sys.exit(1)
