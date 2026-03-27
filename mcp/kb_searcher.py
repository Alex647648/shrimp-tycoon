"""虾塘大亨 · 知识库检索器

职责：加载 crayfish_kb.md，提供关键词检索接口。
约束（AGENT_CONSTRAINTS.md）：
- §1.2：MCP 工具层无状态，只读，无副作用
- §2.4：幂等，无 DB 写入，超时≤5s
- §1.3：文件 ≤250 行，函数 ≤60 行
- §3.2：类名 PascalCase
"""

import re
import logging
from pathlib import Path

logger = logging.getLogger("kb_searcher")

KB_PATH = Path(__file__).parent.parent / "knowledge-base" / "crayfish_kb.md"


class KBSearcher:
    """克氏原螯虾养殖知识库检索器。

    加载 crayfish_kb.md，按条目解析，支持关键词检索。
    每个条目包含：id、类别、标题、内容正文。
    """

    def __init__(self, kb_path: str | Path | None = None):
        """初始化并加载知识库。

        Args:
            kb_path: 知识库 md 文件路径，默认读取 knowledge-base/crayfish_kb.md
        """
        self._kb_path = Path(kb_path) if kb_path else KB_PATH
        self._entries: list[dict] = []
        self._load_kb()

    def _load_kb(self) -> None:
        """解析 md 文件，按 ### KB-XXX 切分为知识条目列表。"""
        try:
            text = self._kb_path.read_text(encoding="utf-8")
            self._entries = self._parse_entries(text)
            logger.info("KBSearcher loaded %d entries from %s", len(self._entries), self._kb_path)
        except FileNotFoundError:
            logger.error("KB file not found: %s", self._kb_path)
            self._entries = []
        except Exception as e:
            logger.error("KB load failed: %s", e)
            self._entries = []

    def _parse_entries(self, text: str) -> list[dict]:
        """将 md 文本按 ### KB-XXX 标题切分为结构化条目列表。

        Returns:
            每条记录: {"id": "KB-A01", "category": "水质管理", "title": "...", "content": "..."}
        """
        entries: list[dict] = []
        # 按 "### KB-" 分割每个条目
        sections = re.split(r"(?=^### KB-)", text, flags=re.MULTILINE)

        for section in sections:
            section = section.strip()
            if not section.startswith("### KB-"):
                continue

            # 第一行：### KB-A01 [类别] 标题
            first_line = section.split("\n")[0]
            match = re.match(
                r"### (KB-[A-Z]\d+)\s+\[([^\]]+)\]\s+(.+)", first_line
            )
            if not match:
                continue

            kb_id = match.group(1)
            category = match.group(2)
            title = match.group(3).strip()
            content = section  # 保留完整原文用于匹配

            entries.append(
                {
                    "id": kb_id,
                    "category": category,
                    "title": title,
                    "content": content,
                }
            )

        return entries

    def _score_entry(self, entry: dict, keywords: list[str]) -> int:
        """计算条目与关键词列表的匹配得分（出现次数累加）。

        Args:
            entry: 知识条目字典
            keywords: 小写关键词列表

        Returns:
            命中次数之和
        """
        # 合并所有可搜索文本（小写）
        searchable = (
            entry["id"]
            + " "
            + entry["category"]
            + " "
            + entry["title"]
            + " "
            + entry["content"]
        ).lower()

        score = 0
        for kw in keywords:
            score += searchable.count(kw)
        return score

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        """关键词检索知识库，返回最相关的 top_k 条目。

        算法：
        1. 将 query 按空格分词，转小写
        2. 对每条目计算关键词命中次数
        3. 按得分降序，返回前 top_k 条（过滤得分为 0 的）

        Args:
            query: 检索查询字符串（中文/英文均可）
            top_k: 返回结果数量上限，默认 5

        Returns:
            [{"id": "KB-A01", "category": "...", "title": "...", "content": "..."}]
            按相关性降序排列，最多 top_k 条
        """
        if not query or not self._entries:
            return []

        # 分词：按空格 + 常见分隔符切分
        raw_tokens = re.split(r"[\s，。、；：,./\\]+", query.strip())
        keywords = [t.lower() for t in raw_tokens if t]

        if not keywords:
            return []

        # 评分
        scored = [
            (self._score_entry(entry, keywords), entry)
            for entry in self._entries
        ]

        # 过滤零分，按得分降序
        scored = [(s, e) for s, e in scored if s > 0]
        scored.sort(key=lambda x: x[0], reverse=True)

        return [entry for _, entry in scored[:top_k]]

    def get_entry(self, kb_id: str) -> dict | None:
        """按 ID 精确获取知识条目（如 "KB-A05"）。

        Args:
            kb_id: 知识条目 ID

        Returns:
            条目字典，未找到返回 None
        """
        for entry in self._entries:
            if entry["id"] == kb_id:
                return entry
        return None

    @property
    def total_entries(self) -> int:
        """已加载的知识条目总数。"""
        return len(self._entries)
