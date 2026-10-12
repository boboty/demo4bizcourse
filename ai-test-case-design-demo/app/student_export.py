"""从学生输入资产导出两套独立的学员材料包（HTML + TXT），严格不含讲师答案。

每套材料包 = 一个可离线阅读、一键复制的 HTML + 一个便于整体复制提示词的 TXT。
数据只来自 `practice/student/*.json` 及其 `input_files`，提示词由 `app.ailab` 本地拼装；
`practice/instructor/` 在构建阶段从不参与内容生成，只在导出前作为“指纹”做反向泄漏扫描。
"""
import json
import re
import zipfile
from collections import namedtuple
from html import escape
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

from app import ailab
from app.assets import DEFAULT_ROOT, load
from app.selection import SUPPORTED_BUDGETS

Tag = namedtuple("Tag", "kind label")
Code = namedtuple("Code", "text")

INSTRUCTOR_PREFIX = "practice/instructor/"
# 即使被误写进 input_files 也不得导出：讲师参考、冻结 AI 输出、可执行用例、V1.1 目标答案。
DENY_PREFIXES = (INSTRUCTOR_PREFIX, "frozen/", "cases/")
DENY_FILES = frozenset({"history/v1_1_additions.json"})
FORBIDDEN_TOKENS = ("practice/instructor", "instructor", "REFERENCE")
MIN_FINGERPRINT = 10
IDENTIFIER = re.compile(r"^[A-Za-z0-9_.\-]+$")

PACKAGES = {
    3: {
        "slug": "demo3-scenario-selection",
        "task": "practice/student/demo3_scenario_design.json",
        "title": "Demo 3 · 在预算内选场景",
        "subtitle": "悦选商城售后退款 V1.0：41 条候选场景，最多选 15 条",
        "steps": [
            "读完下方“任务”“约束”“交付物”，明确要产出什么。",
            "按需阅读“材料”：需求、结构化分析、业务规则、候选场景。",
            "在“提示词”中选预算（本练习约束为 15），点击复制，粘贴到全新的 AI 对话。",
            "对 AI 的回答逐条核对：规则覆盖是否真实、证据状态是否被混淆；按“交付物”整理成自己的方案。",
        ],
        "forbidden": ("49.00", "85.13", "F10", "F20", "P11", "P31", "P41", "极速退款", "V1.1"),
    },
    6: {
        "slug": "demo6-incremental-update",
        "task": "practice/student/demo6_incremental_update.json",
        "title": "Demo 6 · V1.0→V1.1 测试资产增量更新",
        "subtitle": "沿“变更→规则→场景→用例”依赖链，推导保留 / 修改 / 作废 / 新增，并选出不超过 25 条回归用例",
        "steps": [
            "读完下方“任务”“约束”“交付物”，明确要产出什么。",
            "按需阅读“材料”：V1.0 / V1.1 需求、财务规范、已验证历史资产、规则变化。",
            "在“提示词”中复制提示词 A 到全新的 AI 对话，得到处置建议；再用提示词 B 追问回归用例选择。",
            "核对 AI 的回答：每条处置是否沿规则 ID 依赖推导，是否把“来源更新”误判成“行为变化”，是否重建了本可保留的资产。",
        ],
        "forbidden": (),
    },
}

CONSTRAINT_LABEL = {
    "max_selected_scenarios": "入选场景上限",
    "allowed_sources": "只能使用的资料",
    "finance_spec_available": "可使用独立财务规范",
    "no_claim_of_full_coverage": "不得声称完全覆盖",
    "max_regression_cases": "回归用例上限",
    "baseline_is_independently_validated": "历史基线已独立验证",
    "use_dependency_ids": "必须沿规则/场景/用例 ID 依赖推导",
    "preserve_verified_financial_expected_values": "保留已验证的财务预期值",
}
DELIVERABLE_LABEL = {
    "selected_scenario_ids": "入选场景", "rule_coverage": "规则覆盖", "manual_additions": "人工补回",
    "open_questions": "待确认问题", "rule_to_asset_trace": "规则→资产追溯", "migration_actions": "迁移动作",
    "regression_selection": "回归选择", "provenance_changes": "来源变更",
}
DIMENSION_LABEL = {"payment": "支付方式", "promotion": "优惠", "after_sales_type": "售后类型",
                   "order_state": "订单状态", "membership": "会员等级"}
EVIDENCE_KIND = {"fact": "fact", "inference": "inference", "missing": "missing", "conflict": "conflict",
                 "independent_source": "indep"}


class ExportError(ValueError):
    """导出输入不合规，或在输出里发现讲师答案。"""


# ───────────────────────── 块模型：每块同时产出 HTML 与纯文本 ─────────────────────────

Block = Tuple[str, str]


def _cell(value: Any) -> Tuple[str, str]:
    if isinstance(value, Tag):
        return '<span class="tag t-%s">%s</span>' % (value.kind, escape(value.label)), value.label
    if isinstance(value, Code):
        return "<code>%s</code>" % escape(value.text), value.text
    if isinstance(value, (list, tuple)):
        text = "、".join(str(item) for item in value)
        return escape(text), text
    text = "" if value is None else str(value)
    return escape(text), text


def _compact(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":"))


def _evidence(status: str) -> Tag:
    return Tag(EVIDENCE_KIND.get(status, "badge"), ailab.EVIDENCE_LABEL.get(status, status))


def _yes_no(value: Any) -> str:
    return ("是" if value else "否") if isinstance(value, bool) else value


def para(text: str) -> Block:
    return "<p>%s</p>" % escape(text), text


def subhead(text: str) -> Block:
    return "<h3>%s</h3>" % escape(text), "\n" + text


def bullets(items: Iterable[Any]) -> Block:
    cells = [_cell(item) for item in items]
    html = "<ul>%s</ul>" % "".join("<li>%s</li>" % h for h, _ in cells)
    return html, "\n".join("- " + t for _, t in cells)


def kv(pairs: Iterable[Tuple[str, Any]]) -> Block:
    rows = [(label, _cell(value)) for label, value in pairs]
    html = '<dl class="kv">%s</dl>' % "".join("<dt>%s</dt><dd>%s</dd>" % (escape(k), v[0]) for k, v in rows)
    return html, "\n".join("%s：%s" % (k, v[1]) for k, v in rows)


def table(headers: List[str], rows: Iterable[List[Any]]) -> Block:
    cooked = [[_cell(c) for c in row] for row in rows]
    head = "".join("<th>%s</th>" % escape(h) for h in headers)
    body = "".join("<tr>%s</tr>" % "".join("<td>%s</td>" % h for h, _ in row) for row in cooked)
    html = '<div class="table-wrap"><table><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>' % (head, body)
    lines = ["｜".join(headers)] + ["｜".join(t.replace("\n", " ") for _, t in row) for row in cooked]
    return html, "\n".join(lines)


# ───────────────────────── 材料渲染：每个输入文件 → (标题, 块列表) ─────────────────────────

def _prd(doc: Dict[str, Any]) -> Tuple[str, List[Block]]:
    blocks = [kv([("文档", "%s（%s）" % (doc["title"], doc["document_id"])), ("版本", doc["version"]),
                  ("状态", doc["status"]), ("说明", doc.get("source_note", ""))]),
              subhead("需求段落"), table(["段落ID", "内容"], [[p["source_id"], p["text"]] for p in doc["paragraphs"]])]
    if doc.get("open_questions"):
        blocks += [subhead("待确认问题"),
                   table(["问题ID", "问题", "关联段落", "状态"],
                         [[q["question_id"], q["text"], q["source_ids"], q["status"]] for q in doc["open_questions"]])]
    return "需求说明 V%s" % doc["version"], blocks


def _analysis(doc: Dict[str, Any]) -> Tuple[str, List[Block]]:
    def named(rows: List[Dict[str, Any]], key: str = "name") -> List[List[Any]]:
        return [[r["id"], r[key], _evidence(r["evidence_status"]), r.get("source_ids", []), r.get("note", "")] for r in rows]
    head = ["ID", "名称", "证据状态", "来源", "备注"]
    blocks = [kv([("状态图例", "；".join("%s=%s" % (ailab.EVIDENCE_LABEL.get(k, k), v)
                                       for k, v in doc["status_legend"].items()))]),
              subhead("角色"), table(head, named(doc["roles"])),
              subhead("输入"), table(head, named(doc["inputs"])),
              subhead("外部依赖"), table(head, named(doc["external_dependencies"])),
              subhead("流程与状态"), kv([("流程", " → ".join(doc["flow"])), ("状态", "、".join(doc["states"]))]),
              subhead("风险"),
              table(["风险ID", "描述", "证据状态", "关联规则", "影响", "概率", "难发现", "风险分"],
                    [[r["risk_id"], r["statement"], _evidence(r["evidence_status"]), r["rule_ids"], r["impact"],
                      r["probability"], r["hard_to_detect"], r["impact"] * r["probability"] * r["hard_to_detect"]]
                     for r in doc["risks"]]),
              subhead("待回答问题"),
              table(["问题ID", "问题", "证据状态", "来源"],
                    [[q["id"], q["question"], _evidence(q["evidence_status"]), q["source_ids"]] for q in doc["questions"]])]
    return "结构化分析", blocks


def _rules_v10(doc: Dict[str, Any]) -> Tuple[str, List[Block]]:
    rows = [[r["rule_id"], r["statement"], _evidence(r["evidence_status"]), r["source_ids"]] for r in doc["rules"]]
    return "业务规则 V%s（含证据状态）" % doc["version"], [table(["规则ID", "规则内容", "证据状态", "来源"], rows)]


def _candidates(doc: Dict[str, Any]) -> Tuple[str, List[Block]]:
    # 不展示 note：其中 SC36 的备注直接写明了“应人工补回”，其余几条只是重复“待确认”状态。
    dims = [[DIMENSION_LABEL.get(k, k), v] for k, v in doc["dimensions"].items()]
    product = doc["theoretical_product"]
    rows = []
    for s in doc["scenarios"]:
        r = s["risk"]
        rows.append([s["scenario_id"], s["title"], s["stage"], s["category"], s["rule_ids"], Code(_compact(s["conditions"])),
                     r["impact"], r["probability"], r["hard_to_detect"], r["impact"] * r["probability"] * r["hard_to_detect"],
                     s["execution_cost"], Tag("inference" if s["validity"] == "needs_confirmation" else "badge",
                                              ailab.VALIDITY_LABEL.get(s["validity"], s["validity"]))])
    blocks = [para("风险分 = 影响 × 发生概率 × 难发现度；执行成本越大越贵；“待确认”表示场景预期依赖尚未确认的规则。"),
              subhead("场景维度"), table(["维度", "取值"], dims),
              kv([("理论组合", "%s = %s 种" % (product["expression"], product["count"])),
                  ("无效组合示例", product["invalid_combinations"])]),
              subhead("候选场景（共 %d 条，ID 不连续，以清单为准）" % len(doc["scenarios"])),
              table(["场景ID", "场景", "阶段", "类别", "关联规则", "条件", "影响", "概率", "难发现", "风险分", "成本", "状态"], rows)]
    return "候选场景（V1.0）", blocks


def _finance(doc: Dict[str, Any]) -> Tuple[str, List[Block]]:
    ex, cum = doc["worked_example"], doc["cumulative_example"]
    blocks = [kv([("文档", "%s（%s）" % (doc["title"], doc["document_id"])), ("版本", doc["version"]), ("状态", doc["status"])]),
              subhead("财务规则"),
              table(["规则ID", "内容", "来源", "证据状态"],
                    [[r["rule_id"], r["text"], r["source_ids"], _evidence(r["evidence_status"])] for r in doc["rules"]]),
              subhead("示例：经典订单退 B"),
              table(["SKU", "原价"], [[i["sku"], i["gross"]] for i in ex["items"]]),
              kv([("原价合计", ex["gross_total"]), ("原优惠", ex["original_discount"]), ("实付", ex["paid"]),
                  ("退货SKU", ex["return_sku"]), ("剩余原价", ex["remaining_gross"]),
                  ("重算后优惠", ex["recalculated_discount"]), ("应退款", ex["refund"]),
                  ("比例分摊假设金额", ex["assumed_proportional_refund"]), ("差额", ex["difference"]),
                  ("计算过程", ex["calculation"])]),
              subhead("示例：累计退款"),
              kv([("退款顺序", cum["refund_order"]), ("累计应退", cum["cumulative_total"]), ("说明", cum["explanation"])])]
    return "独立财务规范", blocks


def _baseline(doc: Dict[str, Any]) -> Tuple[str, List[Block]]:
    # 不展示 baseline_status（如 legacy_unconditional_gate）：它直接暗示该场景的处置。
    scenes = [[s["scenario_id"], s["title"], s["rule_ids"], Code(_compact(s["conditions"]))] for s in doc["scenarios"]]
    cases = [[c["case_id"], c["title"], c["kind"], c["rule_ids"], c.get("source_rule_ids", ""), c["scenario_ids"],
              Code(_compact(c["input"])), Code(_compact(c["expected"])), c["validation_status"],
              c.get("assertion_scope", ""), c.get("derived_from_case_id", "")] for c in doc["cases"]]
    blocks = [kv([("基线", doc["baseline_id"]), ("业务版本", doc["business_version"]),
                  ("验证状态", doc["validation_status"]), ("来源文档", doc["business_sources"]), ("说明", doc["note"])]),
              subhead("历史场景（%d 条）" % len(scenes)), table(["场景ID", "标题", "关联规则", "条件"], scenes),
              subhead("历史用例（%d 条，均已独立验证）" % len(cases)),
              table(["用例ID", "标题", "类型", "用例规则", "来源规则", "场景", "输入", "预期", "验证状态", "断言范围", "派生自"], cases),
              subhead("已排除的无效资产"),
              table(["资产ID", "排除原因"], [[a["artifact_id"], a["reason"]] for a in doc["excluded_unverified_artifacts"]])]
    return "已验证历史资产（V1.0 基线）", blocks


def _rule_diff(doc: Dict[str, Any]) -> Tuple[str, List[Block]]:
    # 不展示 migration_criteria（逐项写明了处置推导）与 dependency_contract.target_additions（指向 V1.1 目标答案文件）。
    contract = [(k, v) for k, v in doc["dependency_contract"].items() if k != "target_additions"]
    blocks = [kv([("基线版本", doc["base_version"]), ("目标版本", doc["target_version"])]),
              subhead("规则变化"),
              table(["变更ID", "类型", "来源段落", "受影响规则", "摘要"],
                    [[d["change_id"], d["change_type"], d["source_id"], d["affected_rule_ids"], d["summary"]]
                     for d in doc["rule_diff"]]),
              subhead("依赖契约"), kv(contract),
              subhead("四种处置的定义"), kv(list(doc["action_definitions"].items())),
              subhead("回归预算"), kv(list(doc["regression_budget"].items()))]
    return "规则变化（Rule Diff）", blocks


def _prd_v11(doc: Dict[str, Any]) -> Tuple[str, List[Block]]:
    blocks = [kv([("文档", "%s（%s）" % (doc["title"], doc["document_id"])), ("版本", doc["version"]),
                  ("状态", doc["status"]), ("基线版本", doc["base_version"])]),
              subhead("三项变更"),
              table(["变更ID", "规则", "来源段落", "变更原文"],
                    [[c["change_id"], c["rule_id"], c["source_id"], c["text"]] for c in doc["changes"]]),
              subhead("新增段落"), table(["段落ID", "内容"], [[p["source_id"], p["text"]] for p in doc["paragraphs_added"]]),
              subhead("段落替换 / 扩展关系"),
              table(["新段落", "关系", "旧段落", "范围"],
                    [[r["new_source_id"], "替换" if "replaces" in r else "扩展", r.get("replaces", r.get("extends")),
                      r.get("scope", "")] for r in doc["paragraph_replacements"]])]
    return "需求说明 V%s（变更）" % doc["version"], blocks


def _rules_v11(doc: Dict[str, Any]) -> Tuple[str, List[Block]]:
    rows = []
    for r in doc["rules"]:
        versions = r.get("versioned_statement") or {}
        rows.append([r["rule_id"], r["statement"], _evidence(r["evidence_status"]), r["source_ids"], r["versions"],
                     "；".join("V%s：%s" % (v, t) for v, t in versions.items()),
                     r.get("superseded_in", "")])
    return "业务规则 V%s（含版本差异）" % doc["version"], [
        table(["规则ID", "规则内容", "证据状态", "来源", "适用版本", "各版本表述", "被取代"], rows)]


def _generic_renderer(doc: Any) -> Tuple[str, List[Block]]:
    text = json.dumps(doc, ensure_ascii=False, indent=2)
    return "原始材料", [("<pre>%s</pre>" % escape(text), text)]


RENDERERS = {
    "prd/prd_v1_0.json": _prd, "prd/prd_v1_1.json": _prd_v11, "business/analysis.json": _analysis,
    "business/rules_v1_0.json": _rules_v10, "business/rules.json": _rules_v11,
    "scenarios/candidates_v1_0.json": _candidates, "finance/after_sales_funds.json": _finance,
    "history/v1_0_validated_baseline.json": _baseline, "history/v1_1_rule_diff.json": _rule_diff,
}


# ───────────────────────── 输入守卫与泄漏扫描 ─────────────────────────

def _check_input_path(relative: str) -> None:
    normalized = Path(relative).as_posix()
    if ".." in Path(normalized).parts or normalized.startswith("/"):
        raise ExportError("输入路径越界：%s" % relative)
    if normalized in DENY_FILES or normalized.startswith(DENY_PREFIXES):
        raise ExportError("拒绝导出非学生输入资产：%s" % relative)


def _strings(value: Any) -> Iterable[str]:
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        if value and all(isinstance(i, str) for i in value) and len(value) >= 5:
            for sep in (", ", ",", "、", " ", "，"):
                yield sep.join(value)
        for item in value:
            yield from _strings(item)


def instructor_fingerprints(root: Path) -> Set[str]:
    """讲师参考里的长文本与长清单。纯标识符（规则ID、枚举名）是公共词汇，不计为指纹；自然语言一律计入，
    即使它已混进学生输入——那正是要拦住的泄漏。"""
    folder = root / INSTRUCTOR_PREFIX
    found = set()  # type: Set[str]
    if not folder.is_dir():
        return found
    for path in sorted(folder.glob("*.json")):
        with path.open("r", encoding="utf-8") as stream:
            for text in _strings(json.load(stream)):
                if len(text) >= MIN_FINGERPRINT and not IDENTIFIER.match(text):
                    found.add(text)
    return found


def assert_clean(outputs: Dict[str, str], fingerprints: Set[str], extra_forbidden: Iterable[str] = ()) -> None:
    for name, text in outputs.items():
        for token in tuple(FORBIDDEN_TOKENS) + tuple(extra_forbidden):
            if token in text:
                raise ExportError("%s 含禁用内容：%r" % (name, token))
        for fingerprint in fingerprints:
            if fingerprint in text:
                raise ExportError("%s 含讲师参考内容：%r" % (name, fingerprint[:40]))


# ───────────────────────── 页面 ─────────────────────────

CSS = """
:root{--bg:#f6f7f9;--panel:#fff;--ink:#1c2430;--muted:#5d6878;--line:#d9dee6;--accent:#1f5fbf;--accent-ink:#fff;--soft:#eaf1fc;
--fact:#d6f1e2;--fact-ink:#14583a;--inference:#fbebc2;--inference-ink:#6b4a05;--missing:#f9d7da;--missing-ink:#7a1f2a;--indep:#dde6fb;--indep-ink:#24437f;--badge:#e8ebf0;--badge-ink:#3a4452;--code:#eef1f5}
@media(prefers-color-scheme:dark){:root{--bg:#10151d;--panel:#171e29;--ink:#e8edf4;--muted:#a3afc0;--line:#2e3a4b;--accent:#6aa5f5;--accent-ink:#0c1522;--soft:#1b2b44;
--fact:#17402f;--fact-ink:#a5ecc7;--inference:#4a3a12;--inference-ink:#f6dc8c;--missing:#4e2228;--missing-ink:#ffbfc5;--indep:#1f3158;--indep-ink:#b8cdfa;--badge:#262f3d;--badge-ink:#c8d2e0;--code:#1d2532}}
*{box-sizing:border-box}[hidden]{display:none!important}html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 -apple-system,"PingFang SC","Noto Sans CJK SC","Microsoft YaHei",sans-serif}
.wrap{max-width:1120px;margin:0 auto;padding:0 20px 56px}
header.hero{padding:34px 0 18px}.eyebrow{margin:0 0 4px;color:var(--muted);font-size:14px;letter-spacing:.04em}
h1{margin:0;font-size:30px;line-height:1.3}.sub{margin:6px 0 0;color:var(--muted);font-size:17px}
nav.toc{position:sticky;top:0;z-index:3;background:var(--bg);border-bottom:1px solid var(--line);padding:10px 0;display:flex;gap:6px 8px;flex-wrap:wrap}
nav.toc a{color:var(--ink);text-decoration:none;border:1px solid var(--line);background:var(--panel);border-radius:999px;padding:3px 12px;font-size:14px}
nav.toc a:hover{border-color:var(--accent);color:var(--accent)}
section{background:var(--panel);border:1px solid var(--line);border-radius:12px;padding:20px 24px;margin:20px 0;scroll-margin-top:64px}
section>.head{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:10px}
h2{margin:0;font-size:21px}h3{margin:20px 0 8px;font-size:16px;color:var(--muted)}
p{margin:8px 0}ul{margin:8px 0;padding-left:22px}ol{padding-left:22px}
.task{background:var(--soft);border-left:5px solid var(--accent);border-radius:6px;padding:12px 16px;font-size:17px}
button.copy{font:inherit;font-size:14px;color:var(--accent-ink);background:var(--accent);border:0;border-radius:7px;padding:6px 14px;cursor:pointer;white-space:nowrap}
button.copy:hover{filter:brightness(1.08)}button.copy:focus-visible,summary:focus-visible,a:focus-visible{outline:3px solid #f5a623;outline-offset:2px}
button.copy.ok{background:#1f8a58}button.copy.err{background:#b3372f}
dl.kv{display:grid;grid-template-columns:max-content 1fr;gap:5px 18px;margin:8px 0}dl.kv dt{color:var(--muted)}dl.kv dd{margin:0}
.table-wrap{overflow:auto;max-height:70vh;border:1px solid var(--line);border-radius:8px;margin:8px 0}
table{border-collapse:collapse;width:100%;font-size:14px;line-height:1.5}
th,td{padding:7px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}
th{position:sticky;top:0;background:var(--badge);white-space:nowrap}tr:last-child td{border-bottom:0}td:first-child{white-space:nowrap;font-weight:600}
code,pre{font-family:ui-monospace,SFMono-Regular,Menlo,Consolas,monospace}code{background:var(--code);border-radius:4px;padding:1px 5px;font-size:12.5px;word-break:break-all}
pre{background:var(--code);border-radius:8px;padding:14px 16px;overflow:auto;font-size:13.5px;line-height:1.6;white-space:pre-wrap;overflow-wrap:anywhere;max-height:60vh;margin:10px 0 0}
.tag{display:inline-block;border-radius:999px;padding:0 9px;font-size:12.5px;font-weight:700;white-space:nowrap}
.t-fact{background:var(--fact);color:var(--fact-ink)}.t-inference{background:var(--inference);color:var(--inference-ink)}
.t-missing,.t-conflict{background:var(--missing);color:var(--missing-ink)}.t-indep{background:var(--indep);color:var(--indep-ink)}.t-badge{background:var(--badge);color:var(--badge-ink)}
details.prompt{border:1px solid var(--line);border-radius:10px;padding:10px 14px;margin:12px 0}
details.prompt>summary{cursor:pointer;font-weight:700;display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;list-style-position:inside}
details.prompt .row{display:flex;gap:10px;align-items:center;flex-wrap:wrap;margin-top:8px}
.note{color:var(--muted);font-size:14px}.recommended{border-color:var(--accent)}
footer{color:var(--muted);font-size:13.5px;border-top:1px solid var(--line);padding-top:14px;margin-top:28px}
@media(max-width:640px){section{padding:16px}h1{font-size:24px}dl.kv{grid-template-columns:1fr}dl.kv dt{margin-top:6px}}
@media print{nav.toc,button.copy{display:none}body{background:#fff}section{break-inside:avoid-page;border-color:#bbb}.table-wrap{max-height:none;overflow:visible}pre{max-height:none}}
"""

JS = """
(function(){
  function legacy(text){
    var ta=document.createElement('textarea');ta.value=text;ta.setAttribute('readonly','');
    ta.style.cssText='position:fixed;top:0;left:0;opacity:0';document.body.appendChild(ta);ta.select();
    var ok=false;try{ok=document.execCommand('copy');}catch(e){}
    document.body.removeChild(ta);return ok;
  }
  function copy(text){
    if(navigator.clipboard&&window.isSecureContext){
      return navigator.clipboard.writeText(text).then(function(){return true;},function(){return legacy(text);});
    }
    return Promise.resolve(legacy(text));
  }
  function flash(btn,cls,msg){
    var old=btn.getAttribute('data-label')||btn.textContent;btn.setAttribute('data-label',old);
    btn.textContent=msg;btn.classList.add(cls);
    setTimeout(function(){btn.textContent=old;btn.classList.remove(cls);},2200);
  }
  document.addEventListener('click',function(ev){
    var btn=ev.target.closest('[data-copy-from]');if(!btn)return;
    ev.preventDefault();ev.stopPropagation();
    var src=document.getElementById(btn.getAttribute('data-copy-from'));if(!src)return;
    var text=('value' in src)?src.value:src.textContent;
    copy(text).then(function(ok){
      if(ok){flash(btn,'ok','已复制 ✓');return;}
      if(src.tagName==='PRE'){var r=document.createRange();r.selectNodeContents(src);var s=window.getSelection();s.removeAllRanges();s.addRange(r);
        flash(btn,'err','已选中，请按 ⌘C / Ctrl+C');}
      else{flash(btn,'err','复制失败，请改用 prompts.txt');}
    });
  });
})();
"""


def _copy_button(target: str, label: str = "复制") -> str:
    return '<button type="button" class="copy" data-copy-from="%s">%s</button>' % (target, escape(label))


def _section(sid: str, title: str, blocks: List[Block], copy_label: str = "复制本节文本") -> str:
    """纯文本放入隐藏 textarea 供复制按钮读取。"""
    body = "".join(h for h, _ in blocks)
    text = title + "\n" + "\n".join(t for _, t in blocks)
    return ('<section id="%s"><div class="head"><h2>%s</h2>%s</div>%s'
            '<textarea id="txt-%s" hidden readonly aria-hidden="true" tabindex="-1">%s</textarea></section>'
            % (sid, escape(title), _copy_button("txt-" + sid, copy_label), body, sid, escape(text)))


def _task_text(task: Dict[str, Any]) -> str:
    lines = ["练习：%s（%s）" % (task["exercise_id"], task["course_lesson"]), "", "【任务】", task["student_prompt"], "", "【约束】"]
    lines += ["- %s：%s" % (CONSTRAINT_LABEL.get(k, k), _cell(_yes_no(v))[1]) for k, v in task["constraints"].items()]
    lines += ["", "【交付物】"]
    lines += ["- %s：%s" % (DELIVERABLE_LABEL.get(k, k), v) for k, v in task["deliverable_shape"].items()]
    return "\n".join(lines)


def _prompt_cards(prompts: List[Dict[str, str]]) -> str:
    cards = []
    for index, item in enumerate(prompts):
        pid = "prompt-%s" % item["key"]
        cards.append(
            '<details class="prompt%s"%s><summary><span>%s</span>%s</summary>'
            '<p class="note">%s</p><pre id="%s">%s</pre></details>'
            % (" recommended" if item.get("recommended") else "", " open" if index == 0 else "", escape(item["label"]),
               _copy_button(pid, "复制提示词"), escape(item["note"]), pid, escape(item["text"])))
    return "".join(cards)


def build_task_prompt(task: Dict[str, Any]) -> str:
    """练习任务说明（追加提问用）：逐字取自学生任务文件，不加任何额外判断。"""
    return _task_text(task)


# ───────────────────────── 提示词 ─────────────────────────

def _prompts(number: int, task: Dict[str, Any]) -> List[Dict[str, str]]:
    result = []
    if number == 3:
        limit = task["constraints"]["max_selected_scenarios"]
        for budget in SUPPORTED_BUDGETS:
            built = ailab.build_prompt("d3_select", budget)
            fits = budget == limit
            result.append({
                "key": "a%d" % budget, "label": "提示词 A · 预算 %d 条%s" % (budget, "（本练习约束）" if fits else "（对比用）"),
                "note": "自带需求、规则、41 条候选场景，直接粘贴到全新的 AI 对话即可。" + ("" if fits else "本练习的入选上限是 %d，此档仅用于观察预算变化。" % limit),
                "text": built["prompt"], "recommended": fits})
    else:
        built = ailab.build_prompt("d6_impact")
        result.append({"key": "a", "label": "提示词 A · 需求变更影响分析（V1.0 → V1.1）",
                       "note": "自带 V1.0 基线、财务规范、V1.1 三项变更、历史场景与全部历史用例；粘贴到全新的 AI 对话。",
                       "text": built["prompt"], "recommended": True})
    result.append({"key": "task", "label": "提示词 B · 练习任务说明（在 A 的回答之后追问）",
                   "note": "逐字取自练习任务；如需 AI 参与，请先发提示词 A，再在同一对话里发这一段。",
                   "text": build_task_prompt(task), "recommended": False})
    return result


def _txt(number: int, title: str, subtitle: str, prompts: List[Dict[str, str]]) -> str:
    bar = "=" * 64
    lines = [bar, "%s · 提示词（纯文本，可整体复制）" % title, subtitle, bar, "",
             "使用方法：每个提示词位于 BEGIN / END 两行之间，复制两行之间的全部内容，粘贴到全新的 AI 对话。",
             "对应的阅读版材料见同目录 student-package.html。", ""]
    for item in prompts:
        lines += ["─" * 64, "【%s】" % item["label"], item["note"], "", "----- BEGIN -----", item["text"], "----- END -----", ""]
    return "\n".join(lines).rstrip() + "\n"


# ───────────────────────── 组装 ─────────────────────────

def build_package(number: int, root: Optional[Path] = None) -> Dict[str, str]:
    """生成单个材料包的全部文件内容（文件名 → 文本）。"""
    if number not in PACKAGES:
        raise ExportError("只提供 Demo 3 与 Demo 6 的学员材料包")
    meta = PACKAGES[number]
    base = Path(root) if root is not None else DEFAULT_ROOT
    _check_input_path(meta["task"])
    task = load(meta["task"], base)
    for relative in task["input_files"]:
        _check_input_path(relative)

    constraints = table(["约束", "要求"], [[CONSTRAINT_LABEL.get(k, k), _yes_no(v)] for k, v in task["constraints"].items()])
    deliverables = table(["交付物", "要求"], [[DELIVERABLE_LABEL.get(k, k), v] for k, v in task["deliverable_shape"].items()])
    task_blocks = [('<p class="task">%s</p>' % escape(task["student_prompt"]), task["student_prompt"]),
                   subhead("约束"), constraints, subhead("交付物"), deliverables]
    steps = "<ol>%s</ol>" % "".join("<li>%s</li>" % escape(s) for s in meta["steps"])
    prompts = _prompts(number, task)
    # (锚点, 目录标签, section HTML)
    sections = [
        ("start", "怎么用", '<section id="start"><div class="head"><h2>怎么用这份材料</h2></div>%s</section>' % steps),
        ("task", "任务", _section("task", "任务", task_blocks, "复制任务说明")),
        ("prompts", "提示词",
         '<section id="prompts"><div class="head"><h2>提示词</h2></div><p class="note">提示词已内嵌全部所需数据，不要求 AI 读取任何文件。'
         "浏览器禁止自动复制时会自动选中文本，按 ⌘C / Ctrl+C 即可；也可使用同目录 prompts.txt。</p>%s</section>" % _prompt_cards(prompts)),
    ]
    for index, relative in enumerate(task["input_files"], 1):
        title, blocks = RENDERERS.get(relative, _generic_renderer)(load(relative, base))
        sections.append(("m%d" % index, "材料 %d" % index, _section("m%d" % index, "材料 %d · %s" % (index, title), blocks)))

    toc = "".join('<a href="#%s">%s</a>' % (anchor, escape(label)) for anchor, label, _ in sections)
    sources = [meta["task"]] + list(task["input_files"])
    footer = ("<footer>本材料包由学生输入资产自动导出，内容来源：%s；提示词由本地业务资产拼装。"
              "纯文本版见 prompts.txt。本案例为虚构课堂案例，不作为真实商城售后政策。</footer>"
              % "、".join("<code>%s</code>" % escape(s) for s in sources))
    page = ('<!DOCTYPE html>\n<html lang="zh-CN"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            "<title>%s · 学员材料包</title><style>%s</style></head><body><div class=\"wrap\">"
            '<header class="hero"><p class="eyebrow">AI赋能业务测试用例设计与优化 · 悦选商城 · %s</p><h1>%s</h1><p class="sub">%s</p></header>'
            '<nav class="toc" aria-label="目录">%s</nav>%s%s</div><script>%s</script></body></html>\n'
            % (escape(meta["title"]), CSS, escape(task["exercise_id"]), escape(meta["title"]), escape(meta["subtitle"]),
               toc, "".join(html for _, _, html in sections), footer, JS))
    return {"student-package.html": page, "prompts.txt": _txt(number, meta["title"], meta["subtitle"], prompts)}


def export_all(out_dir: Path, root: Optional[Path] = None) -> Dict[str, List[Path]]:
    """构建并校验两套材料包；全部通过泄漏扫描后才写盘（每包：文件夹 + 同名 ZIP）。"""
    base = Path(root) if root is not None else DEFAULT_ROOT
    built = {number: build_package(number, base) for number in PACKAGES}
    fingerprints = instructor_fingerprints(base)
    for number, files in built.items():
        assert_clean({"demo%d/%s" % (number, k): v for k, v in files.items()}, fingerprints, PACKAGES[number]["forbidden"])
    written = {}  # type: Dict[str, List[Path]]
    for number, files in built.items():
        slug = PACKAGES[number]["slug"]
        folder = Path(out_dir) / slug
        folder.mkdir(parents=True, exist_ok=True)
        written[slug] = []
        for name, text in files.items():
            target = folder / name
            target.write_text(text, encoding="utf-8")
            written[slug].append(target)
        written[slug].append(write_zip(Path(out_dir) / (slug + ".zip"), slug, files))
    return written


def write_zip(target: Path, slug: str, files: Dict[str, str]) -> Path:
    """每包一个独立 ZIP：只含 HTML 与 TXT，外层带同名文件夹；固定时间戳与权限，重复导出字节一致。"""
    with zipfile.ZipFile(str(target), "w", zipfile.ZIP_DEFLATED) as archive:
        for name in sorted(files):
            info = zipfile.ZipInfo("%s/%s" % (slug, name), date_time=(2020, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, files[name].encode("utf-8"))
    return target
