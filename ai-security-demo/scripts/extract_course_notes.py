"""从用户指定 Bento HTML 中提取逐页讲师备注及可复核映射。"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path

EXPECTED_SHA256 = "a845dbbbf3a0b979327640c62484d582cd248a1adc53e2d75bacee6aed43865f"
DEMO = {
    17: ("A", "1 规则检查 → 2 离线辅助识别 → 3 人工修正误报 → 4 脱敏预览 → 5 人工确认进入下一步；自动演示停在人工核对前。"),
    18: ("A 回顾", "不点 Demo 按钮；用讲师口头回顾误报修正、脱敏预览和人工确认的顺序，不展示具体结果截图。"),
    30: ("B", "正常只读 → 注入污染文档 → 故障注入执行 → 安全模式执行同一提案；比较授权、状态与审计。"),
    45: ("C", "加载 AI 使用记录与制度 → 规则分析 → 离线辅助解释 → 原文证据核查 → 人工认定 → 下载候选问题 JSON。"),
    46: ("C 回顾", "不点 Demo 按钮；讲解规则命中、AI 推测、人工核实和最终认定的证据阶梯。"),
    54: ("D", "查看合成日志 → 运行确定性规则 → 离线 AI 分析 → 打开原始日志人工核查 → 导出四栏 JSON。"),
    55: ("D 回顾", "不点 Demo 按钮；按已证事实、AI 推测、待核查事项、建议动作四栏解释来源和授权要求。"),
}


class Text(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        value = " ".join(data.split())
        if value:
            self.parts.append(value)


def plain(fragment: str) -> str:
    parser = Text()
    parser.feed(fragment or "")
    return " ".join(parser.parts)


def main() -> None:
    cli = argparse.ArgumentParser()
    cli.add_argument("--source", type=Path, default=Path("/Users/yanbo/Downloads/人工智能安全保障能力提升_全课件_V4.bento.html"))
    cli.add_argument("--notes", type=Path, default=Path("evidence/course-source/notes.json"))
    cli.add_argument("--mapping", type=Path, default=Path("DEMO_COURSE_MAPPING.md"))
    args = cli.parse_args()
    raw = args.source.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXPECTED_SHA256:
        raise SystemExit(f"课件 SHA256 不符：{digest}")
    source = raw.decode("utf-8")
    match = re.search(r'<script[^>]*id=["\']bento-doc["\'][^>]*>(.*?)</script>', source, re.DOTALL)
    if not match:
        raise SystemExit("找不到 script#bento-doc")
    document = json.loads(html.unescape(match.group(1)))
    slides = document.get("slides", [])
    if len(slides) != 62:
        raise SystemExit(f"预期 62 页，实际 {len(slides)} 页")
    records: list[dict[str, object]] = []
    for page, slide in enumerate(slides, 1):
        title = next((plain(item.get("html", "")) for item in slide.get("elements", []) if item.get("role") == "title"), "")
        note = slide.get("notes", "")
        paragraphs = re.findall(r"<p\b[^>]*>(.*?)</p>", note, re.DOTALL)
        sections = [plain(p) for p in paragraphs]
        actions = [text for text in sections if "讲师动作" in text]
        focus = [text for text in sections if "讲述重点" in text]
        turn = [text for text in sections if "转场" in text]
        records.append({
            "page": page,
            "slide_id": slide.get("id", ""),
            "title": slide.get("name", ""),
            "visual_title": title,
            "speaker_action": actions[0] if actions else "讲师备注未单列‘讲师动作’。",
            "teaching_focus": focus[0] if focus else "本页无单列讲述重点。",
            "transition": turn[0] if turn else "",
            "notes_html": note,
        })
    args.notes.parent.mkdir(parents=True, exist_ok=True)
    args.notes.write_text(json.dumps({"source": str(args.source), "sha256": digest, "slide_count": 62, "slides": records}, ensure_ascii=False, indent=2) + "\n")

    lines = [
        "# 定稿课件逐页 Demo 映射",
        "",
        f"源文件：`{args.source}`  ",
        f"SHA256：`{digest}`；`script#bento-doc` 中共 62 页。原始讲师备注逐页抽取到忽略目录 `evidence/course-source/notes.json`。",
        "",
        "此表按备注记录逐页编号、稳定 slide ID、页面名、讲师动作和演示入口。未标为 Demo 的页面属于讲授、讨论、提问或转场；备注没有要求现场操作时不人为分配按钮。",
        "",
        "| 页 | slideID | 标题 | 讲师动作（备注摘录） | Demo 按钮或无 Demo 理由 |",
        "|---:|---|---|---|---|",
    ]
    for record in records:
        page = int(record["page"])
        action = str(record["speaker_action"])
        action = re.sub(r"^讲师动作\s*[：:]\s*", "", action)
        action = action.replace("|", "\\|")
        if page in DEMO:
            demo, buttons = DEMO[page]
            mapping = f"**{demo}**：{buttons}"
        else:
            section = "A" if page < 21 else "B" if page < 39 else "C" if page < 51 else "D"
            focus = re.sub(r"^讲述重点\s*[：:]\s*", "", str(record["teaching_focus"]))
            focus = focus.replace("|", "\\|")
            summary = focus[:72] + ("…" if len(focus) > 72 else "")
            mapping = f"无现场 Demo：本页讲解重点为“{summary}”；按备注讲授，不要求点击 Demo {section} 按钮。"
        title = str(record["title"]).replace("|", "\\|")
        lines.append(f"| {page} | `{record['slide_id']}` | {title} | {action} | {mapping} |")
    lines += [
        "",
        "## 重点页的实现对应与差异",
        "",
        "- 第 17 页 `l1-13`：原备注要求规则检查、AI 辅助识别、解释风险原因、人工修正一处误报/漏检、脱敏预览、日志及人工确认。Demo A 现提供规则识别、固定离线辅助识别误报（金额 `128000 元` 被误报为个人信息）、逐项证据修正、本地脱敏预览和显式人工确认；自动复演停在人工步骤前。日志包含各动作记录。",
        "- 第 18 页 `l1-14`：回顾顺序和责任，不展示具体演示结果；对应 Demo A 的人工核对和确认流程。",
        "- 第 30 页 `l2-09`：对应 Demo B 污染文档和安全后端授权链。备注中四工具/登录/摘要讲法与当前固定只读身份、读取与审批两类工具，以及状态查询展示不完全逐字一致；课堂以固定身份替代登录、比较读取/审批两类工具体现最小权限，读取后的状态即为摘要，并在讲师剧本明确说明这项教学适配。B 已按既有 Board 事实 Human 接受，本集成不修改其核心实现。",
        "- 第 45 页 `l3-06`：对应 Demo C 的规则、离线解释、原始证据核查、人工认定和候选 JSON 下载。",
        "- 第 46 页 `l3-07`：对应 Demo C 回顾证据阶梯；回顾不重复点击 Demo。",
        "- 第 54 页 `l4-03`：对应 Demo D 合成日志、规则聚合、AI 推测、人工核查和四栏导出。",
        "- 第 55 页 `l4-04`：对应 Demo D 四栏回顾；不把历史截图或建议动作说成现场处置。",
        "",
        "讲师可按 `DEMO_REHEARSAL.md` 中建议顺序 A → B → C → D 彩排；页面入口由每页唯一导航提供。",
        "",
    ]
    args.mapping.write_text("\n".join(lines))
    print(json.dumps({"sha256": digest, "slides": len(records), "notes": str(args.notes), "mapping": str(args.mapping)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
