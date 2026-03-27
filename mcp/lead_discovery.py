"""线索自动发现引擎 — Growth Agent 获客入口。

10 个线索来源，按优先级排序：
1. 全国水产流通协会名录（公开数据）
2. 天眼查/企查查（企业信息）
3. 美团/饿了么（餐饮买家）
4. 抖音/快手养殖达人（短视频平台）
5. 展会名片 OCR（线下活动）
6. 行业媒体（水产前沿/中国水产等）
7. 微信公众号（水产自媒体）
8. 1688（批发供应链）
9. 农业农村部统计数据
10. 成交客户转介绍

实现方式：
- OpenClaw 模式：调用 web_search 工具，Claude 解析结果
- 独立模式：aiohttp 抓取公开页面，正则提取联系信息
"""

import re
import json
import time
import asyncio
import logging
from datetime import datetime
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)

# ── 搜索查询模板（10个来源 × 多个关键词）──

SEARCH_QUERIES = {
    "association": [
        "全国水产流通与加工协会 会员名录",
        "中国水产养殖协会 会员单位",
        "湖北省水产技术推广总站 合作养殖户",
    ],
    "enterprise": [
        "小龙虾养殖 企业 site:tianyancha.com",
        "水产养殖 合作社 潜江 OR 监利 OR 洪湖",
        "淡水虾 养殖场 注册资本",
    ],
    "catering": [
        "小龙虾 餐饮 供应商招募 site:meituan.com",
        "龙虾馆 批量采购 联系方式",
        "小龙虾 加盟 供应链",
    ],
    "social": [
        "小龙虾养殖 抖音达人 粉丝过万",
        "养虾技术 快手 养殖户",
        "水产养殖 短视频 博主",
    ],
    "exhibition": [
        "2026 水产养殖展会 参展商名录",
        "中国国际渔业博览会 展商",
        "潜江龙虾节 参展企业",
    ],
    "media": [
        "水产前沿 养殖户采访 联系",
        "中国水产 杂志 养殖案例",
        "水产养殖网 企业黄页",
    ],
    "wechat": [
        "小龙虾养殖 公众号 技术交流群",
        "水产人 微信群 养殖户",
    ],
    "wholesale": [
        "小龙虾 活虾 批发 site:1688.com",
        "淡水虾 养殖基地 供货 1688",
    ],
    "gov": [
        "农业农村部 小龙虾产业发展报告 养殖面积",
        "湖北省 小龙虾 养殖户 统计",
    ],
    "referral": [],  # 转介绍由 CRM 内部触发，不需要搜索
}

# ── 信息提取正则 ──

PHONE_RE = re.compile(r"1[3-9]\d{9}")
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
AREA_RE = re.compile(r"(\d+(?:\.\d+)?)\s*(?:亩|mu|公顷)")
REGION_RE = re.compile(
    r"(潜江|监利|洪湖|荆州|仙桃|武汉|岳阳|益阳|常德|盱眙|"
    r"合肥|芜湖|南京|上海|广州|深圳|长沙|成都|重庆)"
)


@dataclass
class RawLead:
    """从搜索结果中提取的原始线索。"""
    name: str
    source: str
    source_url: str = ""
    region: str = ""
    area_mu: float = 0.0
    phone: str = ""
    email: str = ""
    description: str = ""
    raw_text: str = ""
    discovered_at: str = ""


def extract_leads_from_text(text: str, source: str, url: str = "") -> list[RawLead]:
    """从搜索结果文本中提取线索信息。"""
    leads = []
    now = datetime.now().isoformat()

    # 按段落分割
    paragraphs = text.split("\n")
    current_lead = None

    for para in paragraphs:
        para = para.strip()
        if not para or len(para) < 10:
            continue

        phones = PHONE_RE.findall(para)
        emails = EMAIL_RE.findall(para)
        regions = REGION_RE.findall(para)
        areas = AREA_RE.findall(para)

        # 有联系方式或地域信息 → 可能是线索
        if phones or emails or (regions and ("养殖" in para or "水产" in para or "虾" in para)):
            lead = RawLead(
                name=_extract_name(para),
                source=source,
                source_url=url,
                region=regions[0] if regions else "",
                area_mu=float(areas[0]) if areas else 0.0,
                phone=phones[0] if phones else "",
                email=emails[0] if emails else "",
                description=para[:200],
                raw_text=para[:500],
                discovered_at=now,
            )
            leads.append(lead)

    return leads


def _extract_name(text: str) -> str:
    """从文本中提取可能的企业/个人名称。"""
    # 常见模式：XX养殖场 / XX水产 / XX合作社
    patterns = [
        re.compile(r"([\u4e00-\u9fa5]{2,10}(?:养殖场|水产|合作社|农业|渔业|水产品|龙虾|养殖))"),
        re.compile(r"([\u4e00-\u9fa5]{2,6}(?:公司|企业|基地|农场))"),
    ]
    for p in patterns:
        m = p.search(text)
        if m:
            return m.group(1)
    # fallback: 取前20字
    return text[:20].strip()


def deduplicate_leads(leads: list[RawLead], existing_names: set = None) -> list[RawLead]:
    """去重（按手机号+名称）。"""
    seen_phones = set()
    seen_names = existing_names or set()
    unique = []

    for lead in leads:
        if lead.phone and lead.phone in seen_phones:
            continue
        if lead.name in seen_names:
            continue
        if lead.phone:
            seen_phones.add(lead.phone)
        seen_names.add(lead.name)
        unique.append(lead)

    return unique


class LeadDiscovery:
    """线索发现引擎。

    两种运行模式：
    1. OpenClaw 模式：返回搜索查询列表，由 Claude 执行 web_search
    2. 独立模式：用 aiohttp 直接搜索（需配置搜索 API）
    """

    def __init__(self, crm=None):
        self.crm = crm

    def get_search_tasks(self, sources: list[str] = None,
                         max_per_source: int = 2) -> list[dict]:
        """生成搜索任务清单（OpenClaw 模式）。

        返回给 Claude，让 Claude 用 web_search 执行每个查询，
        然后把结果传回 process_search_results()。
        """
        if sources is None:
            sources = list(SEARCH_QUERIES.keys())

        tasks = []
        for src in sources:
            queries = SEARCH_QUERIES.get(src, [])
            for q in queries[:max_per_source]:
                tasks.append({
                    "source": src,
                    "query": q,
                    "priority": _source_priority(src),
                })

        # 按优先级排序
        tasks.sort(key=lambda t: t["priority"])
        return tasks

    def process_search_results(self, results: list[dict]) -> list[RawLead]:
        """处理搜索结果，提取线索。

        Args:
            results: [{"source": "...", "query": "...", "text": "...", "url": "..."}]

        Returns:
            去重后的线索列表
        """
        all_leads = []
        for r in results:
            text = r.get("text", "")
            source = r.get("source", "unknown")
            url = r.get("url", "")
            leads = extract_leads_from_text(text, source, url)
            all_leads.extend(leads)

        # 获取已有名称（去重用）
        existing = set()
        if self.crm:
            for lead in self.crm.list_leads(limit=500):
                existing.add(lead.get("name", ""))

        unique = deduplicate_leads(all_leads, existing)
        logger.info("Lead discovery: %d raw → %d unique (after dedup)", len(all_leads), len(unique))
        return unique

    def save_to_crm(self, leads: list[RawLead], scorer=None) -> list[dict]:
        """评分并写入 CRM。"""
        if not self.crm:
            logger.warning("No CRM configured, skipping save")
            return [asdict(l) for l in leads]

        from mcp.lead_scorer import score_lead

        saved = []
        for lead in leads:
            lead_dict = asdict(lead)
            score_result = score_lead(lead_dict)
            lead_dict.update(score_result)

            lead_id = self.crm.add_lead(lead_dict)
            lead_dict["id"] = lead_id
            saved.append(lead_dict)

        logger.info("Saved %d leads to CRM", len(saved))
        return saved

    async def run_full_cycle(self, search_fn=None,
                              sources: list[str] = None) -> dict:
        """完整获客周期（独立模式）。

        Args:
            search_fn: async def search(query: str) -> str
                       搜索函数，返回搜索结果文本
            sources: 指定来源列表

        Returns:
            {"tasks": N, "raw_leads": N, "unique_leads": N, "saved": N}
        """
        tasks = self.get_search_tasks(sources)

        if search_fn is None:
            # 无搜索函数，返回任务清单
            return {
                "mode": "openclaw",
                "message": "请用 web_search 执行以下搜索，结果传回 process_search_results()",
                "tasks": tasks,
                "task_count": len(tasks),
            }

        # 有搜索函数，执行搜索
        results = []
        for task in tasks:
            try:
                async with asyncio.timeout(10):
                    text = await search_fn(task["query"])
                    results.append({
                        "source": task["source"],
                        "query": task["query"],
                        "text": text,
                    })
            except Exception as e:
                logger.warning("Search failed for '%s': %s", task["query"], e)

        leads = self.process_search_results(results)
        saved = self.save_to_crm(leads)

        return {
            "mode": "standalone",
            "tasks_executed": len(results),
            "raw_leads": len(leads),
            "unique_leads": len(leads),
            "saved_to_crm": len(saved),
            "leads": saved[:10],  # 返回前10条预览
        }


def _source_priority(source: str) -> int:
    """来源优先级（1=最高）。"""
    order = {
        "association": 1, "enterprise": 2, "wholesale": 3,
        "catering": 4, "media": 5, "gov": 6,
        "social": 7, "wechat": 8, "exhibition": 9, "referral": 10,
    }
    return order.get(source, 99)
