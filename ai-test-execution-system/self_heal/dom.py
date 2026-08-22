"""Round 2 只支持课程页实际使用的两个 CSS locator 形式。"""

from __future__ import annotations

import re
from html.parser import HTMLParser
from typing import Dict, List


class _AttributeCollector(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.nodes: List[Dict[str, str]] = []

    def handle_starttag(self, _tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.nodes.append({key: value or "" for key, value in attrs})


def matching_node_count(page_source: str, locator: Dict[str, str]) -> int:
    """返回当前 DOM 的精确匹配数；拒绝不在本课范围内的 selector。"""
    if locator.get("using") != "css selector":
        raise ValueError("Round 2 Policy 只允许 css selector locator。")
    selector = locator.get("value", "")
    by_id = re.fullmatch(r"#([A-Za-z][A-Za-z0-9_-]*)", selector)
    by_testid = re.fullmatch(r"\[data-testid=['\"]([A-Za-z][A-Za-z0-9_-]*)['\"]\]", selector)
    if by_id:
        key, wanted = "id", by_id.group(1)
    elif by_testid:
        key, wanted = "data-testid", by_testid.group(1)
    else:
        raise ValueError("Round 2 不接受未审查的 CSS selector：{0}".format(selector))
    parser = _AttributeCollector()
    parser.feed(page_source)
    return sum(node.get(key) == wanted for node in parser.nodes)
